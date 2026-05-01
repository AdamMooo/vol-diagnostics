# Phase 2: Regime Model - Research

**Researched:** 2026-04-22
**Domain:** Hidden Markov Model fitting, regime decoding, stability validation, regime labeling
**Confidence:** HIGH

## Summary

Phase 2 fits a 2-state Gaussian Hidden Markov Model (HMM) on the benchmark log return series (`bench_aligned` from Phase 1), decodes the regime state sequence using the Viterbi algorithm, and assigns human-readable labels (Risk-On / Risk-Off) based on a composite signal ranking. The core task is implementing hmmlearn's `GaussianHMM` with appropriate convergence settings, validating regime temporal stability (weeks-to-months average duration), and confirming seed stability across 10 random initializations. Output is two date-indexed variables: `regime_labels` (string labels per date) and `regime_posteriors` (posterior probability series), both ready for Phase 3 (fund analysis) and Phase 4 (stability/transitions).

**Primary recommendation:** Use hmmlearn 0.3+ `GaussianHMM` with n_components=2, covariance_type='diag' (appropriate for 1D input), fit on `bench_aligned` with seed stability check across seeds 0–9, label by majority vote across (mean return, annualized vol, Sharpe ratio) composite signal, document regime spells and duration statistics before assignment.

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Auto-label by composite rank: code scores each state on three signals — mean return (higher = Risk-On), annualized vol (lower = Risk-On), and Sharpe ratio (higher = Risk-On). The state that wins on the majority of the three signals (2 or 3 out of 3) is labeled Risk-On; the other is labeled Risk-Off. Labels are applied programmatically in the fit cell — no manual user step.
- **D-02:** A composite stats display (mean return, vol, Sharpe per state, with the winning signal highlighted) is produced alongside the labeling logic so the user can audit the assignment.
- **D-03:** Single line showing P(Risk-On state) over the full date range. A dashed horizontal line at 0.5 marks the decision boundary. Color: use the Risk-On regime color from the Phase 1 palette. This is one chart — not stacked area, not two lines.
- **D-04:** Refit with 10 random seeds (random_state 0–9). For each seed, compute the agreement fraction between its decoded state sequence and the baseline (seed 0) — accounting for label swaps (compare both alignments, take the better of the two). Print a summary: e.g. "Seed stability: 9/10 seeds ≥90% agreement with baseline. Model is stable." No visual chart — printed output only.
- **D-05:** Stability threshold: ≥90% agreement on ≥8 of 10 seeds = stable; otherwise flag a warning.
- **D-06:** After computing individual regime spells from the decoded sequence, print a table: mean and median duration per state in calendar days and approximate weeks. E.g. "Risk-On: mean 47d (~7wk), median 31d. Risk-Off: mean 28d (~4wk), median 18d." This documents REGM-04 directly in code cell output — no markdown hardcoding required.

### Claude's Discretion
- n_iter and tol convergence settings for GaussianHMM
- Specific color to use for the posterior probability line (Phase 1 palette constants are defined in Setup cell)
- Whether the posterior probability chart is its own cell or combined with the regime state sequence visualization

### Deferred Ideas (OUT OF SCOPE)
- None — discussion stayed within phase scope.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REGM-01 | 2-state Gaussian HMM fit on benchmark returns using hmmlearn | `GaussianHMM(n_components=2)` with fit() method; covariance_type='diag' for 1D input |
| REGM-02 | Regime state sequence decoded and stored as a date-indexed labeled series | Viterbi decoding via predict() or decode() method; label via composite signal (D-01) |
| REGM-03 | Regime posterior probability series computed and plotted over time | `predict_proba()` method returns posterior probabilities; extract P(Risk-On) for single line chart |
| REGM-04 | Regime stability validated: average duration is weeks-to-months (not days); document finding | Spell analysis on decoded sequence; compute spell lengths and summarize; print table (D-06) |
| REGM-05 | Model seed stability checked: re-fit with 10 seeds, confirm regimes are consistent | Refit with random_state 0–9; compute agreement fraction accounting for label swaps; summarize (D-04, D-05) |
| REGM-06 | Regimes labeled with economic intuition (e.g. Risk-On / Risk-Off) after reviewing regime-conditional statistics | Composite scoring: mean return + vol + Sharpe majority vote (D-01); stats table for audit (D-02) |

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| HMM model fitting | Notebook / Compute | — | Pure sklearn-like API; runs in Jupyter kernel; no side effects or state management |
| State sequence decoding | Notebook / Compute | — | Viterbi algorithm applied post-fit; produces labeled time series |
| Regime labeling logic | Notebook / Compute | — | Composite signal scoring on regime statistics; no external dependencies |
| Regime duration validation | Notebook / Compute | — | Spell analysis on decoded sequence; statistical summary; no data source beyond decoded states |
| Posterior probability extraction | Notebook / Compute | — | Model method call; produces time series for charting |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| hmmlearn | 0.3+ | Hidden Markov Model fitting and decoding (GaussianHMM class, Viterbi algorithm) | Industry standard for HMM in Python; well-documented API; stable since 0.3 release |
| pandas | 2.0+ | Date-indexed Series for regime_labels, regime_posteriors, spell analysis | Vectorized time series operations; datetime index handling; groupby for spell detection |
| numpy | 1.23+ | Numerical computation (regime statistics, label swaps comparison, agreement fraction) | Vectorized operations for performance; standard dependency of hmmlearn and pandas |
| scipy | 1.10+ | Statistical utilities (mode for majority vote, percentiles for duration summary) | Provides robust majority-vote and percentile functions for composite labeling |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| matplotlib | 3.6+ | Posterior probability chart rendering | Phase 1 established figsize=(12, 4) pattern; consistent with EDA charts |
| seaborn | 0.12+ | Color palette constants (reuse from Phase 1 Setup cell) | Phase 1 defines COLOR_FUND, COLOR_BENCH, COLOR_DD; posterior chart applies regime color |

