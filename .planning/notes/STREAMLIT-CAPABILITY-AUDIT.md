# Streamlit Capability Audit — vol-diagnostics dashboard
Last updated: 2026-08-06 | Verified against the installed **Streamlit 1.59.2** in `.venv` by introspection, not recall.

**Why this document exists.** Adam: *"this is like the 5th time we had a 'oh wow Streamlit can do this for us now'."* That pattern comes from looking things up ad hoc. This is the exhaustive pass, produced mechanically so nothing is left to stumble on.

**Method:** enumerated every public name in the installed `streamlit` namespace and regex-matched each against `app.py`.

> **148 public `st.*` names. 25 used. 123 unused.**

Used today: `button, cache_data, caption, columns, container, dataframe, error, expander, fragment, info, markdown, metric, multiselect, plotly_chart, popover, rerun, segmented_control, selectbox, set_page_config, sidebar, spinner, stop, tabs, text_input, warning`

Every unused name is classified below with a verdict. There is no "rest of the API" left over.

---

## ⚠️ Regression found and fixed during this audit

Adding `[theme.light]` last night (`2feba75`) shipped a **broken light mode**. Streamlit shows the light/dark toggle only when both blocks exist, so anyone could switch to a light theme the app cannot render:

- `engine/gex/analytics.py` hardcodes `template="plotly_dark"` at lines 105, 202, 289, 353, 416 — those charts become black boxes on a white page. Line 523 uses `template="plotly_white"`, a **pre-existing inconsistency** independent of this.
- `app.py` carries ~11 hardcoded dark-mode values in `_CSS` and inline HTML (`#64748b`, `#8b949e`, `#94a3b8`, `#334155`, plus semantic `#f87171`/`#4ade80`/`#16a34a`/`#ea580c`) that go illegible on light.

**Fixed:** `[theme.light]` removed, so the app locks to dark — which also suits the desk-terminal direction. Re-enabling light requires driving the Plotly template from `st.context.theme.type` and moving those hex values onto theme variables first. The light palette is recoverable from git history.

---

## Verdicts on all 123 unused names

### ADOPT — high value for this app

| API | What it buys here |
|---|---|
| `st.column_config` (21 column types) | `LineChartColumn`, `BarChartColumn`, `ProgressColumn`, `NumberColumn(format=…)`. Inline sparklines and numeric formatting in the OI-by-expiry and history tables with **zero HTML**. House rule: `column_config` for formatting, Pandas Styler *only* for colouring. |
| `st.latex` + `$…$` / `$$…$$` in markdown | A quant dashboard that renders its actual formulas — VRP, GEX `Γ×OI×100×S²×0.01`, Breeden–Litzenberger `q(K)=e^{rT}∂²C/∂K²`. Currently the methodology block writes these as backticked plain text. **Highest credibility-per-line change in the app.** |
| `st.context` | `st.context.theme.type` → the fix that unblocks light mode (see regression above). |
| `st.skeleton` | Animated placeholder that reserves layout during the cold load. Context-manager form recommended: `with st.skeleton(height=200): …`. Directly targets the blank-page first impression. |
| `st.status` | Multi-step progress for the cold fetch — "Fetching SPY chain… fitting surface…" — instead of an opaque spinner. Collapsible, can end in error state. |
| `st.badge` / `:green-badge[…]` | Replaces hand-styled `<span>` read chips. Works inside `st.metric` labels too. |
| `st.query_params` | Deep-linkable state — share a URL that opens IWM's Surfaces tab. Genuinely useful for a link posted publicly. |
| `st.download_button` | Let a viewer download the snapshot/history as CSV. Signals real data ownership on a portfolio piece. |
| `st.logo` | Sidebar branding; `assets/gamma-icon-lg.png` already exists and is only used as the page icon. |
| `st.title` / `header` / `subheader` / `divider` | Semantic headings instead of `st.markdown` + `<div class="sec">`. |
| `st.html` | Pure HTML without markdown processing — the correct tool where HTML genuinely is needed, instead of `st.markdown(unsafe_allow_html=True)`. |
| `st.space` | Explicit spacing without `<br>` or dividers. |
| `st.toggle` | Cleaner than a checkbox for gating expensive sections (`if st.toggle(...)` also gives lazy execution). |
| `st.pills` | Compact multi-select for the ticker picker — fits the terminal aesthetic better than `st.multiselect` chips. |
| `st.dialog` | Focused modal for full methodology, instead of a cramped sidebar popover. |
| `st.mermaid_chart` | Render the data pipeline (CBOE → compute → parquet → surfaces) as a diagram. Strong for explaining the system in an interview. |
| `st.cache_resource` | For non-serializable shared objects if any appear; distinct from `cache_data`. |
| `st.session_state` | Not directly used anywhere today. Needed for any cross-view state (e.g. remembering the selected ticker across views). |

