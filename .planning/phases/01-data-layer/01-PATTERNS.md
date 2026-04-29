# Phase 1: Data Layer - Pattern Map

**Mapped:** 2026-04-22  
**Files analyzed:** 1 (hmm.ipynb cells)  
**Analogs found:** 1/1 (Data.ipynb, perfect match)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `hmm.ipynb` (Phase 1 cells: Setup, Data Load, Log Returns, Alignment, EDA) | notebook (research, data load, compute) | request-response (Django ORM + Bloomberg API) → batch transform (log returns, alignment) → visualization | `Data.ipynb` | exact |

**Rationale:** Phase 1 notebook cells directly mirror the canonical reference patterns in Data.ipynb. Same server environment (shell_plus), same data sources (Django ORM for fund NAV, Bloomberg `con.bdh()` for benchmark), same pandas/numpy transform patterns.

---

## Pattern Assignments

### `hmm.ipynb` — Phase 1 Setup Cell

**Analog:** `Data.ipynb` (lines 1-10, 51-69)

**Imports pattern** (standard stack for notebook data science):
```python
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

# Pandas display options
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
```

**Setup documentation pattern** (from Data.ipynb cell explaining ORM/Bloomberg context):
```python
# ===== SETUP: Fund & Benchmark Parameters =====
# Fund identifier (via FundAccount model)
FUND_SYMBOL = 'PYF'  # Example: Purpose Investments target fund

# Benchmark choice
BENCHMARK_TICKER = 'SPXT Index'  # S&P 500 Total Return Index

# Date range
START_DATE = '2020-01-01'
END_DATE = '2026-04-22'

# Connection context (pre-loaded in shell_plus on server)
# Django: FundAccount, Fund models pre-loaded
# Bloomberg: con object pre-loaded (con.bdh, con.ref methods available)

print(f"Setup: {FUND_SYMBOL} vs {BENCHMARK_TICKER}")
print(f"Period: {START_DATE} to {END_DATE}")
print(f"Note: This notebook runs on server (shell_plus). Django ORM and Bloomberg con are pre-loaded.")
```

**Anti-pattern to avoid:** Do not assume local file paths or external API keys. Everything references server-side pre-loaded context.

---

### `hmm.ipynb` — Phase 1 Data Load Cell

**Analog:** `Data.ipynb` (lines 625-796, lines 388-532)

**Django ORM Fund Data Pull** (exact signature from Data.ipynb):
```python
# Source: Data.ipynb lines 625-796
# Load fund NAV via Django ORM (FundAccount query)

from datetime import datetime

# Get fund account by symbol
fa = FundAccount.objects.get(symbol=FUND_SYMBOL)

# Retrieve adjusted NAV series (returns pd.Series with DatetimeIndex)
df_nav = fa.primary_fund.get_adj_nav()

# Validate loaded data
print(f"Fund NAV loaded: {len(df_nav)} observations")
print(f"Date range: {df_nav.index.min()} to {df_nav.index.max()}")
print(f"NAV range: {df_nav.min():.2f} to {df_nav.max():.2f}")

# Filter to requested date range
df_nav = df_nav[(df_nav.index >= pd.to_datetime(START_DATE)) & 
                (df_nav.index <= pd.to_datetime(END_DATE))]
```

**Bloomberg Benchmark Data Pull** (exact signature from Data.ipynb):
```python
# Source: Data.ipynb lines 388-532
# Load benchmark price via Bloomberg API (con.bdh)

import pandas as pd

# con object is pre-loaded in shell_plus
# con.bdh() fetches historical time series data

# Fetch S&P 500 Total Return Index (SPXT)
df_bench = con.bdh(BENCHMARK_TICKER, 'PX_LAST', 
                    start_date=START_DATE, end_date=END_DATE)

# Rename column for clarity and extract as Series
df_bench.columns = ['price']
df_bench_price = df_bench['price']

# Validate loaded data
print(f"Benchmark loaded: {len(df_bench_price)} observations")
print(f"Date range: {df_bench_price.index.min()} to {df_bench_price.index.max()}")
print(f"Price range: {df_bench_price.min():.2f} to {df_bench_price.max():.2f}")
```

**Key detail:** Both `get_adj_nav()` and `con.bdh()` return Series/DataFrames with DatetimeIndex. No additional date parsing needed.

---

### `hmm.ipynb` — Phase 1 Log Returns Cell