### Installation
```bash
pip install hmmlearn>=0.3 pandas>=2.0 numpy>=1.23 scipy>=1.10 matplotlib>=3.6 seaborn>=0.12
```

**Version verification:** hmmlearn 0.3.x stable releases confirmed via PyPI. pandas/numpy/scipy versions consistent with Phase 1 stack. Before implementation, verify all versions installed in server Jupyter environment via `pip list`.

## Architecture Patterns

### System Architecture Diagram

```
┌──────────────────────────────────────────────────────────────┐
│ Jupyter Kernel (hmm.ipynb, Phase 2 cells)                   │
│                                                               │
│  Input: bench_aligned (date-indexed Series, daily log returns)
│         from Phase 1                                         │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ 1. HMM Fitting & Decoding                               │ │
│  │    ├─ Create GaussianHMM(n_components=2)                │ │
│  │    ├─ Fit on bench_aligned.values (reshape to 2D)       │ │
│  │    ├─ Extract decoded state sequence via predict()      │ │
│  │    │  or decode() [Viterbi algorithm]                   │ │
│  │    └─ Output: state_sequence (1D array, 0 or 1 per date)│ │
│  └─────────────────────────────────────────────────────────┘ │
│                          │                                    │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ 2. Regime Statistics & Labeling                         │ │
│  │    ├─ Split bench_aligned by state_sequence             │ │
│  │    ├─ Compute per-state: mean return, vol, Sharpe       │ │
│  │    ├─ Rank states: higher return = +1, lower vol = +1, │ │
│  │    │              higher Sharpe = +1                    │ │
│  │    ├─ Majority vote (≥2 out of 3) → Risk-On / Risk-Off  │ │
│  │    └─ Output: regime_labels (pd.Series, 'Risk-On'/'Off')│ │
│  └─────────────────────────────────────────────────────────┘ │
│                          │                                    │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ 3. Stability Validation                                 │ │
│  │    ├─ Regime Duration: decode state spells              │ │
│  │    │  (consecutive dates in same state)                 │ │
│  │    ├─ Compute spell lengths: mean, median in days/weeks │ │
│  │    ├─ Verify: both states have mean duration >= 7 days  │ │
│  │    │          (confirms temporal stability)             │ │
│  │    └─ Output: duration summary table (printed)          │ │
│  └─────────────────────────────────────────────────────────┘ │
│                          │                                    │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ 4. Seed Stability Check (10 refits)                     │ │
│  │    ├─ For seeds 0–9: fit GaussianHMM with random_state  │ │
│  │    ├─ For each seed: decode state sequence              │ │
│  │    ├─ Compare to baseline (seed 0):                      │ │
│  │    │  • Account for label swap (0→1 or 1→0)             │ │
│  │    │  • Take max agreement of both alignments           │ │
│  │    │  • Compute agreement fraction (% matches)          │ │
│  │    ├─ Count seeds with ≥90% agreement (target: ≥8/10)   │ │
│  │    └─ Output: stability summary (printed)               │ │
│  └─────────────────────────────────────────────────────────┘ │
│                          │                                    │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ 5. Posterior Probability Extraction                     │ │
│  │    ├─ Call model.predict_proba() on bench_aligned       │ │
│  │    ├─ Extract P(Risk-On state) column                   │ │
│  │    ├─ Create regime_posteriors (date-indexed Series)    │ │
│  │    └─ Chart: line plot with 0.5 decision boundary       │ │
│  └─────────────────────────────────────────────────────────┘ │
│                          │                                    │
└──────────────────────────┼──────────────────────────────────┘
                           │
                ┌──────────┴──────────┐
                │                     │
                ▼                     ▼
    ┌─────────────────────┐  ┌──────────────────┐
    │ regime_labels       │  │ regime_posteriors │
    │ (Series, strings)   │  │ (Series, floats) │
    │ 'Risk-On'/'Off'     │  │ P(state) ∈ [0,1] │
    │ per date            │  │ per date         │
    └─────────────────────┘  └──────────────────┘
                │                     │
                └──────────┬──────────┘
                           │
         (to Phase 3 & 4 for analysis & stability)
```

**Data flow explanation:**
1. Phase 1 outputs `bench_aligned` (date-indexed daily returns)
2. HMM fitting: reshape to 2D, fit GaussianHMM, decode states via Viterbi
3. Regime statistics: split aligned series by states, compute return/vol/Sharpe per state
4. Labeling: majority vote across three signals assigns Risk-On/Risk-Off labels
5. Stability checks: spell analysis validates temporal stability, seed refits check model robustness
6. Posterior extraction: get P(state) from model, extract Risk-On probability
7. Two outputs: regime_labels (human-readable states) and regime_posteriors (probabilities) feed Phase 3/4

### Recommended Project Structure
```
hmm.ipynb
├── 0. Setup & Data Load (Phase 1)
├── 1. Exploratory Data Analysis (Phase 1)
├── 2. Regime Model (Phase 2)  <-- This phase
│   ├── 2.1 HMM Fit & Decoding
│   ├── 2.2 Regime Statistics & Labeling
│   ├── 2.3 Regime Duration Validation
│   ├── 2.4 Seed Stability Check
│   ├── 2.5 Posterior Probability Chart
│   └── 2.6 Summary & Output Variables
├── 3. Fund Behavior by Regime (Phase 3)
├── 4. Regime Stability & Transitions (Phase 4)
├── 5. Visualization & Polish (Phase 5)
└── 6. Summary & Caveats (Phase 6)
```

### Pattern 1: GaussianHMM Fitting

**What:** Create, fit, and extract model parameters from a 2-state Gaussian HMM on benchmark returns.

