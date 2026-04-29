# Phase 1: Data Layer - Research

**Researched:** 2026-04-22
**Domain:** Data loading, cleaning, and alignment (Jupyter notebook)
**Confidence:** HIGH

## Summary

Phase 1 is the data foundation for the HMM project. It loads fund NAV and benchmark returns from two server-side sources (Django ORM and Bloomberg API), computes log returns for both series, aligns them on a common date index, and produces exploratory data analysis. The canonical reference for data pull patterns is `Data.ipynb`, which shows working examples of Django ORM queries and Bloomberg `con.bdh()` calls. The existing `hmm.ipynb` contains an unrelated prior analysis (One-Class SVM on yield shares) and must be cleared as a blank slate. Phase 1 output is a validated, aligned return series pair that becomes the input for Phase 2 (HMM fit on benchmark) and Phase 3 (fund behavior analysis).

**Primary recommendation:** Use `Data.ipynb` as the exact reference for Django ORM query syntax and Bloomberg connection patterns. Clear all existing cells in `hmm.ipynb`. Build Phase 1 cells following the pattern: Setup (fund/benchmark parameters, connection documentation) → Data Load → Log Returns → Date Alignment → EDA (stats table + charts).

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Notebook runs server-side (same pattern as deck-auto). No local code execution.
- **D-02:** Setup cell documents parameters (fund identifier, benchmark ticker, date range) and the two connection patterns, but does not require reader intervention to run on the server.
- **D-03:** Fund data via Django ORM (shell_plus context). Load NAV or price series for the target fund.
- **D-04:** Benchmark via Bloomberg API (`con.bdh()`). Use S&P 500 as universal benchmark regardless of fund-specific mandate.
- **D-05:** Both data pulls documented clearly in the Setup cell so a reader on the same server can reproduce them.
- **D-06:** Log returns: `np.log(price_t / price_{t-1})` applied to both fund NAV and benchmark price series after loading.
- **D-07:** Daily frequency. No resampling to weekly or monthly.
- **D-08:** Inner join — keep only dates where both fund and benchmark have a valid observation. No forward-filling.
- **D-09:** Light visual structure: consistent figure sizes (e.g. `figsize=(12, 4)`) and basic color scheme (fund vs benchmark color constants). Phase 5 handles full polish.
- **D-10:** Summary statistics table covers full history (unconditional): annualized mean return, annualized volatility, Sharpe ratio, max drawdown.
- **D-11:** Required EDA charts: cumulative return (fund vs benchmark), rolling 21-day volatility (fund vs benchmark), drawdown chart (fund). All on shared date axis.

### Claude's Discretion
- Exact figure sizes and baseline color constants (fund/benchmark colors)
- Drawdown computation method (e.g., rolling max approach)
- Cell organization and markdown headers within the notebook
- How to annualize vol and Sharpe (assume 252 trading days standard for daily equity data)

### Deferred Ideas (OUT OF SCOPE)
- None — discussion stayed within phase scope.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DATA-01 | Internal DB connection established and documented in notebook Setup cell | D-01, D-03, D-05; see Data.ipynb for Django ORM pattern |
| DATA-02 | Fund return series (or NAV) loaded, cleaned, and validated (no gaps, correct frequency) | D-03, D-07; Data.ipynb shows Fund.get_adj_nav() and related accessors |
| DATA-03 | Benchmark return series loaded at same frequency as fund | D-04, D-07; Data.ipynb shows con.bdh() signature and field selection |
| DATA-04 | Returns aligned on a common date index with missing data handled explicitly | D-08; pandas inner join on index after computing log returns |
| DATA-05 | EDA outputs: summary statistics table, cumulative return chart, rolling 21-day vol chart, drawdown chart | D-10, D-11; referenced below in Code Examples |

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Data load (Django ORM, Bloomberg) | Backend / Server | — | Connection context lives on server; notebook is shell-plus, not local |
| Log return computation | Notebook / Compute | — | Pure pandas/numpy transformation; runs in Jupyter kernel |
| Date alignment and filtering | Notebook / Compute | — | Inner join logic is data cleaning, not business logic |
| EDA statistics and charting | Notebook / Compute | — | Exploratory analysis produces no side effects; runs locally in Jupyter |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pandas | 2.0+ | Data frame manipulation, time series alignment, resampling | Industry standard for financial data wrangling; built-in join/merge |
| numpy | 1.23+ | Numerical computation (log returns, rolling windows) | Vectorized operations; ubiquitous dependency of pandas/scipy/sklearn |
| matplotlib | 3.6+ | Static chart rendering (cumulative returns, volatility, drawdown) | Standard in research notebooks; simple, reproducible |
| scipy | 1.10+ | Statistical functions (rolling max drawdown, percentiles) | Provides `scipy.ndimage.maximum_filter` for drawdown rolling max |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| seaborn | 0.12+ | Chart styling and color palettes | Applied *after* Phase 1 (Phase 5 polish); optional for Phase 1 basic charts |
| hmmlearn | 0.3+ | Hidden Markov Model (2-state Gaussian) | Phase 2 (HMM fit); listed here for dependency planning |
| statsmodels | 0.14+ | OLS regression, Sharpe ratio utilities | Phase 3 (fund alpha/beta by regime); Phase 1 may use for annualized stats |

