# Coding Conventions

**Analysis Date:** 2026-05-06

## Naming Patterns

**Files:**
- `snake_case.py` throughout — `greeks_engine.py`, `exposure_engine.py`, `data_loader.py`
- Private helpers prefixed with `_`: `_parse_symbol`, `_find_zero_crossing`, `_bar_width`, `_fmt_gex`
- Entry-point modules prefixed with `run_`: `run_gex.py`, `run_daily.py`
- Test files: `test_<module_name>.py` or `test_<feature_area>.py`

**Functions:**
- `snake_case` throughout
- Pure computation functions: `bs_gamma`, `bs_vanna`, `bs_charm`, `compute_gex`, `compute_vex`
- Aggregation functions: `strike_gex`, `strike_vex`, `strike_chex`, `expiry_gex`
- Builder/orchestrator functions: `build_email`, `compute_ticker`, `add_greeks`
- Private HTML fragment builders: `_index_row`, `_purpose_row`, `_badge`, `_section_header`

**Variables:**
- `snake_case` for locals and parameters
- Short scientific names accepted for math: `d1`, `d2`, `s`, `k`, `v`, `t` inside tight computation scope
- DataFrame convention: `df` for working frame, `s_df`/`v_df`/`c_df` for strike-level aggregates, `p_df` for profile
- Summary scalars: `net_gex`, `net_vex`, `net_chex` — consistent across all callers

**Constants:**
- `SCREAMING_SNAKE_CASE`: `MULTIPLIER`, `NEUTRAL_BAND_PCT`, `NEUTRAL_ABS_FLOOR`, `T_MIN`, `STORE`, `OUT_DIR`
- Module-level mapping dicts: `REGIME_COLOR`, `REGIME_BG`, `TICKER_LABEL`, `GEX_CELL_BG`

**Types/Classes:**
- `PascalCase` for dataclasses: `ChainSnapshot`
- No ABCs, no base classes — composition via dict passing

## Code Style

**Formatting:**
- No formatter config file detected (no `.prettierrc`, `black.toml`, `ruff.toml`)
- Consistent 4-space indent throughout
- Line lengths generally ≤100 chars; HTML template strings in `report.py` are wider
- Blank line between logical blocks within functions; two blank lines between top-level definitions

**Linting:**
- No linter config detected (no `.flake8`, `pyproject.toml`, `ruff.toml`)
- Code is clean: zero `TODO`, `FIXME`, `HACK`, `type: ignore` comments found in any source file

## Import Organization

**Order (observed pattern):**
1. `from __future__ import annotations` — present in every source file
2. Standard library (`datetime`, `pathlib`, `dataclasses`, `os`)
3. Third-party (`numpy`, `pandas`, `scipy`, `plotly`, `requests`, `yfinance`)
4. Internal `gex.*` imports

**Deferred imports:** Heavy optional imports deferred inside functions where appropriate — e.g., `win32com.client` inside `emailer.send()`, `pandas_market_calendars` inside `load_yesterday()`, `datetime` inside `add_greeks()`.

**Path Aliases:** None — bare `gex.` package imports used throughout.

## Module Docstrings

Every source module has a module-level docstring explaining:
- What the module computes/does
- Key conventions (e.g., sign convention in `exposure_engine.py`)
- Assumptions baked in (e.g., retail-buys-dealers-sell in `exposure_engine.py`)
- Data source notes (e.g., CBOE vs Black-Scholes distinction in `greeks_engine.py`)

Function docstrings present on public API functions; absent on private helpers and trivial internal functions.

## Error Handling

**Strategy:** Validate at data boundaries; no defensive catches in pure computation.

**Patterns:**
- `data_loader.py`: `resp.raise_for_status()` — HTTP errors propagate as exceptions
- `validation.py` `load_yesterday()`: broad `except Exception: return None` — network/parquet failures return None, never raise
- `run_daily.py` `process_ticker()`: catches all exceptions, stores error in result dict — orchestrator never crashes on one bad ticker
- `emailer.py`: narrow try/except around `GetActiveObject` / `Dispatch` — raises descriptive `RuntimeError` on failure
- No empty `except:` blocks

## DataFrame Mutation

Functions that modify DataFrames always:
1. Call `df = df.copy()` at the top
2. Return the copy

This is consistent across `compute_gex`, `compute_vex`, `compute_chex`, `add_greeks`, `strike_gex`. Tests verify this pattern explicitly (`test_add_greeks_does_not_mutate_input`, `test_original_df_unchanged`).

## Comments

**When to Comment:**
- Math formulas with non-obvious derivation: `d1`, `d2`, charm numerator/denominator
- Sign conventions: `# Unsigned — sign convention applied in Phase 2`
- Guard conditions: `# T_MIN guard: rows where original T < 1/365 return 0.0`
- Calibration notes: `# Calibrated 2026-05-05 against post-filter noise tickers`
- No docstrings on trivial private helpers (`_bar_width`, `_fmt_price`)

## Function Design

**Size:** Functions stay focused; longest is `compute_ticker` in `gex/compute.py` at ~60 effective lines, most are under 20.

**Parameters:** Positional for primary data (`df`, `spot`), keyword with defaults for tuning params (`r=0.05`, `n_points=200`, `width_pct=0.15`).

**Return Values:** 
- Computation functions return a single typed value (DataFrame, float, dict)
- `summarise()` returns a flat dict — keys documented in module docstring
- `compute_ticker()` returns a structured dict with documented keys in its docstring

## Module Design

**Exports:** No `__all__` defined anywhere — all public names importable directly.

**Barrel Files:** `gex/__init__.py` is empty — no re-exports. Callers use explicit paths: `from gex.analytics import summarise`.

**Shared Constants:** Cross-module constants (`REGIME_COLOR`, `TICKER_LABEL`) live in `gex/report.py` and are imported by `gex/analytics.py` where needed.

---

*Convention analysis: 2026-05-06*

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
<!-- LINKS:END -->
