# Phase 1: POC Delivery & Calibration — Research

**Researched:** 2026-05-04
**Domain:** Jupyter notebook generation, Bloomberg data integration, section reframing
**Confidence:** HIGH (locked engine, well-understood patterns; POC implementation straightforward)

## Summary

Phase 1 is a delivery sprint that takes the v2.0 engine (closed, validated, 74 tests passing) and packages it for quant-team evaluation. The work is scoped, straightforward, and mechanically well-defined:

1. **Bloomberg calibration** — Replace synthesized 90mny IV with real `con.bdh('SPX Index', '30DAY_IMPVOL_90.0%MNY_DF', ...)` in `local_data.py`. The `FreeCon` class interface is stable and portable; add a `BloombergCon` class mirroring it, use a config flag to select which.

2. **Notebook artifact** — Build a `.ipynb` from the engine modules using `nbformat` 4.5 (current standard, compatible with locked Jupyter server). Top-of-page current-state strip, drill-down sections (A–E, G–H), embedded charts with regime shading. The section helpers (`section_a_state`, `section_c_buckets`, etc.) already exist in `dashboard.py` and are reusable; the notebook builder stitches them into cells with charts.

3. **Walkthrough doc** — `WALKTHROUGH.md` at repo root explaining each section with how-to-read guidance, statistical methods, and the key question: *"What would have to be true for this to inform a real decision?"*

**Primary recommendation:** Build the notebook programmatically (not manually via Jupyter UI) so it's reproducible and assets can be regenerated weekly without loss. Use `nbformat.v4.new_notebook()` + cell builders, not string-template hacks.

---

## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01:** Primary audience = quant team. Review math, stats, framework rigor before PM presentation.

**D-02:** Cadence = weekly Monday review. Designed for recurring regime check, not ad-hoc triggers.

**D-03:** Most-important sections = **Section A (current state)** + **Section C (conditional history)**. Others are supporting context.

**D-04:** Open question for the team: *Does the team already have a vol/regime/sleeve-context dashboard we shouldn't duplicate?* Capture explicitly in walkthrough doc.

**D-05:** Output medium = **Jupyter notebook (.ipynb)**. Quants read notebooks. Embedded charts + tables + markdown narrative. Closest to eventual Cron2 production target.

**D-06:** Generation = **manual run**. `python build_report.py` Monday morning produces the notebook. No scheduler infra for POC.

**D-07:** Layout = **top-down: current state → drill-down.** Section A leads (with optional week-over-week change vs prior run). Sections B/C/E/G/H follow as supporting context.

**D-08:** Charts = **critical.** Invest in chart quality — labels, palette, regime shading, consistent styling. Quants scan charts before tables.

**D-09:** **Delete `validate.py`.** Walk-forward "find a rule that wins" was forecasting drift. Negative finding (0 of 30 rules survive Holm, no rule beats passive OOS) is absorbed into framework understanding. Clean deletion, no orphan module.

**D-10:** **Section D reframe.** Rename to **"Past Periods That Looked Like Now"**. Replace realized sleeve P&L (forecast-flavored) with **realized environment** — vol/skew/term/drawdown AFTER the analog match. Drops forecast framing, keeps historical-context value.

**D-11:** **Keep Section C bucket means + Welch's t-test + Holm-Bonferroni.** The "0 of 30 tests survive Holm" result is the credibility centerpiece. Do not condense or remove.

**D-12:** **Bloomberg integration BEFORE delivery.** Synthesized 90mny IV (slope=0.2 calibration guess) will get pushback. Swap to real `con.bdh` 30D 90mny IV before showing the team — calibration matters for credibility on put-skew sleeves.

**D-13:** Done bar = **notebook + Bloomberg-calibrated data + written walkthrough doc.** Three deliverables, all required before showing the team.

**D-14:** Handoff = **async first, then meeting.** Send the notebook + walkthrough; let them review for days; then focused discussion.

**D-15:** Sharpest feedback question: **"What would have to be true for this to inform a real decision?"** Path-to-utility question. Surfaces missing pieces or trust gaps without leading.

**D-16:** **Hard scope cap — explicitly OUT:** PDIV / fund specialization, Markov-switching/HMM, any new signals. This phase is delivery + Bloomberg + cleanup, period.

### Claude's Discretion

- Notebook chart styling (palette, regime shading details, font sizes) — pick tasteful defaults
- Walkthrough doc structure (section ordering, depth per section) — draft, user reviews
- Section A "week-over-week change" computation — pick approach, flag the choice in the doc
- Section D reframe specifics — design the "realized environment" output (which signals to show, time horizon, table layout)