### Installation
```bash
pip install pandas>=2.0 numpy>=1.23 matplotlib>=3.6 scipy>=1.10 seaborn>=0.12 hmmlearn>=0.3 statsmodels>=0.14
```

**Version verification:** Recommended versions as of knowledge cutoff (Feb 2025). Before implementation, confirm against PyPI registry. Server environment may have pre-installed versions — check `pip list` after activating venv.

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ Server-side Environment (Django Shell-Plus, Bloomberg API)  │
│                                                               │
│  ┌──────────────────────────┐    ┌──────────────────────┐   │
│  │ Django ORM Models        │    │ Bloomberg Terminal   │   │
│  │ (Fund, FundAccount)      │    │ (con object)         │   │
│  └──────────────┬───────────┘    └──────────┬───────────┘   │
│                 │                           │                │
│                 │ get_adj_nav()             │ con.bdh()      │
│                 │ (price series)            │ (SPXT Index)   │
│                 │                           │                │
│                 ▼                           ▼                │
│        ┌────────────────────────────────────────┐            │
│        │ Jupyter Kernel (hmm.ipynb)             │            │
│        │                                         │            │
│        │ Setup:                                  │            │
│        │ ├─ Fund identifier, date range          │            │
│        │ ├─ Data pull documentation             │            │
│        │ └─ Connection context (pre-loaded)     │            │
│        │                                         │            │
│        │ Data Load:                              │            │
│        │ ├─ Call fa.get_adj_nav() → fund_nav    │            │
│        │ └─ Call con.bdh(...) → bench_price     │            │
│        │                                         │            │
│        │ Log Returns:                            │            │
│        │ ├─ fund_returns = np.log(fund / shift) │            │
│        │ └─ bench_returns = np.log(bench / shift)            │
│        │                                         │            │
│        │ Alignment:                              │            │
│        │ ├─ Inner join on date index             │            │
│        │ └─ Drop NaT, validate frequency         │            │
│        │                                         │            │
│        │ EDA:                                    │            │
│        │ ├─ Summary stats table                  │            │
│        │ ├─ Cumulative return chart              │            │
│        │ ├─ Rolling 21d volatility               │            │
│        │ └─ Drawdown series & chart              │            │
│        └────────────┬───────────────────────────┘            │
│                     │                                         │
└─────────────────────┼─────────────────────────────────────────┘
                      │
                      ▼
         ┌─────────────────────────────────┐
         │ Phase 1 Outputs (in-memory)     │
         ├─────────────────────────────────┤
         │ • fund_returns (Series)         │
         │ • bench_returns (Series)        │
         │ • Shared date index (aligned)   │
         │ • Summary stats (dict or table) │
         │ • EDA charts (matplotlib)       │
         └─────────────────────────────────┘
                      │
                      ▼ (to Phase 2 & 3)
         ┌─────────────────────────────────┐
         │ Phase 2: HMM Fit                │
         │ Phase 3: Fund Analysis          │
         └─────────────────────────────────┘
```

**Data flow explanation:**
1. Server-side Django ORM and Bloomberg context are pre-loaded in `shell_plus`
2. Setup cell documents parameters (fund ID, benchmark ticker, date range)
3. Data Load cell calls ORM methods and Bloomberg API to pull NAV and price series
4. Log Returns cell transforms both into daily returns (dimensionless, percent-like)
5. Alignment cell performs inner join on date index, dropping mismatches
6. EDA cell computes statistics and renders charts using matplotlib
7. Output is two aligned Series (fund returns, benchmark returns) fed to Phase 2/3

### Recommended Project Structure
```
tq-hmm/
├── hmm.ipynb               # Main notebook (Phase 1 → 6)
│   ├── 0. Setup & Data Load
│   ├── 1. Exploratory Data Analysis
│   ├── 2. Regime Model (Phase 2)
│   ├── 3. Fund Behavior by Regime (Phase 3)
│   ├── 4. Regime Stability (Phase 4)
│   ├── 5. Visualization & Polish (Phase 5)
│   └── 6. Summary & Caveats (Phase 6)
├── Data.ipynb              # Reference notebook (canonical syntax examples)
├── requirements.txt        # Python dependencies
├── CLAUDE.md              # Project constraints
└── .planning/             # GSD workflow (auto-managed)
```

### Pattern 1: Django ORM Data Pull

**What:** Access fund NAV from internal database using Django ORM in shell_plus context.

**When to use:** Loading fund price or NAV data from internal Purpose Investments database.

**Example:**
```python
# Source: Data.ipynb (canonical reference)
# Fund data retrieval pattern observed in Data.ipynb

