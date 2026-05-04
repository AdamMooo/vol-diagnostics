# Phase 1: POC Delivery & Calibration - Pattern Map

**Mapped:** 2026-05-04
**Files analyzed:** 6 (1 delete, 3 modify, 2 new)
**Analogs found:** 6 / 6

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `local_data.py` (modify) | data-layer facade | request-response | `local_data.FreeCon` | exact role match |
| `dashboard.py` (modify) | section builder | transform | `dashboard.section_d_analog()` | exact role match |
| `run.py` (modify) | orchestrator | request-response | `run.py` (remove imports) | exact role match |
| `validate.py` | DELETE module | N/A | N/A | delete, no analog |
| `build_report.py` (new) | notebook builder | file-I/O | `nbformat.v4` + `run.py` plotting | pattern match |
| `WALKTHROUGH.md` (new) | documentation | static | `dashboard.py` docstrings + `validate.py` comments | pattern match |

---

## Pattern Assignments

### `local_data.py` — Add `BloombergCon` Class (data-layer facade, request-response)

**Analog:** `local_data.FreeCon` (lines 140–196)

The existing `FreeCon` class provides the contract interface. Bloomberg swap requires a parallel class with **identical method signature**.

**Existing FreeCon interface** (lines 140–196):
```python
class FreeCon:
    """`con.bdh`-shaped facade backed by free, official sources.

    Returns DataFrame indexed by date with a single column. Empty DataFrame
    on unsupported (ticker, field) so callers can use the same
    landed-or-deferred branching as on Cron2.
    """

    def bdh(self, ticker: str, field: str, start_date: str, end_date: str) -> pd.DataFrame:
        # Cache logic (lines 149–154)
        path = _cache_path(ticker, field, start_date, end_date)
        if not _is_stale(path):
            try:
                return pd.read_parquet(path)
            except Exception:
                pass

        try:
            series = self._dispatch(ticker, field, start_date, end_date)
        except Exception as e:
            # Fallback to cache (lines 158–162)
            if path.exists():
                warnings.warn(f"source failed for {ticker}/{field} ({e}); serving cached")
                return pd.read_parquet(path)
            raise

        if series is None or len(series) == 0:
            return pd.DataFrame()

        df = series.to_frame(name=field)
        df.to_parquet(path)
        return df

    def _dispatch(self, ticker: str, field: str, start: str, end: str) -> pd.Series:
        # Returns pd.Series or empty Series
        ...
```

**Pattern for BloombergCon:**
- Same `bdh(ticker, field, start_date, end_date) -> pd.DataFrame` signature
- Normalize output: single column named `field`, DatetimeIndex normalized
- Return empty DataFrame on error (not None or exception) for graceful fallback
- Cache to parquet with same naming scheme as FreeCon (lines 70–71)
- Import `emds_client` at use site (only on Cron2) inside try/except

**Config flag pattern** (lines 198):
```python
con = FreeCon()  # Current: default to free sources
```

New pattern:
```python
try:
    from emds_client import con as bloomberg_con
    BLOOMBERG_AVAILABLE = True
except ImportError:
    BLOOMBERG_AVAILABLE = False

# At module level
USE_BLOOMBERG = False  # Change to True on Cron2
con = BloombergCon() if (BLOOMBERG_AVAILABLE and USE_BLOOMBERG) else FreeCon()
```

**Key fields to support** (from RESEARCH.md DATA-06 and CONTEXT.md D-12):
- `30DAY_IMPVOL_100.0%MNY_DF` — 30d ATM IV
- `30DAY_IMPVOL_90.0%MNY_DF` — 30d 90%-moneyness IV (Bloomberg-calibrated replacement for synthetic)
- `90DAY_IMPVOL_100.0%MNY_DF` — 90d ATM IV
- `PX_LAST` — price level

---

### `dashboard.py` — Reframe Section D (transform, environment signals)

**Analog:** `dashboard.section_d_analog()` (lines 210–257)

Current Section D reports realized **sleeve P&L** from analog periods (forecast-flavored). Phase 1 reframes to show realized **environment signals** instead (pure history, no forecast).