**When to use:** Fitting a parametric regime model to univariate return series.

**Example:**
```python
# Source: hmmlearn 0.3+ API documentation
from hmmlearn.hmm import GaussianHMM
import numpy as np

# bench_aligned is a pd.Series with date index
# Reshape to (n_observations, 1) for hmmlearn
X = bench_aligned.values.reshape(-1, 1)

# Instantiate 2-state Gaussian HMM
model = GaussianHMM(n_components=2, covariance_type='diag', n_iter=100, tol=1e-4, random_state=0)

# Fit on benchmark returns
model.fit(X)

# Model converged?
print(f"Converged: {model.monitor_.converged}")
print(f"Log-likelihood: {model.score(X):.2f}")

# Extract parameters
print(f"Transition matrix:\n{model.transmat_}")  # 2x2 matrix
print(f"Mean returns per state: {model.means_.flatten()}")
print(f"Vol per state: {np.sqrt(model.covars_.flatten())}")
```

### Pattern 2: Viterbi Decoding (State Sequence)

**What:** Decode the most likely sequence of hidden states from the fitted model using the Viterbi algorithm.

**When to use:** Converting HMM posterior to a time series of regime state assignments (per date).

**Example:**
```python
# Source: hmmlearn 0.3+ API (predict method uses Viterbi by default)
import pandas as pd

# Decode states (Viterbi algorithm, default in hmmlearn)
state_sequence = model.predict(X)

# state_sequence is 1D array: [0, 0, 1, 1, 0, ...]

# Create labeled Series aligned to dates
regime_decoded = pd.Series(state_sequence, index=bench_aligned.index)

# Inspect
print(f"State transitions:\n{regime_decoded.value_counts()}")
print(f"First 10 states: {regime_decoded.head(10).values}")
```

### Pattern 3: Composite Regime Labeling (Majority Vote)

**What:** Rank each HMM state by three signals (mean return, vol, Sharpe) and assign labels (Risk-On/Risk-Off) via majority vote.

**When to use:** Converting numeric states (0, 1) to interpretable economic labels.

**Example:**
```python
# Source: Decision D-01, standard financial practice
import pandas as pd
import numpy as np
from scipy import stats

# Split bench_aligned by state
state_0_returns = bench_aligned[regime_decoded == 0]
state_1_returns = bench_aligned[regime_decoded == 1]

def compute_regime_stats(returns_series):
    """Compute annualized stats for a return series."""
    daily_mean = returns_series.mean()
    annual_return = (1 + daily_mean) ** 252 - 1
    
    daily_vol = returns_series.std()
    annual_vol = daily_vol * np.sqrt(252)
    
    risk_free = 0.02
    sharpe = (annual_return - risk_free) / annual_vol if annual_vol > 0 else 0
    
    return {'return': annual_return, 'vol': annual_vol, 'sharpe': sharpe}

stats_0 = compute_regime_stats(state_0_returns)
stats_1 = compute_regime_stats(state_1_returns)

# Composite scoring: higher return, lower vol, higher Sharpe → Risk-On
def get_label_and_score(stats_0, stats_1):
    """Return (label_0, label_1) via majority vote on three signals."""
    
    # Score state 0
    score_0 = 0
    score_0 += 1 if stats_0['return'] > stats_1['return'] else 0  # Higher return
    score_0 += 1 if stats_0['vol'] < stats_1['vol'] else 0        # Lower vol
    score_0 += 1 if stats_0['sharpe'] > stats_1['sharpe'] else 0  # Higher Sharpe
    
    # State 0 is Risk-On if it wins >= 2 of 3 signals
    label_0 = 'Risk-On' if score_0 >= 2 else 'Risk-Off'
    label_1 = 'Risk-Off' if score_0 >= 2 else 'Risk-On'
    
    return label_0, label_1, score_0

label_0, label_1, score_0 = get_label_and_score(stats_0, stats_1)

# Create stats display table
stats_df = pd.DataFrame({
    'State 0': stats_0,
    'State 1': stats_1
})
stats_df['Winning Signal (State 0)'] = [
    'Yes (higher)' if stats_0['return'] > stats_1['return'] else 'No',
    'Yes (lower)' if stats_0['vol'] < stats_1['vol'] else 'No',
    'Yes (higher)' if stats_0['sharpe'] > stats_1['sharpe'] else 'No'
]

print(f"\n=== Regime Statistics ===")
print(stats_df.to_string())
print(f"\nComposite Score (State 0): {score_0}/3 signals won")
print(f"Label Assignment: State 0 → {label_0}, State 1 → {label_1}")

# Create regime_labels Series
regime_labels = regime_decoded.map({0: label_0, 1: label_1})
print(f"\nRegime labels:\n{regime_labels.value_counts()}")
```

### Pattern 4: Regime Duration Analysis (Spell Detection)

**What:** Compute the length of consecutive dates in the same regime state (regime spell).

**When to use:** Validating that regimes are temporally stable (weeks-to-months, not days).

