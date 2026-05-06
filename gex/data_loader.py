"""
Pull options chain and spot price via yfinance.

Returns a standardized DataFrame suitable for greeks_engine and exposure_engine.
Caller is responsible for caching — this module always fetches live.
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass

import pandas as pd
import yfinance as yf


# Liquid index ETFs: keep min_oi=10, no moneyness filter (market is deep enough).
# All others: enforce min_oi=100 and ±10% moneyness — eliminates phantom IV on
# wide-spread illiquid strikes that would otherwise inflate GEX via BS gamma.
_LIQUID_TICKERS = {"SPY", "QQQ"}
_ILLIQUID_MIN_OI = 100
_MONEYNESS_BAND = 0.10


@dataclass
class ChainSnapshot:
    ticker: str
    spot: float
    as_of: datetime.date
    chains: pd.DataFrame  # columns: expiry, strike, type, oi, iv, bid, ask


def load_chain(ticker: str = "SPY", min_oi: int = 10) -> ChainSnapshot:
    """
    Fetch all listed expiries for ticker and return a ChainSnapshot.

    min_oi: drop options with fewer than this many contracts open interest.
    Keeps only expiries with T > 0 (today's expiry excluded).
    For non-liquid tickers, enforces min_oi=100 and ±10% moneyness filter.
    """
    tk = yf.Ticker(ticker)
    spot = tk.fast_info["lastPrice"]
    today = datetime.date.today()

    liquid = ticker in _LIQUID_TICKERS
    effective_min_oi = min_oi if liquid else max(min_oi, _ILLIQUID_MIN_OI)

    rows: list[dict] = []
    for expiry_str in tk.options:
        expiry = datetime.date.fromisoformat(expiry_str)
        if expiry <= today:
            continue

        chain = tk.option_chain(expiry_str)
        for side, df in (("call", chain.calls), ("put", chain.puts)):
            for _, row in df.iterrows():
                iv = row.get("impliedVolatility", float("nan"))
                oi_raw = row.get("openInterest")
                oi = int(oi_raw) if pd.notna(oi_raw) and oi_raw else 0
                if oi < effective_min_oi or iv != iv or iv <= 0:
                    continue
                if not liquid and abs(float(row["strike"]) / spot - 1) > _MONEYNESS_BAND:
                    continue
                rows.append(
                    {
                        "expiry": expiry,
                        "strike": float(row["strike"]),
                        "type": side,
                        "oi": oi,
                        "iv": float(iv),
                        "bid": float(row.get("bid") or 0),
                        "ask": float(row.get("ask") or 0),
                    }
                )

    chains = pd.DataFrame(rows)
    return ChainSnapshot(ticker=ticker, spot=float(spot), as_of=today, chains=chains)