**Current implementation** (lines 235–256):
```python
def section_d_analog(sigs: Signals, bt: BacktestResults, k: int = K_NEIGHBORS) -> str:
    last_dt = sigs.latest_date()
    out = [
        "## Section D — Closest Regime Analogs",
        "",
        f"K={k} nearest historical roll-opens, Euclidean distance over signal vector:",
        f"  features: {', '.join(NEIGHBOR_FEATURES)}",
        "Mean and dispersion of realized sleeve returns from those analogs.",  # ← OLD: sleeve returns
        "",
    ]
    for u in bt.rolls:
        rolls = bt.rolls[u]
        today_vec = np.array([sigs.pct[s].loc[last_dt, u] for s in NEIGHBOR_FEATURES])
        # ... K-NN matching logic (lines 221–234) ...
        nn_rolls = rolls.loc[nn.index, ["open"] + SLEEVE_COLS]  # ← OLD: fetch sleeve returns

        # ... output matched dates (lines 237–246) ...
        agg = pd.DataFrame({
            "mean%": nn_rolls[SLEEVE_COLS].mean() * 100,  # ← OLD: aggregate sleeve returns
            # ...
        }).round(2)
        # ...
```

**New pattern for Section D:**

1. Keep K-NN matching logic unchanged (lines 221–234, finding nearest neighbors in signal space)
2. Replace `nn_rolls` fetch: instead of sleeve returns, extract **realized signals** from T+1m, T+3m, T+6m forward
3. Add helper function `_forward_realized_environment()`:

```python
def _forward_realized_environment(close_dt: pd.Timestamp, sigs: Signals, 
                                    horizons: list[int] = [21, 63, 126]) -> dict:
    """For a given match date, return realized signals 1m/3m/6m forward.
    
    Args:
        close_dt: roll close date (end of match period)
        sigs: Signals object with pct-rank panels
        horizons: trading days forward [21, 63, 126] ~ [1m, 3m, 6m]
    
    Returns:
        dict of {horizon_days: {signal_name: value, ...}} for matched horizon
    """
    result = {}
    all_sigs = pd.concat(sigs.pct, axis=1)  # All signals, all dates
    for h in horizons:
        future_dt = close_dt + pd.Timedelta(days=h)
        if future_dt not in all_sigs.index:
            # Snap to nearest valid date
            valid = all_sigs[all_sigs.index >= future_dt].index
            if len(valid) == 0:
                result[h] = None
            else:
                future_dt = valid[0]
                result[h] = all_sigs.loc[future_dt].to_dict()
        else:
            result[h] = all_sigs.loc[future_dt].to_dict()
    return result
```

4. Replace section output to report forward-realized environment per match:

```python
# In the output loop (replacing lines 247–256)
for close_dt, dist in nn["_d"].items():
    open_dt = rolls.loc[close_dt, "open"]
    out.append(f"  Match: open {open_dt.date()}  close {close_dt.date()}  d={dist:.3f}")
    
    # NEW: Show what the environment did AFTER the match
    fwd = _forward_realized_environment(close_dt, sigs, horizons=[21, 63, 126])
    for h, sig_dict in fwd.items():
        if sig_dict is None:
            out.append(f"    {h}d forward: (no data)")
        else:
            # Compact output: show key signals only
            out.append(
                f"    {h}d forward: vrp={sig_dict.get('vrp', np.nan):.2f}, "
                f"skew={sig_dict.get('skew', np.nan):.2f}, "
                f"term={sig_dict.get('term', np.nan):.2f}, "
                f"dd={sig_dict.get('dd', np.nan):.2f}"
            )
    out.append("")
```

5. Update section header and description (lines 212–218):
```python
out = [
    "## Section D — Past Periods That Looked Like Now",  # ← RENAME
    "",
    f"K={k} nearest historical roll-opens, Euclidean distance over signal vector:",
    f"  features: {', '.join(NEIGHBOR_FEATURES)}",
    "For each matched period, the realized environment (signals) that followed.",  # ← REFRAME
    "",
]
```

**Language discipline:** Use "realized" and "historical" consistently. Never "expected" or "likely."

---

### `run.py` — Remove `validate.py` imports and calls (orchestrator, request-response)

**Analog:** `run.py` current structure (lines 1–143)

