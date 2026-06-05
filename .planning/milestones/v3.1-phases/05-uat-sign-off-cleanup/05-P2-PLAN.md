---
wave: 2
plan_id: P2
phase: 5
title: "Live UAT walkthrough — 4 Streamlit scenarios"
autonomous: false
depends_on: [P1]
files_modified:
  - .planning/phases/03-streamlit-dashboard/03-HUMAN-UAT.md
requirements_addressed: [UAT-01, UAT-02, UAT-03, UAT-04]
must_haves:
  - "03-HUMAN-UAT.md shows result: pass for all 4 scenarios (or result: fail with fix applied)"
  - "Summary block in 03-HUMAN-UAT.md shows passed: 4, pending: 0"
  - "App launches behind password gate with no unhandled exceptions"
  - "Regime cards render for all selected tickers with correct color and all 5 core fields"
  - "Per-ticker expander shows 7-column summary table and at least 2 Plotly charts"
  - "Refresh data button triggers visible re-fetch (spinners reappear)"
---

<objective>
Run the 4 deferred Streamlit UAT scenarios as a live interactive walkthrough. Claude guides each step; Adam runs the app and reports observed behavior. Results recorded in 03-HUMAN-UAT.md in-place.

The UAT doc has stale expected values (written for a 3-ticker app). This plan updates expected values to match the current 20-ticker app before Adam runs each scenario.

Per D-03: if any scenario fails, a fix cycle runs before marking UAT complete.

Purpose: Sign off that the Streamlit dashboard works end-to-end on the live machine.
Output: 03-HUMAN-UAT.md with all 4 result: fields updated from [pending] to pass or fail.
</objective>

<execution_context>
@C:/Users/AdamMorris/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/AdamMorris/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@C:/dev/options-quant/.planning/PROJECT.md
@C:/dev/options-quant/.planning/ROADMAP.md
@C:/dev/options-quant/.planning/phases/05-uat-sign-off-cleanup/05-CONTEXT.md
@C:/dev/options-quant/.planning/phases/05-uat-sign-off-cleanup/05-RESEARCH.md
@C:/dev/options-quant/.planning/phases/03-streamlit-dashboard/03-HUMAN-UAT.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Update UAT expected values to reflect current app</name>
  <read_first>
    .planning/phases/03-streamlit-dashboard/03-HUMAN-UAT.md
    streamlit_app.py
  </read_first>
  <action>
The 03-HUMAN-UAT.md was written for a 3-ticker app. The current app has 20 tickers, a password gate, and a 7-column summary table. Update the `expected:` values in-place for all 4 scenarios before running any live tests.

Edit `.planning/phases/03-streamlit-dashboard/03-HUMAN-UAT.md`:

**Scenario 1 (App launch):**
Replace the existing `expected:` text with:
```
expected: `streamlit run streamlit_app.py` starts the dev server and prints a localhost URL. Browser shows a password prompt (this is expected — not an error). After entering the password from `.streamlit/secrets.toml`, the page loads showing "GEX Dashboard" title and a sidebar with two multi-selects (Index and Purpose Yield Shares) and a "Refresh data" button. No Python traceback in terminal.
```

**Scenario 2 (Regime cards):**
Replace the existing `expected:` text with:
```
expected: After CBOE data loads (~3-20 seconds, spinner visible), colored regime cards render for all selected tickers. Cards are grouped under "Index Tickers" (SPY, QQQ, IWM, XLF, GLD, TLT) and "Purpose Yield Shares" (14 Purpose tickers). Each card shows: ticker symbol, regime label, net GEX (B), VEX (B), delta-flow ($X.XB/1%), and vs-yesterday label. Background color matches regime (green = positive, red = negative, grey = neutral).
```

**Scenario 3 (Per-ticker expander):**
Replace the existing `expected:` text with:
```
expected: Clicking a ticker expander (e.g., "SPY") reveals a summary table with 7 columns (Spot, Net GEX, VEX, CHEX, Zero-γ, Call Wall, Put Wall) and at least 2 Plotly charts (strike GEX bar chart, gamma profile line chart). If parquet history exists for the ticker, a ZGL-vs-Spot line chart and regime distribution table may also appear — these are bonus, not required for pass. No Python traceback.
```

