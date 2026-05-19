# Codebase Concerns

**Analysis Date:** 2026-05-06

---

## Bugs

**`run_gex.py` calls `.savefig()` on a Plotly Figure:**
- Issue: `plot_strike_gex()` and `plot_gamma_profile()` in `gex/analytics.py` return `plotly.graph_objects.Figure` objects. `gex/run_gex.py` imports `matplotlib` and calls `fig1.savefig(path1, dpi=150)` on these — a matplotlib method. Plotly Figure has no `.savefig()`. This raises `AttributeError` at runtime whenever `--no-save` is not passed.
- Files: `gex/run_gex.py` lines 54–62, `gex/analytics.py` lines 80–126
- Impact: `python -m gex.run_gex` always crashes on save unless `--no-save` is passed. The `--no-save` path also switches to `TkAgg` backend and calls `plt.show()` on Plotly figures — equally broken.
- Fix approach: Replace `fig1.savefig(path1, dpi=150)` with `fig1.write_image(str(path1))` (requires `kaleido`) or `fig1.write_html(str(path1))`. `kaleido` is not in `requirements.txt`. Either add it or switch saves to `.write_html()`.

---

## Tech Debt

**`run_gex.py` is a stale POC artifact kept as a live entry point:**
- Issue: The module docstring calls it a "POC entry point" and it's structured for matplotlib. The rest of the system (Streamlit, `run_daily`, `compute.py`) has moved to Plotly and `compute_ticker()`. `run_gex.py` duplicates a partial pipeline: it calls `load_chain → add_greeks → compute_gex → strike_gex → gamma_profile → summarise` directly, bypassing `compute.py`. VEX/CHEX and `vs_yesterday` are not computed.
- Files: `gex/run_gex.py`
- Impact: Any pipeline change in `compute.py` won't be reflected in `run_gex.py` output. Currently broken at save path (see Bug above).
- Fix approach: Rewrite as a thin wrapper around `compute_ticker()` + `write_html()`/print, or remove entirely if `streamlit_app.py` and `run_daily.py` cover all use cases.

**Hardcoded risk-free rate (`r=0.05`) throughout:**
- Issue: `bs_gamma`, `bs_vanna`, `bs_charm`, and `gamma_profile` all default to `r=0.05`. The rate is never pulled from data. As of 2026 the Fed funds rate is materially different from 5%.
- Files: `gex/greeks_engine.py` lines 22, 50, 73, 107; `gex/exposure_engine.py` line 72
- Impact: Vanna, charm, and gamma profile (used for ZGL) are computed with a stale rate. Primary GEX uses CBOE's own gamma (unaffected), but ZGL interpolation is derived from the BS-recalculated profile.
- Fix approach: Accept `r` as a parameter in `compute_ticker()` and thread it through. Alternatively pull FRED SOFR — the infra (`FreeCon`) exists in the v2.1 engine.

**Dual gamma sources (CBOE for strike-level GEX, BS for gamma profile/ZGL):**
- Issue: `compute_gex()` uses `df["gamma"]` from CBOE (American-style, dividend-adjusted). `gamma_profile()` in `exposure_engine.py` recalculates gamma via `bs_gamma()` (European Black-Scholes) for the profile sweep. This means the net GEX value and the ZGL can diverge in sign when American vs European valuations differ significantly (deep ITM, dividend-paying single names).
- Files: `gex/exposure_engine.py` lines 30 and 73–76
- Impact: ZGL computed from the BS profile may not align with the strike-level GEX computed from CBOE gammas — especially for equities with dividends (AAPL, MSFT, COST, AMZN).
- Fix approach: Document the dual-source explicitly in `exposure_engine.py`; consider using CBOE gammas for the profile sweep too (interpolate by strike) rather than recomputing via BS.

**`save_snapshot()` has no file lock — concurrent writes corrupt the parquet store:**
- Issue: `save_snapshot()` in `gex/validation.py` reads the existing parquet, appends a row, and writes back. If `run_daily.py` runs while `streamlit_app.py` is also triggering a history read, or if the scheduler fires twice (Task Scheduler `StartWhenAvailable`), the file can be partially written mid-read.
- Files: `gex/validation.py` lines 25–51
- Impact: Parquet corruption causes the next read to raise `pyarrow` exceptions; `load_history` silently returns an empty DataFrame (bare `except Exception: return pd.DataFrame()`), losing historical data display. The scheduler's `StartWhenAvailable` setting increases the window: if the prior run was missed, it re-fires on resume.
- Fix approach: Write to a temp file and use `pathlib.Path.replace()` for atomic rename, or use `filelock`.