**Analog:** RESEARCH.md Code Examples (Pattern 3), verified against Data.ipynb usage

**Log Returns Computation** (standard pattern, verified in RESEARCH.md):
```python
# Source: CONTEXT.md Decision D-06 (numpy.log approach)
# Convert price/NAV series to log returns

import numpy as np

# Compute log returns
fund_price = df_nav
fund_log_returns = np.log(fund_price / fund_price.shift(1))
fund_log_returns = fund_log_returns.dropna()

bench_price = df_bench_price
bench_log_returns = np.log(bench_price / bench_price.shift(1))
bench_log_returns = bench_log_returns.dropna()

# Validate returns
print(f"Fund returns: {len(fund_log_returns)} observations")
print(f"Bench returns: {len(bench_log_returns)} observations")
print(f"Fund return range: {fund_log_returns.min():.4f} to {fund_log_returns.max():.4f}")
print(f"Bench return range: {bench_log_returns.min():.4f} to {bench_log_returns.max():.4f}")

# Check frequency
print(f"Fund frequency inferred: {fund_log_returns.index.inferred_freq}")
print(f"Bench frequency inferred: {bench_log_returns.index.inferred_freq}")
# Both should be 'D' (daily)
```

**Why log returns:** Preferred for HMM fitting (better Gaussian assumption). Additive over time, which aligns with Gaussian HMM model.

---

### `hmm.ipynb` — Phase 1 Alignment Cell

**Analog:** RESEARCH.md Code Examples (Pattern 4), pandas standard practice

**Inner Join Alignment** (decision D-08 enforced):
```python
# Source: RESEARCH.md Pattern 4 (Date Alignment)
# Synchronize fund and benchmark returns on common date index

import pandas as pd

# Create aligned DataFrame (inner join)
returns_df = pd.DataFrame({
    'fund': fund_log_returns,
    'bench': bench_log_returns
})

# Inner join: keep only dates where both have valid data
# This is equivalent to dropna() on the combined frame
aligned_returns = returns_df.dropna()

# Validate alignment
print(f"Original fund observations: {len(fund_log_returns)}")
print(f"Original bench observations: {len(bench_log_returns)}")
print(f"Aligned observations: {len(aligned_returns)}")
print(f"Coverage: {len(aligned_returns) / min(len(fund_log_returns), len(bench_log_returns)) * 100:.1f}%")

# Check for date gaps (business day gaps expected — weekends, holidays)
date_diffs = aligned_returns.index.to_series().diff()
max_gap = date_diffs.max()
print(f"Max gap in aligned index: {max_gap.days} days")
print(f"Expected: 3 days (Friday to Monday) or 1 day (normal)")

# Verify no NaN in final aligned data
assert aligned_returns.isnull().sum().sum() == 0, "Unexpected NaN in aligned data"

# Extract individual series for downstream use
fund_aligned = aligned_returns['fund']
bench_aligned = aligned_returns['bench']
```

**Anti-pattern to avoid:** No forward-filling. Decision D-08 is explicit: drop missing dates via inner join, do not impute.

---

### `hmm.ipynb` — Phase 1 EDA Summary Statistics Cell

**Analog:** RESEARCH.md Code Examples (Pattern 6), Data.ipynb cell 14ba6934

**Summary Statistics Computation** (annualization with 252 trading days):
```python
# Source: RESEARCH.md Pattern 6 (Annualized Statistics)
# Compute full-history summary stats for baseline comparison

import pandas as pd
import numpy as np

def compute_summary_stats(returns_series, risk_free_rate=0.02):
    """
    Compute annualized statistics from daily return series.
    
    Args:
        returns_series: pd.Series of daily log returns
        risk_free_rate: annual risk-free rate (default 2%)
    
    Returns:
        dict with annualized metrics
    """
    
    # Daily metrics
    daily_mean = returns_series.mean()
    daily_std = returns_series.std()
    
    # Annualized return (compound daily returns)
    annual_return = (1 + daily_mean) ** 252 - 1
    
    # Annualized volatility (scale daily std dev)
    annual_vol = daily_std * np.sqrt(252)
    
    # Sharpe ratio (excess return / volatility)
    excess_return = annual_return - risk_free_rate
    sharpe = excess_return / annual_vol if annual_vol > 0 else 0
    
    # Maximum drawdown (full history)
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

# Compute for both fund and benchmark
fund_stats = compute_summary_stats(fund_aligned, risk_free_rate=0.02)
bench_stats = compute_summary_stats(bench_aligned, risk_free_rate=0.02)

# Create summary table
stats_table = pd.DataFrame({
    'Fund': fund_stats,
    'Benchmark': bench_stats
}).T

print("\n=== SUMMARY STATISTICS (Full History) ===")
print(stats_table.to_string())

# Format for readability
print(f"\nFund Annual Return: {fund_stats['Annual Return']:.2%}")
print(f"Fund Annual Volatility: {fund_stats['Annual Volatility']:.2%}")
print(f"Fund Sharpe Ratio: {fund_stats['Sharpe Ratio']:.2f}")
print(f"Fund Max Drawdown: {fund_stats['Max Drawdown']:.2%}")
```

