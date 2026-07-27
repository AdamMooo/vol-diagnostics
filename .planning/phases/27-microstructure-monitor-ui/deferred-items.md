# Deferred / Out-of-Scope Items — Phase 27

## Discovered during 27-01 execution (2026-07-26)

- **`app.py` uncommitted modification (not made by this plan).** A one-line change
  appeared in the working tree during the 27-01 session:
  `st.button("Refresh", use_container_width=True)` → `st.button("Refresh", width="stretch")`
  (sidebar Refresh button, ~line 375). Plan 27-01 only touches
  `engine/monitor/monitor_reader.py`, `engine/vol/vrp_history.py`, and their tests —
  this app.py edit is out of scope and was NOT committed. Likely produced by a running
  Streamlit dev process (Streamlit deprecation auto-migration) rather than by the
  executor. Left in the working tree for Adam to review/commit with the Plan 27-02
  board work (which owns app.py). No action taken.
