"""
CBOE vol-index daily history fetch + parquet store.
Downstream phases call load_vol_index(symbol) — they never import requests or touch a CSV path.
Bloomberg swap: replace _fetch_cboe_vol_index only.
"""
from __future__ import annotations

import io
import pathlib

import pandas as pd
import requests

from engine.config import DEFAULT_VOL_INDICES
from engine.data.store import atomic_to_parquet

_CBOE_VOL_URL = "https://cdn.cboe.com/api/global/us_indices/daily_prices/{SYM}_History.csv"
_HEADERS = {"User-Agent": "gamma-omm/3.5"}

STORE_DIR = pathlib.Path(__file__).resolve().parents[2] / "out" / "vol_index"


def _store_path(symbol: str) -> pathlib.Path:
    return STORE_DIR / f"{symbol}.parquet"


def _fetch_cboe_vol_index(symbol: str) -> pd.DataFrame | None:
    """Fetch CBOE vol-index daily history CSV. Returns None on 403 (discontinued) or network error."""
    try:
        url = _CBOE_VOL_URL.format(SYM=symbol)
        resp = requests.get(url, headers=_HEADERS, timeout=30)
        if resp.status_code == 403:
            print(f"[vol_index] {symbol}: 403 (discontinued), skipping")
            return None
        resp.raise_for_status()

        # CBOE returns full history; no pagination.
        df = pd.read_csv(io.StringIO(resp.text))
        df["DATE"] = pd.to_datetime(df["DATE"]).dt.date

        # Some CBOE indices (e.g., VVIX) have a single value column named after
        # the symbol instead of OHLC. Normalize to the OHLC schema.
        if "OPEN" not in df.columns and symbol in df.columns:
            val = pd.to_numeric(df[symbol], errors="coerce")
            df["OPEN"] = val
            df["HIGH"] = val
            df["LOW"] = val
            df["CLOSE"] = val
        else:
            df["OPEN"] = pd.to_numeric(df["OPEN"], errors="coerce")
            df["HIGH"] = pd.to_numeric(df["HIGH"], errors="coerce")
            df["LOW"] = pd.to_numeric(df["LOW"], errors="coerce")
            df["CLOSE"] = pd.to_numeric(df["CLOSE"], errors="coerce")

        clean_df = df.dropna(subset=["OPEN", "HIGH", "LOW", "CLOSE"])
        dropped = len(df) - len(clean_df)
        if dropped > 0:
            print(f"[vol_index] {symbol}: dropped {dropped} malformed rows")

        if clean_df.empty:
            print(f"[vol_index] {symbol}: CSV returned no valid data")
            return None

        return clean_df

    except Exception as exc:
        # Broad on purpose: a 200-with-bad-body (HTML maintenance page, schema
        # drift) raises KeyError/ParserError, not RequestException. The function
        # contract is "return None on any fetch/parse error".
        print(f"[vol_index] {symbol}: fetch/parse failed: {exc}")
        return None


def save_vol_index_snapshot(df: pd.DataFrame | None, symbol: str) -> None:
    """Write the per-symbol parquet store. CBOE ships full history every fetch, so this
    is an unconditional overwrite — appending would duplicate every historical row daily."""
    if df is None or df.empty:
        return

    df_to_store = df[["DATE", "OPEN", "HIGH", "LOW", "CLOSE"]].copy()
    df_to_store.columns = ["date", "open", "high", "low", "close"]
    df_to_store.insert(0, "symbol", symbol)

    atomic_to_parquet(df_to_store, _store_path(symbol))
    print(f"[vol_index] {symbol}: {len(df_to_store)} rows written (replace)")


def load_vol_index(symbol: str, days: int | None = None) -> pd.DataFrame:
    """Load vol-index history for symbol. Returns empty DataFrame if not found.

    Returns DataFrame with columns: symbol, date, open, high, low, close
    Sorted ascending by date. If days is given, returns the most recent N rows.
    """
    path = _store_path(symbol)
    if not path.exists():
        return pd.DataFrame()

    try:
        hist = pd.read_parquet(path)
        hist["date"] = pd.to_datetime(hist["date"]).dt.date
        if days is not None:
            hist = hist.sort_values("date", ascending=False).head(days).reset_index(drop=True)
        return hist.sort_values("date", ascending=True).reset_index(drop=True)
    except Exception as exc:
        print(f"[vol_index] load_vol_index({symbol}) failed: {exc}")
        return pd.DataFrame()


def refresh_vol_indices(symbols: list[str] | None = None) -> list[str]:
    """Fetch and cache vol-index daily snapshots for all symbols. Non-fatal on 403
    or network error. Returns the symbols successfully refreshed this run so the
    caller can flag a dead feed."""
    symbols = DEFAULT_VOL_INDICES if symbols is None else symbols
    refreshed: list[str] = []
    for sym in symbols:
        try:
            df = _fetch_cboe_vol_index(sym)
            if df is None:
                continue
            save_vol_index_snapshot(df, sym)
            refreshed.append(sym)
        except Exception as exc:
            print(f"[vol_index] {sym}: refresh failed (skipping): {exc}")
            continue
    return refreshed