**Annualization note:** Standard 252 trading days convention for daily equity data. Risk-free rate default is 2%; can be overridden.

---

### `hmm.ipynb` — Phase 1 EDA Charts Cell (Cumulative Return)

**Analog:** RESEARCH.md Code Examples (Pattern 7), matplotlib standard

**Cumulative Return Chart** (shared time axis, fund vs benchmark):
```python
# Source: RESEARCH.md Pattern 7 (EDA Cumulative Return Chart)
# Plot cumulative returns for fund and benchmark

import pandas as pd
import matplotlib.pyplot as plt

# Compute cumulative returns
cumret_fund = (1 + fund_aligned).cumprod()
cumret_bench = (1 + bench_aligned).cumprod()

# Create figure
fig, ax = plt.subplots(figsize=(12, 4))

# Plot both series
ax.plot(cumret_fund.index, cumret_fund.values, 
        label='Fund', linewidth=2, color='#1f77b4')
ax.plot(cumret_bench.index, cumret_bench.values, 
        label='Benchmark', linewidth=2, color='#ff7f0e')

# Formatting
ax.set_xlabel('Date')
ax.set_ylabel('Cumulative Return (index)')
ax.set_title('Fund vs Benchmark Cumulative Returns')
ax.legend()
ax.grid(True, alpha=0.3)

# Format y-axis as multiple of starting value (e.g., 1.5x)
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:.1f}x'))

plt.tight_layout()
plt.show()
```

**Color constants:** Fund = '#1f77b4' (blue), Benchmark = '#ff7f0e' (orange). Phase 5 will refine palette.

---

### `hmm.ipynb` — Phase 1 EDA Charts Cell (Rolling Volatility)

**Analog:** RESEARCH.md Code Examples (Pattern 8), Data.ipynb patterns

**Rolling 21-Day Volatility Chart**:
```python
# Source: RESEARCH.md Pattern 8 (Rolling 21-Day Volatility)
# Annualized volatility in a rolling 21-day window

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Compute rolling 21-day volatility (annualized)
rolling_vol_fund = fund_aligned.rolling(window=21).std() * np.sqrt(252)
rolling_vol_bench = bench_aligned.rolling(window=21).std() * np.sqrt(252)

# Create figure
fig, ax = plt.subplots(figsize=(12, 4))

# Plot both series
ax.plot(rolling_vol_fund.index, rolling_vol_fund.values, 
        label='Fund', linewidth=2, color='#1f77b4')
ax.plot(rolling_vol_bench.index, rolling_vol_bench.values, 
        label='Benchmark', linewidth=2, color='#ff7f0e')

# Formatting
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

**Window choice:** 21-day rolling window (approximately 1 month of trading days). Annualization factor: sqrt(252).

---

### `hmm.ipynb` — Phase 1 EDA Charts Cell (Drawdown)

**Analog:** RESEARCH.md Code Examples (Pattern 5), standard financial practice

**Drawdown Chart** (fund only):
```python
# Source: RESEARCH.md Pattern 5 (Rolling Maximum Drawdown)
# Compute and visualize peak-to-trough decline

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Compute cumulative return and running maximum
cumret_fund = (1 + fund_aligned).cumprod()
running_max = cumret_fund.expanding().max()

# Drawdown = (current - peak) / peak
drawdown = (cumret_fund - running_max) / running_max

# Create figure
fig, ax = plt.subplots(figsize=(12, 4))

# Plot drawdown (as negative values)
ax.fill_between(drawdown.index, 0, drawdown.values, 
                color='#d62728', alpha=0.5, label='Drawdown')
ax.plot(drawdown.index, drawdown.values, 
        color='#d62728', linewidth=1.5)