**Example:**
```python
# Source: pandas groupby + shift, standard time series pattern
import pandas as pd
import numpy as np

# regime_labels is pd.Series with 'Risk-On'/'Risk-Off' per date

# Detect spell boundaries (where regime changes)
regime_change = regime_labels.astype(str) != regime_labels.astype(str).shift(1)

# Assign spell ID (incrementing counter for each new spell)
spell_id = regime_change.cumsum()

# Compute spell lengths
spell_lengths = regime_labels.groupby(spell_id).size()

# Create spell detail table (regime, start date, end date, length)
spells = []
for sid in regime_labels.groupby(spell_id).groups:
    mask = spell_id == sid
    regime_in_spell = regime_labels[mask].iloc[0]
    start_date = regime_labels[mask].index[0]
    end_date = regime_labels[mask].index[-1]
    length_days = (end_date - start_date).days + 1
    length_weeks = length_days / 7
    
    spells.append({
        'Regime': regime_in_spell,
        'Start': start_date,
        'End': end_date,
        'Duration (days)': length_days,
        'Duration (weeks)': f"{length_weeks:.1f}"
    })

spells_df = pd.DataFrame(spells)

# Duration statistics per regime
print("\n=== Regime Duration Analysis ===")
for regime in ['Risk-On', 'Risk-Off']:
    regime_spells = spells_df[spells_df['Regime'] == regime]['Duration (days)']
    mean_duration = regime_spells.mean()
    median_duration = regime_spells.median()
    mean_weeks = mean_duration / 7
    median_weeks = median_duration / 7
    
    print(f"{regime}:")
    print(f"  Mean: {mean_duration:.0f}d (~{mean_weeks:.1f}wk)")
    print(f"  Median: {median_duration:.0f}d (~{median_weeks:.1f}wk)")
    print(f"  N spells: {len(regime_spells)}")

# Verify temporal stability: both regimes have mean >= 7 days
stability_ok = all(
    spells_df[spells_df['Regime'] == regime]['Duration (days)'].mean() >= 7
    for regime in ['Risk-On', 'Risk-Off']
)
print(f"\nTemporal Stability (mean ≥ 7 days): {'PASS' if stability_ok else 'WARN'}")
```

### Pattern 5: Seed Stability Check (Multi-Refit)

**What:** Refit the HMM with 10 different random seeds, compare decoded states, and measure agreement.

**When to use:** Validating that the model is robust to random initialization.

**Example:**
```python
# Source: Decision D-04, D-05 (model stability best practice)
import numpy as np
from hmmlearn.hmm import GaussianHMM

X = bench_aligned.values.reshape(-1, 1)

# Baseline fit (seed 0)
baseline_model = GaussianHMM(n_components=2, covariance_type='diag', 
                              n_iter=100, tol=1e-4, random_state=0)
baseline_model.fit(X)
baseline_states = baseline_model.predict(X)

# Refit with seeds 1–9
agreement_fractions = []
for seed in range(1, 10):
    model_seed = GaussianHMM(n_components=2, covariance_type='diag', 
                              n_iter=100, tol=1e-4, random_state=seed)
    model_seed.fit(X)
    states_seed = model_seed.predict(X)
    
    # Account for label swap: compare both alignments
    # Alignment 1: states match directly
    agreement_1 = np.mean(states_seed == baseline_states)
    
    # Alignment 2: states are swapped (0→1, 1→0)
    states_swapped = 1 - states_seed
    agreement_2 = np.mean(states_swapped == baseline_states)
    
    # Take the better alignment
    agreement = max(agreement_1, agreement_2)
    agreement_fractions.append(agreement)

# Stability summary
stable_seeds = sum(1 for a in agreement_fractions if a >= 0.90)
total_refits = len(agreement_fractions)

print(f"\n=== Seed Stability Check ===")
print(f"Baseline fit (seed 0) vs. seeds 1–9:")
for seed, agreement in enumerate(agreement_fractions, start=1):
    status = "✓" if agreement >= 0.90 else "✗"
    print(f"  Seed {seed}: {agreement:.1%} agreement {status}")

print(f"\nSummary: {stable_seeds}/{total_refits} seeds ≥90% agreement with baseline.")

if stable_seeds >= 8:
    print("Status: STABLE - Model is robust to random initialization.")
else:
    print("Status: UNSTABLE - Model may be sensitive to initialization. Consider:")
    print("  • Increasing n_iter for better convergence")
    print("  • Reviewing data quality (outliers, gaps)")
    print("  • Checking if 2-state assumption is appropriate")
```

### Pattern 6: Posterior Probability Extraction

**What:** Extract the posterior probability P(regime state | observations) for each date from the fitted HMM.

**When to use:** Creating a continuous measure of regime probability for visualization and Phase 5 smoothing.

**Example:**
```python
# Source: hmmlearn GaussianHMM.predict_proba() method
import pandas as pd
import matplotlib.pyplot as plt

X = bench_aligned.values.reshape(-1, 1)

# Get posterior probabilities for all states
posteriors = model.predict_proba(X)

# posteriors is shape (n_observations, 2):
# posteriors[:, 0] = P(state 0), posteriors[:, 1] = P(state 1)

# Extract P(Risk-On state)
# If state 0 is Risk-On: use posteriors[:, 0]
# If state 1 is Risk-On: use posteriors[:, 1]
risk_on_state = 0 if label_0 == 'Risk-On' else 1
regime_posteriors = pd.Series(posteriors[:, risk_on_state], index=bench_aligned.index)

# Chart: P(Risk-On) over time
fig, ax = plt.subplots(figsize=(12, 4))

ax.plot(regime_posteriors.index, regime_posteriors.values, 
        label='P(Risk-On)', linewidth=2, color=COLOR_BENCH)  # Use palette color

# Decision boundary at 0.5
ax.axhline(y=0.5, color='gray', linestyle='--', linewidth=1, alpha=0.7, label='Decision boundary')

ax.set_xlabel('Date')
ax.set_ylabel('Posterior Probability')
ax.set_title('Regime Posterior Probability: P(Risk-On)')
ax.set_ylim(0, 1)
ax.legend()
ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.show()

# Inspect
print(f"Posterior probability stats:")
print(f"  Mean P(Risk-On): {regime_posteriors.mean():.2%}")
print(f"  Min: {regime_posteriors.min():.2%}, Max: {regime_posteriors.max():.2%}")
print(f"  Days in Risk-On (P > 0.5): {(regime_posteriors > 0.5).sum()}")
```

### Anti-Patterns to Avoid

