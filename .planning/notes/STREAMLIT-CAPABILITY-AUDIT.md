# Streamlit Capability Audit — vol-diagnostics dashboard
Last updated: 2026-08-06 | Verified against the installed **Streamlit 1.59.2** in `.venv`, not from memory.

Adam's prompt for this: *"I truly think we are not doing what we truly can with Streamlit."* He is right, and this is the specific version. Written as a work list for the desk-terminal UI sweep, not as a Streamlit tutorial.

---

## Verified available in 1.59.2

Every API below was checked by introspecting the installed package. Do not re-derive.

| API | Status | Why it matters here |
|---|---|---|
| `st.tabs(..., on_change="rerun")` + `TabContainer.open` | ✅ present (`elements/lib/mutable_tab_container.py:124`) | **Lazy tab bodies.** The single most valuable finding — see below. |
| `st.metric(chart_data=…, chart_type=…)` | ✅ present | Native sparklines inside a metric. |
| `st.column_config.*` | ✅ **21 column types**, incl. `LineChartColumn`, `BarChartColumn`, `ProgressColumn` | Inline sparkline/bar columns in a dataframe with zero HTML. |
| `st.skeleton` | ✅ present | Reserve layout space during the cold load instead of showing nothing. |
| `st.space` | ✅ present | Spacing without `st.divider()` or `<br>`. |
| `st.fragment(parallel=True)` | ✅ present | See the warning below — **not** useful on our box. |

## Current app audit (`app.py`, 1068 lines)

| Signal | Count | Read |
|---|---|---|
| `unsafe_allow_html=True` blocks | **16** | Hand-rolled HTML/CSS doing work native widgets now do. The single biggest source of visual inconsistency and maintenance drag. |
| `st.column_config` uses | **0** | Every table is plain. No inline sparklines, no formatting config, no progress bars. |
| `use_container_width` | **2** | Deprecated. Replace with `width="stretch"`. |
| `st.tabs` | 2 | Both eager — every body computes on every rerun (see below). |
| `st.fragment` | 3 | Some adoption already; room for more. |
| Plotly / `components.html` | 6 | Correct for the 3D surfaces. Keep. |
| Native/Altair charts | **0** | The 2D charts are all Plotly; Altair ships with Streamlit and is the house recommendation for 2D. |

---

## ⚠️ Correction to the STATE.md handoff

The 2026-08-06 handoff said the next step was **"`st.tabs` → view selector with `if/elif` gating"**. That is **no longer the right plan** and would have been an unnecessary rewrite of the app's whole navigation.

Streamlit 1.55+ supports **dynamic tabs**, which keeps the tabs UX and gets the same lazy execution:

```python
# Current — every tab body computes on every rerun, visible or not
tab_regime, tab_surfaces, tab_options, tab_explore = st.tabs([...])
with tab_surfaces:
    expensive_surface_render()          # always runs

# Target — same UX, only the open tab computes
tab_regime, tab_surfaces, tab_options, tab_explore = st.tabs([...], on_change="rerun")
if tab_surfaces.open:
    with tab_surfaces:
        expensive_surface_render()      # only when selected
```

With the default `on_change="ignore"`, `.open` is `None` on every tab and all content runs. `on_change="rerun"` is what activates the property.

This is a far smaller diff than a navigation rewrite, and it applies to the nested `st.tabs(["Today", "Compare", "Evolution"])` inside Surfaces too — which today builds all three surface payloads whenever the Surfaces tab is touched.

Same mechanism exists for expanders: `st.expander(..., on_change="rerun")` then `if exp.open:`. Relevant to the sidebar's "Full methodology & citations" expander and the Regime tab's "All fields" expander.

---

## Ranked opportunities

### 1. Lazy tab bodies — `on_change="rerun"` (biggest win, smallest diff)
Attacks the measured ~40–60s cold first paint directly. Combined with snapshot-first Regime rendering, the landing view becomes a parquet read and nothing else executes until a tab is clicked.

### 2. Snapshot-first Regime view
Unchanged from the handoff and still correct. `out/gex_snapshots.parquet` holds everything the landing cards need except `vrp_pct` / `vrp_pct_n` and `price_change_pct` (derived in `compute.py:189, 261-265`); both recompute with **no network**.

### 3. Retire hand-rolled HTML where a native widget exists
16 `unsafe_allow_html` blocks. Highest-value swaps:
- `st.metric(chart_data=…, chart_type="line")` for the KPI sparklines.
- `st.column_config.LineChartColumn` / `BarChartColumn` for the OI-by-expiry and history tables — inline sparklines, no HTML.
- `st.column_config.NumberColumn(format=…)` for all numeric formatting. Per the house guidance: **`column_config` for formatting, Pandas Styler only for colouring.**
- `st.badge` / `:green-badge[…]` for the read chips instead of styled `<span>`s.
- Keep the custom CSS only where it encodes the desk-terminal identity (tabular numerals, section rules) that `config.toml` genuinely cannot express.

### 4. `st.skeleton` during the unavoidable cold load
Even after 1+2, the first uncached visit does real work. `st.skeleton` reserves the layout so the page looks like it is arriving rather than broken. Pairs with `st.spinner`/`st.status` — perceived performance, not actual.

### 5. Housekeeping
Two `use_container_width` → `width="stretch"`. Sentence-case labels. `:material/...:` icons over the current arrow glyphs.

---

## Do NOT do these

- **`st.fragment(parallel=True)` for the 3-ticker fetch.** Tempting, and wrong here. `app.py:524` records a real measurement on the Oracle E2.1.Micro: threading made it **slower** (35.2s vs 26.4s sequential), because the GIL only releases on network I/O and this pipeline is CPU-bound in surface fitting and coherence diagnostics — parallel workers just fight over the single core. Revisit only if the box ever gets more vCPUs.
- **Ripping out Plotly.** The house preference is Altair/Vega for 2D, but the 3D vol surfaces and the interactive smile/term slices have no Altair equivalent. Plotly stays for 3D; Altair is only a candidate for the simple 2D charts, and only if it does not fracture the visual language.
- **CSS for theming.** Colours, fonts and radii now live in `.streamlit/config.toml` (added 2026-08-06). Do not reintroduce them as CSS.
- **`COPY .streamlit/` in the Dockerfile.** Would bake the gitignored-but-present `secrets.toml` into the image. The Dockerfile copies `config.toml` explicitly for this reason.

---

## Working mechanics (hard-won, don't rediscover)

- **Headless screenshots of a Streamlit app**: Edge at `C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe`, `--headless=new --screenshot=<path>`. Two traps: the path must be the full `C:\Users\AdamMorris\...` form (the 8.3 shortname `ADAMMO~1` fails with "Access is denied"), and **`--virtual-time-budget` does not work** — it fast-forwards timers while Streamlit renders over a real-time WebSocket, so it captures a blank page. Use a real `sleep 70` before the screenshot.
- **Never run pytest with a Streamlit server up** — they contend for CPU (39s → 198s).
- The dashboard reads `out/`; if it is stale the page renders a thin red banner and little else. `.\scripts\sync-from-oracle.ps1` refreshes it (needs Adam's SSH key — he runs it).

---

**Related:** `.planning/STATE.md` → "Session Continuity (2026-08-06 late — UI SWEEP, IN PROGRESS)" · `.streamlit/config.toml` (desk-terminal theme)

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/vol-diagnostics/ROADMAP|ROADMAP]] · [[_planning/vol-diagnostics/STATE|STATE]] · [[vol-diagnostics/vol-diagnostics|Hub]]
<!-- LINKS:END -->
