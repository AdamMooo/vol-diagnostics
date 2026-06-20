# Option Diagnostics — Retroactive UI Review

**Audited:** 2026-06-20
**Baseline:** Heuristic (no UI-SPEC.md). North star: dark Bloomberg-like terminal, dense, restrained amber-on-black, descriptive-only, honest about data limits. Audience: index income-sleeve PM (covered calls / CSPs on SPY/QQQ/IWM).
**Screenshots:** Not captured — no Streamlit dev server on 8501/3000. Audit is from source, CSS, and emitted HTML only.
**Edit surface:** `app.py`, `gex/surface_interactive.py`, `gex/card_model.py` (+ `gex/config.py` for palette verification).

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Visual hierarchy | 2/4 | Read-line is the right hero idea but is visually outweighed by the 14-row field grid; iframes (640px) dwarf the cards |
| 2. Legibility / learnability | 2/4 | No "how to read this" affordance for the 3D surface; iframe theme (#0e1117) diverges from card theme; axis labels mix `ln(K/S)` (3D) and `K/S` (slices) |
| 3. Density & restraint | 2/4 | Card grid carries redundant wall rows + multi-clause compound cells; amber north-star accent is barely used (cards use green/red, not amber) |
| 4. Consistency | 1/4 | Three conflicting color systems for "up"; amber accent inconsistently applied; three hand-rolled plotly iframes vs native Streamlit charts |
| 5. Affordance / interaction clarity | 2/4 | Fullscreen is an unlabeled glyph; surface drag/hover not signposted; Level/Change toggle has a collapsed label |
| 6. Trust / honesty cues | 4/4 | Coverage/RMS/resid shown raw, chips gated on credibility floor, model assumptions labeled inline and in a consolidated methodology expander |

**Overall: 13/24**

---

## Top 3 Priority Fixes

1. **Unify "direction" color semantics across cards, ΔIV, and chips (BLOCKER).** Today a PM sees green=up (sign cards / `_get_sign`), red=up (ΔIV surface), and a *third* mapping where "vol lifting" is red-negative but "dealers stabilizing" is green-positive in the same chip row. Pick one axis convention (recommend: green/red reserved for P&L-favorable/unfavorable to the *writer*, and the diverging blue↔red strictly for ΔIV magnitude, clearly fenced as "this chart only"). Add a one-line legend on the cards. — Files: `app.py:63-67,200-207`, `card_model.py:115-127,372-382`, `surface_interactive.py:300-301,314`.

2. **Make the read-line the visual hero and demote the field grid (WARNING→BLOCKER for the 5-second goal).** The "so what" (`build_card_read`) is rendered at `0.8rem` italic immediately above a 14-field `0.80rem` bold tabular grid — same weight class, so the eye lands on the number wall, not the call. Bump the lean to ~1rem/non-italic, give chips more vertical separation, and collapse the field grid behind a "details" disclosure or visually recede it (lower opacity / smaller). — Files: `app.py:84-88,208-219`, `card_model.py:227-301`.

3. **Add a persistent "how to read this" affordance to the 3D surface (WARNING).** User's explicit complaint is the surface is aggressive/hard to interpret. The only in-context cue is `smile / term — hover the surface` in the slice label (`surface_interactive.py:157`). Add a small inline legend/tooltip in `#hdr` explaining: axes (DTE × moneyness × IV), that the right panels are live cross-sections, that warmer=higher IV (Plasma), and that you drag to rotate. — Files: `surface_interactive.py:130-158,147-158`.

---

## Detailed Findings

### Pillar 1: Visual hierarchy (2/4)

- **The cards are structurally correct but visually under-ranked. (WARNING)** `render_regime_card` (`app.py:166-219`) puts the read (chips + lean) above the grid — good ordering. But the lean is `font-size:0.8rem; font-style:italic` (`app.py:210`) while the grid values are `0.80rem; font-weight:700; tabular-nums` (`.rc-v`, `app.py:87`). Identical size, and the grid is bolder and has 14 rows (`build_card_fields` returns 14, `card_model.py:227-301`), so the dense number block wins the eye. The 5-second "is premium worth selling" call loses to a spec sheet.
- **Heavy iframes dominate the page. (WARNING)** Each `components.html(... height=640)` (`app.py:313,418`) and the movie at `height=620` (`app.py:489`) render a 3D WebGL scene that is physically ~2× the height of a card row. The hierarchy the layout *intends* (cards = hero, surfaces = drill-down behind tabs) is partly preserved by tab placement, but within any tab the surface is the whole viewport. Acceptable since surfaces are tabbed, hence WARNING not BLOCKER.
- **Section chrome is muted and consistent. (PASS)** `.sec` and `.top-bar` (`app.py:73-96`) use small-caps slate labels — appropriately recessive terminal chrome.
- **No single focal accent on the card.** The ticker name takes the sign color (`app.py:215`), competing with the left accent bar (`app.py:214`) and the chips for the eye. Three colored elements, no clear primary.

### Pillar 2: Legibility / learnability (2/4)

- **No standing "how to read it" for the surface. (WARNING)** Confirmed user pain. The 3D figure (`surface_interactive.py:162-171`) ships axis titles `DTE`, `ln(K/S)`, `IV %` but nothing explains what a vol surface *is* or that warmer Plasma = higher IV. The slice label is the only hint and it's transient (`#lbl`, line 157, 195).
- **Axis-label vocabulary is inconsistent within one component. (WARNING)** The 3D y-axis is `ln(K/S)` (`surface_interactive.py:168`) but the slice panels label the same dimension `K/S (smile)` (line 182) and the hover shows `K/S` (line 166). A non-specialist must reconcile log-moneyness vs raw ratio across panels of the same widget. The diff component repeats this (`ln(K/S)` at 319 vs `K/S` at 329).
- **Iframe theme diverges from Streamlit theme. (WARNING)** Iframe `body` is `#0e1117` (`surface_interactive.py:134,287,456`), text `#e6e6e6`/`#cfcfcf`. The surrounding Streamlit cards use `#c9d1d9` lean text (`app.py:210`) and slate `#64748b`/`#94a3b8` chrome. Two near-but-not-equal dark grays read as a seam, not one terminal. The amber differs too: app palette accent is `#d97706` (`config.py:187`) but iframes use `#ffd24d` (`surface_interactive.py:140,173`) — a brighter, greener amber. The "restrained amber" north star is violated inside the iframes.
- **Slice panels are a genuine legibility asset. (PASS)** The 60/40 split with live smile + term cross-sections (`surface_interactive.py:137-138,172-186`) is the right move for a non-specialist — it turns the scary 3D into readable 2D lines. The raw-scatter overlay (line 174) lets the PM see data density. This is the strongest learnability feature present.
- **Near-expiry excluded series is labeled but cryptic.** `near 'X'DTE (excl.)` (`surface_interactive.py:177`) — the "(excl.)" will not be self-explanatory to a PM without the methodology expander.

### Pillar 3: Information density & restraint (2/4)

- **Redundant wall rows. (WARNING)** The card shows four wall rows: `Call Wall (model)`, `Put Wall (model)`, `OI Call Wall (raw OI)`, `OI Put Wall (raw OI)` (`card_model.py:273-300`), plus a `Range` row that re-derives from the model walls (line 283-290). Five of fourteen rows are wall/range variants. Dense is fine; *redundant* is not — a PM scanning for "where do I write" sees two competing wall definitions with no guidance on which to trust on the card itself (the IWM caveat lives only in Positioning, `app.py:609-612`).
- **Compound multi-clause cells. (WARNING)** `IV30 / 1d σ` packs `iv30 + delta + expected_str` into one value (`card_model.py:238-242`), and VRP packs `value · pctile · lookback-state` (`_fmt_vrp`, line 95-112). These are three facts in one cell, fighting the tabular scan. Bloomberg density works because each cell is atomic; these aren't.
- **Amber is under-used, not over-used. (note)** The restraint goal is met to a fault — the north-star amber `#d97706` appears only on the γ-flip history line (`app.py:552`). The cards carry no amber at all; their accent is green/red sign color. The "restrained amber-on-black" identity is essentially absent from the hero surface (the cards). This is a consistency/identity gap more than clutter.
- **Top bar is appropriately terse. (PASS)** `app.py:256-262` — tickers + date + data-lag + OI caveat on one recessive line.

### Pillar 4: Consistency (1/4)

- **Three conflicting color systems for "up." (BLOCKER)** Verified against `config.PALETTE` (`config.py:186-192`):
  - Sign cards / chips P&L axis: green `#16a34a` = positive, red `#dc2626` = negative (`card_model.py:115-127`, `app.py:200-201`).
  - ΔIV surface: red `#b2182b` = vol **up**, blue `#2166ac` = vol down (`surface_interactive.py:314`, header text 300-301).
  - OI bars: blue = call, red = put (`config.py:191-192`, `app.py:525`).
  So red simultaneously means "negative/bad," "vol up," and "puts," and blue means "down," "calls." A PM glancing across the Surface→Positioning→cards must reload the color key three times. This is the single worst consistency defect.
- **Chip semantics invert within one row. (BLOCKER, same root)** In `build_card_read` (`card_model.py:364-382`): `skew steep` → negative(red), `vol lifting (5d)` → negative(red), but `dealers stabilizing` → positive(green). "Vol lifting" being red-bad while sitting next to "dealers stabilizing" green-good is defensible *to a writer* but is never explained, and it directly contradicts the ΔIV surface where vol-up is red as a neutral magnitude, not a value judgment. Same color, opposite meaning, adjacent in the UI.
- **Amber value is inconsistent. (WARNING)** `#d97706` (config) vs `#ffd24d` (iframes) vs `#f59e0b` (the neon the config comment says it deliberately stepped away from). Three ambers in one product.
- **Three bespoke plotly iframes vs native charts. (WARNING)** Surface/diff/movie are hand-built `_HTML`/`_DIFF_HTML`/`_MOVIE_HTML` strings with their own CSS, fonts, and fullscreen button (`surface_interactive.py:130-206,283-350,452-507`), while Positioning uses native `st.plotly_chart` with `plotly_dark` (`app.py:518,585`). Two rendering stacks, two header-chrome styles, two font stacks (`-apple-system,Segoe UI` in iframes vs Streamlit default). The perf rationale for the split iframe is sound (documented in the module docstring), but the styling drift is incidental, not required.
- **Typography is otherwise reasonably tight.** Font sizes across CSS: `0.62rem, 0.72rem, 0.78rem, 0.80rem, 1.05rem` (`app.py:69-96`) plus iframe 9–13px. Five card sizes is on the high side but each maps to a clear tier (chrome / chip / lean / value / ticker).

### Pillar 5: Affordance / interaction clarity (2/4)

- **Fullscreen is an unlabeled glyph. (WARNING)** `⛶` button with only a `title="Fullscreen"` tooltip (`surface_interactive.py:152,302,465`). Tooltips don't show on touch and are easy to miss; no text label.
- **Surface drag/rotate is undiscoverable. (WARNING)** Nothing tells the PM the 3D scene is drag-to-rotate / hover-to-slice. The slice label `hover the surface` (line 157) is the only cue and it reads as a status, not an instruction.
- **Movie play/scrub is well signposted. (PASS)** `play ▶ to watch it move` placeholder in the header (`surface_interactive.py:464`), an on-canvas `▶ Play` / `❚❚ Pause` button pair (lines 483-486), and a labeled slider (488-489). Plus the Streamlit caption above it explains play/scrub (`app.py:438-441`). This is the model the surface tab should copy.
- **Level/Change toggle has a collapsed label. (WARNING)** `st.radio("Mode", ["Level","Change vs start"], label_visibility="collapsed")` (`app.py:449-452`). The options are self-describing, but with the label hidden and two radios side by side (ticker radio + mode radio, both collapsed, `app.py:444-452`), it's ambiguous which radio is which. Same pattern on the Surface tab ticker radio (`app.py:296-299,332-335`).
- **Compare-tab horizon selectors are clear. (PASS)** Two labeled selectboxes "Date A"/"Date B" with sensible live-vs-5d default (`app.py:363-378`).

### Pillar 6: Trust / honesty cues (4/4)

- **Raw trust readout, no badge. (PASS)** `Coverage / Fit RMS / Max resid` shown as bare numbers above each surface (`app.py:307-308`, `_trust_readout_strings` 119-136), with `—` for missing — PM judges, no traffic-light overclaim. Coverage/RMSE also echoed in the iframe header (`surface_interactive.py:151`).
- **Chips gated on a credibility floor. (PASS)** `build_card_read` only emits a band when the sample clears `CARD_READ_MIN_SESSIONS` (`card_model.py:347-378`), and the lean explicitly says "Premium history still building — no rich/cheap call yet" when thin (line 324-325). A thin rank is omitted, not shown with a caveat — the right call.
- **Model assumptions labeled inline. (PASS)** "(model)" / "(raw OI)" on wall rows (`card_model.py:273-300`), "assumes dealers net short" on Positioning (`app.py:499-503,527,606`), the consolidated Methodology expander titled "read before trading off this" (`app.py:615`), and the honest NaN coverage holes in the surface (`surface_interactive.py:88-92`).
- **Cold-start handling everywhere. (PASS)** Compare/Evolution/Positioning all degrade to "accumulates from run_daily forward" captions when history is thin (`app.py:345-348,491-494,587-590`), and VRP shows "building to N" (`card_model.py:110-111`).
- **Descriptive-only discipline holds. (PASS)** The lean uses "favors"/"relatively attractive," never a directive (`card_model.py:326-332`), and the docstring explicitly notes it stays inside "descriptive, no prescription." γ-flip/walls flagged as zero-peer-reviewed model constructs (`app.py:656-664`). This pillar is the product's strength and should not be diluted while fixing the others.

---

## Files Audited

- `C:\dev\gamma-omm\app.py` — full file (CSS, `render_regime_card`, three tabs, methodology expander)
- `C:\dev\gamma-omm\gex\surface_interactive.py` — full file (`_HTML`, `_DIFF_HTML`, `_MOVIE_HTML` + payload builders)
- `C:\dev\gamma-omm\gex\card_model.py` — full file (`build_card_fields`, `build_card_read`, formatters)
- `C:\dev\gamma-omm\gex\config.py` — `PALETTE` block (lines 186-199) for color-semantics verification

Registry audit: not applicable (no `components.json`; not a shadcn project).