### Deferred Ideas (OUT OF SCOPE)

- **PDIV / fund specialization** — dropped 2026-05-04; future phase if team requests after evaluating market-general POC
- **Markov-switching fragility flag** — optional appendix, deferred indefinitely
- **New signals** — six + fragility composite are it; locked until team validates current set
- **Automated weekly schedule** — current decision is manual run; revisit if team uses weekly
- **HTML/PDF/Slack export** — POC ships as .ipynb; revisit if asked
- **Transaction cost calibration to specific broker** — generic 0/5/10/20 bp grid in current dashboard

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Data layer (panels, signals, backtest) | Backend / Python module | — | Engine is pure-Python; math layer is tier-agnostic |
| Notebook generation | Backend (build script) | — | `nbformat` writes .ipynb files; runs as a CLI tool |
| Data source dispatch (Bloomberg vs. free) | Backend (local_data.py) | — | Swap point at data ingestion; math layer unchanged |
| Notebook rendering / display | Browser / Jupyter UI | — | End user views rendered .ipynb in Jupyter; we build the artifact |
| Chart rendering | Browser (Jupyter) | — | Charts are embedded as PNG/SVG in notebook cells; generated by matplotlib in the build script |

---

## Standard Stack

### Core Engine (v2.0, Closed, Reusable)

| Module | Purpose | Reusable? |
|--------|---------|-----------|
| `data_layer.py` | Build panels from raw data. Returns `Panels` dataclass with prices, IV, skew, VIX, rf_rate. | ✓ Yes — schema stable, math layer expects this shape |
| `signals.py` | Six raw signals + causal 5y percentile rank + fragility composite. Returns `Signals` dataclass. | ✓ Yes — unchanged in Phase 1 |
| `backtest.py` | Black-Scholes monthly-roll P&L for four sleeves (CC, CSP, Collar, Strangle). Returns `BacktestResults`. | ✓ Yes — unchanged in Phase 1 |
| `dashboard.py` | Section helpers (`section_a_state`, `section_c_buckets`, `section_d_analog`, `section_e_subperiod`). Text output. | ✓ Yes — section D reframed, others unchanged |
| `stats_rigor.py` | Holm-Bonferroni, Welch's t-test, stationary block bootstrap. | ✓ Yes — unchanged |
| `sensitivity.py` | Transaction cost grid, tail-risk metrics. | ✓ Yes — unchanged |

**All above are untouched by Phase 1 except:**
- `local_data.py` — add `BloombergCon` class; keep `FreeCon` for fallback/POC
- `dashboard.py` — reframe Section D; keep all other sections verbatim

### New in Phase 1

| Tool | Version | Purpose | Why |
|------|---------|---------|-----|
| `nbformat` | 4.5 | Build .ipynb files programmatically from cells + outputs | Standard, lightweight, shipped with Jupyter |
| `matplotlib` | 3.9.0 (locked env) | Generate charts for embedding in notebook | Already in locked env; seamless PNG output to notebook |

**Installation:** Both are already in the locked Cron2 environment. No `pip install` needed.

**Version verification:** [VERIFIED: locked env] `matplotlib 3.9.0`, `nbformat 4.5` are standard in current Jupyter distributions.

---

## Architecture Patterns

### Notebook Builder Pattern

The key task is **reproducible notebook generation**. Instead of editing `.ipynb` JSON by hand (brittle, unmergeable), we:

1. **Use `nbformat.v4`** — programmatic cell builders
2. **Organize as section functions** — each section returns a dict of {cells: [...], outputs: [...]}
3. **Serialize once at the end** — write to `.ipynb` with `nbformat.write()`

**Why this matters:** The planner will likely task this as a single `build_report.py` script that takes no CLI args, pulls latest data, runs the engine, and emits a timestamped `.ipynb`. That script must be **deterministic and idempotent** — running it twice on the same day should produce identical notebooks (modulo timestamps).

### Section D Reframing Pattern

**Current (Section D — "Closest Regime Analogs"):**
- Find K=12 nearest historical roll-opens in signal space
- Report mean/min/max/hit% of realized sleeve P&L from those periods
- **Problem:** This is a *forecast* framing ("if we were in that regime, what would we have earned?") → conflicts with v2.0's "state + history, never prescriptive" principle