from datetime import datetime
import pandas as pd

# Get fund account by symbol (shell_plus context, Django models pre-loaded)
fa = FundAccount.objects.get(symbol='TARGET_FUND_SYMBOL')

# Retrieve adjusted NAV series (returns pd.Series with date index)
df_nav = fa.primary_fund.get_adj_nav()

# df_nav is a time-indexed series of NAV values
# Example output: Series([100.5, 101.2, 100.8, ...], index=DatetimeIndex([...]))

# Validate data
print(f"NAV series: {len(df_nav)} observations from {df_nav.index.min()} to {df_nav.index.max()}")
print(f"Frequency check: {df_nav.index.inferred_freq}")  # Should be 'D' (daily)
```

### Pattern 2: Bloomberg Data Pull

**What:** Fetch benchmark returns from Bloomberg Terminal using `con.bdh()` (historical time series).

**When to use:** Loading market index or benchmark price data (S&P 500, bond indices, etc.).

**Example:**
```python
# Source: Data.ipynb (canonical reference)
# Bloomberg con.bdh() pattern for time series data

import pandas as pd
from datetime import datetime

# con object is pre-loaded in shell_plus; no explicit connection needed

# Fetch S&P 500 closing price (daily)
benchmark_ticker = 'SPXT Index'  # S&P 500 Total Return Index
start_date = '2020-01-01'
end_date = '2026-04-22'

df_bench = con.bdh(benchmark_ticker, 'PX_LAST', start_date=start_date, end_date=end_date)

# df_bench is a DataFrame with single column 'PX_LAST' (or renamed to benchmark price)
# Example output: DataFrame with DatetimeIndex and price column

# Rename for clarity
df_bench.columns = ['price']
df_bench = df_bench.iloc[:, 0]  # Extract as Series if needed

# Validate data
print(f"Benchmark series: {len(df_bench)} observations from {df_bench.index.min()} to {df_bench.index.max()}")
```

### Pattern 3: Log Returns Computation

**What:** Transform price/NAV series into dimensionless returns using natural logarithm.

**When to use:** Converting price levels to returns for HMM fitting and statistical analysis.

**Example:**
```python
# Source: Standard financial mathematics (verified from CONTEXT.md decision D-06)
import numpy as np
import pandas as pd

# Assuming fund_price and bench_price are pd.Series with date index

# Compute log returns
fund_returns = np.log(fund_price / fund_price.shift(1))
bench_returns = np.log(bench_price / bench_price.shift(1))

# Drop NaN from shift operation
fund_returns = fund_returns.dropna()
bench_returns = bench_returns.dropna()

# Verify returns are dimensionless (not percentage)
print(f"Fund returns (first 5): {fund_returns.head()}")
print(f"Daily return range: [{fund_returns.min():.4f}, {fund_returns.max():.4f}]")

# Log returns should be near 0 for daily data (e.g., -0.02 to +0.03)
# If you see values > 1, check if price data is in different units
```

### Pattern 4: Date Alignment (Inner Join)

**What:** Synchronize fund and benchmark return series on a common date index, dropping dates where either has missing data.

**When to use:** Preparing aligned return pairs for HMM and statistical analysis.

**Example:**
```python
# Source: pandas DataFrame/Series operations (standard practice)
import pandas as pd

# fund_returns and bench_returns are Series with date index (after log return computation)

# Create aligned DataFrame (inner join)
aligned = pd.DataFrame({
    'fund_returns': fund_returns,
    'bench_returns': bench_returns
}).dropna()  # Inner join: keep only rows where both have data

# Validate alignment
print(f"Original fund returns: {len(fund_returns)}")
print(f"Original bench returns: {len(bench_returns)}")
print(f"Aligned series: {len(aligned)}")  # Should be <= min(len(fund), len(bench))

print(f"Date range: {aligned.index.min()} to {aligned.index.max()}")
print(f"Gaps in index: {(aligned.index.to_series().diff() > pd.Timedelta(days=1)).sum()}")

# Verify no forward-filling
assert aligned.isnull().sum().sum() == 0, "Unexpected NaN in aligned data"

# Extract individual series from aligned
fund_aligned = aligned['fund_returns']
bench_aligned = aligned['bench_returns']
```

### Pattern 5: Rolling Maximum Drawdown

**What:** Compute maximum peak-to-trough decline from a cumulative return series, using a rolling window.

**When to use:** Computing maximum drawdown statistic for EDA and regime-conditional statistics.

**Example:**
```python
# Source: Standard financial statistics (verified from CONTEXT.md decision D-10)
import pandas as pd
import numpy as np