**Scenario 4 (Refresh button):**
Replace the existing `expected:` text with:
```
expected: Clicking "Refresh data" in the sidebar clears the cache and triggers a full re-fetch. The "Loading chains from CBOE..." spinner reappears for each ticker. Data reloads successfully — regime cards and expanders re-render without error.
```

Also update the `## Current Test` section header:
```
## Current Test

UAT-01 through UAT-04 — Live Streamlit walkthrough (20-ticker app). Guided by Claude. Run 2026-05-06.
```
  </action>
  <verify>
    <automated>
Select-String -Path ".planning/phases/03-streamlit-dashboard/03-HUMAN-UAT.md" -Pattern "password prompt"
# Expected: at least 1 match (scenario 1 updated)

Select-String -Path ".planning/phases/03-streamlit-dashboard/03-HUMAN-UAT.md" -Pattern "Purpose Yield Shares"
# Expected: at least 1 match (scenario 2 updated)

Select-String -Path ".planning/phases/03-streamlit-dashboard/03-HUMAN-UAT.md" -Pattern "7 columns"
# Expected: at least 1 match (scenario 3 updated)
    </automated>
  </verify>
  <acceptance_criteria>
    - `.planning/phases/03-streamlit-dashboard/03-HUMAN-UAT.md` contains "password prompt" in the scenario 1 expected value
    - File contains "Purpose Yield Shares" in the scenario 2 expected value
    - File contains "7 columns" in the scenario 3 expected value
    - File contains "Refresh data" in the scenario 4 expected value
    - All 4 `result:` fields still show `[pending]` (not yet filled in — that happens in task 2)
  </acceptance_criteria>
  <done>UAT expected values updated to match current 20-ticker app. Scenarios have accurate pass criteria.</done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 2: Live walkthrough — run all 4 UAT scenarios</name>
  <read_first>
    .planning/phases/03-streamlit-dashboard/03-HUMAN-UAT.md
    .streamlit/secrets.toml
  </read_first>
  <what-built>
Task 1 updated the expected values. Now run the app and walk through each scenario. Claude will prompt each step. Adam reports what was observed. Claude records results in 03-HUMAN-UAT.md.
  </what-built>
  <how-to-verify>
Run each scenario in sequence. After each one, report the observed behavior.

---

**SCENARIO 1 — App Launch (UAT-01)**

1. Open a terminal in `C:/dev/options-quant`
2. Activate the venv: `.venv/Scripts/Activate.ps1`
3. Run: `streamlit run streamlit_app.py`
4. Open the printed localhost URL in a browser

Expected: Password prompt appears in browser. Enter the password from `.streamlit/secrets.toml`. After authentication, the GEX Dashboard title is visible with two multi-selects in the sidebar and a "Refresh data" button. No traceback in terminal.

Report: Did the browser show a password prompt? After entering it, did the dashboard load? Any terminal errors?

---

**SCENARIO 2 — Regime Cards (UAT-02)**

(Continue with the app running from Scenario 1.)

1. Leave all tickers selected in both multi-selects (or select at least SPY, QQQ, IWM)
2. Wait for data to load (spinner may show "Loading chains from CBOE...")
3. Observe the regime cards section

Expected: Colored cards appear for each selected ticker. Each card shows: ticker, regime label, net GEX, VEX, delta-flow, vs-yesterday label. Background color reflects regime.

Report: Did cards appear for all selected tickers? Were all 5 core fields visible on each card? Any errors or blank cards?

---

**SCENARIO 3 — Per-Ticker Expander (UAT-03)**

(Continue with the app running.)

1. Click the expander for SPY (or any ticker with data)
2. Observe what renders inside

Expected: A summary table with columns: Spot, Net GEX, VEX, CHEX, Zero-γ, Call Wall, Put Wall (7 columns). Two Plotly charts below (strike GEX bar chart, gamma profile line chart). Possibly a ZGL history chart and regime distribution table if parquet history exists — these are bonus.

Report: How many columns did the summary table show? Did both main charts render? Any traceback?

---

**SCENARIO 4 — Refresh Button (UAT-04)**

(Continue with the app running.)

1. Click "Refresh data" in the sidebar
2. Observe whether spinners reappear

