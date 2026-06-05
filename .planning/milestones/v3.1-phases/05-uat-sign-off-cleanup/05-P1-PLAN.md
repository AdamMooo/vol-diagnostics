---
wave: 1
plan_id: P1
phase: 5
title: "Commit 3 outstanding code fixes"
autonomous: true
depends_on: []
files_modified:
  - gex/emailer.py
  - gex/report.py
  - gex/validation.py
requirements_addressed: []
must_haves:
  - "gex/emailer.py has Dispatch not DispatchEx in the COM fallback"
  - "gex/report.py wraps build_email() content in nested table at width=820"
  - "gex/validation.py casts nullable float cols to float64 before pd.concat in save_snapshot()"
  - "git status shows all 3 files clean (no outstanding modifications)"
  - "pytest gex/tests/ -q still passes (no regressions)"
---

<objective>
Commit the 3 outstanding clean fixes before UAT begins. These diffs are verified complete and in the working tree — not in-progress work. The commit must be atomic (all 3 files in one commit) per D-04.

Purpose: Clear working-tree debt so UAT tests against the committed state, and git history accurately reflects what changed.
Output: One atomic commit; clean working tree for the 3 files.
</objective>

<execution_context>
@C:/Users/AdamMorris/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/AdamMorris/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@C:/dev/options-quant/.planning/PROJECT.md
@C:/dev/options-quant/.planning/ROADMAP.md
@C:/dev/options-quant/.planning/STATE.md
@C:/dev/options-quant/.planning/phases/05-uat-sign-off-cleanup/05-CONTEXT.md
@C:/dev/options-quant/.planning/phases/05-uat-sign-off-cleanup/05-RESEARCH.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Verify diffs and commit 3 outstanding fixes atomically</name>
  <read_first>
    gex/emailer.py
    gex/report.py
    gex/validation.py
  </read_first>
  <action>
Run `git diff HEAD gex/emailer.py gex/report.py gex/validation.py` to confirm the 3 diffs are exactly as expected before committing:

- emailer.py line ~32: `DispatchEx` → `Dispatch` (one line change in COM fallback)
- report.py lines ~236-256: `<div style="max-width:820px;margin:0 auto;">` replaced with two-level table structure (outer full-width, inner width="820")
- validation.py lines ~41-43: 3-line block added — for loop casting `zero_gamma_level`, `call_wall`, `put_wall`, `vanna_exposure` to float64 before pd.concat

Then run the test suite to confirm no regressions:
```
C:/dev/options-quant/.venv/Scripts/pytest gex/tests/ -q
```

Then stage and commit all 3 files as a single atomic commit:
```
git add gex/emailer.py gex/report.py gex/validation.py
git commit -m "$(cat <<'EOF'
fix(gex): emailer Dispatch, report nested-table layout, validation dtype guard

emailer.py: DispatchEx -> Dispatch in COM fallback (more reliable when Outlook
already running; DispatchEx always spawns new instance)

report.py: wrap build_email() content in nested table structure (width=820,
max-width enforced via table attributes for Outlook/Apple Mail compatibility)

validation.py: cast nullable float cols to float64 before pd.concat in
save_snapshot() to prevent dtype merge errors on parquet round-trip
EOF
)"
```
  </action>
  <verify>
    <automated>
git status gex/emailer.py gex/report.py gex/validation.py
# Expected: no output (all 3 files clean, committed)

C:/dev/options-quant/.venv/Scripts/pytest gex/tests/ -q
# Expected: all tests pass, no failures
    </automated>
  </verify>
  <acceptance_criteria>
    - `git status gex/emailer.py gex/report.py gex/validation.py` produces no output
    - `git log --oneline -1` shows a commit starting with "fix(gex):"
    - `grep -n "DispatchEx" gex/emailer.py` returns no matches
    - `grep -n "Dispatch(" gex/emailer.py` returns exactly one match
    - `grep -n "width=\"820\"" gex/report.py` returns at least one match
    - `grep -n "float64" gex/validation.py` returns at least one match
    - pytest exits 0 (all tests pass)
  </acceptance_criteria>
  <done>All 3 files committed; working tree clean; tests green.</done>
</task>

</tasks>

<verification>
```powershell
# Confirm clean working tree for the 3 files
git status gex/emailer.py gex/report.py gex/validation.py

# Confirm commit present
git log --oneline -3

# Confirm DispatchEx removed
Select-String -Path gex/emailer.py -Pattern "DispatchEx"

# Confirm tests pass
C:/dev/options-quant/.venv/Scripts/pytest gex/tests/ -q
```
</verification>

<success_criteria>
- git working tree shows no outstanding modifications for all 3 files
- One new commit in git log with fix(gex) prefix and correct body
- DispatchEx no longer present in emailer.py
- pytest suite passes with 0 failures
</success_criteria>

<output>
After completion, create `C:/dev/options-quant/.planning/phases/05-uat-sign-off-cleanup/05-P1-SUMMARY.md`
</output>

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
**Phase siblings:**
- [[_planning/gamma-omm/phases/05-uat-sign-off-cleanup/05-CONTEXT|05-CONTEXT]]
- [[_planning/gamma-omm/phases/05-uat-sign-off-cleanup/05-DISCUSSION-LOG|05-DISCUSSION-LOG]]
- [[_planning/gamma-omm/phases/05-uat-sign-off-cleanup/05-P1-SUMMARY|05-P1-SUMMARY]]
- [[_planning/gamma-omm/phases/05-uat-sign-off-cleanup/05-P2-PLAN|05-P2-PLAN]]
- [[_planning/gamma-omm/phases/05-uat-sign-off-cleanup/05-P2-SUMMARY|05-P2-SUMMARY]]
- [[_planning/gamma-omm/phases/05-uat-sign-off-cleanup/05-P3-PLAN|05-P3-PLAN]]
- [[_planning/gamma-omm/phases/05-uat-sign-off-cleanup/05-P3-SUMMARY|05-P3-SUMMARY]]
- [[_planning/gamma-omm/phases/05-uat-sign-off-cleanup/05-RESEARCH|05-RESEARCH]]

<!-- LINKS:END -->