The run.py orchestrator currently calls `validate.py` in Phase 6 section. Per D-09, delete the entire module and its references.

**Current references** (to remove):
- Line 25: `from validate import run_walk_forward, format_walk_forward_report`
- Lines 126–133: Phase 6 walk-forward section (entire block)

**Pattern to keep:**
- Main orchestrator structure (lines 51–136) remains intact
- Sections A–E stay as-is (lines 54–124)
- Remove only Phase 6 section (lines 126–133) and its import

**Revised structure after edit:**
```python
def main(start: str = "2010-01-01") -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Sections 1–5 stay identical (lines 54–124)
    _section("Phase 1 — Data Layer")
    # ...
    
    _section("Phase 4 — Decision Dashboard")
    # ...
    
    # DELETE Phase 6 section (lines 126–133)
    
    _section("Done")
    print(f"Outputs in {OUT_DIR.resolve()}")
```

No other changes needed. Data layer, signals, backtest, and dashboard modules are untouched.

---

### `build_report.py` — New Notebook Builder Script (file-I/O, static artifact generation)

**Analogs:**
1. `nbformat.v4` cell builders (from RESEARCH.md Code Examples 3)
2. `run.py` (lines 51–124) — section orchestration and chart generation patterns
3. `dashboard.py` (lines 62–295) — section helper functions as cell content sources

**Core pattern — Programmatic notebook generation:**

The notebook builder follows the nbformat.v4 cell-builder pattern from RESEARCH.md Code Examples 3:

```python
import nbformat
from nbformat.v4 import new_notebook, new_code_cell, new_markdown_cell

nb = new_notebook()

# 1. Title
nb.cells.append(new_markdown_cell("# Options Quant — Sleeve Allocation Framework (α Engine)"))
nb.cells.append(new_markdown_cell(f"**Latest update:** {dt.date.today().isoformat()}"))

# 2. Sections A–E from dashboard helpers
nb.cells.append(new_markdown_cell(section_a_state(sigs)))

# 3. Embedded charts (see chart pattern below)
# ... generate figure, convert to PNG, embed ...

# 4. Serialize
with open("sleeve_alpha_latest.ipynb", "w") as f:
    nbformat.write(nb, f)
```

**Chart embedding pattern** (from run.py lines 63–86 + RESEARCH.md Code Examples 3):

```python
import base64
import io

# Generate figure (same pattern as run.py)
fig, axes = plt.subplots(len(sigs_to_plot), 1, figsize=(12, 2 * len(sigs_to_plot)), sharex=True)
for ax, sig in zip(axes, sigs_to_plot):
    sigs.pct[sig].plot(ax=ax, lw=0.9)
    ax.axhline(0.5, color="grey", ls="--", lw=0.5)
    ax.set_ylim(0, 1)
    ax.set_title(f"{sig} (causal 5y pct rank)", fontsize=10)
plt.tight_layout()

# Convert to PNG and embed
buf = io.BytesIO()
fig.savefig(buf, format="png", dpi=110, bbox_inches="tight")
buf.seek(0)
img_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
plt.close(fig)

# Create display output
from nbformat.v4 import new_output
output = new_output(
    output_type='display_data',
    data={'image/png': img_b64}
)

nb.cells.append(new_code_cell("# Chart: Signals time-series"))
nb.cells[-1]['outputs'] = [output]
```

**Section organization** (from dashboard.py lines 298–332):

Use existing section helpers as markdown cell sources:

```python
from dashboard import (
    section_a_state,
    section_b_mechanics,
    section_c_buckets,
    section_d_analog,  # Will be reframed version after Phase 1
    section_e_subperiod,
)
from sensitivity import (
    format_tail_metrics,
    format_tc_grid,
    tail_metrics_table,
    tc_sensitivity_table,
)

# In notebook builder:
nb.cells.append(new_markdown_cell(section_a_state(sigs)))
nb.cells.append(new_markdown_cell(section_b_mechanics()))
nb.cells.append(new_markdown_cell(section_c_buckets(sigs, bt)))
nb.cells.append(new_markdown_cell(section_d_analog(sigs, bt)))  # Reframed version
nb.cells.append(new_markdown_cell(section_e_subperiod(bt)))
nb.cells.append(new_markdown_cell(format_tc_grid(tc_sensitivity_table(bt))))
nb.cells.append(new_markdown_cell(format_tail_metrics(tail_metrics_table(bt))))
```