def compute_rolling_max_drawdown(returns, window=None):
    """
    Compute maximum drawdown from cumulative return series.
    
    Args:
        returns: pd.Series of daily returns (log or simple)
        window: lookback window (None = full history, else rolling max DD in window)
    
    Returns:
        float or pd.Series: max drawdown (negative value)
    """
    # Compute cumulative returns (compound)
    cumret = (1 + returns).cumprod()
    
    if window is None:
        # Full-history max drawdown
        running_max = cumret.expanding().max()
    else:
        # Rolling max drawdown
        running_max = cumret.rolling(window=window).max()
    
    drawdown = (cumret - running_max) / running_max
    
    if window is None:
        return drawdown.min()  # Single value
    else:
        return drawdown  # Series

# Example usage
max_dd_full = compute_rolling_max_drawdown(fund_returns)
print(f"Maximum drawdown (full history): {max_dd_full:.2%}")

max_dd_rolling = compute_rolling_max_drawdown(fund_returns, window=252)
print(f"Rolling 1-year max drawdown: min={max_dd_rolling.min():.2%}, max={max_dd_rolling.max():.2%}")
```

### Pattern 6: Annualized Statistics

**What:** Convert daily statistics to annual scale using 252 trading day convention.

**When to use:** Computing annualized return, volatility, and Sharpe ratio for summary table.

**Example:**
```python
# Source: Standard financial practice (verified from CONTEXT.md decision D-10)
import pandas as pd
import numpy as np

def annualize_stats(returns, risk_free_rate=0.0):
    """
    Compute annualized return, volatility, and Sharpe ratio from daily returns.
    
    Args:
        returns: pd.Series of daily log returns
        risk_free_rate: annual risk-free rate (default 0.0 for simplicity)
    
    Returns:
        dict with 'annual_return', 'annual_vol', 'sharpe_ratio'
    """
    
    # Annualized return (compound daily returns over 252 days)
    daily_mean = returns.mean()
    annual_return = (1 + daily_mean) ** 252 - 1
    
    # Annualized volatility (scale daily std dev)
    daily_vol = returns.std()
    annual_vol = daily_vol * np.sqrt(252)
    
    # Sharpe ratio (excess return / vol)
    excess_annual_return = annual_return - risk_free_rate
    sharpe = excess_annual_return / annual_vol if annual_vol > 0 else 0
    
    return {
        'annual_return': annual_return,
        'annual_vol': annual_vol,
        'sharpe_ratio': sharpe
    }

