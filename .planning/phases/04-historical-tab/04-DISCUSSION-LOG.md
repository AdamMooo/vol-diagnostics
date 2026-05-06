# Phase 4: Historical Tab - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-06
**Phase:** 04-historical-tab
**Areas discussed:** Layout integration, Event study display, Streak counter loading, Historical data loader

---

## Layout Integration

| Option | Description | Selected |
|--------|-------------|----------|
| st.tabs(["Live", "Historical"]) | Wrap full app in two tabs; existing Phase 3 content in tab[0], Phase 4 in tab[1]. Requires restructuring Phase 3 layout (low-risk indentation). | ✓ |
| Scroll section below | Append divider + Historical heading below existing content. Zero changes to Phase 3 code but grows long over time. | |

**User's choice:** st.tabs(["Live", "Historical"])
**Notes:** None

---

## Event Study Display

| Option | Description | Selected |
|--------|-------------|----------|
| Regime split stats from parquet only | Sessions, % Days, Avg Net GEX per regime from parquet store. No live yfinance fetch. Fast, offline-safe. | ✓ |
| Full forward-return analysis | Call existing event_study() which fetches forward price data from yfinance. Adds a second live network call; heavier. | |

**User's choice:** Regime split stats from parquet only
**Notes:** The existing `event_study()` CLI function is not called from the dashboard.

---

## Streak Counter Loading

| Option | Description | Selected |
|--------|-------------|----------|
| Separate cached history function | New `load_history()` with @st.cache_data(ttl=1800). Streak computed separately; keeps fetch_ticker() fast. | ✓ |
| Bundle into fetch_ticker() | Add parquet read to existing fetch. Simpler call-site but couples live/historical cache TTLs. | |

**User's choice:** Separate cached history function
**Notes:** TTL=1800 (30 min) chosen because parquet only changes once per daily run.

---

## Historical Data Loader

| Option | Description | Selected |
|--------|-------------|----------|
| New helper in validation.py | load_history(ticker, days=30) added to gex/validation.py alongside load_yesterday(). Testable and keeps parquet access centralized. | ✓ |
| Inline in streamlit_app.py | Function defined directly in app. Simpler diff but splits parquet logic across files. | |

**User's choice:** New helper in validation.py
**Notes:** Follows the same pattern as load_yesterday().

---

## Claude's Discretion

- Exact formatting of streak counter in regime card typography
- Column order/styling for regime persistence st.dataframe
- Whether ZGL trend and persistence sections are per-ticker stacked or side-by-side columns

## Deferred Ideas

None