**New (Section D — "Past Periods That Looked Like Now"):**
- Find K=12 nearest historical roll-opens in signal space (same matching logic)
- For each matched period, report the **environment that followed** — what did vol/skew/term/drawdown do in the next 1–3 months?
- **Benefit:** Pure description of historical co-movements, no forecast claim. Quant team can synthesize with their own sleeve preferences.

**Implementation:** In `dashboard.py`, `section_d_analog()` currently:
```python
nn_rolls = rolls.loc[nn.index, ["open"] + SLEEVE_COLS]  # ← Current: sleeve returns
# New: nn_rolls should show realized environment signals after the match
```

Reframe to:
```python
# For each matched period close_dt, look forward 1m/2m/3m
# Report what happened to: vrp_pct, skew_pct, term_pct, dd_pct
```

This requires a small helper function that takes a matched date and returns forward-realized signals. Add to `dashboard.py`.

### Chart Styling (Consistent Across All Sections)

**Pattern (from `run.py` example):**
```python
fig, axes = plt.subplots(len(sigs_to_plot), 1, figsize=(12, 2 * len(sigs_to_plot)), sharex=True)
for ax, sig in zip(axes, sigs_to_plot):
    sigs.pct[sig].plot(ax=ax, lw=0.9)
    ax.axhline(0.5, color="grey", ls="--", lw=0.5)
    ax.set_ylim(0, 1)
    ax.set_title(f"{sig} (causal 5y pct rank)", fontsize=10)
    ax.legend(loc="upper left", fontsize=8)
```

**For Phase 1 notebook:**
- Use the same palette and line weights throughout (already consistent in `run.py`)
- Add regime shading (vertical bands for high-fragility periods) to all time-series charts
- Consistent fontsize, margins, tight_layout()
- Save each chart as PNG, embed in notebook as `Image` cell output

### Notebook Cell Organization

Suggested structure for `build_report.py`:

```python
# 1. Setup: nbformat.v4.new_notebook(), import engine modules
nb = nbformat.v4.new_notebook()

# 2. Data Layer (Section 1)
nb.cells.append(nbformat.v4.new_markdown_cell("## Section 1 — Data Layer"))
panels = build_panels()
nb.cells.append(nbformat.v4.new_code_cell(f"# Data summary\nprint({panels.shape_summary()})"))

# 3. Signal Engineering (Section 2)
nb.cells.append(nbformat.v4.new_markdown_cell("## Section 2 — Signals"))
sigs = build_signals(panels)
nb.cells.append(nbformat.v4.new_code_cell(f"# Latest signals\nprint({sigs.latest()})"))

# 4. Section A (Current State)
nb.cells.append(nbformat.v4.new_markdown_cell(section_a_state(sigs)))

# 5. Charts, other sections...
# 6. Serialize
with open("sleeve_alpha_latest.ipynb", "w") as f:
    nbformat.write(nb, f)
```

**Key:** Every cell's **output** is pre-computed (not live) — the notebook is a **static artifact**, not a live Jupyter session. This makes it reproducible and shareable.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Notebook serialization | Custom JSON dict hacks | `nbformat.v4.new_notebook()` + cell builders | nbformat handles version compliance, cell metadata, MIME types; hand-rolled JSON breaks on Jupyter upgrades |
| Section reframing logic (Section D) | Rewrite section_d_analog() from scratch | Extend existing function with a helper for forward-realized signals | Math is correct; only the output framing changes. Reuse avoids introducing bugs in a stable module. |
| Chart generation for embedding | Matplotlib + manual base64 encoding | Matplotlib output → nbformat `Image` cell with PNG bytes | nbformat.v4 handles Image cell construction; manual base64 is error-prone |
| Data-source dispatch logic | Copy `FreeCon.bdh` into Bloomberg branch | Create `BloombergCon` class mirroring `FreeCon` interface, use a config flag to select which | Math layer never touches the dispatch layer; swapping sources should be a one-line config change. Interface consistency prevents math-layer rework. |

**Key insight:** The engine modules (`data_layer`, `signals`, `backtest`, `dashboard`) are stable and tested. Phase 1 is packaging, not rewriting. Reuse section helpers, reuse chart patterns, reuse data contracts. Every line of new code is a liability.

---

## Runtime State Inventory

**Trigger:** This is a refactor/cleanup phase (delete `validate.py`). Audit what runtime systems reference the code being deleted.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| **Stored data** | None — `validate.py` is pure code, no stored keys/IDs | — |
| **Live service config** | None — no external services involved; POC runs locally or on Cron2 | — |
| **OS-registered state** | None — no scheduled tasks or installed CLIs | — |
| **Secrets / env vars** | None — no validate-specific secrets | — |
| **Build artifacts** | `out/walkforward_*.txt` — outputs from `validate.py` walk-forward runs. Code path: `run.py:127` imports and calls `format_walk_forward_report()`. | Delete files; remove import + call in `run.py` |