**Parquet store column name drift (`vanna_exposure` vs `net_vex`):**
- Issue: The `validation.py` docstring lists columns as `date, ticker, spot, net_gex, gamma_regime, zero_gamma_level, call_wall, put_wall`. The actual written data has a ninth column `vanna_exposure` (line 36). `CLAUDE.md` table also omits it. The summary dict uses the key `net_vex`, which is mapped to `vanna_exposure` only at write time.
- Files: `gex/validation.py` lines 10–11 (docstring), line 36
- Impact: Low for current code, but any new code reading `summary["vanna_exposure"]` from a loaded row will find it under that name, while the same value in a live `summary` dict is under `net_vex`. Cross-session comparisons can silently use the wrong key.
- Fix approach: Standardise on one name; update the docstring. Prefer `net_vex` throughout.

**`win32com` email delivery is Windows-Outlook-only with no fallback:**
- Issue: `gex/emailer.py` requires Outlook to be running on Windows. The send path first tries `GetActiveObject` (fails if Outlook closed), then `Dispatch` with a 3-second sleep, then raises `RuntimeError`. There is no SMTP fallback.
- Files: `gex/emailer.py` lines 29–38
- Impact: `run_daily.py` catches the exception and prints "Email failed:" then exits silently — the daily report is dropped with no alerting. If run from Task Scheduler as a background process with Outlook closed, this is the expected outcome.
- Fix approach: Add an SMTP path (e.g. `smtplib` + Gmail app password) as fallback, or at minimum write the HTML to `out/` on failure so the report is retrievable.

---

## Security Considerations

**`.env` file contains email recipients in plaintext adjacent to the codebase:**
- Risk: `GEX_EMAIL_TO` loaded from `C:/dev/options-quant/.env`. The `.gitignore` entry for `.env` was added only in commit `38d2f3e` — prior commits may have exposed the file if the repo was ever public-accessible.
- Files: `gex/emailer.py` line 11–16, `.env`
- Current mitigation: `.env` now in `.gitignore`.
- Recommendations: Rotate any emails committed in history. Verify `git log --all -- .env` to confirm it was never tracked.

**Streamlit password check uses bare string comparison with no rate limiting:**
- Risk: `_check_password()` in `streamlit_app.py` compares password with `==` in a loop re-executed on every rerun. No lockout, no timing-safe compare.
- Files: `streamlit_app.py` lines 31–45
- Current mitigation: Deployed locally or behind VPN — not public.
- Recommendations: If ever publicly hosted, replace with `hmac.compare_digest()` and add attempt throttling.

---

## Fragile Areas

**Empty chain after filtering crashes `analytics.summarise()`:**
- Issue: If all options fail the `min_oi`/`min_dte`/`max_iv` filters in `load_chain()`, `snapshot.chains` is an empty DataFrame. `compute_gex()` returns an empty df, `strike_gex()` returns empty, and `summarise()` calls `gex_df["gex"].abs().max()` which returns `NaN` on an empty series — not `0`. The `abs(net_gex) < NEUTRAL_ABS_FLOOR` guard passes because `NaN < x` is `False`, sending execution into regime logic with NaN comparisons. Later `delta_hedge_flow = net_gex_scalar / (snapshot.spot * 0.01)` divides 0 by a live spot (fine), but the whole summary dict contains NaN fields that can produce rendering errors.
- Files: `gex/analytics.py` lines 36–55, `gex/compute.py` line 47
- Safe modification: Add an empty-df guard at the top of `summarise()` returning a neutral summary.
- Test coverage: No test covers an empty chain input.

**`snapshot.spot = 0.0` causes division by zero in `compute_ticker()`:**
- Issue: `data.get("current_price") or 0.0` in `data_loader.py` line 70 returns `0.0` if the field is missing or falsy. `compute_ticker()` uses `snapshot.spot * 0.01` as a denominator for `delta_hedge_flow` — division by zero if spot is 0.
- Files: `gex/compute.py` line 47, `gex/data_loader.py` line 70
- Trigger: CBOE API returns null/missing `current_price` field (possible during pre-market or for less-liquid names).
- Fix approach: Guard `delta_hedge_flow = net_gex_scalar / (snapshot.spot * 0.01) if snapshot.spot else None`.