**Chart style consistency** (from run.py lines 63–86):

Define style dict at module level and reuse:

```python
CHART_STYLE = {
    "figsize": (12, 3),
    "dpi": 110,
    "linewidth": 0.9,
    "fontsize_title": 10,
    "fontsize_legend": 8,
    "figsize_multi": (12, 2.5),  # Per-subplot height
}
```

**Entry point:**

```python
if __name__ == "__main__":
    # No CLI args for POC; hard-code paths
    OUT_DIR = pathlib.Path(".")
    NB_PATH = OUT_DIR / "sleeve_alpha_latest.ipynb"
    
    # Build → serialize once
    panels = build_panels(start="2010-01-01")
    sigs = build_signals(panels)
    bt = run_backtest(panels)
    
    nb = build_notebook(panels, sigs, bt)
    
    with open(NB_PATH, "w") as f:
        nbformat.write(nb, f)
    
    print(f"Notebook saved to {NB_PATH}")
```

---

### `WALKTHROUGH.md` — New Documentation (static, reference guide)

**Analogs:**
1. `local_data.py` docstring (lines 1–24) — module-level framing
2. `dashboard.py` docstrings and section comments (lines 1–48) — section explanation pattern
3. `validate.py` docstring (lines 1–13) — decision framing explanation

**Structure pattern** (one section per dashboard section):

