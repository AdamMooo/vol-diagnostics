# Phase 2: Regime Model - Pattern Map

**Mapped:** 2026-04-22  
**Files analyzed:** 1 (hmm.ipynb cells to be created)  
**Analogs found:** 7/7 (all Phase 1 cells provide patterns for Phase 2)

## File Classification

| New Cell(s) | Role | Data Flow | Closest Phase 1 Analog | Match Quality |
|---|---|---|---|---|
| **2.1 HMM Fit & Decoding** | compute | CRUD (fit model, extract states) | Phase 1 Setup & Data Load | role-match |
| **2.2 Regime Statistics & Labeling** | compute/analysis | transform (split series, compute stats) | Phase 1 Summary Stats cell | exact |
| **2.3 Regime Duration Validation** | validation | analysis (spell detection) | Phase 1 EDA charts (time series processing) | role-match |
| **2.4 Seed Stability Check** | validation | batch iteration (10 refits) | Phase 1 Summary Stats (loop for audit) | role-match |
| **2.5 Posterior Probability Chart** | visualization | transform → visualization | Phase 1 EDA Charts cell | exact |
| **(implicit) Output Variables** | state | data pipeline | Phase 1 Alignment cell (`fund_aligned`, `bench_aligned`) | exact |

**Rationale:** Phase 2 cells operate within the same Jupyter notebook, using the same data structures (pandas Series with DatetimeIndex), the same import patterns, and the same visualization setup (matplotlib with `figsize=(12, 4)`, color constants from Setup cell). Phase 1 established the foundational patterns for data handling, statistics computation, and charting that Phase 2 directly inherits.

---

## Pattern Assignments

### Phase 2 Cell 2.1: HMM Fit & Decoding

**Role:** Compute | **Data Flow:** Model fitting + Viterbi decoding

**Analog:** Phase 1 Setup cell (lines 1-10, imports and constants) + Phase 1 Data Load cell (variable instantiation and error handling)

**Imports pattern** (from Phase 1 Setup):
```python
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from hmmlearn.hmm import GaussianHMM

# (Constants COLOR_FUND, COLOR_BENCH, COLOR_DD already defined in Phase 1 Setup)
```

**Key variable input** (consumed from Phase 1 Alignment cell):
```python
# bench_aligned is a pd.Series with DatetimeIndex, daily log returns
# Shape: (n_observations,), dtype=float64, index=DatetimeIndex
# This variable was produced in Phase 1, cell 4 (Alignment cell)
```

**Core HMM Fitting pattern** (from 02-RESEARCH.md Code Examples):
```python
# Reshape bench_aligned to 2D for hmmlearn (required)
X = bench_aligned.values.reshape(-1, 1)

# Instantiate 2-state Gaussian HMM
model = GaussianHMM(n_components=2, covariance_type='diag', 
                    n_iter=100, tol=1e-4, random_state=0)

# Fit on benchmark returns
model.fit(X)

# Check convergence (critical step — do not skip)
print(f"Converged: {model.monitor_.converged}")
print(f"Log-likelihood: {model.score(X):.4f}")

# Extract model parameters for inspection
print(f"Transition matrix:\n{model.transmat_}")
print(f"Mean returns per state: {model.means_.flatten()}")
print(f"Volatility per state: {np.sqrt(model.covars_.flatten())}")
```

**Viterbi Decoding pattern** (from 02-RESEARCH.md Pattern 2):
```python
# Decode most likely state sequence using Viterbi algorithm
state_sequence = model.predict(X)

# Create labeled Series aligned to dates (analog to Phase 1 fund_aligned/bench_aligned pattern)
regime_decoded = pd.Series(state_sequence, index=bench_aligned.index)
regime_decoded.name = 'regime_state'

# Inspect state counts (similar to Phase 1 frequency checks)
print(f"State 0 observations: {(regime_decoded == 0).sum()}")
print(f"State 1 observations: {(regime_decoded == 1).sum()}")
```

**Error handling pattern** (from Phase 1 Data Load — simple validation):
```python
# Validate input shape
assert len(bench_aligned) > 100, "Not enough observations for HMM fitting"
assert bench_aligned.isnull().sum() == 0, "bench_aligned contains NaN — alignment failed"

# Validate model convergence
if not model.monitor_.converged:
    print(f"WARNING: EM algorithm did not converge (iterations={model.n_iter})")
    print(f"  Consider increasing n_iter or loosening tol")
```