**Task Scheduler fires at local wall-clock time, not ET:**
- Issue: `runners/gex_daily.ps1` registers the task at `16:30` with no timezone specification. Windows Task Scheduler uses the machine's local time. The `run_daily.py` script uses `pytz("America/New_York")` for the trading-day check — so the check is ET-aware — but the trigger fires at 4:30 local time. If the machine is not in ET (or is in ET but observes DST differently), the script fires before or after market close.
- Files: `runners/gex_daily.ps1` line 12
- Impact: Firing at 4:30 before market close (3:30 ET) pulls intraday data, not close data.
- Fix approach: Document that machine timezone must be ET, or use a UTC-anchored trigger (`21:30 UTC` for Eastern Standard; no clean fix for DST without a wrapper script).

---

## Test Coverage Gaps

**`compute_ticker()` pipeline has no integration test:**
- What's not tested: The full `load_chain → add_greeks → compute_gex/vex/chex → summarise → save_snapshot` path. Tests exist for individual components but nothing that exercises the pipeline with a fixture chain.
- Files: `gex/compute.py`
- Risk: Regression in field names, sign conventions, or empty-chain behaviour would go undetected.
- Priority: Medium

**No test for empty chain input through `summarise()`:**
- What's not tested: `summarise(empty_gex_df, empty_profile_df, spot=500)` — the zero-option case.
- Files: `gex/analytics.py`
- Risk: NaN propagation into summary dict, silent bad data in email and Streamlit display.
- Priority: High

**`run_gex.py` save path untested (and currently broken):**
- What's not tested: The `run()` function's save branch — `.savefig()` call would be the first failure point.
- Files: `gex/run_gex.py`
- Risk: Entry point documented in CLAUDE.md silently broken.
- Priority: High

**No test for `save_snapshot()` with a corrupt or schema-mismatched parquet:**
- What's not tested: What happens when the existing parquet file has columns added/removed between versions.
- Files: `gex/validation.py`
- Risk: Production store accumulated under v3.0 development may have mixed schemas; next run either panics or silently drops columns.
- Priority: Medium

---

## Scaling Limits

**20-ticker sequential fetch with 0.15s sleep between calls:**
- Current capacity: Streamlit fetches `ALL_TICKERS` (20 tickers) sequentially with a 150ms inter-request sleep = minimum ~3 seconds network-bound fetch before render. `run_daily.py` has no sleep between calls.
- Limit: CBOE delayed quotes has no published rate limit; undocumented throttling would cause silent 429/503 errors, caught by `process_ticker()`'s bare `except Exception` and reported as `error` tickers.
- Scaling path: Parallelize with `concurrent.futures.ThreadPoolExecutor`; add retry with backoff on `requests.HTTPError`.

**Parquet store grows unbounded:**
- Current capacity: `gex_snapshots.parquet` appends one row per ticker per trading day. At 20 tickers × ~252 days = ~5,040 rows/year. File size is negligible, but `save_snapshot()` reads the full file on every write.
- Limit: Not a near-term concern, but the read-entire-file-on-write pattern becomes a bottleneck if the ticker list grows substantially.

---

## Dependencies at Risk

**`yfinance` used only in `event_study()` (low-use path):**
- Risk: `yfinance` uses unofficial Yahoo Finance scraping; breaks periodically when Yahoo changes endpoints. It's in `requirements.txt` but only used in `gex/validation.py`'s `event_study()` function, which is a manual/ad-hoc utility, not part of the daily pipeline.
- Impact: `event_study()` silently returns bad data or raises on Yahoo outages. Daily pipeline unaffected.
- Migration plan: Remove `yfinance` from `requirements.txt` if `event_study()` is never run, or pin to a known-good version.

**`win32com` (pywin32) is undeclared in `requirements.txt`:**
- Risk: `gex/emailer.py` imports `win32com.client` but `pywin32` is not in `requirements.txt`. Fresh venv setup produces a working pipeline that silently fails at email time.
- Files: `gex/emailer.py` line 28, `requirements.txt`
- Impact: CI or fresh installs can't send email; no warning until `run_daily.py` hits the email step.
- Fix approach: Add `pywin32` to `requirements.txt` with a Windows platform marker: `pywin32; sys_platform == "win32"`.

**`pandas_market_calendars` has no upper bound pin:**
- Risk: `pandas_market_calendars>=4.4` with no upper bound. The library has changed its `schedule()` return type and calendar names across major versions.
- Files: `requirements.txt` line 7
- Impact: An upgrade to a future major version could break `is_trading_day()` in `run_daily.py` or `load_yesterday()` in `validation.py` silently returning wrong dates.
- Fix approach: Pin to `<5.0` until tested against a new major version.

---

*Concerns audit: 2026-05-06*

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
<!-- LINKS:END -->
