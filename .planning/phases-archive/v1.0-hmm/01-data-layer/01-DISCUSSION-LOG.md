# Phase 1: Data Layer - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-22
**Phase:** 01-data-layer
**Areas discussed:** DB connection setup, Data pull shape, Return type and cleaning, EDA scope

---

## Architecture

| Option | Description | Selected |
|--------|-------------|----------|
| data.ipynb runs first, saves files | Pulls from server, saves CSVs/parquet; hmm.ipynb reads files | |
| data.ipynb is reference/context only | Documents pull patterns; hmm.ipynb connects directly | ✓ |
| Same notebook, two sections | data.ipynb content merged into hmm.ipynb | |

**User's clarification:** Same pattern as deck-auto — notebook runs server-side, not locally. `data.ipynb` provides context on how to pull data on the Jupyter server. No local code execution.

---

## DB Connection Setup

| Option | Description | Selected |
|--------|-------------|----------|
| Django ORM / shell_plus | Same as deck-auto — Django models accessible directly | ✓ |
| pandas + SQL (pyodbc/SQLAlchemy) | pd.read_sql() with connection string | |
| Custom internal library | Company-specific wrapper or Bloomberg con.bdh | |

**User's choice:** Django ORM / shell_plus

---

## Data Pull Shape — Fund

| Option | Description | Selected |
|--------|-------------|----------|
| NAV or price series | Load and compute returns with pct_change / log | ✓ |
| Pre-computed daily returns | DB stores returns directly | |
| data.ipynb will clarify | Details in reference notebook | |

**User's choice:** NAV or price series (compute returns ourselves)

---

## Data Pull Shape — Benchmark

| Option | Description | Selected |
|--------|-------------|----------|
| Bloomberg API (con.bdh) | Separate from Django ORM, used for market data | ✓ |
| Stored in Django DB too | Bloomberg data imported into same DB | |
| data.ipynb will show both | Details in reference notebook | |

**User's notes:** Each fund has a different benchmark which is complex to match. Decision: use S&P 500 as universal benchmark via Bloomberg API to avoid the peer-matching complexity.

---

## Return Type

| Option | Description | Selected |
|--------|-------------|----------|
| Log returns | ln(P_t / P_{t-1}) — better normality, standard for Gaussian HMM | ✓ |
| Simple returns | pct_change() — more intuitive but slightly skewed | |
| Claude decides | Statistically appropriate choice | |

**User's choice:** Log returns

---

## Return Frequency

| Option | Description | Selected |
|--------|-------------|----------|
| Daily | More data for regime estimation; standard for equity HMMs | ✓ |
| Weekly | Less noise, fewer observations | |
| Monthly | Fewest observations | |

**User's choice:** Daily

---

## Gap Handling / Date Alignment

| Option | Description | Selected |
|--------|-------------|----------|
| Inner join — keep shared dates | Drop dates where either series is missing. No imputation. | ✓ |
| Forward fill gaps | Use last known value to fill non-trading days | |
| Claude decides | Use statistically cleanest approach | |

**User's choice:** Inner join

---

## EDA Chart Style

| Option | Description | Selected |
|--------|-------------|----------|
| Functional only | Matplotlib defaults, labels and titles only | |
| Light structure now | Figure sizes + basic color scheme set up in Phase 1 | ✓ |

**User's choice:** Light structure (figure sizes + color scheme in Phase 1; Phase 5 polishes)

---

## EDA Summary Statistics

| Option | Description | Selected |
|--------|-------------|----------|
| Return + vol + Sharpe + max drawdown | Four metrics, full history, baseline for Phase 3 | ✓ |
| Expand with skew, kurtosis, VaR | Richer quant-oriented stats | |
| Claude decides | Whatever is appropriate for data quality check | |

**User's choice:** Return + vol + Sharpe + max drawdown

---

## Claude's Discretion

- Exact figure sizes and baseline color constants
- Drawdown computation method
- Cell organization and markdown headers
- Annualization convention (252 trading days assumed)

## Deferred Ideas

None surfaced during discussion.