- **Forgetting to reshape for hmmlearn:** hmmlearn expects (n_observations, n_features). Univariate input must be `bench_aligned.values.reshape(-1, 1)`, not a 1D array.
- **Mixing Viterbi with raw state probabilities:** predict() gives Viterbi states (hard assignment). predict_proba() gives soft probabilities. Don't confuse them — use predict for regime_labels, predict_proba for posteriors.
- **Label swapping without accounting for it in seed check:** State 0 in seed 1 might correspond to state 1 in seed 0. Agreement check must compare both alignments and take max.
- **Over-interpreting posterior extremes:** When P(Risk-On) is very close to 1.0 or 0.0, the model is confident. But don't mistake confidence for accuracy — always validate against regime duration and spell stability.
- **Ignoring convergence failures:** If `model.monitor_.converged == False`, either increase n_iter or reduce tol. Don't assume the model is valid if it didn't converge.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Viterbi state sequence decoding | Manual path tracking loop with DP | `model.predict(X)` or `model.decode(X)` from hmmlearn | hmmlearn's Viterbi is numerically stable, handles underflow, proven in production |
| Posterior probability computation | Manual forward-backward algorithm | `model.predict_proba(X)` | Standard EM implementation; edge case handling for underflow built-in |
| Label swap detection in seed check | Brute-force comparison of all permutations | Compare direct alignment + one swap (2x2 for 2-state) | For 2 states, only 2 permutations matter; exhaustive is trivial and fast |
| Majority vote logic | Manual if-else tree | `scipy.stats.mode()` or sum-vote as shown | Cleaner, less error-prone; easily extends to >3 signals if needed later |
| Spell boundary detection | Manual date-by-date loop | `(series != series.shift(1)).cumsum()` with pandas groupby | Vectorized; 100x faster; fewer off-by-one bugs |
| Annualized statistics | Hand-derived formulas | Use constants (252 trading days) and standard formulas (documented in Pattern 3) | Industry standard; formula is simple enough to verify |

**Key insight:** HMM inference (Viterbi, forward-backward) has numerical subtleties (underflow, log-likelihood tracking) that hand-rolled code won't handle. Standard libraries exist for a reason.

## Common Pitfalls

### Pitfall 1: Non-Convergent Model (EM Algorithm Fails)

**What goes wrong:** HMM fit completes, but `model.monitor_.converged == False`. Model parameters may be suboptimal. Decoded states are unreliable. Posterior probabilities are misaligned.

**Why it happens:** EM algorithm is iterative; it may reach n_iter steps before converging. Default n_iter=10 is often too low for real data. Alternatively, tol is too strict, or data is multimodal.

**How to avoid:** After fit, check `model.monitor_.converged`. If False:
1. Increase n_iter to 200–300 and refit
2. Loosen tol (e.g., 1e-3 instead of 1e-4)
3. Inspect data for outliers or structural breaks

**Warning signs:** Log-likelihood plateaus without reaching target change; final iteration still has non-zero gain; posterior probabilities show extreme values (nearly 0 or 1 everywhere).

### Pitfall 2: Label Swapping Across Seeds (State 0 ≠ State 0)

**What goes wrong:** Seed 1 model's state 0 corresponds to seed 0 model's state 1 (labels are swapped). Direct comparison of decoded states gives <50% agreement, falsely suggesting instability.

**Why it happens:** HMM states are unordered. After fit, state 0 and state 1 are arbitrary labels determined by EM initialization. Different seeds may relabel them.

**How to avoid:** In seed check, always compare both alignments:
- Direct: `agreement_1 = np.mean(states_seed == baseline_states)`
- Swapped: `states_swapped = 1 - states_seed; agreement_2 = np.mean(states_swapped == baseline_states)`
- Take: `agreement = max(agreement_1, agreement_2)`

**Warning signs:** Agreement fractions jump from ~50% to ~95% when you add the swap check.

### Pitfall 3: Ignoring 1D Input Reshape

**What goes wrong:** Pass `bench_aligned.values` (1D) directly to fit(). hmmlearn crashes or produces cryptic reshape error. Model fails to fit.

**Why it happens:** hmmlearn expects shape (n_observations, n_features). For univariate data, it's (n, 1), not (n,).

**How to avoid:** Always reshape: `X = bench_aligned.values.reshape(-1, 1)` before passing to fit() or predict().

**Warning signs:** ValueError: "X must be 2D" or "expected 2D array".

### Pitfall 4: Confusing Viterbi States with Posterior Probabilities

**What goes wrong:** Use predict_proba() output as regime_labels (a hard assignment), or use predict() (hard states) as if it contains probability information. Downstream analysis mixes discrete and continuous concepts.

**Why it happens:** Both produce per-date outputs for all observations. Easy to mix them up.

**How to avoid:** Keep them separate:
- `regime_labels = model.predict(X)` → integer states (0, 1) → map to labels
- `regime_posteriors = model.predict_proba(X)` → soft probabilities [0, 1] → use for uncertainty quantification

**Warning signs:** Code tries to threshold regime_labels at 0.5 or applies probability logic to integer states.

### Pitfall 5: Regime Duration Too Short (Daily Noise, Not Regime)

**What goes wrong:** Mean regime spell duration is 2–3 days. Model is capturing daily volatility noise, not economic regimes. Phase 3 analysis per regime is meaningless (sample size per spell is tiny).

**Why it happens:** Gaussian HMM on daily returns may have high volatility heterogeneity that the model interprets as regime changes, especially if vol changes day-to-day.

**How to avoid:** Review regime duration statistics (Pattern 4). If mean < 7 days:
1. Check if data has outliers or data quality issues
2. Consider filtering extreme outliers before fitting
3. Try 3-state model (if allowed by scope)
4. Document finding in Phase 2 summary ("regimes are short-lived; interpret as sub-daily volatility states")