### CONSIDER — real, but weigh against churn

| API | Note |
|---|---|
| `st.navigation` / `st.Page` / `page_link` / `switch_page` | Would split the 1068-line `app.py` into an `app_pages/` structure. Modern pattern and better code organisation, but a large refactor — do it *after* the lazy-tab and snapshot-first work, if at all. |
| `st.altair_chart` / `line_chart` / `bar_chart` / `area_chart` / `scatter_chart` / `vega_lite_chart` | House preference is Vega/Altair over Plotly for 2D, and Altair ships with Streamlit. Candidate for the simple 2D charts **only** — see Do-Not-Do on 3D. Mixing two chart libraries fractures the visual language, so this is all-or-nothing per chart class. |
| `st.table` | Static, markdown-rendering table. Good for small fixed grids (the card field list) where `st.dataframe`'s interactivity is noise. |
| `st.form` / `form_submit_button` | Batches inputs into one rerun. Low value now (few inputs), higher if a filter panel appears. |
| `st.empty` | Out-of-order rendering — useful if a control must appear below content whose value it determines. |
| `st.pagination` | Only if a long table appears. |
| `st.data_editor` | Only if anything becomes editable. Nothing is today. |
| `st.code` / `st.json` | Showing config or raw snapshot rows in a diagnostics view. |
| `st.toast` / `st.progress` / `st.success` | Lightweight feedback; `st.toast` for the Refresh action. |
| `st.feedback` | Star/thumb widget — could collect reactions on a public link. |
| `st.link_button` / `st.menu_button` | Navigation affordances (link to the GitHub repo, methodology doc). |
| `st.bottom` | Pinned bottom bar — probably unnecessary here. |
| `st.pdf` | Could surface `research/*.md`-derived PDFs. Marginal. |

### N/A — deliberately not applicable

| API | Why not |
|---|---|
| `chat_message`, `chat_input`, `write_stream` | No conversational surface. |
| `audio`, `audio_input`, `video`, `camera_input`, `image`, `file_uploader` | No media or upload flow. |
| `map`, `pydeck_chart`, `graphviz_chart`, `pyplot` | No geo data; matplotlib unused and shouldn't be introduced. |
| `login`, `logout`, `user`, `user_info`, `auth_util` | Dashboard is intentionally public, no auth. |
| `connection`, `connections` | Data comes from CBOE HTTP + local parquet, not a SQL/warehouse connection. |
| `balloons`, `snow` | No. |
| `App`, `starlette` | ASGI/custom-server territory; Docker + `streamlit run` is correct here. |
| `secrets`, `get_option`, `set_option`, `config`, `config_option` | Config lives in `.env` + `engine/config.py` + `config.toml`; no need. |
| `cache` | Legacy, superseded by `cache_data`/`cache_resource`. |
| `help`, `echo` | Dev/teaching aids. |
| `components` | Only if a widget genuinely does not exist natively — and `st.components.v1` is **deprecated**; CCv2 (`st.components.v2.component()`) is the current API. `surface_interactive.py` already embeds plotly.js this way; leave it. |
| Internal modules — `util`, `proto`, `runtime`, `elements`, `errors`, `logger`, `watcher`, `web`, `cursor`, `development`, `delta_generator*`, `*_util`, `path_security`, `source_util`, `type_util`, `version`, `commands`, `dataframe_util` | Not public API. They appear in `dir(st)` but are implementation detail. |

---

## The single most valuable finding — lazy tab bodies

**Supersedes** the earlier handoff instruction to replace `st.tabs` with a segmented control. That rewrite is unnecessary.

Streamlit 1.55+ has **dynamic tabs**. Confirmed present at `streamlit/elements/lib/mutable_tab_container.py:124`:

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

With the default `on_change="ignore"`, `.open` is `None` on every tab and everything runs — that is today's behaviour. `on_change="rerun"` activates the property.