---

### Phase 2 Cell 2.2: Regime Statistics & Labeling

**Role:** Compute/Analysis | **Data Flow:** Transform (split by state, compute stats, apply logic)

**Analog:** Phase 1 Summary Statistics cell (lines 8deea6af, `compute_summary_stats()` function)

**Function structure pattern** (reuse Phase 1 `compute_summary_stats`):
```python
# Phase 1 already defined this function in cell 6 — reuse it directly
# compute_summary_stats(returns_series, risk_free_rate=0.02)
# returns: dict with 'Annual Return', 'Annual Volatility', 'Sharpe Ratio', 'Max Drawdown'

# Compute stats for each regime state
state_0_returns = bench_aligned[regime_decoded == 0]
state_1_returns = bench_aligned[regime_decoded == 1]

stats_0 = compute_summary_stats(state_0_returns, risk_free_rate=0.02)
stats_1 = compute_summary_stats(state_1_returns, risk_free_rate=0.02)
```

**Composite labeling pattern** (from 02-RESEARCH.md Pattern 3):
```python
# Majority vote across three signals: mean return, vol, Sharpe
# Higher return → +1 for Risk-On
# Lower vol → +1 for Risk-On
# Higher Sharpe → +1 for Risk-On
# Majority (≥2 of 3) → Risk-On; else Risk-Off (Decision D-01)

def label_states_by_composite(stats_0, stats_1):
    """Return (label_0, label_1, score_0) via majority vote on three signals."""
    
    score_0 = 0
    score_0 += 1 if stats_0['Annual Return'] > stats_1['Annual Return'] else 0
    score_0 += 1 if stats_0['Annual Volatility'] < stats_1['Annual Volatility'] else 0
    score_0 += 1 if stats_0['Sharpe Ratio'] > stats_1['Sharpe Ratio'] else 0
    
    label_0 = 'Risk-On' if score_0 >= 2 else 'Risk-Off'
    label_1 = 'Risk-Off' if score_0 >= 2 else 'Risk-On'
    
    return label_0, label_1, score_0

label_0, label_1, score_0 = label_states_by_composite(stats_0, stats_1)
```

**Stats display table pattern** (from Phase 1 Summary Stats cell, lines 254-258):
```python
# Create DataFrame for audit (Decision D-02)
stats_df = pd.DataFrame({
    'State 0': stats_0,
    'State 1': stats_1,
}).T

# Format for readability (same pattern as Phase 1 cell 6)
fmt_table = stats_df.copy()
for col in ['Annual Return', 'Annual Volatility', 'Max Drawdown']:
    fmt_table[col] = stats_df[col].apply(lambda x: f'{x:.2%}')
fmt_table['Sharpe Ratio'] = stats_df['Sharpe Ratio'].apply(lambda x: f'{x:.2f}')

print("=== REGIME STATISTICS ===")
print(fmt_table.to_string())
print(f"\nComposite Score (State 0): {score_0}/3 signals won")
print(f"Label Assignment: State 0 → {label_0}, State 1 → {label_1}")
```

**Output variable creation** (analog to Phase 1 Alignment cell output pattern):
```python
# Create regime_labels Series — canonical name for downstream (Phase 3, Phase 4)
regime_labels = regime_decoded.map({0: label_0, 1: label_1})
regime_labels.name = 'regime_label'

print(f"\nRegime labels distribution:")
print(regime_labels.value_counts())
print(f"Output variable ready: regime_labels ({len(regime_labels):,} observations)")
```

---

### Phase 2 Cell 2.3: Regime Duration Validation

**Role:** Validation | **Data Flow:** Analysis (spell detection on decoded sequence)

**Analog:** Phase 1 EDA Charts cell (lines 023f3f85, time series processing with `.shift()`, `.rolling()`, `.expanding()`)