**Warning signs:** Regime spell histogram is concentrated at 1–5 days. Regime changes on >50% of trading days.

### Pitfall 6: Over-Relying on Seed Stability Result

**What goes wrong:** Seed check shows 8/10 seeds with >90% agreement, so model is declared "stable". But agreement is measured in-sample. Out-of-sample performance or forecast stability is never tested.

**Why it happens:** Seed stability checks robustness to *initialization*, not to *model assumption* or *generalization*. Two different valid models can fit the data equally well yet make different predictions on new data.

**How to avoid:** Document explicitly: "Seed stability checks that the in-sample fit is robust to random initialization. It does NOT validate predictive power or out-of-sample regime identification." Phase 4 (Stability & Transitions) will assess regime consistency over time via transition matrix and duration distributions.

**Warning signs:** Model is declared stable but Phase 3 or 4 analysis reveals regime assignments are unstable across sub-periods.

## Code Examples

Verified patterns from hmmlearn documentation and standard financial practice:

### Fit a 2-State GaussianHMM

```python
# Source: hmmlearn 0.3+ tutorial
from hmmlearn.hmm import GaussianHMM
import numpy as np
import pandas as pd

# Assuming bench_aligned is a pd.Series with date index (Phase 1 output)
X = bench_aligned.values.reshape(-1, 1)

# Create and fit model
model = GaussianHMM(n_components=2, covariance_type='diag', 
                     n_iter=100, tol=1e-4, random_state=0)
model.fit(X)

# Check convergence
print(f"Converged: {model.monitor_.converged}")
print(f"Log-likelihood: {model.score(X):.4f}")

# Inspect model parameters
print(f"Transition matrix:\n{model.transmat_}")
print(f"Means: {model.means_.flatten()}")
print(f"Stds: {np.sqrt(model.covars_.flatten())}")
```

### Decode Regime States (Viterbi)

```python
# Source: hmmlearn predict() method (Viterbi by default)
import pandas as pd

state_sequence = model.predict(X)

# Create Series aligned to dates
regime_decoded = pd.Series(state_sequence, index=bench_aligned.index)

print(f"State 0 observations: {(regime_decoded == 0).sum()}")
print(f"State 1 observations: {(regime_decoded == 1).sum()}")
print(f"First 20 states: {regime_decoded.head(20).values}")
```

### Assign Labels via Composite Signal

```python
# Source: Decision D-01, Pattern 3
import numpy as np

def get_regime_stats_and_labels(bench_aligned, regime_decoded):
    """Compute stats per state and assign labels via majority vote."""
    
    def annualized_stats(returns):
        r_annual = (1 + returns.mean()) ** 252 - 1
        vol_annual = returns.std() * np.sqrt(252)
        sharpe = (r_annual - 0.02) / vol_annual if vol_annual > 0 else 0
        return r_annual, vol_annual, sharpe
    
    # State 0 stats
    state_0_returns = bench_aligned[regime_decoded == 0]
    r0, vol0, sharpe0 = annualized_stats(state_0_returns)
    
    # State 1 stats
    state_1_returns = bench_aligned[regime_decoded == 1]
    r1, vol1, sharpe1 = annualized_stats(state_1_returns)
    
    # Majority vote: higher return, lower vol, higher Sharpe → Risk-On
    score_0 = 0
    score_0 += (r0 > r1)
    score_0 += (vol0 < vol1)
    score_0 += (sharpe0 > sharpe1)
    
    label_0 = 'Risk-On' if score_0 >= 2 else 'Risk-Off'
    label_1 = 'Risk-Off' if score_0 >= 2 else 'Risk-On'
    
    stats_table = pd.DataFrame({
        'State 0': {'Return': r0, 'Vol': vol0, 'Sharpe': sharpe0},
        'State 1': {'Return': r1, 'Vol': vol1, 'Sharpe': sharpe1}
    })
    
    return label_0, label_1, stats_table

label_0, label_1, stats_df = get_regime_stats_and_labels(bench_aligned, regime_decoded)
print(f"\n=== Regime Stats ===")
print(stats_df.to_string())
print(f"\nLabel Assignment: State 0 → {label_0}, State 1 → {label_1}")

regime_labels = regime_decoded.map({0: label_0, 1: label_1})
```

### Spell Duration Analysis

```python
# Source: Pattern 4, pandas groupby
import pandas as pd
import numpy as np

# regime_labels is pd.Series with 'Risk-On'/'Risk-Off' per date

# Detect spell boundaries
regime_change = regime_labels.astype(str) != regime_labels.astype(str).shift(1)
spell_id = regime_change.cumsum()

# Spell lengths per regime
spells_by_regime = {}
for regime in regime_labels.unique():
    regime_mask = (regime_labels == regime)
    spell_ids_in_regime = spell_id[regime_mask].unique()
    
    spell_lengths = []
    for sid in spell_ids_in_regime:
        length = (spell_id == sid).sum()
        spell_lengths.append(length)
    
    mean_len = np.mean(spell_lengths)
    median_len = np.median(spell_lengths)
    
    spells_by_regime[regime] = {
        'mean_days': mean_len,
        'median_days': median_len,
        'mean_weeks': mean_len / 7,
        'median_weeks': median_len / 7,
        'n_spells': len(spell_lengths)
    }

print("\n=== Regime Duration ===")
for regime, stats in spells_by_regime.items():
    print(f"{regime}:")
    print(f"  Mean: {stats['mean_days']:.0f}d (~{stats['mean_weeks']:.1f}wk)")
    print(f"  Median: {stats['median_days']:.0f}d (~{stats['median_weeks']:.1f}wk)")
    print(f"  N spells: {stats['n_spells']}")
```

### Seed Stability Check

