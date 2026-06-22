---
phase: quick-260621-v8g
plan: 01
subsystem: dashboard
tags: [ui, streamlit, analytics, fragment, axis-labels]
dependency_graph:
  requires: []
  provides: [fragment-isolated surface/evolution, card γ-flip filter, ln(K/S) axis consistency]
  affects: [app.py, gex/analytics.py]
tech_stack:
  added: []
  patterns: [@st.fragment for widget-scoped reruns]
key_files:
  created: []
  modified:
    - app.py
    - gex/analytics.py
decisions:
  - γ-flip filtered at display time in render_regime_card (not in card_model.py) — email parity preserved
  - @st.fragment wraps sub_today body, sub_compare body, tab_evolution body; tab/sub_today/sub_compare layout elements stay at outer scope
  - Evolution mode radio moved into _evolution_section fragment (was inline); label_visibility="collapsed" preserved
metrics:
  duration: ~8 min
  completed: 2026-06-21
---

# Quick 260621-v8g: UI Pass 2 — Axis Label Unification, Card Trim, Fragment Isolation

**One-liner:** ln(K/S) axis label unified across analytics.py static fallback surfaces, γ-flip card row hidden at render time, and three @st.fragment functions isolate surface/evolution widget reruns.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Fix axis labels (analytics.py) + radio options (app.py) | ec13dc2 | gex/analytics.py, app.py |
| 2 | Filter γ-flip row from card display + @st.fragment | c92ddaf | app.py |

## Changes Made

**gex/analytics.py**
- `plot_vol_surface`: scene `yaxis_title` K/S → ln(K/S)
- `plot_iv_change_surface`: scene `yaxis_title` K/S → ln(K/S)

**app.py**
- `render_regime_card`: added `fields = [f for f in fields if f.label != "γ-flip"]` after `build_card_fields` call; before `grid_html` join
- Evolution mode radio options: `["Level", "Change vs start"]` → `["Level (IV)", "Change vs ref"]`
- Three `@st.fragment` functions defined above `if sel_index:` block: `_surface_today_section`, `_surface_compare_section`, `_evolution_section`; tab bodies replaced with single-line calls

## Verification

- `python -m py_compile app.py gex/analytics.py` — clean
- `pytest gex/tests -x -q` — 246 passed (venv python)

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Threat Flags

None.

## Self-Check: PASSED

- `gex/analytics.py` modified: verified
- `app.py` modified: verified
- Commits ec13dc2 and c92ddaf: verified
- `card_model.py` unchanged: confirmed (not touched)

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
<!-- LINKS:END -->