**Spell detection pattern** (from 02-RESEARCH.md Pattern 4, pandas time series style):
```python
# Detect regime spell boundaries using shift (same pattern as Phase 1 rolling analysis)
regime_change = regime_labels.astype(str) != regime_labels.astype(str).shift(1)

# Assign spell ID to each regime period
spell_id = regime_change.cumsum()

# Build spell detail table (same structure as Phase 1 summary)
spells = []
for sid in spell_id.unique():
    if pd.isna(sid):
        continue
    mask = spell_id == sid
    regime_in_spell = regime_labels[mask].iloc[0]
    start_date = regime_labels[mask].index[0]
    end_date = regime_labels[mask].index[-1]
    length_days = (end_date - start_date).days + 1
    length_weeks = length_days / 7
    
    spells.append({
        'Regime': regime_in_spell,
        'Start': start_date.strftime('%Y-%m-%d'),
        'End': end_date.strftime('%Y-%m-%d'),
        'Duration (days)': length_days,
        'Duration (weeks)': f"{length_weeks:.1f}",
    })

spells_df = pd.DataFrame(spells)
```

**Duration statistics print pattern** (from Phase 1 Summary Stats cell, simple print output):
```python
# Compute mean/median duration per regime (Decision D-06)
print("\n=== REGIME DURATION ANALYSIS ===")
for regime in ['Risk-On', 'Risk-Off']:
    regime_spells = spells_df[spells_df['Regime'] == regime]['Duration (days)']
    
    mean_duration = regime_spells.mean()
    median_duration = regime_spells.median()
    mean_weeks = mean_duration / 7
    median_weeks = median_duration / 7
    n_spells = len(regime_spells)
    
    print(f"{regime}:")
    print(f"  Mean: {mean_duration:.0f}d (~{mean_weeks:.1f}wk)")
    print(f"  Median: {median_duration:.0f}d (~{median_weeks:.1f}wk)")
    print(f"  N spells: {n_spells}")

# Temporal stability check
stability_ok = all(
    spells_df[spells_df['Regime'] == regime]['Duration (days)'].mean() >= 7
    for regime in ['Risk-On', 'Risk-Off']
)
print(f"\nTemporal Stability (mean ≥ 7 days): {'PASS' if stability_ok else 'WARN'}")
```

---

### Phase 2 Cell 2.4: Seed Stability Check

**Role:** Validation | **Data Flow:** Batch iteration (10 refits with comparison)

**Analog:** Phase 1 would be a loop structure (not present in Phase 1, but follows the same pattern as Phase 1 function definition + iteration)

**Multi-refit pattern** (from 02-RESEARCH.md Pattern 5):
```python
# Baseline fit (seed 0) — reuse the model fitted in cell 2.1
X = bench_aligned.values.reshape(-1, 1)

# Baseline (already fitted above as 'model')
baseline_states = model.predict(X)

# Refits with seeds 1–9 (Decision D-04)
agreement_fractions = []
seed_results = []

for seed in range(1, 10):
    model_seed = GaussianHMM(n_components=2, covariance_type='diag', 
                              n_iter=100, tol=1e-4, random_state=seed)
    model_seed.fit(X)
    states_seed = model_seed.predict(X)
    
    # Account for label swap (compare both alignments, take max)
    agreement_direct = np.mean(states_seed == baseline_states)
    agreement_swap = np.mean((1 - states_seed) == baseline_states)
    agreement = max(agreement_direct, agreement_swap)
    
    agreement_fractions.append(agreement)
    seed_results.append({
        'seed': seed,
        'agreement': agreement,
        'status': '✓' if agreement >= 0.90 else '✗'
    })
```

**Stability summary print pattern** (from Phase 1 Summary Stats cell, print-based output):
```python
# Summary output (Decision D-04, D-05)
stable_seeds = sum(1 for a in agreement_fractions if a >= 0.90)
total_refits = len(agreement_fractions)

print("\n=== SEED STABILITY CHECK ===")
print(f"Baseline fit (seed 0) vs. seeds 1–9:")
for result in seed_results:
    print(f"  Seed {result['seed']}: {result['agreement']:.1%} agreement {result['status']}")

print(f"\nSummary: {stable_seeds}/{total_refits} seeds ≥90% agreement with baseline.")

if stable_seeds >= 8:
    print("Status: STABLE - Model is robust to random initialization.")
else:
    print("Status: UNSTABLE - Model may be sensitive to initialization.")
    print("  Consider: increasing n_iter, loosening tol, reviewing data quality")
```

---

### Phase 2 Cell 2.5: Posterior Probability Chart

**Role:** Visualization | **Data Flow:** Transform (extract posterior) → Visualization (line chart)

**Analog:** Phase 1 EDA Charts cell (lines 023f3f85, `plt.subplots(figsize=(12, 4))` pattern with color constants)