Applies equally to the **nested** `st.tabs(["Today", "Compare", "Evolution"])` inside Surfaces, which currently builds all three payloads whenever Surfaces is touched. Same mechanism for expanders: `st.expander(..., on_change="rerun")` then `if exp.open:` — relevant to the sidebar's "Full methodology & citations" and the Regime tab's "All fields".

---

## `app.py` anti-pattern counts

| Signal | Count | Read |
|---|---|---|
| `unsafe_allow_html=True` | **16** | Hand-rolled HTML doing work native widgets now do. Biggest source of visual inconsistency and maintenance drag. |
| `st.column_config` | **0** | Every table plain — no sparklines, no formatting. |
| `use_container_width` | **2** | Deprecated → `width="stretch"`. |
| Native/Altair 2D charts | **0** | All charts are Plotly. |
| `st.tabs` | 2 | Both eager. |
| `st.fragment` | 3 | Partial adoption. |

---

## Ranked work plan

1. **Lazy tab bodies** (`on_change="rerun"` + `.open`) — biggest win, smallest diff, attacks the measured ~40–60s cold first paint.
2. **Snapshot-first Regime view** — `out/gex_snapshots.parquet` holds everything the landing cards need except `vrp_pct`/`vrp_pct_n` and `price_change_pct` (`compute.py:189, 261-265`); both recompute with **no network**.
3. **Retire hand-rolled HTML** — `st.metric(chart_data=…)`, `column_config` chart columns, `st.badge`, semantic headings. Keep custom CSS only where it encodes desk-terminal identity `config.toml` cannot express.
4. **`st.latex` for the formulas** — cheapest credibility win available.
5. **`st.skeleton` / `st.status`** for the unavoidable first load.
6. **Theme-aware charts** (`st.context.theme.type`) — the prerequisite for restoring light mode.
7. Housekeeping: 2× `use_container_width`, sentence-case labels, `:material/…:` icons.

---

## Do NOT do these

- **`st.fragment(parallel=True)` for the 3-ticker fetch.** Tempting and wrong. `app.py:524` records a measurement on the Oracle E2.1.Micro: threading was **slower** (35.2s vs 26.4s sequential) because the GIL only releases on network I/O while this pipeline is CPU-bound in surface fitting and coherence diagnostics — parallel workers fight over the single core. Revisit only if the box gains vCPUs.
- **Ripping out Plotly for the 3D surfaces.** The interactive vol surface, smile/term slices and the surface "video" have no Altair equivalent. Plotly stays for 3D.
- **CSS for theming.** Colours, fonts, radii live in `.streamlit/config.toml`. Do not reintroduce them as CSS.
- **`COPY .streamlit/` in the Dockerfile.** Would bake the gitignored-but-present `secrets.toml` into the image. The Dockerfile copies `config.toml` explicitly for exactly this reason.
- **Restoring `[theme.light]`** before charts are theme-aware — see the regression section.
- **`st.components.v1`** — deprecated; CCv2 is current.

---

## Working mechanics (hard-won)

- **Headless screenshots of a Streamlit app:** Edge at `C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe`, `--headless=new --screenshot=<path>`. Two traps: the path must be the full `C:\Users\AdamMorris\...` form (8.3 shortname `ADAMMO~1` → "Access is denied"), and **`--virtual-time-budget` does not work** — it fast-forwards timers while Streamlit renders over a real-time WebSocket, so it captures blank. Use a real `sleep 70` before the screenshot.
- **Never run pytest with a Streamlit server up** — CPU contention (39s → 198s).
- The dashboard reads `out/`; if stale it renders a thin red banner and little else. `.\scripts\sync-from-oracle.ps1` refreshes it (needs Adam's SSH key — he runs it).
- Reference docs ship inside the package: `.venv/Lib/site-packages/streamlit/.agents/skills/developing-with-streamlit/references/`. Version-matched — prefer them over web docs.

---

**Related:** `.planning/STATE.md` → "Session Continuity (2026-08-06 late — UI SWEEP, IN PROGRESS)" · `.streamlit/config.toml`

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/vol-diagnostics/ROADMAP|ROADMAP]] · [[_planning/vol-diagnostics/STATE|STATE]] · [[vol-diagnostics/vol-diagnostics|Hub]]
<!-- LINKS:END -->