```markdown
# Options Quant — Sleeve Allocation Framework (α Engine)
## Walkthrough Guide — How to Read the Dashboard

**Purpose:** This document explains each section of the weekly decision dashboard, how to interpret it, and its statistical foundations.

**Core principle:** State + exposure + historical context. No scoring. No recommendations. The framework describes what is happening and what happened in similar periods. You synthesize the decision.

---

### Section A — Current Market State

**What it shows:** Today's market conditions measured as percentile ranks on a 5-year rolling window.

**Signals displayed:**
- rv30: 30-day realized volatility (annualized %)
- vrp: Vol risk premium = IV₃₀ - realized vol
- term: Term structure = IV₉₀ - IV₃₀
- skew: Put-skew = IV₉₀%moneyness - IV₃₀%ATM
- trend: Log price / 200-day SMA
- dd: Drawdown = current price / rolling 252-day max

**How to read it:**
- pct rank 0–0.33: "low" → signal in bottom third of 5y history
- pct rank 0.33–0.67: "mid" → median condition
- pct rank 0.67–1.00: "high" → signal in top third of 5y history

**Interpretation note:** High fragility means (high vol premium + steep skew + weak trend + deep drawdown). Conditions that breed defensive sleeve demand.

**Limitations:**
- 5-year window is a POC choice; optimizing lookback is deferred
- Percentile rank is causal (no forward-looking data), but signal definitions themselves are lagged (e.g., rv30 uses past 30d)

**Built with:** Causal rolling-window percentile rank over 5y (1260 trading days), 1y warmup

---

### Section B — Sleeve Mechanics

**What it shows:** One-line description of each sleeve tool.

**Why it's here:** Context for understanding the mean returns in Section C. Not a recommendation.

**Built with:** Static reference text.

---

### Section C — Sleeve Returns by Signal Quartile

**What it shows:** Historical mean monthly returns for each sleeve, broken down by the quartile of a signal **at roll open**.

**Example:** "When VRP was in Q4 (top 25%), covered call returned +1.5% on average."

**How to read it:**
1. Find today's signal in the "today: X → Q?" row
2. Look at that quartile's returns for each sleeve
3. Check if Q4-vs-Q1 difference is significant (marked with ** if Holm-survives, or (raw) if raw p<0.05)

**The Holm-Bonferroni correction:** Because we run many tests (underlyings × signals × sleeves), raw p-values must be adjusted to control family-wise error rate (FWE α=0.05). Holm step-down is our gate:
- `n tests`: How many (underlying × signal × sleeve) comparisons we ran
- Raw p < 0.05: Number that would pass if we ignored multiple comparisons
- Holm-survives: Number that still look significant after family-wise adjustment

**Key insight:** If 0 tests survive Holm (typical), the apparent quartile differences are likely false positives from multiple testing. This is a *feature* not a bug — it's the rigor that lets us trust the framework.

**Limitations:**
- In-sample: these are historical means, not predictions
- Assumes future signal ↔ return relationship is stable (testable with walk-forward; deferred to Phase 6)
- Uses lagged signals at roll open, not real-time (realistic for trading, but causality-safe)

**Built with:** Welch's t-test for Q4-vs-Q1, Holm-Bonferroni FWE correction (α=0.05), stationary block bootstrap Sharpe CI (block ≈ 6m to span autocorrelation)

---

### Section D — Past Periods That Looked Like Now

**What it shows:** K=12 historical periods where the signal vector (vrp, term, skew, trend, dd, fragility) was closest to today, and what the environment realized in the following 1/3/6 months.

**How to read it:**
1. "Today's vector" row: today's percentile ranks on key signals
2. "Closest analogs": K=12 dates where history looked most like today (Euclidean distance in signal space)
3. "Forward-realized environment": For each matched period, what happened to signals 1m, 3m, 6m later

**Example:** "In the past, when vrp was 0.6, term was 0.3, skew was 0.8..., realized vrp shifted to 0.45 over the next month."

**Why this framing:** Pure historical co-movement. No forecast claim. You use this to think: "If the environment typically flows toward [X] after conditions like today, what sleeves do I want to be long?"

**Not what it is:**
- NOT a forecast of where signals will go
- NOT a sleeve return prediction
- NOT a recommendation for which sleeve to pick

**Limitations:**
- K=12 is arbitrary (POC); sensitivity to K untested
- Assumes past co-movements predict future (testable; deferred to Phase 6)
- Only 5y of history; pre-2020 dynamics may not apply to current market
- Does not account for macro catalysts (Fed policy, earnings, geopolitics)

**Built with:** K-nearest neighbors in signal space (Euclidean norm over NEIGHBOR_FEATURES), forward-realized signals at T+1m/3m/6m

---

### Section E — Subperiod Stability

**What it shows:** Same full-period sleeve stats (CAGR, Sharpe, max DD, hit %), but computed on three rough 5y windows.

**How to read it:** Does the sleeve's behavior persist across regimes, or is the full-period number averaging opposite halves?

**Example:** "Collar Sharpe is +0.5 full-period, but +0.8 in 2010–2015 (bull) and +0.3 in 2016–2020 (late-cycle). Caution: less stable in choppy water."

**Limitations:**
- Subperiod boundaries are arbitrary; not regime-detected
- Small sample in each window reduces precision
- Forward-looking regime-detection deferred to Phase γ (optional)

**Built with:** Geometric returns, annualized Sharpe (block bootstrap, block ≈ 6m)

---

### Section G — Transaction Cost Sensitivity

**What it shows:** How sleeve returns degrade under different transaction cost assumptions (0bp, 5bp, 10bp, 20bp round-trip per leg).

**How to read it:** Compare to your actual costs. If you trade at 2bp per leg, results at 5bp are conservative; at 20bp, very conservative.

**Note:** POC assumes symmetric costs; bid-ask skew and slippage are deferred.

---

### Section H — Tail-Risk Metrics

**What it shows:** Expected shortfall (ES) and max monthly drawdown for each sleeve.

**Why it matters:** Downside risk that Sharpe alone doesn't capture.

---

## For the Quant Team

**Open question we want your input on:**

Does your team already have a vol/regime/sleeve-context dashboard we shouldn't duplicate? If so, how does it differ from this one? Are there specific signals or periods you'd want to see recut?

---

## The Question We're Asking You

**If you were running capital, what would have to be true for this framework to inform a real decision?**

Surfaces missing pieces or trust gaps without leading. Use your answer to guide feedback: Is it a data problem? A statistical rigor problem? A model-specification problem? An instrumentation problem (can't execute efficiently)? Something else?

---

## Changelog

- **2026-05-04:** v1 — POC framework with six signals + fragility, Section D reframed to realized environment, Bloomberg calibration in progress.
```

---

## Shared Patterns

### Data Retrieval / Dispatch

