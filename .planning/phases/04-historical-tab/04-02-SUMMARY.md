---
phase: 04-historical-tab
plan: "02"
status: complete
completed: 2026-05-06
commits:
  - 49e5b15  # Task 1: helpers + streak
  - 6e2c691  # Task 2: tabs + Historical tab
---

# Plan 04-02 Summary — Streamlit tabs + Historical tab

## What Was Built

Extended `streamlit_app.py` in two atomic commits:

**Task 1:** Added `_load_history_cached` (ttl=1800 cached wrapper for load_history), `_compute_streak` (counts consecutive trailing sessions matching current regime), and extended `render_regime_card` with optional `streak: int | None = None` kwarg that appends a "Streak N sessions" row to the .rc-grid HTML block.

**Task 2:** Wrapped the entire app layout in `st.tabs(["Live", "Historical"])`. All existing Phase 3 content (fetch loop, regime cards, overview chart, per-ticker expanders) moved into `with tabs[0]:`. Regime card loop updated to compute and pass streak via `_load_history_cached` + `_compute_streak`. Historical tab (`with tabs[1]:`) adds:
- ZGL vs Spot line chart (30-session, matplotlib, D-06)
- Regime persistence table (20-session, st.dataframe, D-07)
- Event study with single-ticker selectbox and 20-session gate (D-08/D-09/D-10)

## Key Files

- `streamlit_app.py` — all changes, no other files modified

## Test Results

```
75 passed, 2 failed (full suite — 2 failures are pre-existing secrets.toml issue in test_streamlit_app.py, unrelated to this plan)
All 7 load_history tests still green.
```

## Pattern Compliance

- Every `st.pyplot(fig)` immediately followed by `plt.close(fig)` — confirmed via grep
- `st.info(...)` for all gate messages
- `st.dataframe(..., hide_index=True, use_container_width=True)` for all tables
- `key="event_study_ticker"` on selectbox
- Historical tab uses only `_load_history_cached`, never `load_history` directly, never `fetch_ticker`

## Self-Check: PASSED

- [x] `tabs = st.tabs(["Live", "Historical"])` present
- [x] `with tabs[0]:` and `with tabs[1]:` present
- [x] `def _load_history_cached` and `def _compute_streak` present
- [x] `render_regime_card` signature has `streak: int | None = None`
- [x] `streak_row` in render_regime_card body
- [x] `fig.autofmt_xdate()` in ZGL chart
- [x] `st.selectbox("Ticker", TICKERS, key="event_study_ticker")` present
- [x] `st.info("Insufficient history — need ≥20 sessions.")` present
- [x] Every `st.pyplot(fig)` paired with `plt.close(fig)`
- [x] `python -m pytest gex/tests/ -q` — 75 passed, 2 pre-existing failures

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
**Phase siblings:**
- [[_planning/gamma-omm/phases/04-historical-tab/04-01-PLAN|04-01-PLAN]]
- [[_planning/gamma-omm/phases/04-historical-tab/04-01-SUMMARY|04-01-SUMMARY]]
- [[_planning/gamma-omm/phases/04-historical-tab/04-02-PLAN|04-02-PLAN]]
- [[_planning/gamma-omm/phases/04-historical-tab/04-CONTEXT|04-CONTEXT]]
- [[_planning/gamma-omm/phases/04-historical-tab/04-DISCUSSION-LOG|04-DISCUSSION-LOG]]
- [[_planning/gamma-omm/phases/04-historical-tab/04-PATTERNS|04-PATTERNS]]
- [[_planning/gamma-omm/phases/04-historical-tab/04-REVIEW|04-REVIEW]]
- [[_planning/gamma-omm/phases/04-historical-tab/04-VERIFICATION|04-VERIFICATION]]

<!-- LINKS:END -->