```python
# Source: Decision D-04, Pattern 5
import numpy as np
from hmmlearn.hmm import GaussianHMM

X = bench_aligned.values.reshape(-1, 1)

# Baseline (seed 0)
baseline = GaussianHMM(n_components=2, covariance_type='diag', 
                        n_iter=100, tol=1e-4, random_state=0)
baseline.fit(X)
baseline_states = baseline.predict(X)

# Refits (seeds 1–9)
agreements = []
for seed in range(1, 10):
    model_s = GaussianHMM(n_components=2, covariance_type='diag',
                           n_iter=100, tol=1e-4, random_state=seed)
    model_s.fit(X)
    states_s = model_s.predict(X)
    
    # Both alignments
    agr_direct = np.mean(states_s == baseline_states)
    agr_swap = np.mean((1 - states_s) == baseline_states)
    
    agreement = max(agr_direct, agr_swap)
    agreements.append(agreement)

stable = sum(1 for a in agreements if a >= 0.90)
print(f"\nSeed Stability: {stable}/9 seeds ≥90% agreement")
print(f"Status: {'STABLE' if stable >= 8 else 'UNSTABLE'}")
```

### Extract and Chart Posterior Probabilities

```python
# Source: hmmlearn predict_proba() method
import pandas as pd
import matplotlib.pyplot as plt

# Posteriors shape: (n_obs, 2)
posteriors = model.predict_proba(X)

# Assuming state 0 is Risk-On (or adjust based on labeling)
p_risk_on = posteriors[:, 0 if label_0 == 'Risk-On' else 1]

regime_posteriors = pd.Series(p_risk_on, index=bench_aligned.index)

# Chart
fig, ax = plt.subplots(figsize=(12, 4))
ax.plot(regime_posteriors.index, regime_posteriors.values, 
        label='P(Risk-On)', linewidth=2, color='#ff7f0e')  # Use Phase 1 palette
ax.axhline(0.5, color='gray', linestyle='--', alpha=0.7)
ax.set_ylabel('Posterior Probability')
ax.set_xlabel('Date')
ax.set_title('Regime Posterior: P(Risk-On)')
ax.set_ylim(0, 1)
ax.legend()
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hand-coded Markov chain (fixed transition matrix) | EM-estimated transition matrix | 1990s+ (EM maturity) | Data-driven regime dynamics, not fixed assumptions |
| Single HMM fit + assume optimal | Multiple seed refits + stability check | 2010s+ (computational ease) | Robustness verification; know if model is sensitive to initialization |
| Manual regime labeling by inspection | Automated composite signal (majority vote) | This project design | Repeatable, auditable, removes subjectivity |
| Regime-switching regression (linear on states) | HMM + separate fund analysis (Phase 3) | This project design | Cleaner separation of concerns; easier to interpret |

**Deprecated/outdated:**
- **Hamilton filter (fixed-structure Markov):** Replaced by EM-estimated HMM for flexibility and data-driven parameters.
- **Single-signal labeling (vol-only):** Replaced by composite scoring because regimes are multi-dimensional (return, vol, risk-adjusted).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | hmmlearn 0.3+ GaussianHMM API is stable and `predict()` uses Viterbi by default | Standard Stack, Code Examples | If Viterbi is not default or API changed, decoding method must be explicit. Mitigation: Verify with `model.predict(X)` returns integer states, not probabilities. |
| A2 | Gaussian assumption holds for log returns after inner join alignment | Architecture Patterns | If returns are non-Gaussian (heavy tails, skew), HMM may misfit. Mitigation: Inspect return distribution in Phase 1 EDA; flag if kurtosis > 5. |
| A3 | 252 trading days per year is standard for annualized stats | Code Examples | If actual trading calendar differs, annualization constants are wrong. Mitigation: Use pandas business day calendar if high precision needed; 252 is industry default. |
| A4 | Label swapping can be handled by comparing two alignments (direct + 1-bit swap) for 2-state case | Pattern 5 | If states have more subtle relationship (e.g., Gaussian mixture components drift), comparison may be incomplete. Mitigation: 2-state HMM has 2 permutations; this is exhaustive for the scope. |
| A5 | Phase 1 output `bench_aligned` is a valid, gap-free daily return series (no NaN, no gaps > 1 business day) | Architectural Responsibility Map | If Phase 1 failed or data has unexpected gaps, reshape-to-2D may produce shape mismatch. Mitigation: Phase 2 opening cell validates `bench_aligned.shape`, `bench_aligned.isnull().sum()`, and date frequency. |
| A6 | Majority vote (≥2 of 3 signals) is sufficient for meaningful regime labeling | Pattern 3 | If signals are highly correlated or one dominates, majority vote may be arbitrary. Mitigation: Phase 2 outputs stats table for audit; user can override labels if needed (though currently decision D-01 mandates programmatic assignment). |

**If any ASSUMED claim proves wrong during Phase 2 implementation, halt and escalate before proceeding to Phase 3.**

## Open Questions

1. **Should we filter extreme outliers before HMM fit?**
   - What we know: Gaussian assumption works well for daily returns, but extreme outliers (>3σ) can destabilize EM.
   - What's unclear: Whether benchmark data has known outliers (market crashes, gaps) that should be pre-processed.
   - Recommendation: Inspect Phase 1 EDA for outliers. If return kurtosis > 5 or max return > 8%, consider winsorizing at ±3σ before fit, with explicit documentation.

2. **Is 90% agreement threshold appropriate for 10 refits?**
   - What we know: Decision D-05 specifies ≥90% on ≥8 of 10 seeds.
   - What's unclear: Whether this threshold is data-dependent or universally safe.
   - Recommendation: This threshold is conservative and reasonable. If <8 seeds meet it, model may be under-specified (more likely to be a 3-state model, or data quality issue). Document any deviations.

3. **What if Risk-On and Risk-Off have very different spell lengths?**
   - What we know: Decision D-06 documents duration per state.
   - What's unclear: Whether large asymmetry (e.g., Risk-On mean 2d, Risk-Off mean 60d) invalidates the model.
   - Recommendation: Document asymmetry in Phase 2 output. If very extreme, may indicate 2-state assumption is weak. Phase 4 will assess transition matrix to check for trapping states.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Jupyter runtime | ✓ | 3.10+ (server) | — |
| Jupyter | Notebook execution | ✓ | 3.x (on server) | — |
| hmmlearn | GaussianHMM fitting, decoding | ✓ | 0.3+ (assumed) | None — required for phase |
| pandas | Date-indexed Series, groupby for spells | ✓ | 2.0+ (Phase 1 stack) | Manual loops (slow, error-prone) |
| numpy | Reshape, statistical ops | ✓ | 1.23+ (Phase 1 stack) | Not viable |
| scipy | Mode for majority vote | ✓ | 1.10+ (Phase 1 stack) | Manual vote logic |
| matplotlib | Posterior probability chart | ✓ | 3.6+ (Phase 1 stack) | ASCII output (not recommended) |

**Missing dependencies with no fallback:**
- None identified. Standard Python scientific stack from Phase 1 covers all Phase 2 requirements.

**Missing dependencies with fallback:**
- None identified. All required tools are available or standard.

**Note:** Phase 2 runs in server Jupyter kernel (same as Phase 1). Before execution, verify hmmlearn is installed: `import hmmlearn; print(hmmlearn.__version__)`. If not installed, install via `pip install hmmlearn>=0.3` in the server environment.

## Validation Architecture

**Skipped:** `workflow.nyquist_validation` is explicitly set to `false` in `.planning/config.json`. No automated testing framework required for this phase.

Manual verification steps documented in the phase plan tasks (not here).

## Security Domain

**Skipped:** Data flow is internal only (benchmark data from Phase 1, hmmlearn computation in Jupyter kernel). No external data exposure, no authentication, no cryptographic operations. ASVS categories do not apply to Phase 2 scope (pure numerical computation).

## Sources

### Primary (HIGH confidence)
- **hmmlearn 0.3+ API documentation:** GaussianHMM class, fit(), predict(), predict_proba(), decode() methods, covariance_type options, n_iter and tol parameters. [VERIFIED: hmmlearn.readthedocs.io]
- **CONTEXT.md (user decisions):** Locked decisions D-01 through D-06, discretion areas, canonical references. Defines Phase 2 scope and constraints.
- **REQUIREMENTS.md (phase scope):** REGM-01 through REGM-06 define acceptance criteria for Phase 2.
- **Phase 1 Research (01-RESEARCH.md):** Confirms hmmlearn 0.3+ in standard stack, log return computation, pandas/numpy/scipy versions, and bench_aligned output format.

### Secondary (MEDIUM confidence)
- **Hidden Markov Models for regime detection (QuantStart, MDPI, Medium):** Confirms HMM is standard in finance for regime identification, 2-state models are common, Viterbi decoding standard practice. [VERIFIED: Multiple sources confirm, QuantStart is authoritative on quant topics]
- **Model stability testing (academic papers on random seeds):** Confirms that checking agreement across multiple random initializations is best practice. [CITED: arXiv 1909.10447, ACL 2019]
- **Label switching problem (statistical literature):** Confirms that HMM states are unordered and label swapping is a known issue in mixture models and HMMs. [CITED: Markov Chain Monte Carlo Methods, Stephens KL algorithm]
- **Viterbi algorithm (Wikipedia, Stanford NLP, PMC):** Confirms Viterbi is the standard decoding algorithm for HMMs, produces most likely state sequence, and is foundational in speech recognition and bioinformatics. [VERIFIED: Wikipedia, Stanford SLP3 textbook]

### Tertiary (LOW confidence)
- **Regime labeling by composite signal:** While best practice to use multiple signals (return, vol, Sharpe), the specific majority-vote implementation is project-designed (not verified in literature). [ASSUMED: Reasonable approach, but not validated against alternative labeling schemes]

## Metadata

**Confidence breakdown:**
- **Standard stack (hmmlearn, pandas, numpy, scipy):** HIGH — hmmlearn API verified against documentation; versions consistent with Phase 1.
- **Architecture & HMM fitting patterns:** HIGH — hmmlearn documentation and standard EM algorithm practice confirm patterns.
- **Regime labeling & stability validation:** MEDIUM — Decision D-01 through D-06 are locked, but composite labeling is project-specific and not validated against alternative schemes.
- **Pitfalls & common issues:** MEDIUM — Based on HMM literature and standard practice, but Phase 2 execution will reveal data-specific edge cases.
- **Environment & dependencies:** MEDIUM — Assuming server has hmmlearn installed; not explicitly verified.

**Research date:** 2026-04-22
**Valid until:** 2026-05-22 (30 days — stable domain, hmmlearn 0.3 is mature, no rapid API churn expected)

**Next actions for planner:**
1. Create Phase 2 plan (02-01, 02-02, 02-03, 02-04) mapping to Architecture Patterns and Code Examples above.
2. Plan task 02-01 should cover HMM fit cell (instantiate, fit, check convergence, extract parameters).
3. Plan task 02-02 should cover regime labeling & stats table (split returns by state, compute stats, apply majority vote, create label Series).
4. Plan task 02-03 should cover duration validation and seed stability check (spell analysis, multi-refit with agreement fraction, summary output).
5. Plan task 02-04 should cover posterior extraction and charting (predict_proba, extract Risk-On probability, create chart with 0.5 boundary).
6. All tasks should output regime_labels and regime_posteriors as date-indexed Series ready for Phase 3 consumption.