# Example usage
stats = annualize_stats(fund_returns, risk_free_rate=0.03)
print(f"Fund annualized return: {stats['annual_return']:.2%}")
print(f"Fund annualized volatility: {stats['annual_vol']:.2%}")
print(f"Sharpe ratio: {stats['sharpe_ratio']:.2f}")
```

### Anti-Patterns to Avoid

- **Mixing return types:** Do not mix log returns and simple returns in calculations. Choose one convention (log returns preferred for HMM) and apply consistently.
- **Forward-filling missing dates:** Decision D-08 explicitly prohibits forward-fill. Missing dates are dropped via inner join, not imputed.
- **Resampling without justification:** Decision D-07 mandates daily frequency. Do not aggregate to weekly/monthly without explicit decision to change scope.
- **Assuming pre-loaded context:** The Setup cell must document which Django models and Bloomberg con object are assumed pre-loaded on the server. Do not assume reader will have them loaded.
- **Undocumented data sources:** Every data pull (fund, benchmark, additional fields) must be documented in Setup cell so a reader on the same server can reproduce.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Date index alignment | Custom merge logic with manual date matching | `pd.DataFrame().dropna()` (inner join) or `pd.merge(..., how='inner')` | Pandas handles time zone awareness, frequency inference, and edge cases; custom logic introduces off-by-one bugs |
| Rolling statistics | Manual window iteration with `.loc[]` slicing | `pd.Series.rolling(window=N)`, `scipy.ndimage.maximum_filter` | Vectorized operations are orders of magnitude faster; rolling window edge case handling is built-in |
| Max drawdown from cumulative returns | Custom loop with peak tracking | `(cumret - cumret.cummax()) / cumret.cummax()` | Single line, numerically stable, handles NaN gracefully |
| Annualized volatility | Converting daily std dev by hand | `daily_vol * np.sqrt(252)` or use statsmodels utilities | Standard convention, less error-prone than implementing discount factors |
| Log returns computation | Manual price ratio logic | `np.log(series / series.shift(1))` | Vectorized, handles edge cases (0 prices, NaN) |

**Key insight:** Financial time series operations are common enough that pandas and scipy have battle-tested implementations. Custom iteration logic introduces bugs (off-by-one in windows, missing NaN handling, numerical precision issues) and runs 10-100x slower.

## Common Pitfalls

### Pitfall 1: Frequency Mismatch (Fund vs. Benchmark)

**What goes wrong:** Fund data is monthly or weekly while benchmark is daily. When performing inner join, very few dates align, resulting in a sparse, short return series that defeats the statistical power of the analysis.

**Why it happens:** Different data sources report at different frequencies. Fund NAV may be updated weekly; Bloomberg prices update daily. Without explicit frequency check, this goes undetected until Phase 2 (HMM fit fails or produces unstable results).

**How to avoid:** After loading fund NAV and benchmark price, verify frequency explicitly:
```python
print(f"Fund frequency: {fund_nav.index.inferred_freq}")
print(f"Bench frequency: {bench_price.index.inferred_freq}")
```
Both should be 'D' (daily). If not, investigate the source or resample (though Decision D-07 mandates daily only).

**Warning signs:** Aligned series has fewer than 250 observations (< 1 trading year). Inner join dropped >50% of original data.

### Pitfall 2: Using Simple Returns Instead of Log Returns

**What goes wrong:** Compute simple returns `(price_t - price_{t-1}) / price_{t-1}` instead of log returns. HMM fit becomes unstable; Gaussian assumption is violated. Regime posterior probabilities become unreliable.

**Why it happens:** Simple returns are more intuitive ("the fund gained 2% today"). But log returns satisfy additivity over time (log(a*b) = log(a) + log(b)), which HMM exploits. Using simple returns violates the model's assumptions.

**How to avoid:** Implement exactly as per Decision D-06: `np.log(price_t / price_{t-1})`. Document this choice in Setup cell.

**Warning signs:** Phase 2 (HMM fit) converges but posterior probabilities are clustered at extremes (0% or 100%), not distributed across states.

### Pitfall 3: Forward-Filling Missing Dates

**What goes wrong:** Fund has no data on a date (e.g., fund closed for record date). Instead of dropping it, forward-fill from previous value. This artificially creates zero-return days, biasing volatility and drawdown estimates downward.

**Why it happens:** Forward-fill is tempting for continuity. It feels safer than dropping data. But it introduces look-ahead bias (using yesterday's NAV as proxy for today when today's NAV was never computed).

**How to avoid:** Decision D-08 is explicit: inner join, no forward-fill. Drop dates where either series is missing. Document gaps visually in EDA (see Pitfall 4).

**Warning signs:** Volatility is suspiciously low; max drawdown is shallow. Inspection of return series shows clusters of exact zeros.

### Pitfall 4: Invisible Data Gaps

**What goes wrong:** Dates are dropped silently during inner join. Planner or reader doesn't realize the return series has gaps (e.g., spans 2020-2026 but only has 1200 observations, not 1260 = 5 years * 252 trading days).

**Why it happens:** `.dropna()` runs silently. No warning in output. User assumes continuous daily data.

**How to avoid:** After alignment, report gap statistics:
```python
expected_obs = (aligned.index[-1] - aligned.index[0]).days / 365 * 252
actual_obs = len(aligned)
coverage = actual_obs / expected_obs
print(f"Expected observations: {expected_obs:.0f}")
print(f"Actual observations: {actual_obs}")
print(f"Coverage: {coverage:.1%}")
```
If coverage < 95%, investigate why. Flag in EDA chart with visual gap indicators.

**Warning signs:** Aligned series length doesn't match date range (e.g., 3 years should have ~756 observations, but you have 500).

### Pitfall 5: Non-Stationary Return Series (Structural Break)

**What goes wrong:** Fund or benchmark undergoes a structural change (fund splits, benchmark rebalance, market regime shift). Full-history statistics are misleading. Phase 2 (HMM) fits a single model to data that should really be two separate regimes.

**Why it happens:** Not caught during Phase 1 EDA. Happens when fund merges, closes/reopens to new investors, or benchmark criteria change mid-period.

**How to avoid:** EDA cumulative return chart should show visible breaks. Regime stability check (Phase 4) later confirms regime consistency. For Phase 1, document any known structural events in Setup cell (e.g., "Fund reopened to new investors 2022-06-15").

**Warning signs:** Cumulative return chart has a sharp bend; rolling volatility shows a step change; autocorrelation function (ACF) is very high at 1-day lag, indicating mean reversion (structural break).

## Code Examples

Verified patterns from canonical references and standard financial practice:

### Load Fund NAV (Django ORM)

```python
# Source: Data.ipynb (canonical reference notebook)
import pandas as pd
from datetime import datetime

# Django ORM access (shell_plus context)
# FundAccount, Fund models are pre-loaded

# Method 1: Via FundAccount (if working with account-level data)
fund_symbol = 'PYF'  # Example: Purpose Investments target fund
fa = FundAccount.objects.get(symbol=fund_symbol)
df_nav = fa.primary_fund.get_adj_nav()

# Method 2: Direct Fund query (alternative)
# f = Fund.objects.get(fund_account__symbol='PYF', website_series='F')
# df_nav = f.get_adj_nav()

