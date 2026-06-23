"""
Shared GEX compute pipeline — single source of truth for both run_daily and app.

Both callers wrap this function:
  - run_daily.process_ticker()  → adds error handling
  - app.fetch_ticker() → adds @st.cache_data
"""
from __future__ import annotations

from engine import config
from engine.data.data_loader import load_chain
from engine.gex.greeks_engine import add_greeks
from engine.gex.exposure_engine import (
    compute_gex, strike_gex, strike_oi, expiry_oi, gamma_profile, vol_surface_data,
    compute_skew, surface_diagnostics,
)
from engine.gex.analytics import summarise
from engine.vol.vol_metrics import compute_model_free_em, compute_skew_25d, compute_term_structure, compute_rv20
from engine.data.validation import load_history
from engine.vol.vrp_history import vrp_percentile
from engine.surface.surface_evolution import load_evolution
from scipy.stats import percentileofscore


def _fetch_spot_history_yf(ticker: str, days: int = 400) -> "pd.Series | None":
    """Fetch daily closing prices from yfinance (oldest-first) for RV20 computation.

    Falls back gracefully — never raises. Returns None if data is insufficient.
    BRK.B is remapped to BRK-B for yfinance compatibility.

    Window widened to ~400d so a 252-session rolling RV20 series is buildable
    (the VRP percentile engine fetches its own closes, but this keeps the local
    rv20 path consistent — CONTEXT 16).
    """
    try:
        import yfinance as yf
        import pandas as pd
        yf_ticker = ticker.replace(".", "-")
        hist = yf.Ticker(yf_ticker).history(period=f"{days}d")
        if hist.empty or "Close" not in hist.columns:
            return None
        closes = hist["Close"].dropna().reset_index(drop=True)
        return closes if len(closes) >= 2 else None
    except Exception as exc:
        print(f"[compute] yf history failed for {ticker}: {exc}")
        return None


def _get_risk_free_rate() -> float:
    """3-month T-bill rate from ^IRX; falls back to config.RISK_FREE_FALLBACK on failure."""
    try:
        import yfinance as yf
        fi = yf.Ticker("^IRX").fast_info
        rate = fi.get("lastPrice") or fi.get("last_price")
        if rate and rate > 0:
            return float(rate) / 100
        print(f"[compute] ^IRX rate fetch returned None; using fallback {config.RISK_FREE_FALLBACK}")
    except Exception as exc:
        print(f"[compute] rate fetch failed ({exc}); using fallback {config.RISK_FREE_FALLBACK}")
    return config.RISK_FREE_FALLBACK


