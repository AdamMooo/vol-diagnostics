"""
Daily feature + forward-outcome panel for the Risk Lens.

One row per SPX session from 1990. Feature columns are known at that session's close;
`fwd_*` columns are the outcomes over the NEXT `RISK_LENS_HORIZON` sessions and are NaN
for the most recent rows whose window hasn't finished. Anything that conditions on
history must only use rows whose forward window closed before the as-of date — see
`known_by`.

SPX (^GSPC) rather than SPY: 1990 depth matches VIX, and SPY's dividend drops would show
up as fake down-days in the drawdown outcome.
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

from engine import config
from engine.data.store import atomic_to_parquet
from engine.data.vol_index import load_vol_index

STORE_DIR = pathlib.Path(__file__).resolve().parents[2] / "out" / "insight"
SPX_STORE = STORE_DIR / "spx.parquet"
VOL_SYMBOLS = ("VIX", "VIX3M", "VIX9D", "VVIX", "VXN", "RVX")


def refresh_spx() -> bool:
    """Re-download full ^GSPC close history (one call, ~9k rows). Overwrite, like the
    vol-index store — yfinance ships the whole series. Returns False on any failure so
    the caller falls back to the cached copy."""
    try:
        import yfinance as yf
        hist = yf.Ticker("^GSPC").history(start="1990-01-01", auto_adjust=False)
        if hist is None or hist.empty or "Close" not in hist:
            print("[insight] ^GSPC fetch returned nothing — keeping cached copy")
            return False
        df = pd.DataFrame({
            "date": pd.to_datetime(hist.index).tz_localize(None).normalize(),
            "close": hist["Close"].astype(float).values,
        }).dropna()
        atomic_to_parquet(df, SPX_STORE)
        print(f"[insight] ^GSPC: {len(df)} rows written")
        return True
    except Exception as exc:
        print(f"[insight] ^GSPC fetch failed: {exc}")
        return False


def load_spx() -> pd.Series:
    if not SPX_STORE.exists():
        return pd.Series(dtype=float, name="spx")
    df = pd.read_parquet(SPX_STORE)
    s = pd.Series(df["close"].values, index=pd.to_datetime(df["date"]), name="spx")
    return s[~s.index.duplicated(keep="last")].sort_index()


def load_vols() -> dict[str, pd.Series]:
    out: dict[str, pd.Series] = {}
    for sym in VOL_SYMBOLS:
        v = load_vol_index(sym)
        if v.empty:
            continue
        s = pd.Series(v["close"].values, index=pd.to_datetime(v["date"]), name=sym)
        out[sym] = s[~s.index.duplicated(keep="last")]
    return out


def _rolling_pct(s: pd.Series) -> pd.Series:
    return s.rolling(config.RISK_LENS_PCT_LOOKBACK,
                     min_periods=config.RISK_LENS_PCT_MIN_SESSIONS).rank(pct=True)


def build_panel(spx: pd.Series, vols: dict[str, pd.Series],
                horizon: int | None = None) -> pd.DataFrame:
    """Pure: closes in, panel out. Vol indices are aligned onto the SPX calendar
    without forward-fill — a missing CBOE print is a missing feature, not yesterday's."""
    h = horizon or config.RISK_LENS_HORIZON
    df = pd.DataFrame({"spx": spx.astype(float)}).sort_index()
    for sym, s in vols.items():
        df[sym] = s.reindex(df.index)

    r = np.log(df["spx"]).diff()
    df["ret1"] = df["spx"].pct_change()
    df["rv20"] = r.rolling(20).std() * np.sqrt(252) * 100
    if "VIX" in df:
        df["vrp"] = df["VIX"] - df["rv20"]
        df["vix_pct"] = _rolling_pct(df["VIX"])
        df["vix_chg1"] = df["VIX"].pct_change(fill_method=None)
        df["vix_chg5"] = df["VIX"].pct_change(5, fill_method=None)
        # Forecast for the exposure scalar: half implied (forward-looking, rich on
        # average), half realized (unbiased, lagging). See exposure.py.
        df["forecast_vol"] = 0.5 * df["VIX"] + 0.5 * df["rv20"]
    if "VIX" in df and "VIX3M" in df:
        df["term"] = df["VIX"] / df["VIX3M"]
    for sym in ("VXN", "RVX"):
        if sym in df:
            df[f"{sym.lower()}_pct"] = _rolling_pct(df[sym])

    # Forward outcomes over sessions t+1..t+h.
    fwd_r = pd.concat([r.shift(-k) for k in range(1, h + 1)], axis=1)
    complete = fwd_r.notna().all(axis=1)
    df["fwd_rv"] = (fwd_r.std(axis=1) * np.sqrt(252) * 100).where(complete)
    path = pd.concat([df["spx"].shift(-k) for k in range(1, h + 1)], axis=1).div(df["spx"], axis=0)
    df["fwd_mdd"] = (path.min(axis=1).clip(upper=1.0) - 1).where(complete)
    df["fwd_ret"] = (df["spx"].shift(-h) / df["spx"] - 1).where(complete)
    if "VIX" in df:
        # Did the implied vol you could have sold exceed what actually got delivered?
        df["carry_edge"] = (df["VIX"] - df["fwd_rv"]).where(complete)
    return df


def known_by(panel: pd.DataFrame, asof: pd.Timestamp, horizon: int | None = None) -> pd.DataFrame:
    """Rows whose forward window had fully closed by `asof` — the only history an
    honest as-of read (or replay) may condition on."""
    h = horizon or config.RISK_LENS_HORIZON
    pos = panel.index.searchsorted(pd.Timestamp(asof), side="right") - 1
    if pos - h < 0:
        return panel.iloc[0:0]
    return panel.iloc[: pos - h + 1]


def latest_asof(panel: pd.DataFrame) -> pd.Timestamp | None:
    """Most recent session with both an SPX close and a VIX print."""
    ok = panel.dropna(subset=["spx", "VIX"]) if "VIX" in panel else panel.iloc[0:0]
    return None if ok.empty else ok.index[-1]


def load_panel(refresh: bool = False) -> pd.DataFrame:
    if refresh or not SPX_STORE.exists():
        refresh_spx()
    return build_panel(load_spx(), load_vols())
