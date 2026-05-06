"""
Pull options chain and spot price via CBOE delayed quotes (15-min lag).
Endpoint: cdn.cboe.com/api/global/delayed_quotes/options/{ticker}.json
No auth, no API key, no rate limits.

These are American-style options (US equity and ETF listed options).
Greeks (gamma, delta, vega, theta) are taken directly from CBOE — they use
their own American option pricing model accounting for early exercise and
dividend yield. Do not recompute these via Black-Scholes (European only).

Returns a standardized DataFrame suitable for greeks_engine and exposure_engine.
Caller is responsible for caching — this module always fetches live.
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass

import pandas as pd
import requests

_CBOE_URL = "https://cdn.cboe.com/api/global/delayed_quotes/options/{ticker}.json"
_HEADERS = {"User-Agent": "options-quant/1.0"}


@dataclass
class ChainSnapshot:
    ticker: str
    spot: float
    as_of: datetime.date
    chains: pd.DataFrame  # columns: expiry, strike, type, oi, iv, bid, ask
    iv30: float = 0.0            # CBOE 30-day implied vol for the underlying
    price_change_pct: float = 0.0  # underlying day % change


def _parse_symbol(sym: str, ticker: str) -> tuple[datetime.date, str, float] | None:
    """Parse OPRA symbol e.g. 'SPY260506C00640000' → (expiry, 'call'/'put', strike)."""
    rest = sym[len(ticker):]
    if len(rest) < 15:
        return None
    try:
        expiry = datetime.date(2000 + int(rest[0:2]), int(rest[2:4]), int(rest[4:6]))
        side = "call" if rest[6] == "C" else "put"
        strike = int(rest[7:]) / 1000.0
        return expiry, side, strike
    except (ValueError, IndexError):
        return None


def load_chain(
    ticker: str = "SPY",
    min_oi: int = 100,
    min_dte: int = 7,
    max_iv: float = 3.0,
) -> ChainSnapshot:
    """
    Fetch all listed expiries for ticker from CBOE delayed quotes and return a ChainSnapshot.

    min_oi: drop options with fewer than this many contracts open interest.
    min_dte: skip expiries closer than this many calendar days (excludes 0DTE/weeklies
             that cause gamma blowup when swept spot crosses ATM with tiny T).
    max_iv: drop options with IV above this threshold (stale/garbage quotes).
    """
    url = _CBOE_URL.format(ticker=ticker)
    resp = requests.get(url, headers=_HEADERS, timeout=30)
    resp.raise_for_status()
    payload = resp.json()

    data = payload["data"]
    spot = float(data.get("current_price") or 0.0)
    iv30 = float(data.get("iv30") or 0.0)
    price_change_pct = float(data.get("price_change_percent") or 0.0)
    today = datetime.date.today()

    rows: list[dict] = []
    for opt in data["options"]:
        parsed = _parse_symbol(opt["option"], ticker)
        if parsed is None:
            continue
        expiry, side, strike = parsed

        dte = (expiry - today).days
        if dte < min_dte:
            continue

        oi = int(opt.get("open_interest") or 0)
        iv = float(opt.get("iv") or 0.0)

        if oi < min_oi or iv <= 0 or iv > max_iv:
            continue

        rows.append(
            {
                "expiry": expiry,
                "strike": strike,
                "type": side,
                "oi": oi,
                "iv": iv,
                "bid": float(opt.get("bid") or 0),
                "ask": float(opt.get("ask") or 0),
                "gamma": float(opt.get("gamma") or 0.0),
                "delta": float(opt.get("delta") or 0.0),
                "vega":  float(opt.get("vega")  or 0.0),
                "theta": float(opt.get("theta") or 0.0),
            }
        )

    chains = pd.DataFrame(rows)
    return ChainSnapshot(ticker=ticker, spot=spot, as_of=today, chains=chains,
                         iv30=iv30, price_change_pct=price_change_pct)