Expected: "Loading chains from CBOE..." spinner reappears for each ticker. Page re-renders with fresh data and no error.

Report: Did spinners reappear? Did the page reload without error?

---

**After each scenario:** Report observed behavior. Claude will record pass or fail in 03-HUMAN-UAT.md.

**If any scenario fails:** Describe the error or unexpected behavior. Claude will diagnose and implement a fix before marking UAT complete (per D-03).

**Fix cycle reference (if needed):**
- Matplotlib backend error on startup: add `import matplotlib; matplotlib.use("Agg")` in streamlit_app.py before gex.* imports
- CBOE fetch error (all tickers fail): check network connectivity; single-ticker failure is acceptable
- Expander column count mismatch: verify against actual columns seen — 7 is pass, fewer may indicate a code issue
  </how-to-verify>
  <action>
After Adam reports each scenario result, update `.planning/phases/03-streamlit-dashboard/03-HUMAN-UAT.md`:

- Set `result: pass` or `result: fail — [brief description]` for each scenario
- Update the Summary block:
  ```
  passed: 4
  pending: 0
  ```
  (adjust counts based on actual results)

If a scenario fails, implement the fix per the fix-cycle reference above, re-run the scenario, then record the result.
  </action>
  <resume-signal>Report observed behavior for each scenario. Type "all pass" if all 4 pass, or describe which failed and what was observed.</resume-signal>
  <acceptance_criteria>
    - `Select-String -Path ".planning/phases/03-streamlit-dashboard/03-HUMAN-UAT.md" -Pattern "\[pending\]"` returns no matches
    - All 4 result: fields contain "pass" or "fail" (no [pending] remaining)
    - Summary block shows `passed:` value matching actual results
    - If any result is "fail": a fix was applied and noted before this task completes
  </acceptance_criteria>
  <done>All 4 UAT scenarios recorded as pass or fail in 03-HUMAN-UAT.md. Summary counts updated. No [pending] entries remain.</done>
</task>

</tasks>

<verification>
```powershell
# Confirm no pending UAT items remain
Select-String -Path ".planning/phases/03-streamlit-dashboard/03-HUMAN-UAT.md" -Pattern "\[pending\]"
# Expected: no matches

# Confirm expected values updated
Select-String -Path ".planning/phases/03-streamlit-dashboard/03-HUMAN-UAT.md" -Pattern "password prompt"
# Expected: 1+ match

# Confirm results recorded
Select-String -Path ".planning/phases/03-streamlit-dashboard/03-HUMAN-UAT.md" -Pattern "result: pass"
# Expected: 4 matches (all pass), or fewer if any failed
```
</verification>

<success_criteria>
- 03-HUMAN-UAT.md has no [pending] result fields
- All 4 scenarios have been run live and recorded
- If any scenario failed: fix applied and re-tested before recording final result
- App launched, password gate entered, all visual elements observed by Adam
</success_criteria>

<output>
After completion, create `C:/dev/options-quant/.planning/phases/05-uat-sign-off-cleanup/05-P2-SUMMARY.md`
</output>

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
**Phase siblings:**
- [[_planning/gamma-omm/phases/05-uat-sign-off-cleanup/05-CONTEXT|05-CONTEXT]]
- [[_planning/gamma-omm/phases/05-uat-sign-off-cleanup/05-DISCUSSION-LOG|05-DISCUSSION-LOG]]
- [[_planning/gamma-omm/phases/05-uat-sign-off-cleanup/05-P1-PLAN|05-P1-PLAN]]
- [[_planning/gamma-omm/phases/05-uat-sign-off-cleanup/05-P1-SUMMARY|05-P1-SUMMARY]]
- [[_planning/gamma-omm/phases/05-uat-sign-off-cleanup/05-P2-SUMMARY|05-P2-SUMMARY]]
- [[_planning/gamma-omm/phases/05-uat-sign-off-cleanup/05-P3-PLAN|05-P3-PLAN]]
- [[_planning/gamma-omm/phases/05-uat-sign-off-cleanup/05-P3-SUMMARY|05-P3-SUMMARY]]
- [[_planning/gamma-omm/phases/05-uat-sign-off-cleanup/05-RESEARCH|05-RESEARCH]]

<!-- LINKS:END -->
