"""
Compute Gamma Exposure (GEX) from a greeks-enriched chains DataFrame.

Convention (SpotGamma/retail standard):
    GEX_per_option = gamma * OI * multiplier * spot^2 * 0.01

    Calls contribute positive GEX, puts negative.
    Positive net GEX = dealers net long gamma (stabilising: sell rallies, buy dips).
    Negative net GEX = dealers net short gamma (destabilising: accelerates moves).

Assumptions baked in:
    - Retail buys options, dealers sell them (dealer short net = retail long net).
    - Standard US equity multiplier = 100 shares/contract.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from gex import config

MULTIPLIER = 100  # shares per contract


def compute_gex(df: pd.DataFrame, spot: float) -> pd.DataFrame:
    """
    Add gex column to a greeks-enriched DataFrame.
    Returns a copy.
    """
    df = df.copy()
    sign = np.where(df["type"] == "call", 1.0, -1.0)
    df["gex"] = sign * df["gamma"] * df["oi"] * MULTIPLIER * spot**2 * 0.01
    return df


def strike_gex(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate GEX by strike (sum across all expiries and sides)."""
    return (
        df.groupby("strike")["gex"]
        .sum()
        .reset_index()
        .sort_values("strike")
        .reset_index(drop=True)
    )


def strike_oi(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate open interest by strike, split into call/put sides.

    Returns columns: strike, call_oi, put_oi, oi (total). Observable — no
    dealer assumption, unlike GEX.
    """
    pivot = df.pivot_table(
        index="strike", columns="type", values="oi", aggfunc="sum", fill_value=0
    )
    for side in ("call", "put"):
        if side not in pivot.columns:
            pivot[side] = 0
    out = pivot.reset_index()[["strike", "call", "put"]]
    out = out.rename(columns={"call": "call_oi", "put": "put_oi"})
    out["oi"] = out["call_oi"] + out["put_oi"]
    return out.sort_values("strike").reset_index(drop=True)



def vol_surface_data(df: pd.DataFrame, spot: float,
                     dte_max: int = config.SURFACE_DTE_MAX,
                     moneyness_band: float = config.SURFACE_MONEYNESS_BAND) -> pd.DataFrame:
    """
    Extract (dte, log_moneyness, iv_pct) points for the implied vol surface.

    OTM convention (Gatheral, "The Volatility Surface" §2.1 — industry standard):
        - K <  spot: use the PUT IV  (OTM put — more liquid below spot)
        - K >= spot: use the CALL IV (OTM call — more liquid at/above spot)
    OTM options are more liquid and avoid early-exercise premium distortions in
    American equity options. Yields exactly one IV per (expiry, strike) point
    with no aggregation/weighting decision.

    Axes follow academic convention (Cont & da Fonseca 2002, Gatheral):
        - log-moneyness = log(strike/spot), centred at 0 = ATM
        - DTE in days

    Filtered to the liquid near-money region (±22% of spot, ≤180 DTE).
    Returns DataFrame: dte (days), strike, moneyness, log_moneyness, iv_pct.
    """
    lo = spot * (1 - moneyness_band)
    hi = spot * (1 + moneyness_band)

    is_otm = (((df["type"] == "put") & (df["strike"] < spot)) |
              ((df["type"] == "call") & (df["strike"] >= spot)))

    valid = df[
        is_otm &
        (df["T_years"] > 0) &
        (df["iv"] > 0) &
        (df["oi"] > 0) &
        (df["strike"] >= lo) &
        (df["strike"] <= hi)
    ].copy()
    valid["dte"] = valid["T_years"] * 365
    valid = valid[valid["dte"] <= dte_max].copy()
    valid["moneyness"] = valid["strike"] / spot
    valid["log_moneyness"] = np.log(valid["moneyness"])
    valid["iv_pct"] = valid["iv"] * 100

    return (
        valid[["dte", "strike", "moneyness", "log_moneyness", "iv_pct"]]
        .dropna()
        .sort_values("dte")
        .reset_index(drop=True)
    )


def compute_skew(df: pd.DataFrame, spot: float, min_dte: int = config.SKEW_MIN_DTE) -> pd.DataFrame:
    """
    Per-expiry IV skew: IV(25Δ put) − IV(25Δ call), in percentage points.

    Symmetric 25Δ risk reversal — measures wing asymmetry without conflating
    ATM level with skew. Uses delta-based selection (CBOE-supplied). Front-month
    defined as nearest expiry with DTE >= min_dte to avoid expiry-day noise.

    OTM filter enforced: puts must be below spot, calls at/above spot. Prevents
    deep ITM options (which can have |delta|≈0.25) from being selected as the
    wing leg — ITM IVs carry intrinsic value distortion, not wing vol.

    Methodology: symmetric 25Δ convention. Xing, Zhang & Zhao (2010, JFQA) used
    50Δ−25Δ; directional finding holds but magnitude comparisons don't apply directly.

    Returns DataFrame: expiry, dte, put_25d_iv, call_25d_iv, skew_pp.
    """
    valid = df[(df["T_years"] > 0) & (df["iv"] > 0) & (df["oi"] > 0)].copy()
    valid["dte"] = valid["T_years"] * 365

    rows = []
    for expiry, grp in valid.groupby("expiry"):
        dte = grp["dte"].iloc[0]
        if dte < min_dte:
            continue
        puts = grp[(grp["type"] == "put") & (grp["strike"] < spot)]
        calls = grp[(grp["type"] == "call") & (grp["strike"] >= spot)]
        if puts.empty or calls.empty:
            continue
        put_idx = (puts["delta"] - config.SKEW_PUT_DELTA).abs().idxmin()
        call_idx = (calls["delta"] - config.SKEW_CALL_DELTA).abs().idxmin()
        put_iv = puts.loc[put_idx, "iv"] * 100
        call_iv = calls.loc[call_idx, "iv"] * 100
        rows.append({
            "expiry": expiry,
            "dte": dte,
            "put_25d_iv": put_iv,
            "call_25d_iv": call_iv,
            "skew_pp": put_iv - call_iv,
        })

    return pd.DataFrame(rows).sort_values("dte").reset_index(drop=True)


def compute_surface_slopes(surface_df: pd.DataFrame) -> dict:
    """
    Strike slope and term structure slope from the raw surface scatter points.

    strike_slope: ∂IV/∂(log K) at front expiry (DTE ≤ 45), scaled to pp per 10%
        K/S move (multiplied by log(1.10)). Negative = normal put skew dominant.
        Measures how fast OTM put IV rises vs OTM call IV.

    term_slope: ∂IV/∂(DTE) at ATM (|log_moneyness| < 0.05), scaled to pp per
        30 DTE. Positive = contango (normal). Negative = backwardation (short-
        end stress/event premium).

    Both are linear fits — model constructs, no peer-reviewed predictive backing.
    Returns dict: {strike_slope: float|None, term_slope: float|None}
    """
    if surface_df.empty:
        return {"strike_slope": None, "term_slope": None}

    # Strike slope: front expiry band, moderate moneyness
    front = surface_df[surface_df["dte"] <= 45]
    if len(front) >= 4:
        coeff = np.polyfit(front["log_moneyness"], front["iv_pct"], 1)[0]
        strike_slope = float(coeff * np.log(1.10))
    else:
        strike_slope = None

    # Term slope: ATM band across all expiries, average IV per expiry
    atm = surface_df[surface_df["log_moneyness"].abs() < 0.05]
    if len(atm) >= 3:
        atm_avg = (atm.assign(dte_r=atm["dte"].round(0))
                      .groupby("dte_r")["iv_pct"].mean()
                      .reset_index())
        if len(atm_avg) >= 3:
            coeff = np.polyfit(atm_avg["dte_r"], atm_avg["iv_pct"], 1)[0]
            term_slope = float(coeff * 30)
        else:
            term_slope = None
    else:
        term_slope = None

    return {"strike_slope": strike_slope, "term_slope": term_slope}


def surface_diagnostics(surface_df, spot) -> dict:
    """Headless fit-honesty + surface-coherence QA for the vol surface (VALID-02/04).

    Pure (DataFrame in, dict out, no I/O). Returns:
        coverage_pct, fit_rmse (pp), max_resid (pp), cv_rmse (pp, leave-one-expiry-out),
        coherence_calendar (bool PASS), coherence_butterfly (bool PASS), coherence_violations (int)

    Coherence checks are FIT-QUALITY QA, never a trading signal: on delayed CBOE quotes any
    genuine arbitrage is untradable, so calendar total-variance monotonicity + butterfly
    convexity only confirm the fitted surface is internally consistent. They never auto-repair.
    Degrades to NaN floats (coherence PASS / 0 violations) on empty / sparse / single-expiry
    input — never raises (a single expiry is a smile, not a surface; the RBF is singular there).
    """
    from scipy.interpolate import RBFInterpolator
    from gex.analytics import coverage_mask

    nan_result = {
        "coverage_pct": float("nan"), "fit_rmse": float("nan"),
        "max_resid": float("nan"), "cv_rmse": float("nan"),
        "coherence_calendar": True, "coherence_butterfly": True,
        "coherence_violations": 0,
    }
    if (surface_df is None or len(surface_df) == 0
            or not {"strike", "dte", "iv_pct"}.issubset(surface_df.columns)):
        return nan_result

    clip_pct = config.SURFACE_PLOT_OTM_CLIP * 100.0
    dte_floor = 5
    pct_otm = (surface_df["strike"].to_numpy() / spot - 1.0) * 100.0
    dte_v = surface_df["dte"].to_numpy()
    iv_v = surface_df["iv_pct"].to_numpy()
    in_band = (np.abs(pct_otm) <= clip_pct) & (dte_v >= dte_floor)
    pct_otm, dte_v, iv_v = pct_otm[in_band], dte_v[in_band], iv_v[in_band]
    if len(iv_v) < 6 or len(np.unique(dte_v)) < 2:
        return nan_result

    # Fit residuals: RBF evaluated AT the real quote locations vs their actual IV.
    pts = np.column_stack([dte_v, pct_otm])
    pts_std = pts.std(axis=0)
    pts_std[pts_std < 1e-6] = 1.0
    rbf = RBFInterpolator(pts / pts_std, iv_v, kernel="thin_plate_spline",
                          smoothing=config.SURFACE_SMOOTHING)
    resid = rbf(pts / pts_std) - iv_v
    fit_rmse = float(np.sqrt(np.mean(resid ** 2)))
    max_resid = float(np.max(np.abs(resid)))

    # Leave-one-EXPIRY-out CV (adjacent strikes correlate and flatter leave-one-point-out).
    expiries = np.unique(dte_v)
    cv_sq = []
    for e in expiries:
        hold = dte_v == e
        train = ~hold
        if train.sum() < 4 or len(np.unique(dte_v[train])) < 2:
            continue
        tp = np.column_stack([dte_v[train], pct_otm[train]])
        ts = tp.std(axis=0)
        ts[ts < 1e-6] = 1.0
        rbf_cv = RBFInterpolator(tp / ts, iv_v[train], kernel="thin_plate_spline",
                                 smoothing=config.SURFACE_SMOOTHING)
        hp = np.column_stack([dte_v[hold], pct_otm[hold]])
        cv_sq.extend(((rbf_cv(hp / ts) - iv_v[hold]) ** 2).tolist())
    cv_rmse = float(np.sqrt(np.mean(cv_sq))) if cv_sq else float("nan")

    # Coverage % on the standard grid (reuses the Plan-01 gate artifact).
    dte_max = min(float(dte_v.max()), float(config.SURFACE_DTE_MAX))
    dte_grid = np.linspace(dte_floor, max(dte_max, dte_floor + 1.0), config.SURFACE_GRID_DTE)
    otm_grid = np.linspace(-clip_pct, clip_pct, config.SURFACE_GRID_LM)
    coverage_pct = 100.0 * float(coverage_mask(
        surface_df, spot, dte_grid, otm_grid, dte_floor=dte_floor, clip_pct=clip_pct).mean())

    # --- coherence (fit-QA only; flag + count + log, NEVER repair the surface) ---
    violations = 0

    # Calendar: per ~5% moneyness bucket, total variance IV^2*T must not fall as DTE rises.
    cal_ok = True
    band = pd.DataFrame({"dte": dte_v, "p": pct_otm, "iv": iv_v})
    band["bucket"] = (band["p"] / 5.0).round() * 5.0
    for bucket, grp in band.groupby("bucket"):
        agg = grp.groupby("dte")["iv"].mean().sort_index()
        if len(agg) < 2:
            continue
        d = agg.index.to_numpy(dtype=float)
        w = (agg.to_numpy() / 100.0) ** 2 * (d / 365.0)
        for i in np.where(np.diff(w) < -1e-6)[0]:
            cal_ok = False
            violations += 1
            print(f"[coherence] calendar variance drop at {bucket:+.0f}%OTM "
                  f"DTE {d[i]:.0f}->{d[i + 1]:.0f}")

    # Butterfly: within each expiry, 2nd difference of IV across sorted strikes >= -tol
    # (a concave bump implies negative implied density).
    bf_ok = True
    tol = 0.5  # pp — tolerate quote noise
    for e in expiries:
        m = dte_v == e
        if m.sum() < 3:
            continue
        order = np.argsort(pct_otm[m])
        ivs = iv_v[m][order]
        ps = pct_otm[m][order]
        for i in np.where(np.diff(ivs, n=2) < -tol)[0]:
            bf_ok = False
            violations += 1
            print(f"[coherence] butterfly concavity at DTE={e:.0f} %OTM~{ps[i + 1]:+.1f}")

    print(f"[coherence] calendar={'PASS' if cal_ok else 'FAIL'} "
          f"butterfly={'PASS' if bf_ok else 'FAIL'} violations={violations}")

    return {
        "coverage_pct": coverage_pct,
        "fit_rmse": fit_rmse,
        "max_resid": max_resid,
        "cv_rmse": cv_rmse,
        "coherence_calendar": cal_ok,
        "coherence_butterfly": bf_ok,
        "coherence_violations": violations,
    }


def gamma_profile(df: pd.DataFrame, spot: float,
                  n_points: int = config.PROFILE_N_POINTS,
                  width_pct: float = config.PROFILE_WIDTH_PCT,
                  r: float = config.RISK_FREE_FALLBACK) -> pd.DataFrame:
    """
    Recompute net GEX across a grid of hypothetical spot levels.
    Used to find the zero-gamma level and visualise the profile.

    Returns DataFrame with columns: spot_level, net_gex.
    """
    from gex.greeks_engine import bs_gamma

    lo = spot * (1 - width_pct)
    hi = spot * (1 + width_pct)
    spot_grid = np.linspace(lo, hi, n_points)

    net_gex = np.zeros(n_points)
    for i, s in enumerate(spot_grid):
        gamma = bs_gamma(s, df["strike"].to_numpy(), df["iv"].to_numpy(),
                         df["T_years"].to_numpy(), r=r)
        sign = np.where(df["type"] == "call", 1.0, -1.0)
        net_gex[i] = (sign * gamma * df["oi"].to_numpy() * MULTIPLIER * s**2 * 0.01).sum()

    return pd.DataFrame({"spot_level": spot_grid, "net_gex": net_gex})