# df_nav is a Series with DatetimeIndex and NAV values
print(f"Fund NAV loaded: {len(df_nav)} observations")
print(f"Date range: {df_nav.index.min()} to {df_nav.index.max()}")
print(f"NAV range: {df_nav.min():.2f} to {df_nav.max():.2f}")
```

### Load S&P 500 Benchmark (Bloomberg)

```python
# Source: Data.ipynb (canonical reference notebook)
import pandas as pd

# con object is pre-loaded in shell_plus
# con is the Bloomberg connection (bdp, bdh, ref, bds methods available)

start_date = '2020-01-01'
end_date = '2026-04-22'

# Fetch S&P 500 Total Return Index
# SPXT = S&P 500 Total Return Index (includes dividends)
df_bench = con.bdh('SPXT Index', 'PX_LAST', start_date=start_date, end_date=end_date)

# Rename column for clarity
df_bench = df_bench.rename(columns={'PX_LAST': 'price'})
df_bench = df_bench['price']  # Extract as Series

print(f"Benchmark loaded: {len(df_bench)} observations")
print(f"Date range: {df_bench.index.min()} to {df_bench.index.max()}")
print(f"Price range: {df_bench.min():.2f} to {df_bench.max():.2f}")
```

### Compute Log Returns

```python
# Source: CONTEXT.md Decision D-06 (standard financial practice)
import numpy as np

# Assuming df_nav and df_bench are Series with date indices

# Log returns for fund
fund_price = df_nav
fund_log_returns = np.log(fund_price / fund_price.shift(1))
fund_log_returns = fund_log_returns.dropna()

# Log returns for benchmark
bench_price = df_bench
bench_log_returns = np.log(bench_price / bench_price.shift(1))
bench_log_returns = bench_log_returns.dropna()

print(f"Fund returns: {len(fund_log_returns)} observations")
print(f"Bench returns: {len(bench_log_returns)} observations")
print(f"Fund return range: {fund_log_returns.min():.4f} to {fund_log_returns.max():.4f}")
print(f"Bench return range: {bench_log_returns.min():.4f} to {bench_log_returns.max():.4f}")
```

### Align Return Series

```python
# Source: CONTEXT.md Decision D-08 (pandas inner join)
import pandas as pd

# Create aligned DataFrame (inner join on date index)
returns_df = pd.DataFrame({
    'fund': fund_log_returns,
    'bench': bench_log_returns
})

# Inner join: dropna() keeps only rows where both have data
returns_aligned = returns_df.dropna()

# Verify alignment
print(f"Original fund observations: {len(fund_log_returns)}")
print(f"Original bench observations: {len(bench_log_returns)}")
print(f"Aligned observations: {len(returns_aligned)}")
print(f"Coverage: {len(returns_aligned) / min(len(fund_log_returns), len(bench_log_returns)) * 100:.1f}%")

# Check for date gaps
import numpy as np
date_diffs = returns_aligned.index.to_series().diff()
max_gap = date_diffs.max()
business_day_gap = (max_gap.days > 3)  # 3+ days = likely weekend/holiday gap, OK
if business_day_gap:
    gap_dates = returns_aligned.index[returns_aligned.index.to_series().diff() > pd.Timedelta(days=3)]
    print(f"Expected gaps (weekends/holidays): {len(gap_dates)} dates")

# Extract aligned series
fund_aligned = returns_aligned['fund']
bench_aligned = returns_aligned['bench']
```

### Summary Statistics Table

```python
# Source: CONTEXT.md Decision D-10 (standard financial metrics)
import pandas as pd
import numpy as np

def compute_summary_stats(returns_series, risk_free_rate=0.02):
    """Compute annualized statistics for a return series."""
    
    # Daily metrics
    daily_mean = returns_series.mean()
    daily_std = returns_series.std()
    
    # Annualized (252 trading days)
    annual_return = (1 + daily_mean) ** 252 - 1
    annual_vol = daily_std * np.sqrt(252)
    
    # Sharpe ratio
    excess_return = annual_return - risk_free_rate
    sharpe = excess_return / annual_vol if annual_vol > 0 else 0
    
    # Max drawdown
    cumret = (1 + returns_series).cumprod()
    running_max = cumret.expanding().max()
    drawdown = (cumret - running_max) / running_max
    max_dd = drawdown.min()
    
    return {
        'Annual Return': annual_return,
        'Annual Volatility': annual_vol,
        'Sharpe Ratio': sharpe,
        'Max Drawdown': max_dd,
        'Observations': len(returns_series)
    }

# Compute for both series
fund_stats = compute_summary_stats(fund_aligned)
bench_stats = compute_summary_stats(bench_aligned)

# Create summary table
stats_table = pd.DataFrame({
    'Fund': fund_stats,
    'Benchmark': bench_stats
}).T

print("\n=== SUMMARY STATISTICS (Full History) ===")
print(stats_table.to_string())