# Formatting
ax.set_xlabel('Date')
ax.set_ylabel('Drawdown')
ax.set_title('Fund Drawdown Over Time')
ax.legend()
ax.grid(True, alpha=0.3)

# Format y-axis as percentage
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:.0%}'))

plt.tight_layout()
plt.show()

# Compute and report max drawdown
max_dd = drawdown.min()
max_dd_date = drawdown.idxmin()
print(f"Maximum Drawdown: {max_dd:.2%} on {max_dd_date.strftime('%Y-%m-%d')}")
```

**Color:** Drawdown chart uses red (#d62728) to highlight losses.

---

## Shared Patterns

### Data Loading Pattern (Django ORM + Bloomberg)

**Source:** `Data.ipynb` (canonical reference)  
**Apply to:** All Phase 1 data loading cells

**Key insight:** Both data sources (Django ORM, Bloomberg API) are pre-loaded in server shell_plus. No explicit connection initialization needed in the notebook. Simply query/call with parameters (symbol, date range) and receive pandas Series/DataFrame with DatetimeIndex.

**Connection verification code** (to add in Setup cell):
```python
# Verify Django context is available
try:
    test_fa = FundAccount.objects.first()
    print("✓ Django ORM available")
except NameError:
    print("✗ Django context not loaded — must run on server shell_plus")

# Verify Bloomberg context is available
try:
    test_df = con.bdh('SPX Index', 'PX_LAST', '2026-04-21', '2026-04-22')
    print(f"✓ Bloomberg available (test pull returned {len(test_df)} rows)")
except NameError:
    print("✗ Bloomberg con object not available — must run on server with terminal")
```

---

### Pandas Data Alignment Pattern

**Source:** RESEARCH.md, pandas standard practice  
**Apply to:** Phase 1 Alignment cell and any subsequent phase that needs synchronized data

**Key principle:** Inner join only (no forward-fill, no interpolation). Missing dates are dropped explicitly via `.dropna()`.

```python
# Standard pattern: combine series, drop NaN
aligned = pd.DataFrame({
    'series1': returns1,
    'series2': returns2
}).dropna()

# Alternative explicit pattern:
aligned = pd.merge(
    returns1.to_frame('series1'),
    returns2.to_frame('series2'),
    left_index=True, right_index=True, how='inner'
)
```

---

### Matplotlib Charting Pattern

**Source:** Data.ipynb, RESEARCH.md Code Examples  
**Apply to:** All Phase 1 and Phase 5 charting cells

**Standard figure setup:**
```python
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(12, 4))  # Consistent size (Phase 1 basic)

# Plot data with color constants
ax.plot(dates, values, label='Series', linewidth=2, color='#1f77b4')

# Always include: labels, title, legend, grid
ax.set_xlabel('Date')
ax.set_ylabel('Value')
ax.set_title('Chart Title')
ax.legend()
ax.grid(True, alpha=0.3)

# Format axes appropriately
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:.0%}'))  # percentage

plt.tight_layout()
plt.show()
```

**Color palette (Phase 1 baseline, Phase 5 will refine):**
- Fund: `#1f77b4` (blue)
- Benchmark: `#ff7f0e` (orange)
- Drawdown: `#d62728` (red)

---

## No Analog Found

**None.** The canonical reference `Data.ipynb` provides all required patterns for Phase 1:
- Django ORM fund data pull
- Bloomberg benchmark API call
- Pandas data alignment
- Matplotlib charting
- Statistics computation

No external patterns needed beyond what's in the codebase and standard financial practice (confirmed in RESEARCH.md).

---

## Metadata

**Analog search scope:** Searched `C:\dev\tq-hmm\` for `.ipynb` files  
**Files scanned:** 2 (Data.ipynb, hmm.ipynb)  
**Analogs matched:** 1/1 (Data.ipynb is 100% match for Phase 1 patterns)  
**Pattern extraction date:** 2026-04-22

**Confidence:** HIGH
- Data.ipynb provides exact working code for Django ORM and Bloomberg patterns
- RESEARCH.md Code Examples section validates all pandas/numpy/matplotlib patterns
- CONTEXT.md decisions (D-01 through D-11) lock all technical choices

**Next step for planner:** Read Data.ipynb directly to verify Django ORM and Bloomberg method signatures are current for the server environment. Then proceed with Phase 1 plan using patterns in this document.