**Posterior extraction pattern** (from 02-RESEARCH.md Pattern 6):
```python
# Extract posterior probabilities from fitted model
posteriors = model.predict_proba(X)
# Shape: (n_observations, 2), columns: [P(state 0), P(state 1)]

# Determine which state is Risk-On (set in cell 2.2)
risk_on_state = 0 if label_0 == 'Risk-On' else 1

# Create regime_posteriors Series (canonical name for Phase 5)
regime_posteriors = pd.Series(posteriors[:, risk_on_state], 
                              index=bench_aligned.index)
regime_posteriors.name = 'p_risk_on'

print(f"Posterior probability stats:")
print(f"  Mean P(Risk-On): {regime_posteriors.mean():.2%}")
print(f"  Min: {regime_posteriors.min():.2%}, Max: {regime_posteriors.max():.2%}")
print(f"  Days with P(Risk-On) > 0.5: {(regime_posteriors > 0.5).sum()}")
```

**Chart pattern** (exact reuse of Phase 1 EDA Charts style):
```python
# Create figure with Phase 1 standard dimensions and color constants
fig, ax = plt.subplots(figsize=(12, 4))

# Plot P(Risk-On) line using COLOR_BENCH from Phase 1 Setup
# (Decision D-03: use Risk-On regime color from Phase 1 palette)
risk_on_color = COLOR_BENCH  # or override with project-specific constant if defined

ax.plot(regime_posteriors.index, regime_posteriors.values, 
        label='P(Risk-On)', linewidth=2, color=risk_on_color)

# Decision boundary at 0.5
ax.axhline(y=0.5, color='gray', linestyle='--', linewidth=1, alpha=0.7, 
           label='Decision boundary (0.5)')

# Formatting (same pattern as Phase 1 EDA charts)
ax.set_xlabel('Date')
ax.set_ylabel('Posterior Probability')
ax.set_title('Regime Posterior Probability: P(Risk-On)')
ax.set_ylim(0, 1)
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:.0%}'))
ax.legend()
ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.show()
```

---

## Shared Patterns

### Data Structure Pattern: DatetimeIndex Series

**Source:** Phase 1 Alignment cell (lines 4d62927f)  
**Apply to:** All Phase 2 output variables

Phase 1 established `fund_aligned` and `bench_aligned` as the canonical data structure: `pd.Series` with `DatetimeIndex` and a `.name` attribute. Phase 2 follows the same pattern for `regime_labels`, `regime_decoded`, and `regime_posteriors`. This ensures seamless downstream consumption in Phase 3 and Phase 4.

```python
# Phase 1 pattern (cell 4):
fund_aligned = aligned_returns['fund']
fund_aligned.name = 'fund'
# Result: pd.Series with DatetimeIndex, .name attribute, zero NaN

# Phase 2 analog (cell 2.2):
regime_labels = regime_decoded.map({0: label_0, 1: label_1})
regime_labels.name = 'regime_label'
# Same structure: pd.Series with DatetimeIndex, .name attribute, zero NaN
```

---

### Function Definition Pattern: Reusable Statistics Functions

**Source:** Phase 1 Summary Statistics cell (lines 8deea6af, `compute_summary_stats()`)  
**Apply to:** Phase 2 Regime Statistics cell

Phase 1 defined `compute_summary_stats(returns_series, risk_free_rate=0.02)` at notebook scope for reuse across phases. Phase 2 reuses this function directly (no copy-paste) to ensure consistent annualization (252 trading days, 2% risk-free rate) across Phase 1, Phase 2, and Phase 3.

```python
# Phase 1 defined this once (cell 6); Phase 2 reuses it (cell 2.2):
stats_0 = compute_summary_stats(state_0_returns, risk_free_rate=0.02)
stats_1 = compute_summary_stats(state_1_returns, risk_free_rate=0.02)

# Avoids drift between Phase 1 baseline and Phase 3 regime-conditional stats
```

---

### Matplotlib Charting Pattern: figsize=(12, 4) and Color Constants

**Source:** Phase 1 Setup cell (color constants) + Phase 1 EDA Charts cell (matplotlib setup)  
**Apply to:** Phase 2 Posterior Probability chart

Phase 1 established `COLOR_FUND`, `COLOR_BENCH`, `COLOR_DD` in the Setup cell (cell 1) and used `figsize=(12, 4)` for all charts (cell 7). Phase 2 inherits this pattern: reference color constants from Setup, use the same figure size, and apply the same axis formatting (labels, title, legend, grid, formatter functions).