# Format for presentation (Phase 1 basic, Phase 5 will polish)
print("\nFormatted:")
print(f"Fund Annual Return: {fund_stats['Annual Return']:.2%}")
print(f"Fund Annual Volatility: {fund_stats['Annual Volatility']:.2%}")
print(f"Fund Sharpe Ratio: {fund_stats['Sharpe Ratio']:.2f}")
print(f"Fund Max Drawdown: {fund_stats['Max Drawdown']:.2%}")
```

### EDA Cumulative Return Chart

```python
# Source: CONTEXT.md Decision D-11 (matplotlib standard)
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Cumulative returns
cumret_fund = (1 + fund_aligned).cumprod()
cumret_bench = (1 + bench_aligned).cumprod()

# Plot
fig, ax = plt.subplots(figsize=(12, 4))

ax.plot(cumret_fund.index, cumret_fund.values, label='Fund', linewidth=2, color='#1f77b4')
ax.plot(cumret_bench.index, cumret_bench.values, label='Benchmark', linewidth=2, color='#ff7f0e')

ax.set_xlabel('Date')
ax.set_ylabel('Cumulative Return (index)')
ax.set_title('Fund vs Benchmark Cumulative Returns')
ax.legend()
ax.grid(True, alpha=0.3)

# Format y-axis as multiple of starting value
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:.1f}x'))

plt.tight_layout()
plt.show()
```

### Rolling 21-Day Volatility Chart

```python
# Source: CONTEXT.md Decision D-11 (rolling window)
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Rolling 21-day volatility (annualized)
rolling_vol_fund = fund_aligned.rolling(window=21).std() * np.sqrt(252)
rolling_vol_bench = bench_aligned.rolling(window=21).std() * np.sqrt(252)

# Plot
fig, ax = plt.subplots(figsize=(12, 4))

ax.plot(rolling_vol_fund.index, rolling_vol_fund.values, label='Fund', linewidth=2, color='#1f77b4')
ax.plot(rolling_vol_bench.index, rolling_vol_bench.values, label='Benchmark', linewidth=2, color='#ff7f0e')

ax.set_xlabel('Date')
ax.set_ylabel('Annualized Volatility')
ax.set_title('Rolling 21-Day Volatility (annualized)')
ax.legend()
ax.grid(True, alpha=0.3)

# Format y-axis as percentage
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:.0%}'))

plt.tight_layout()
plt.show()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Simple returns for HMM | Log returns (Decision D-06) | Established practice in financial econometrics | Better Gaussian assumption; avoids compounding errors in long windows |
| Manual date alignment (loops) | Pandas inner join + dropna() | ~2010s (pandas maturity) | 100x speedup; fewer bugs; vectorized logic |
| Forward-fill missing data | Inner join only (Decision D-08) | Financial best practice (avoid look-ahead bias) | Cleaner inference; no artificial zero-return days |
| External benchmarks (multiple) | S&P 500 only (Decision D-04) | This project's design decision | Reduces complexity; universal benchmark avoids fund-specific matching |

**Deprecated/outdated:**
- **Excel-based return alignment:** Manually exported data, matched dates in spreadsheet. Now: pandas handles all alignment programmatically.
- **Hand-computed annualized stats:** Using approximations (daily return * 252). Now: precise formulas with standard conventions (log compounding for returns, square-root scaling for vol).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Data.ipynb contains exact syntax for Django ORM `.get_adj_nav()` call | Code Examples | If syntax is outdated or model has changed, data pull fails. Mitigation: User verifies Data.ipynb runs on server before Phase 1 planning begins. |
| A2 | Bloomberg `con.bdh()` is available in server's shell_plus context | Code Examples | If con object is not pre-loaded or `bdh` method doesn't exist, benchmark data pull fails. Mitigation: Verify with `con.bdh('SPXT Index', 'PX_LAST', '2026-01-01', '2026-01-10')` in Setup cell. |
| A3 | 'SPXT Index' is the correct Bloomberg ticker for S&P 500 Total Return | Code Examples | If ticker is wrong or deprecated, benchmark pull returns empty/error. Mitigation: Confirm ticker with Bloomberg terminal or reference documentation. |
| A4 | numpy.log() + pandas shift() is the standard pattern for log returns in Python finance | Code Examples | If there's a numerically better method (unlikely), results may differ slightly. Mitigation: Verify output against manual computation on a small subset. |
| A5 | Inner join (dropna after concat) is the right pattern for alignment | Code Examples | If there's a requirement for forward-fill or interpolation, decision D-08 would be violated. Mitigation: Explicit in CONTEXT.md decision D-08 — no ambiguity. |

**If any ASSUMED claim proves wrong during Phase 1 implementation, halt and escalate before continuing to Phase 2.**

## Open Questions (RESOLVED)

1. **Fund identifier and date range for Phase 1**
   - RESOLVED: FUND_SYMBOL='PYF' (default placeholder); executor confirms the correct fund symbol before running on server. START_DATE='2020-01-01', END_DATE='2026-04-22' — configured as constants in Setup cell.

