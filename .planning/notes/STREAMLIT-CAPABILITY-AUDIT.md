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

## The 3D surface iframe — the showpiece is under-built

Adam, 2026-08-06: *"maybe the focus should also be on making those htmls better and more detailed and informative."* Correct instinct — the interactive vol surface is the differentiated artifact, and it is thinner than the rest of the app. It lives in `engine/surface/surface_interactive.py` (525 lines) and reaches the page via `components.html` at `app.py:600` (Today), `700` (Compare), `765` (Evolution movie), i.e. **inside an iframe, outside Streamlit theming entirely**. Nothing in `config.toml` will ever touch it.

Already good, do not "fix": the header tag strip (`:154-158`) shows ticker, date, spot, smoothing, clip, **coverage %** and **fit RMSE pp** — the trust metrics are surfaced. Linked 2D smile/term slices on hover, fullscreen button, and raw quote markers on the term slice (`term_raw`) are all present.

### 🐞 Real bug — hover mislabels the moneyness axis
`:173` (Today) and `:327` (Compare) both render:
```js
hovertemplate:'DTE %{x:.0f}<br>K/S %{y:.3f}<br>IV %{z:.1f}%'
```
but `y` is bound to `D.otm_grid`, whose **axis title is `ln(K/S)`** (`:175`). So hovering a point at ln(K/S) = −0.015 reports "K/S −0.015", when K/S is actually 0.985. The label names the wrong quantity. Fix by either relabelling to `ln(K/S)` or converting: `K/S = exp(y)`.

### Theme mismatch introduced by the new palette
Hardcoded, and now slightly off against `config.toml`'s `#0B0F14` background:
- `paper_bgcolor:'#0e1117'` × 5
- `gridcolor:'#222'` × 17
- `colorscale:'Plasma'` × 1 — unrelated to the theme's `chartSequentialColors`

These are inside the iframe, so they must be threaded through from Python (the payload/format vars) rather than set in `config.toml`.

### Enrichment — buildable with data ALREADY in the payload
`build_surface_payload` already ships `spot`, `ks_grid`, `coverage`, `rmse`, `smile_raw`, `term_raw`, `near`. So these need **no new plumbing**, only client-side arithmetic:
1. **Richer hover** — add strike in dollars (`K = spot × exp(y)`), moneyness as a percentage (`(K/S − 1) × 100`), and the expiry date alongside DTE. Currently a viewer sees raw coordinates they cannot act on.
2. **ATM ridge** — draw the `ln(K/S) = 0` line on the surface. It is the reference every read is relative to and it is invisible today.
3. **30-DTE marker** — the tenor the card's IV30 is quoted at; ties the surface to the number on the Regime card.
4. **25Δ put/call markers** — ties the surface to the skew figure reported on the card. Closes the loop between the chart and the read.

### Enrichment — needs new plumbing (worth it, larger)
5. **Raw quote scatter in 3D.** The 2D term slice plots real markers, but the 3D surface is a fitted RBF with no indication of where actual quotes are. Overlaying the observed `(DTE, ln(K/S), IV)` triples as a `scatter3d` would instantly distinguish **data from model** — the single most defensible thing this chart could show, and directly relevant in an interview.
6. **Coherence violation overlay.** `exposure_engine.py` already computes calendar/butterfly violations per snapshot. Marking violating regions on the surface would make the arbitrage diagnostic visible — **but only after the butterfly test is fixed**, since it currently fires on 100% of days (see the separate finding: it second-differences implied vol rather than call price, so it is not testing the Breeden–Litzenberger condition it claims to).

**Note:** this work is independent of the cold-start fix. Enriching the surfaces does not make the app load faster, and vice versa. Both matter; do not let one stand in for the other.

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