**Detailed audit of `validate.py` references:**

- `run.py:25` — `from validate import run_walk_forward, format_walk_forward_report`
- `run.py:127` — `wf_df = run_walk_forward(sigs, bt)`
- `run.py:128` — `wf_report = format_walk_forward_report(wf_df)`
- `run.py:131–133` — prints and saves walk-forward results to disk

**Phase 1 action:** Remove lines 127–133 from `run.py` (the walk-forward section); remove the import on line 25. This leaves `run.py` calling `build_dashboard()` → outputs Sections A–E + G–H (no Section F validation yet — that's Phase 6 future work per CONTEXT).

---

## Code Examples

### Example 1: BloombergCon Class (Data Layer Swap Point)

**Source:** Analysis of `local_data.py` `FreeCon` class pattern

The `FreeCon.bdh()` method has this signature:
```python
def bdh(self, ticker: str, field: str, start_date: str, end_date: str) -> pd.DataFrame:
```

It returns a DataFrame indexed by date, single column named `field`. The `_dispatch()` method routes to different providers (CBOE, FRED) based on (ticker, field) tuple.

**For Bloomberg**, create a parallel class:

```python
class BloombergCon:
    """Con.bdh facade using emds_client (Cron2 only)."""
    
    def bdh(self, ticker: str, field: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Return DataFrame indexed by date, column name = field."""
        from emds_client import con  # Cron2 only; import at use site
        try:
            df = con.bdh(ticker, field, start_date, end_date)
            # Normalize: ensure column name is `field`, index is DatetimeIndex
            if df is None or len(df) == 0:
                return pd.DataFrame()
            df = df.copy()
            if len(df.columns) > 0:
                df.columns = [field]
            df.index = pd.DatetimeIndex(df.index).normalize()
            return df
        except Exception as e:
            # Log and return empty so downstream branching works
            print(f"BloombergCon failed: {ticker}/{field}: {e}")
            return pd.DataFrame()

# Config switch: set at module level
USE_BLOOMBERG = False  # Change to True on Cron2
con = BloombergCon() if USE_BLOOMBERG else FreeCon()
```

**In `data_layer.py`:**
```python
from local_data import con  # Agnostic to whether it's Bloomberg or Free
# Everything downstream works verbatim
```

### Example 2: Section D Reframing Helper

**Current code** (dashboard.py, lines 210–257):
```python
def section_d_analog(sigs: Signals, bt: BacktestResults, k: int = K_NEIGHBORS) -> str:
    # ... finds K nearest neighbors in signal space ...
    nn_rolls = rolls.loc[nn.index, ["open"] + SLEEVE_COLS]
    # ... reports realized sleeve returns from those analogs ...
```

**Refactor to add forward-realized environment:**

```python
def _forward_realized_environment(close_dt: pd.Timestamp, sigs: Signals, 
                                    horizons: list[int] = [21, 63, 126]) -> dict:
    """For a given match date, return realized signals 1m/2m/3m forward.
    
    horizons: [21, 63, 126] ~ [1m, 3m, 6m] trading days
    Returns dict of {horizon_days: signal_dict_at_that_horizon}}
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

def section_d_analog_reframed(sigs: Signals, bt: BacktestResults, k: int = K_NEIGHBORS) -> str:
    """Past Periods That Looked Like Now — realized environment after match."""
    last_dt = sigs.latest_date()
    out = [
        "## Section D — Past Periods That Looked Like Now",
        "",
        f"K={k} nearest historical roll-opens, Euclidean distance over signal vector:",
        f"  features: {', '.join(NEIGHBOR_FEATURES)}",
        "For each matched period, the realized environment (signals) in the following 1/3/6 months.",
        "",
    ]
    for u in bt.rolls:
        rolls = bt.rolls[u]
        today_vec = np.array([sigs.pct[s].loc[last_dt, u] for s in NEIGHBOR_FEATURES])
        if np.isnan(today_vec).any():
            out.append(f"### {u}: today's vector has NaN — skipping")
            continue
        
        # Find neighbors (same logic as before)
        feat = pd.DataFrame({
            s: sigs.pct[s].reindex(rolls["open"].values)[u].values
            for s in NEIGHBOR_FEATURES
        }, index=rolls.index)
        feat = feat.dropna()
        d = np.linalg.norm(feat.values - today_vec, axis=1)
        feat["_d"] = d
        nn = feat.nsmallest(k, "_d")
        
        out.append(f"### {u}")
        out.append(f"Today's vector: " + ", ".join(
            f"{s}={v:.2f}" for s, v in zip(NEIGHBOR_FEATURES, today_vec)
        ))
        out.append("")
        
        # NEW: Report forward-realized environment for each match
        for close_dt, dist in nn["_d"].items():
            open_dt = rolls.loc[close_dt, "open"]
            out.append(f"  Match: open {open_dt.date()}  close {close_dt.date()}  d={dist:.3f}")
            
            fwd = _forward_realized_environment(close_dt, sigs, horizons=[21, 63, 126])
            for h, sig_dict in fwd.items():
                if sig_dict is None:
                    out.append(f"    {h}d forward: (no data)")
                else:
                    out.append(f"    {h}d forward: vrp={sig_dict.get('vrp', np.nan):.2f}, " +
                               f"skew={sig_dict.get('skew', np.nan):.2f}, " +
                               f"term={sig_dict.get('term', np.nan):.2f}, " +
                               f"dd={sig_dict.get('dd', np.nan):.2f}")
            out.append("")
    
    return "\n".join(out)
```

Replace `section_d_analog()` call in `build_dashboard()` with this new version. Keep section logic simple; avoid over-engineering.

### Example 3: Notebook Cell Builder

**Pattern (from `nbformat.v4`):**

```python
import nbformat
from nbformat.v4 import new_notebook, new_code_cell, new_markdown_cell

nb = new_notebook()

# Title
nb.cells.append(new_markdown_cell("# Options Quant — Sleeve Allocation Framework (α Engine)"))
nb.cells.append(new_markdown_cell(f"**Latest update:** {dt.date.today().isoformat()}"))

# Section A: Current State
state_md = section_a_state(sigs)  # Returns markdown string from dashboard.py
nb.cells.append(new_markdown_cell(state_md))

# Chart: Signal time series
fig, axes = plt.subplots(len(sigs_to_plot), 1, figsize=(12, 2 * len(sigs_to_plot)), sharex=True)
# ... populate axes ...
plt.tight_layout()

# Convert figure to PNG bytes and embed
import io
buf = io.BytesIO()
fig.savefig(buf, format="png", dpi=110, bbox_inches="tight")
buf.seek(0)
img_bytes = buf.getvalue()
plt.close(fig)

# Create an output object for the notebook
from nbformat.from_dict import from_dict
output = {
    'data': {'image/png': ...base64 encode img_bytes...},
    'metadata': {},
    'output_type': 'display_data'
}
nb.cells.append(new_code_cell("# [Chart embedded above]"))
nb.cells[-1]['outputs'] = [output]

# Serialize
with open("sleeve_alpha_latest.ipynb", "w") as f:
    nbformat.write(nb, f)
```

**Better pattern:** Use nbformat's built-in Image support:

```python
from nbformat.v4 import new_output

# After generating figure fig:
import base64
import io
buf = io.BytesIO()
fig.savefig(buf, format="png", dpi=110, bbox_inches="tight")
buf.seek(0)
img_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

output = new_output(
    output_type='display_data',
    data={'image/png': img_b64}
)

nb.cells.append(new_code_cell("# Chart"))
nb.cells[-1]['outputs'] = [output]
```

---

## Common Pitfalls

### Pitfall 1: Notebook Generation Without Clearing Outputs

**What goes wrong:** Build script generates a notebook with old outputs still in cells from a previous manual run. Notebook appears correct but contains stale/phantom data.

**Why it happens:** Tempting to use Jupyter UI to prototype, then wrap it in a script. Leftover cell outputs and metadata don't get serialized correctly.

**How to avoid:** Always start with `nbformat.v4.new_notebook()` (blank). Never modify an existing `.ipynb` file in place. Build → serialize → done. If reproducing a notebook for archival, delete the old one first.

**Warning signs:** "Why is this chart showing 2025 data when I just updated to 2026?" → Check the notebook's cell outputs; they're stale.

---

### Pitfall 2: Section D Reframing Introduces Forecasting Language

**What goes wrong:** Reframing code says "when the environment matched, here's what typically happened next" → sounds like a forecast again. Quants catch this.

**Why it happens:** Section D's original framing was "here's what happened in similar past periods" (historical). Temptation is to say "and here's what to expect next" (forecast). These are the same phrase with different implications.

**How to avoid:** Strict language discipline. Always say "realized" and "historical," never "expected" or "likely" or "typically." Use past tense. "In the following month, realized vol was [X]" is OK. "Vol will probably be [X]" is not.

**Warning signs:** Quant team's first question: "Is this a forecast? We have our own macro forecasts." → If the answer is ambiguous, reframe.

---

### Pitfall 3: Bloomberg Integration Only on Cron2, Breaks Locally

**What goes wrong:** Code assumes `emds_client` is available; runs fine on Cron2, crashes locally with "module not found."

**Why it happens:** Switching from `FreeCon` (free sources) to `BloombergCon` (Bloomberg) without making the switch **optional**.

**How to avoid:** Config flag at module level. Default to `FreeCon` for backward compatibility. Only switch if explicitly enabled or if `emds_client` is importable.

```python
try:
    from emds_client import con as bloomberg_con
    BLOOMBERG_AVAILABLE = True
except ImportError:
    BLOOMBERG_AVAILABLE = False

# At use site in local_data.py:
if BLOOMBERG_AVAILABLE and USE_BLOOMBERG:
    con = BloombergCon()
else:
    con = FreeCon()  # Fallback
```

**Warning signs:** "Works on Cron2, ImportError locally" → Check the config flag and fallback logic.

---

### Pitfall 4: Chart Styling Inconsistency Across Sections

**What goes wrong:** Different sections use different font sizes, palettes, line widths. Dashboard looks cobbled together. Quants lose confidence in the rigor.

**Why it happens:** Each chart generated independently; no shared style guide.

**How to avoid:** Define a chart style dict at the top of `build_report.py`:

```python
CHART_STYLE = {
    "figsize": (12, 3),
    "dpi": 110,
    "linewidth": 0.9,
    "fontsize_title": 10,
    "fontsize_legend": 8,
    "color_palette": plt.cm.Set2,
}
```

Use it consistently in all chart-building functions. Test the notebook visually before handoff.

**Warning signs:** "These charts look professional but… is that intentional?" → Not enough consistency.

---

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DATA-06 | SPX, QQQ price + 30d ATM IV + 30d 90%-moneyness IV pulled via `con.bdh` | `BloombergCon` class swaps data source; schema unchanged; data_layer.py is portable |
| SIG-01..08 | Signal engineering: realized vol, VRP, skew, trend, drawdown, fragility, pct-rank, QA | signals.py unchanged; reusable in notebook |
| SLV-01..07 | Sleeve backtest (BS pricing, monthly roll P&L, stats) | backtest.py unchanged; reusable |
| SCR-01..04 | Sleeve scorecard: linear rule, ranks, weights, top-2 drivers | Implicit in section_a_state() and section_c_buckets() — will be visible in notebook |
| OUT-01..05 | PM-grade output: dashboard table, auto-commentary, charts, parquet snapshots | Notebook cell structure provides OUT-01..04; parquet snapshots via backtest.run_backtest() |
| VAL-01..06 | Validation gates (causality, sleeve-sign, turnover, tail-risk, robustness, trust) | Phase 6 future; validate.py deleted this phase; framework understanding stands |

---

## Validation Architecture

> `workflow.nyquist_validation` not found in config.json; treating as enabled.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (74 tests, existing) |
| Config file | `pytest.ini` or `pyproject.toml` (if present) |
| Quick run command | `pytest tests/ -x --tb=short` |
| Full suite command | `pytest tests/` |

### Phase 1 Verification Strategy

Phase 1 is integration/delivery, not algorithmic. The engine (v2.0) is already tested (74 tests passing). Phase 1 testing focuses on:

1. **Data layer swap:** BloombergCon class mirrors FreeCon interface → test that both classes produce the same DataFrame shape and column names.
2. **Notebook serialization:** Check that `build_report.py` emits valid `.ipynb` with all expected cells and outputs.
3. **Section reframing:** Section D new logic doesn't crash on edge cases (NaN, no future data).

### Phase 1 Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command |
|--------|----------|-----------|-------------------|
| DATA-06 | BloombergCon.bdh() returns DataFrame like FreeCon | unit | `pytest tests/test_local_data.py::test_bloombergcon_interface -x` |
| VAL-01 | Causality preserved in data_layer (no future leak) | unit | `pytest tests/test_data_layer.py::test_causal_index -x` |
| OUT-01 | Notebook artifact builds without crashing | integration | `python build_report.py && test -f sleeve_alpha_latest.ipynb` |
| D-10 | Section D forward-realized logic doesn't crash on edge cases | unit | `pytest tests/test_dashboard.py::test_section_d_forward_realized -x` |

### Wave 0 Gaps
- [ ] `tests/test_local_data.py::test_bloombergcon_interface` — mirrors FreeCon exactly; both return single-column DataFrame
- [ ] `tests/test_dashboard.py::test_section_d_forward_realized` — edge cases: no future data, NaN signals, K > available analogs
- [ ] `build_report.py` — notebook builder script; can be minimal for POC (no CLI args, hard-coded paths)
- [ ] Manual review of notebook output — quants check chart quality, section order, language tone

**If none of these exist:** Create minimal pytest tests for (1) data interface parity, (2) section D edge-case handling. Notebook build testing is best done as a one-off manual check on Cron2 before delivery.

---

## Security Domain

**`security_enforcement` not specified in config.json; treating as enabled.**

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | — (no user login; Cron2 env controls access) |
| V3 Session Management | No | — (notebook is static artifact) |
| V4 Access Control | Partial | Cron2 Jupyter env manages who can run build_report.py |
| V5 Input Validation | Yes | DataFrame schema validation; emds_client con.bdh sanitizes tickers/fields |
| V6 Cryptography | No | No crypto in Phase 1; Bloomberg connection (on Cron2) is pre-auth'd |
| V7 Error Handling | Yes | Exceptions in data fetch → fallback to FreeCon or empty DataFrame; no secrets leaked |

### Known Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Ticker injection (e.g., `SPX"; DROP TABLE--`) | Tampering | emds_client.con.bdh() pre-validates; we pass through, not construct SQL |
| DataFrame index manipulation (NaN/Inf injection) | Tampering | numpy/pandas reject non-numeric values; BS pricing guards against Inf (T <= 0 check) |
| Stale data from cache | Integrity | `_is_stale()` check; max 5 trading days; warning printed if exceeded |
| No data / empty response handling | Availability | Code branches on empty DataFrame; math layer uses dropna() — safe defaults |

**Confidence:** [HIGH] No novel security exposure in Phase 1. Reuses closed v2.0 engine (which passed 74 tests including boundary conditions). Only new code is notebook builder (nbformat + matplotlib) and BloombergCon wrapper (passthrough to emds_client).

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| pandas | Data layer | ✓ | 1.5.2 (locked env) | — |
| numpy | Signals, backtest | ✓ | 1.23.5 (locked env) | — |
| matplotlib | Chart generation | ✓ | 3.9.0 (locked env) | — |
| nbformat | Notebook generation | ✓ | 4.5 (standard Jupyter) | — |
| emds_client | Bloomberg data (Phase 1 Bloomberg path) | ✗ (local POC) | N/A | FreeCon (fallback to CBOE+FRED) |
| Jupyter Notebook | Rendering | ✓ | Latest (Cron2 server) | — |

**Summary:** All Phase 1 core dependencies are available locally and on Cron2. Bloomberg integration requires Cron2 (emds_client import), but code gracefully falls back to FreeCon on local POC (no errors, warnings only).

**Missing dependencies with fallback:** emds_client → use FreeCon (free sources, synthetic 90mny IV) for POC dev; Bloomberg swap happens only on Cron2.

---

## Open Questions

1. **Section D forward-realized signals: which time horizons?**
   - What we know: 1m/3m/6m are reasonable (21d/63d/126d trading days)
   - What's unclear: Should we show realized or expectation? Volatility of the environment or point estimate?
   - Recommendation: Show point estimates (single row per horizon per match); quant team can aggregate or compute band. Keep it simple.

2. **Week-over-week change in Section A: how to compute?**
   - What we know: User wants to surface changes vs. last week's run
   - What's unclear: Delta of pct-rank? Raw signal value? Absolute or relative?
   - Recommendation: Save latest snapshot to a JSON file each run; next week's run compares pct-rank (on 5y window) vs. prior week's rank. Report Δrank (e.g., "vrp was 0.45 last week, 0.52 today → +0.07").

3. **Does the quant team already have a vol/regime/sleeve dashboard?**
   - What we know: This is an explicit ask in D-04.
   - What's unclear: Scope/frequency/coverage of any existing dashboard
   - Recommendation: Capture this as an explicit question in WALKTHROUGH.md; ask at the team meeting before formalizing Phase 2 extensions.

---

## Open Questions Captured for Quant Team

**From D-04 (to capture in WALKTHROUGH.md):**
> **For the team:** Does your team already have a vol/regime/sleeve-context dashboard that we shouldn't duplicate? If so, how does it differ from this one? Are there specific signals or periods you'd want to see recut?

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `nbformat.v4` is the standard Jupyter notebook format version | Standard Stack | If Cron2 uses an older nbformat, the notebook won't render. Mitigation: check Cron2 notebook version on first run. |
| A2 | Section D's forward-realized signals are more credible than sleeve P&L for the quant team | Code Examples | If the team wants realized P&L not signals, the reframe is wrong. Mitigation: user approval in WALKTHROUGH.md before implementation. |
| A3 | BloombergCon can mirror FreeCon.bdh() interface exactly (single-column DataFrame output) | Architecture Patterns | If Bloomberg returns multi-column or different index type, data_layer.py breaks. Mitigation: test on Data.ipynb first (confirmed working Bloomberg patterns). |
| A4 | `emds_client.con.bdh()` is available and working on Cron2 for SPX, QQQ, VIX, USGG3M | Environment Availability | If emds_client is down or moved, Bloomberg path fails. Mitigation: fallback to FreeCon; user verification on Cron2 before delivery. |

---

## Sources

### Primary (HIGH confidence)
- `C:\dev\options-quant\local_data.py` — FreeCon class interface, _dispatch pattern, VERIFIED in codebase
- `C:\dev\options-quant\data_layer.py` — build_panels() return type (Panels dataclass), VERIFIED
- `C:\dev\options-quant\dashboard.py` — section helpers (section_a_state, section_c_buckets, section_d_analog, section_e_subperiod), VERIFIED in code
- `C:\dev\options-quant\signals.py` — Signals dataclass and causal_pct_rank pattern, VERIFIED
- `C:\dev\options-quant\backtest.py` — BacktestResults, SLEEVE_COLS, BS pricing, VERIFIED
- `C:\dev\options-quant\validate.py` — walk-forward logic, output to `walkforward_*.txt`, VERIFIED in code
- `C:\dev\options-quant\run.py` — orchestrator calling validate module, lines 25/127–133, VERIFIED

### Secondary (MEDIUM confidence)
- [CITED: nbformat docs] https://nbformat.readthedocs.io/ — nbformat.v4.new_notebook(), cell builders, standard patterns
- [CITED: Jupyter docs] https://jupyter-notebook.readthedocs.io/ — notebook rendering, cell outputs, PNG embedding
- [VERIFIED: locked env] matplotlib 3.9.0, pandas 1.5.2 in Cron2 environment (per CLAUDE.md)

---

## Metadata

**Confidence breakdown:**
- **Standard Stack:** HIGH — All libraries already in locked env, patterns verified in closed v2.0 code
- **Architecture (notebook generation):** HIGH — nbformat is standard, pattern is straightforward
- **Architecture (Section D reframe):** MEDIUM — Reframe logic is clear, but quant-team buy-in needed on forward-realized signals
- **BloombergCon interface:** HIGH — FreeCon pattern is stable, data_layer.py contract is clear
- **Pitfalls:** HIGH — Drawn from closed v2.0 experience; patterns consistent

**Research date:** 2026-05-04
**Valid until:** 2026-05-18 (POC delivery expected within 2 weeks; locked dependencies are stable)

---

## Summary of Key Decisions for Planner

1. **Notebook generation is programmatic**, not manual. Use `nbformat.v4` cell builders. Output is a static `.ipynb` artifact, reproducible week to week.

2. **BloombergCon class** adds Bloomberg swap point to `local_data.py` without touching the math layer. Config flag selects which. Fallback to FreeCon for POC.

3. **Section D reframe** from "realized sleeve P&L from analogs" to "realized environment signals after analog match." Requires new helper function in `dashboard.py`, no other changes.

4. **Delete `validate.py`** and its import/call in `run.py` (lines 25, 127–133). Walk-forward section is omitted from v2.1 output.

5. **Chart styling** must be consistent across all sections (palette, linewidth, font sizes). Define a style dict, reuse.

6. **Week-over-week change in Section A** is a discretionary feature; suggested implementation is to snapshot prior week's pct-ranks and diff.

7. **WALKTHROUGH.md** is critical deliverable. Explain every section, its limits, and the key question: "What would have to be true for this to inform a real decision?"

8. **All three deliverables must ship together:** notebook + WALKTHROUGH.md + verified Bloomberg data. No partial handoff.