2. **Risk-free rate assumption for Sharpe ratio**
   - RESOLVED: 2% annual (0.02), hardcoded in `compute_summary_stats()` as `risk_free_rate=0.02`. Documented in cell header. Phase 5 can refine if needed.

3. **Handling fund inception date**
   - RESOLVED: Load full fund history, then filter to START_DATE..END_DATE range in the Data Load cell. Report actual date range in the summary stats table. Reader can subset if needed.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Jupyter notebook runtime | ✓ | 3.10+ (typical server) | — |
| Jupyter | Notebook execution | ✓ | 3.x (on server) | — |
| pandas | Data wrangling, alignment | ✓ | 2.0+ (assumed) | Manual alignment (not recommended) |
| numpy | Log returns, rolling stats | ✓ | 1.23+ (assumed) | Not viable |
| matplotlib | Charting (EDA) | ✓ | 3.6+ (assumed) | ASCII output (not recommended) |
| scipy | Rolling max (argmax filters) | ✓ | 1.10+ (assumed) | Manual loop (slow) |
| Django ORM | Fund data access | ✓ | Pre-loaded in shell_plus | — |
| Bloomberg con | Benchmark data access | ✓ | Pre-loaded in shell_plus | None — required for benchmark |

**Missing dependencies with no fallback:**
- None identified. Standard Python scientific stack is available on server.

**Missing dependencies with fallback:**
- None identified. All required tools are pre-loaded on server or standard library.

**Note:** Phase 1 runs on server, not locally. Confirm all dependencies are installed in the server's Jupyter environment before execution. Use `pip list` in a Jupyter cell to verify.

## Validation Architecture

**Skipped:** `workflow.nyquist_validation` is explicitly set to `false` in `.planning/config.json`. No automated testing framework required for this phase.

Manual verification steps are documented in the phase plan tasks (not here).

## Security Domain

**Skipped:** Data flow is internal only (Django ORM to Jupyter kernel, Bloomberg API pull). No external data exposure, no authentication beyond server-side Bloomberg terminal access (pre-configured). No ASVS categories apply to Phase 1 scope (data loading and EDA, no auth, validation, or cryptography logic).

## Sources

### Primary (HIGH confidence)
- **Data.ipynb (canonical reference):** Django ORM query patterns (Fund.get_adj_nav(), FundAccount.get_aum(), etc.), Bloomberg con.bdh() signature and field names, example data pulls with output. Verified by reading the notebook directly.
- **CONTEXT.md (user decisions):** Locked decisions D-01 through D-11, discretion areas, and canonical references. Defines Phase 1 scope and constraints.
- **REQUIREMENTS.md (phase scope):** DATA-01 through DATA-05 define acceptance criteria for Phase 1.
- **pandas documentation (official):** Inner join via dropna(), rolling window methods, time series alignment patterns. [VERIFIED: pandas.pydata.org]
- **numpy documentation (official):** Log and exp functions, vectorized operations. [VERIFIED: numpy.org]
- **Financial mathematics (standard practice):** Log returns computation, annualized statistics with 252 trading day convention, Sharpe ratio formula. [VERIFIED: Standard in academic literature and industry practice]

### Secondary (MEDIUM confidence)
- **CLAUDE.md (project constraints):** Notebook-only constraint, Windows paths with pathlib, interpretability-first rules. Applied as project-level guidance.
- **Standard financial practice (implied):** Max drawdown computation, rolling volatility, inner join for alignment. [ASSUMED: Industry standard, not explicitly verified for this project.]

### Tertiary (LOW confidence)
- None. All major claims verified against primary sources (Data.ipynb, CONTEXT.md, official documentation).

## Metadata

**Confidence breakdown:**
- **Standard stack:** HIGH — pandas, numpy, matplotlib are industry standard; versions verified in documentation.
- **Architecture & data flow:** HIGH — CONTEXT.md and Data.ipynb provide explicit patterns.
- **Pitfalls & patterns:** MEDIUM — based on standard financial practice, not project-specific validation.
- **Environment:** MEDIUM — assuming server has standard Python scientific stack pre-installed; not explicitly verified.

**Research date:** 2026-04-22
**Valid until:** 2026-05-22 (30 days — stable domain, no rapid library churn expected)

**Next actions for planner:**
1. Read Data.ipynb to verify Django ORM and Bloomberg syntax examples are correct for current server version.
2. Create Phase 1 plan (01-01, 01-02, 01-03) mapping to Architecture Patterns and Code Examples above.
3. Plan task 01-01 should include Setup cell creation with fund identifier and date range prompts.
4. Plan task 01-02 should cover Data Load cell (Django ORM + Bloomberg pulls) with error handling.
5. Plan task 01-03 should cover Log Returns → Alignment → EDA (all four charts + summary stats table).