def compute_ticker(ticker: str) -> dict:
    """
    Full pipeline for one ticker.

    Returns:
        {
          "summary":        dict — net_gex, zero_gamma_level, call/put_wall, iv30, rv20, vrp, day %
          "s_df":           DataFrame — strike-level GEX
          "p_df":           DataFrame — gamma profile
          "spot":           float
          "surface_df":     DataFrame — vol surface
          "skew_df":        DataFrame — per-expiry skew (feeds parquet history columns)
          "skew":           dict | None — 25d skew buckets (front_month, second_month)
          "term_structure": dict | None — classification + ATM IV points
          "rv20":           float | None — 20-day annualized realized vol
          "vrp":            float | None — vol_index − RV20 (vol points, VRP-03)
        }
    """
    snapshot = load_chain(ticker)
    df = add_greeks(snapshot.chains, spot=snapshot.spot, today=snapshot.as_of)
    df = compute_gex(df, spot=snapshot.spot)

    # Positioning analysis (GEX, walls, γ-flip, OI walls) is tenor-bounded to where the
    # dealer-net-short assumption holds: short-to-mid. LEAPS = investor write-flow + tiny
    # gamma. Surface/skew below stay on the full chain.
    gex_df = df[(df["T_years"] * 365.0) <= config.GEX_MAX_DTE]

    s_df = strike_gex(gex_df)
    s_df = s_df.merge(strike_oi(gex_df), on="strike", how="left")

    oi_vals = s_df["oi"].fillna(0)
    if oi_vals.gt(0).any():
        s_df["is_top_decile"] = (oi_vals >= oi_vals.quantile(0.9))
    else:
        s_df["is_top_decile"] = False

    expiry_oi_df = expiry_oi(gex_df, max_dte=config.GEX_MAX_DTE)
    expiry_oi_primary_df = expiry_oi(gex_df, max_dte=config.GEX_PRIMARY_DTE)

    r = _get_risk_free_rate()
    p_df = gamma_profile(gex_df, spot=snapshot.spot, r=r)
    surface_df = vol_surface_data(df, spot=snapshot.spot)
    surface_diag = surface_diagnostics(surface_df, snapshot.spot)
    print(f"[diag] {ticker}: coverage {surface_diag['coverage_pct']:.0f}%  "
          f"fit_rmse {surface_diag['fit_rmse']:.1f}pp  cv {surface_diag['cv_rmse']:.1f}pp  "
          f"coherence_violations {surface_diag['coherence_violations']}")
    skew_df = compute_skew(df, spot=snapshot.spot)
    # skew_df is sorted by dte ascending — iloc[0] is shortest qualifying expiry
    front_skew = float(skew_df["skew_pp"].iloc[0]) if not skew_df.empty else None

    net_gex_scalar = float(s_df["gex"].sum())
    # Shares dealers must trade per $1 spot move to stay delta-neutral.
    # Derived by cancelling the S²×0.01 normalization from GEX: Γ_net × OI × 100.
    if snapshot.spot <= 0:
        raise ValueError(f"Invalid spot price {snapshot.spot} for {ticker}")
    delta_hedge_flow = net_gex_scalar / (snapshot.spot ** 2 * 0.01)

    summary = summarise(
        s_df, p_df,
        spot=snapshot.spot,
        delta_hedge_flow=delta_hedge_flow,
    )
    summary["ticker"] = ticker
    summary["iv30"] = snapshot.iv30
    summary["price_change_pct"] = snapshot.price_change_pct
    summary["front_skew"] = front_skew
    summary["coverage_pct"] = surface_diag["coverage_pct"]
    summary["fit_rmse"] = surface_diag["fit_rmse"]
    summary["max_resid"] = surface_diag["max_resid"]
    summary["cv_rmse"] = surface_diag["cv_rmse"]
    summary["coherence_calendar"] = surface_diag["coherence_calendar"]
    summary["coherence_butterfly"] = surface_diag["coherence_butterfly"]
    summary["coherence_violations"] = surface_diag["coherence_violations"]
    summary["positioning_primary_dte_max"] = config.GEX_PRIMARY_DTE
    summary["positioning_secondary_dte_max"] = config.GEX_MAX_DTE

    # OI walls — strike with highest call or put open interest, None-safe
    oi_call_wall = None
    oi_put_wall = None
    if "call_oi" in s_df.columns:
        call_oi = s_df["call_oi"].fillna(0)
        if call_oi.gt(0).any():
            oi_call_wall = float(s_df.loc[call_oi.idxmax(), "strike"])
    if "put_oi" in s_df.columns:
        put_oi = s_df["put_oi"].fillna(0)
        if put_oi.gt(0).any():
            oi_put_wall = float(s_df.loc[put_oi.idxmax(), "strike"])
    summary["oi_call_wall"] = oi_call_wall
    summary["oi_put_wall"] = oi_put_wall

    skew_25d = compute_skew_25d(df, spot=snapshot.spot)
    term_structure = compute_term_structure(df, spot=snapshot.spot)

    front = skew_25d.get("front_month") if isinstance(skew_25d, dict) else None
    butterfly = None
    if front and all(front.get(k) is not None for k in ("put_iv", "call_iv", "atm_iv")):
        butterfly = 0.5 * (float(front["put_iv"]) + float(front["call_iv"])) - float(front["atm_iv"])

    front_expiry = None
    expiry_candidates = df.loc[df["T_years"] > 0, ["expiry", "T_years"]].dropna()
    if not expiry_candidates.empty:
        front_expiry = expiry_candidates.sort_values("T_years").iloc[0]["expiry"]
    em = compute_model_free_em(df, spot=snapshot.spot, front_expiry=front_expiry)

    hist = load_history(ticker, days=config.VRP_PERCENTILE_LOOKBACK)
    # Use parquet history if we have 21+ rows; otherwise fall back to yfinance daily closes.
    if not hist.empty and "spot" in hist.columns and len(hist) >= 21:
        spot_series = hist["spot"].iloc[::-1].reset_index(drop=True)
    else:
        spot_series = _fetch_spot_history_yf(ticker)
        if spot_series is None and not hist.empty and "spot" in hist.columns:
            spot_series = hist["spot"].iloc[::-1].reset_index(drop=True)
    rv20 = compute_rv20(spot_series) if spot_series is not None else None
    summary["rv20"] = rv20
    summary["expected_move_pct"] = em.get("expected_move_pct")
    summary["expected_move_abs"] = em.get("expected_move_abs")
    summary["em_expiry"] = em.get("em_expiry")
    summary["em_dte"] = em.get("em_dte")
    summary["butterfly"] = butterfly

    butterfly_pct = None
    butterfly_pct_n = 0
    if not hist.empty and "butterfly" in hist.columns:
        butterfly_hist = hist["butterfly"].dropna()
        butterfly_pct_n = int(len(butterfly_hist))
        if butterfly is not None and butterfly_pct_n >= config.BUTTERFLY_PERCENTILE_MIN_SESSIONS:
            butterfly_window = butterfly_hist.iloc[-config.VRP_PERCENTILE_LOOKBACK:]
            butterfly_pct = int(percentileofscore(butterfly_window.to_numpy(), butterfly, kind="rank"))
    summary["butterfly_pct"] = butterfly_pct
    summary["butterfly_pct_n"] = butterfly_pct_n

    # VRP-03: the displayed VRP scalar AND its percentile share the vol-index series
    # (vol_index − RV20). snapshot.iv30 is no longer the VRP basis — both numbers come
    # from one definition so they cannot drift. None-values flow through on fetch failure.
    vrp_pct_res = vrp_percentile(ticker)
    vrp = vrp_pct_res["vrp"]
    summary["vrp"] = vrp
    summary["vrp_pct"] = vrp_pct_res["pct"]
    summary["vrp_pct_n"] = vrp_pct_res["n"]

    # Credibility-gated read inputs — computed ONCE here so the dashboard card and the
    # email card show the same chips (the canonical-card seam). Each is None unless its
    # sample clears CARD_READ_MIN_SESSIONS; build_card_read omits ungated chips entirely.
    # hist (load_history above) uses the same window as the dashboard's HISTORY_DAYS.
    floor = config.CARD_READ_MIN_SESSIONS
    read_skew_pct = None
    if front_skew is not None and not hist.empty and "front_skew" in hist.columns:
        skew_series = hist.dropna(subset=["front_skew"])["front_skew"].tolist()
        if len(skew_series) >= floor:
            read_skew_pct = int(percentileofscore(skew_series, front_skew))
    read_move_5d = None
    evo = load_evolution(ticker, horizon=5, days=400)
    if not evo.empty and "level" in evo.columns:
        lvl = evo.dropna(subset=["level"]).sort_values("date")
        if len(lvl) >= floor:
            read_move_5d = float(lvl["level"].iloc[-1])
    summary["read_skew_pct"] = read_skew_pct
    summary["read_move_5d"] = read_move_5d

    return {
        "summary": summary, "s_df": s_df, "p_df": p_df,
        "spot": snapshot.spot, "surface_df": surface_df, "skew_df": skew_df,
        "skew": skew_25d, "term_structure": term_structure,
        "rv20": rv20, "vrp": vrp, "surface_diag": surface_diag,
        "expiry_oi_df": expiry_oi_df,
        "expiry_oi_primary_df": expiry_oi_primary_df,
    }


