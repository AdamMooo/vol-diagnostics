# Testing Patterns

**Analysis Date:** 2026-05-06

## Test Framework

**Runner:**
- pytest >= 8.0
- Config: none — no `pytest.ini`, `setup.cfg`, or `pyproject.toml` found; pytest uses defaults

**Assertion Library:**
- pytest built-in assertions + `pytest.approx` for float comparisons

**Run Commands:**
```bash
# From project root (activate .venv first)
python -m pytest gex/tests/          # Run all tests
python -m pytest gex/tests/ -q       # Quiet summary
python -m pytest gex/tests/ -v       # Verbose (test names)
python -m pytest gex/tests/test_greeks_engine.py   # Single file
```

**Current status:** 77 tests collected; 76 pass, 1 failing (`test_add_greeks_has_gamma_column` — `add_greeks` does not produce a `gamma` column because the chain fixture lacks a `gamma` column; the test assumes pass-through that doesn't exist).

## Test File Organization

**Location:** Co-located inside the package at `gex/tests/`

**Naming:**
- `test_<module>.py` for module-scoped tests: `test_greeks_engine.py`, `test_exposure_engine.py`
- `test_<feature_area>.py` for cross-module or flow tests: `test_exposure_flow.py`, `test_validation_history.py`, `test_analytics_summarise.py`, `test_streamlit_app.py`

**Structure:**
```
gex/
  tests/
    __init__.py                     (empty)
    test_greeks_engine.py           (213 lines — bs_vanna, bs_charm, add_greeks)
    test_exposure_engine.py         (111 lines — compute_vex, compute_chex, strike_vex, strike_chex)
    test_exposure_flow.py           (129 lines — integration: vex/chex pipeline + classify_vs_yesterday)
    test_analytics_summarise.py     ( 54 lines — summarise() signature and return values)
    test_validation_history.py      (118 lines — load_history() with tmp parquet fixtures)
    test_streamlit_app.py           ( 29 lines — import isolation + cache + plot rendering)
```

## Test Structure

**Flat functions for focused unit tests:**
```python
def test_bs_vanna_atm_positive():
    v = bs_vanna(100.0, 100.0, 0.20, 0.25)
    assert np.isfinite(v)
    assert v > 0.0

def test_bs_charm_0dte_guard():
    c = bs_charm(100.0, 100.0, 0.20, 0.0001)
    assert c == pytest.approx(0.0, abs=1e-10)
```

**Class grouping for related sets** (used in `test_exposure_engine.py`):
```python
class TestComputeVex:
    def test_returns_copy_with_vex_column(self, greek_df): ...
    def test_calls_positive_vex(self, greek_df): ...
    def test_formula_spot_not_spot_squared(self, greek_df): ...
```

Both styles are present — flat functions for math boundary tests, classes for DataFrame API tests.

**Separator comments** mark logical groups within flat test files:
```python
# ---------------------------------------------------------------------------
# bs_vanna — scalar inputs
# ---------------------------------------------------------------------------
```

## Mocking

**Framework:** `pytest.monkeypatch` (stdlib, no `unittest.mock`)

**Primary use case:** Redirect module-level `STORE` path to `tmp_path` fixtures to avoid touching the real parquet file:
```python
def test_load_history_returns_n_rows(tmp_path, monkeypatch):
    import gex.validation as val
    store = tmp_path / "snap.parquet"
    _make_store(store, rows)
    monkeypatch.setattr(val, "STORE", store)
    result = load_history("SPY", days=3)
```

**`pytest.importorskip`** used in `test_streamlit_app.py` to skip tests if `streamlit` is not installed:
```python
pytest.importorskip("streamlit")
```

**What is NOT mocked:**
- Network calls (`load_chain`, `yfinance.download`) — no network tests; data-dependent paths are untested
- `win32com.client` — `emailer.send()` is untested
- `datetime.date.today()` — boundary tests use fixed scalar inputs instead

## Fixtures

**pytest fixtures** used for shared DataFrame construction:
```python
@pytest.fixture
def greek_df():
    return pd.DataFrame({
        "strike": [490.0, 490.0, 500.0, 500.0],
        "type":   ["call", "put", "call", "put"],
        "oi":     [100,    200,   150,    250],
        "vanna":  [0.05,   0.04,  0.06,   0.03],
        "charm":  [0.02,   0.015, 0.025,  0.01],
    })
```

**Private helper factories** for inline data construction (used in flat-function test files):
```python
def _make_chain(expiry: str = "2026-09-19") -> pd.DataFrame:
    return pd.DataFrame({...})

def _make_store(path: pathlib.Path, rows: list[dict]) -> None:
    pd.DataFrame(rows).to_parquet(path, index=False)

def _row(ticker, date, spot=500.0, ...) -> dict:
    return {...}
```

**Location:** Fixtures and helpers defined at module top — no shared `conftest.py`.

## Coverage

**Requirements:** None enforced (no coverage config, no CI).

**Covered areas:**
- `gex/greeks_engine.py` — comprehensive: scalar/array inputs, boundary conditions (T=0, iv=0, strike=0, spot=0), T_MIN guard, mutation safety
- `gex/exposure_engine.py` — compute_vex, compute_chex, strike_vex, strike_chex; formula correctness assertions
- `gex/analytics.py` — `summarise()` signature, return dict keys, optional kwarg pass-through
- `gex/validation.py` — `load_history()`, `_classify_vs_yesterday()`, `load_yesterday()` absent-store guard
- `streamlit_app.py` — import isolation, cache decorator presence, `plot_overview` rendering

**Not covered (no tests):**
- `gex/data_loader.py` — `load_chain()` and `_parse_symbol()` have no unit tests; requires network or fixture mocking
- `gex/exposure_engine.py` `gamma_profile()` — the profile computation loop is untested
- `gex/exposure_engine.py` `compute_gex()` and `strike_gex()` — no direct tests (tested transitively via `test_exposure_flow.py` helpers)
- `gex/analytics.py` — all chart functions (`plot_strike_gex`, `plot_gamma_profile`, `plot_overview` partially) and `_find_zero_crossing` are untested directly
- `gex/validation.py` — `save_snapshot()`, `event_study()` have no tests
- `gex/emailer.py` — `send()` is entirely untested
- `gex/run_daily.py` — `is_trading_day()`, `process_ticker()`, `run()` are untested
- `gex/report.py` — all HTML builder functions (`build_email`, `_index_table`, `_purpose_table`, etc.) are untested

## Test Types

**Unit Tests:**
- Primary test type — pure function inputs → expected outputs
- Numeric: `pytest.approx` for float equality, `abs=1e-9` or `abs=1e-10` tolerances used consistently
- DataFrame: column presence, shape, mutation safety, sort order

**Integration Tests:**
- `test_exposure_flow.py` tests the VEX/CHEX pipeline across multiple modules in sequence
- `test_streamlit_app.py` tests the import graph (no emailer bleed) — a lightweight import integration test

**E2E Tests:** None — no tests that exercise the full `compute_ticker()` pipeline end-to-end

## Common Patterns

**Boundary / guard condition testing:**
```python
def test_bs_vanna_zero_T():
    assert bs_vanna(100.0, 100.0, 0.20, 0.0) == 0.0

def test_bs_vanna_negative_T():
    assert bs_vanna(100.0, 100.0, 0.20, -0.01) == 0.0

def test_bs_vanna_zero_iv():
    assert bs_vanna(100.0, 100.0, 0.0, 0.25) == 0.0
```

**Formula regression tests** — assert the mathematical formula, not just sign:
```python
def test_formula_spot_not_spot_squared(self, greek_df):
    expected_first_call = 1.0 * 0.05 * 100 * 100 * 500.0 * 0.01
    assert abs(result.iloc[0]["vex"] - expected_first_call) < 1e-9
```

**Negative formula test** — assert a wrong formula does NOT match:
```python
def test_compute_vex_spot_not_squared():
    wrong = 1.0 * 1 * 100 * 500.0 ** 2 * 0.01
    assert abs(result["vex"].iloc[0]) != pytest.approx(abs(wrong))
```

**Cancellation tests** — equal call/put OI should net to zero:
```python
def test_strike_vex_equal_oi_call_put_cancel():
    df = _chain(calls=1, puts=1, spot=500.0)
    result = strike_vex(compute_vex(df, spot=500.0))
    assert result["vex"].iloc[0] == pytest.approx(0.0)
```

---

*Testing analysis: 2026-05-06*

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
<!-- LINKS:END -->