```python
# Phase 1 Setup (cell 1):
COLOR_FUND  = '#1f77b4'   # blue
COLOR_BENCH = '#ff7f0e'   # orange
COLOR_DD    = '#d62728'   # red

# Phase 2 chart (cell 2.5):
fig, ax = plt.subplots(figsize=(12, 4))  # Same size as Phase 1
ax.plot(..., color=COLOR_BENCH)           # Reuse Phase 1 color constants
ax.yaxis.set_major_formatter(...)         # Same formatter pattern as Phase 1
```

---

### Validation and Assertion Pattern

**Source:** Phase 1 Data Load cell (lines c9df34d9, frequency checks) + Phase 1 Alignment cell (lines 4d62927f, assertion)  
**Apply to:** Phase 2 HMM Fit cell and Regime Duration cell

Phase 1 used simple `print()` warnings for non-critical checks and `assert` for integrity. Phase 2 follows the same pattern:
- Use `print()` with "WARNING:" prefix for validation issues (non-convergence, coverage below threshold)
- Use `assert` for critical failures (NaN in aligned data, shape mismatch)

```python
# Phase 1 pattern (cell 4):
assert aligned_returns.isnull().sum().sum() == 0, "Unexpected NaN in aligned data"

# Phase 2 analog (cell 2.1):
assert bench_aligned.isnull().sum() == 0, "bench_aligned contains NaN — alignment failed"

# Phase 1 pattern (cell 2):
if fund_freq not in ('B', 'D', None):
    print("WARNING: unexpected frequency — verify data sources")

# Phase 2 analog (cell 2.1):
if not model.monitor_.converged:
    print(f"WARNING: EM algorithm did not converge")
```

---

### Print Output Pattern: Readable Tables and Summaries

**Source:** Phase 1 Summary Statistics cell (lines 8deea6af, formatted table output)  
**Apply to:** Phase 2 Regime Statistics, Duration Analysis, and Seed Stability cells

Phase 1 printed formatted tables and summaries using pandas `.to_string()` and `str.apply(lambda x: f'{x:.2%}')` formatting. Phase 2 reuses this pattern for regime stats (cell 2.2), spell duration (cell 2.3), and seed stability (cell 2.4). No markdown tables in code cells — only print output.

```python
# Phase 1 pattern (cell 6):
print("=== SUMMARY STATISTICS (Full History) ===")
print(fmt_table[['Annual Return', ...]].to_string())

# Phase 2 analog (cells 2.2, 2.3, 2.4):
print("=== REGIME STATISTICS ===")
print(fmt_table.to_string())
print("=== REGIME DURATION ANALYSIS ===")
# [regime summary printed]
print("=== SEED STABILITY CHECK ===")
# [seed results printed]
```

---

## No Analog Found

**None.** Phase 1 establishes all required patterns:
- Data structure (DatetimeIndex Series)
- Function definition and reuse (`compute_summary_stats`)
- Matplotlib charting (`figsize=(12, 4)`, color constants, formatters)
- Validation and assertion
- Print output formatting

Phase 2 cells inherit these patterns directly. No external analogs needed beyond Phase 1 and 02-RESEARCH.md code examples.

---

## Metadata

**Analog search scope:** `C:\dev\tq-hmm\hmm.ipynb` (7 cells from Phase 1)  
**Files scanned:** 1  
**Analogs matched:** 7/7 (all Phase 1 cells provide direct patterns for Phase 2)  
**Pattern extraction date:** 2026-04-22

**Confidence:** HIGH
- Phase 1 cells are the primary codebase; Phase 2 is a direct extension within the same notebook
- All import patterns, data structures, visualization patterns, and validation approaches are established in Phase 1
- 02-RESEARCH.md Code Examples provide hmmlearn-specific patterns (GaussianHMM, Viterbi, posterior probabilities) with exact function signatures

**Next step for planner:** Reference this document when creating Phase 2 plan. Each plan task should explicitly cite:
1. Which Phase 1 cell or function to reuse (e.g., "reuse `compute_summary_stats()` from Phase 1 cell 6")
2. Which code excerpt from this PATTERNS.md to adapt (with line references)
3. How the output variable name and shape match the Phase 1 pattern (e.g., "regime_labels follows the `fund_aligned` pattern from Phase 1 cell 4")
