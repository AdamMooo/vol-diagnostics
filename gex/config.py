"""
Central configuration for gamma-omm. Magic numbers that were previously scattered
across modules — gathered here so the assumptions baked into the system are
visible in one place and tunable without grep-and-replace.

Each constant has a one-line rationale and, where applicable, the source paper
or empirical reason. Constants meant to be tuned (e.g., for sensitivity testing)
are exposed via function parameter defaults that reference these values.

True per-module constants (e.g., `MULTIPLIER = 100` shares/contract in
exposure_engine, BS singularity floor `T_MIN = 1/365` in greeks_engine, HTML
colour palette in report.py) are kept local to the module — they're not
configuration, they're domain invariants.
"""
from __future__ import annotations

# ── Chain filtering (gex.data_loader.load_chain defaults) ──────────────────────

MIN_OI: int = 100
"""Drop options with fewer than this many contracts of open interest.
Below this threshold the strike is illiquid enough that GEX contribution is
noise — not dealer hedging signal. 100 is the SpotGamma/perfiliev convention."""

MIN_DTE: int = 1
"""Exclude 0DTE options. BS gamma and charm are mathematically singular at T→0
ATM; vanna approaches zero cleanly. Mixing 0DTE in would require invented T_min
floors for two of three Greek columns and not the third, producing inconsistent
treatment. See .planning/milestones/v3.1-SCOPE.md."""

MAX_IV: float = 3.0
"""Drop options with IV > 300%. These are stale/garbage CBOE quotes that
distort the surface and walls; 300% is well above any plausible realized vol
for SPY/QQQ/IWM."""

# ── Risk-free rate ──────────────────────────────────────────────────────────────

RISK_FREE_FALLBACK: float = 0.05
"""Used when yfinance fetch of ^IRX (3-month T-bill) fails. 5% is a rough
historical midpoint; only matters for the γ-flip BS gamma sweep. Live rate
fetched at startup via `_get_risk_free_rate()` in gex.compute."""

# ── Gamma profile sweep (γ-flip computation) ───────────────────────────────────

PROFILE_N_POINTS: int = 200
"""Spot-grid resolution for the gamma_profile sweep used to find the γ-flip.
200 points across ±15% gives ~0.15%-of-spot precision; well finer than the
strike spacing on any of our underlyings."""

PROFILE_WIDTH_PCT: float = 0.15
"""Half-width of the gamma_profile sweep range, as a fraction of spot.
±15% covers any realistic same-session move while keeping the BS gamma
calculation numerically stable (extreme moneyness amplifies any rate/IV error)."""

# ── Implied vol surface ────────────────────────────────────────────────────────

SURFACE_MONEYNESS_BAND: float = 0.22
"""Half-width of strike filter for the vol surface, as a fraction of spot.
±22% gives far-OTM walls (e.g. QQQ Put Wall at K/S=0.834) comfortable rendering
headroom from the boundary. Strikes beyond this are too illiquid to inform the
surface shape."""

SURFACE_DTE_MAX: int = 180
"""Maximum DTE included in the vol surface. Beyond 180 days, OI thins out and
the surface gets very sparse; SVI would be needed to extrapolate further."""

SURFACE_GRID_DTE: int = 40
"""Number of grid points along the DTE axis for surface interpolation."""

SURFACE_GRID_LM: int = 30
"""Number of grid points along the moneyness axis (% OTM) for surface interpolation."""

SURFACE_PLOT_OTM_CLIP: float = 0.15
"""Max |% OTM| shown on the surface. Data collection uses SURFACE_MONEYNESS_BAND (±22%)
but deep-wing quotes are too noisy to plot — clip to ±15% for a clean surface."""

SURFACE_Z_CAP_PERCENTILE: float = 99.5
"""Clip the z-axis (IV %) at this percentile of the interpolated surface.
99.5th pctile drops only genuine data errors (bad CBOE quotes) while letting
real wing vol show — previously 97th was suppressing real far-OTM IV."""

SURFACE_SMOOTHING: float = 1.5
"""RBF thin-plate-spline smoothing, applied in std-normalized (DTE, %OTM) coords.
Regularises without over-flattening the skew. Non-stationary: effective strength
depends on each day's quote spread (same caveat as any tuned constant here).
Chosen 1.5: fit RMSE stays ~0.4pp on a typical SPY day while regularising enough to
avoid the ringing/overshoot that exact interpolation (smoothing=0, RMSE 0.0) produces on
crossed/wide delayed quotes — leave-one-expiry-out CV mildly favours less smoothing on a
single clean day but that does not outweigh the overfit risk across noisier sessions.
See gex/surface_sweep.py (run `python -m gex.surface_sweep`)."""

COVERAGE_KNN_K: float = 2.0
"""Coverage-mask radius multiplier. A grid cell is NaN'd if its nearest real quote
(in std-normalized DTE/%OTM space) exceeds r = COVERAGE_KNN_K × median nearest-neighbor
distance among real quotes. Data-adaptive (scales to today's chain density) — NOT a fixed
non-stationary cutoff. Chosen 2.0: holes true missing-expiry / far-wing gaps honestly
(coverage ~22% on a typical SPY day — most of the 40×30 grid genuinely lacks nearby quotes);
raising k inflates coverage only by extrapolating, which is exactly what this gate prevents.
See gex/surface_sweep.py (run `python -m gex.surface_sweep`)."""

# ── IV skew (Xing, Zhang & Zhao 2010, JFQA) ────────────────────────────────────

SKEW_MIN_DTE: int = 7
"""Skip expirations within this many days for the skew metric. Within a week
of expiry, the smile is dominated by gamma noise and stale quotes — picking
25Δ put / 50Δ call by delta becomes unreliable."""

SKEW_PUT_DELTA: float = -0.25
"""Target delta for the OTM put leg of the skew metric (Xing et al. 2010
convention). CBOE put deltas are negative."""

SKEW_CALL_DELTA: float = 0.25
"""Target delta for the OTM call leg of the skew metric (symmetric 25Δ risk reversal)."""

# ── Plot anchors ───────────────────────────────────────────────────────────────

PLOT_KS_ANCHORS: tuple[float, ...] = (0.80, 0.85, 0.90, 0.95, 1.00, 1.05, 1.10, 1.15, 1.20)
"""K/S tick anchors for the vol surface y-axis. Renders any anchor that falls
within the actual data range; sized to match SURFACE_MONEYNESS_BAND."""

PLOT_DTE_ANCHORS: tuple[int, ...] = (7, 30, 60, 90, 120, 180)
"""DTE tick anchors for the vol surface x-axis. Trading-week multiples that
match standard option-cycle thinking."""

# ── Streamlit caching ──────────────────────────────────────────────────────────

CACHE_TTL_TICKER: int = 300
"""Seconds to cache compute_ticker() results in the Streamlit app. 5 minutes
roughly matches the CBOE delayed-quote refresh rhythm — quotes won't change
meaningfully inside this window."""

CACHE_TTL_HISTORY: int = 1800
"""Seconds to cache parquet history reads. 30 minutes is fine — history is
append-only and only changes once a day when run_daily fires."""

HISTORY_DAYS: int = 30
"""Rolling lookback (days) for the History tab charts (γ-flip vs spot, skew).
Long enough to see regime shifts; short enough to fit in one screen."""