**Source:** `local_data.py` lines 140–196 (FreeCon class)
**Apply to:** All data-layer operations that need Bloomberg swap

Pattern: Interface stability + graceful fallback
- Same method signature across implementations (bdh)
- Empty DataFrame return on error (not None, not exception)
- Parquet cache with consistent naming
- Config flag selects which at module level

### Chart Styling (Consistent Across Notebook)

**Source:** `run.py` lines 63–86
**Apply to:** All matplotlib figures embedded in notebook

```python
# Define once at module level
CHART_STYLE = {
    "figsize": (12, 3),
    "dpi": 110,
    "linewidth": 0.9,
    "fontsize_title": 10,
    "fontsize_legend": 8,
    "color_grid": "grey",
}

# Use consistently in all chart builders
fig, axes = plt.subplots(..., figsize=CHART_STYLE["figsize"])
ax.plot(..., lw=CHART_STYLE["linewidth"])
ax.set_title(..., fontsize=CHART_STYLE["fontsize_title"])
ax.axhline(0.5, color=CHART_STYLE["color_grid"], ls="--", lw=0.5)
plt.tight_layout()
```

### Section Helper Reuse

**Source:** `dashboard.py` lines 62–295 (section_a_state, section_c_buckets, etc.)
**Apply to:** All notebook sections

All section_X functions return markdown strings. Reuse directly as cell content:
```python
nb.cells.append(new_markdown_cell(section_a_state(sigs)))
```

No rewrites; import and use as-is.

### Notebook Cell Output Embedding

**Source:** `nbformat.v4` (RESEARCH.md Code Examples 3)
**Apply to:** All chart figures

```python
from nbformat.v4 import new_output
import base64, io

# Generate figure, convert to PNG, embed
buf = io.BytesIO()
fig.savefig(buf, format="png", dpi=110, bbox_inches="tight")
buf.seek(0)
img_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
plt.close(fig)

output = new_output(output_type='display_data', data={'image/png': img_b64})
nb.cells.append(new_code_cell("# Chart"))
nb.cells[-1]['outputs'] = [output]
```

---

## Files to Delete

### `validate.py` — Entire Module (7,982 bytes, 216 lines)

Per D-09 (CONTEXT.md), the walk-forward validation module is deprecated. The negative finding ("0 of 30 rules survive Holm, no rule beats passive OOS") is absorbed into framework understanding. No reuse; clean deletion.

**What depends on it:**
- `run.py` lines 25, 127–133 (imports and Phase 6 call) — remove in `run.py` modification

**Orphan outputs to clean up:**
- `out/walkforward_*.txt` files (generated by validate.py; no longer produced after deletion)

---

## Files with No Analog

None. All files being created or modified have clear analogs in the existing codebase.

---

## Metadata

**Analog search scope:** C:\dev\options-quant\*.py (all module-level files)

**Files scanned:** 12 primary modules (local_data, dashboard, run, validate, data_layer, signals, backtest, stats_rigor, sensitivity, 3 test files)

**Pattern extraction date:** 2026-05-04

**Confidence levels:**
- **BloombergCon class pattern:** HIGH — FreeCon is stable and well-documented; interface contract is clear
- **Section D reframing:** HIGH — Reuse existing K-NN logic, replace only output framing; helper function is straightforward
- **run.py cleanup:** HIGH — Simple import + call removal; no logic changes
- **build_report.py:** MEDIUM-HIGH — nbformat and matplotlib patterns are standard; tested against run.py plotting precedent
- **WALKTHROUGH.md:** MEDIUM — Structure mirrors existing docstrings; content approved by CONTEXT.md decisions

---

**References:**
- `C:\dev\options-quant\.planning\phases\01-poc-delivery\01-CONTEXT.md` — decisions D-01 through D-16
- `C:\dev\options-quant\.planning\phases\01-poc-delivery\01-RESEARCH.md` — standard stack, code examples, pitfalls
- `C:\dev\options-quant\local_data.py` — FreeCon class (lines 140–196)
- `C:\dev\options-quant\dashboard.py` — section helpers (lines 62–295)
- `C:\dev\options-quant\run.py` — orchestrator structure (lines 51–143)
- `C:\dev\options-quant\validate.py` — module to delete (all lines)
