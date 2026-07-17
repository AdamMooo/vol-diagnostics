# Phase 11: Richer Daily Report - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-31
**Phase:** 11-richer-daily-report
**Areas discussed:** Email theme, PNG attachment scope, OI in the report, Evolution narrative placement

---

## Email theme

| Option | Description | Selected |
|--------|-------------|----------|
| Light / white | Explicit #ffffff body background. Works in all email clients. Safe formal document. Easy to print. | ✓ |
| Dark / terminal | Bloomberg-like dark background. Email client dark-mode inversion can fight explicit dark backgrounds in older Outlook. | |

**User's choice:** Light / white

| Option | Description | Selected |
|--------|-------------|----------|
| Keep current sign colors | Green/red from config.PALETTE, amber accent bar. Zero code change. | ✓ |
| Tone down to restrained palette | Muted green/red, steel-blue accent. Would require updating config.PALETTE — affects dashboard too. | |

**User's choice:** Keep current sign colors

| Option | Description | Selected |
|--------|-------------|----------|
| Keep clean no-background | White body, centered 720px. Works everywhere. | ✓ |
| Add light gray outer wrapper | Body background #f8fafc, white card inside. Standard 'card on gray' email design. | |

**User's choice:** Keep clean no-background

**Notes:** Light/white is the formal-business default. Explicitly deferred from Phase 10 — resolved here as the safe, universal choice. Dashboard stays dark (Bloomberg-like); email is light. Different audiences/contexts.

---

## PNG attachment scope

| Option | Description | Selected |
|--------|-------------|----------|
| SPY only — 2 images | 1 surface + 1 ΔIV for SPY. Focused, clean. Cross-ticker in text. | |
| All 3 tickers — 6 images | Surface + ΔIV per ticker. Complete but heavy email. | |
| All 3 surfaces + SPY ΔIV — 4 images | 3 vol surfaces + 1 SPY ΔIV. Covers surface priority across tickers without tripling ΔIV charts. | ✓ |

**User's choice:** All 3 surfaces + SPY ΔIV — 4 images

| Option | Description | Selected |
|--------|-------------|----------|
| Skip attachments silently | Non-blocking; no crash; failure logged. | |
| Attach HTML artifact instead | Attach plotly HTML file (interactive). | |
| Skip attachments, add note in email body | Text-only send + inline note so recipient knows PNGs were attempted. | ✓ |

**User's choice:** Skip attachments, add note in email body

| Option | Description | Selected |
|--------|-------------|----------|
| Live vs 5d rolling mean | Consistent with 5d narrative lead (RPT-05). Same as dashboard default. | ✓ |
| Live vs yesterday (1d) | Noisier — same hazard as retired vs-yesterday badge. | |
| Live vs 20d rolling mean | Longer horizon but diverges from 5d narrative — two different horizons in one report. | |

**User's choice:** Live vs 5d rolling mean

**Notes:** 4-image set is the middle ground — comprehensive on surfaces (highest priority per RPT-03) without flooding the email. ΔIV only for SPY since cross-ticker ΔIV comparison is already in the evolution table.

---

## OI in the report

| Option | Description | Selected |
|--------|-------------|----------|
| Data rows in each ticker card | "OI Call Wall" + "OI Put Wall" text rows. No new PNG pass. Assumption-free. | ✓ |
| Per-ticker OI-by-strike PNG (3 more attachments) | plot_oi_by_strike() charts. 7 total attachments. | |
| OI skew scalar only | Dollar-weighted put/call OI ratio. Loses per-strike wall information. | |

**User's choice:** Data rows in each ticker card

| Option | Description | Selected |
|--------|-------------|----------|
| Add below GEX walls in right column | OI rows adjacent to GEX walls. Easy to compare. | |
| Replace GEX walls with OI walls, add GEX walls in expander | OI primary. Bigger architectural change. | |
| You decide | Claude picks based on card structure and D-07. | ✓ |

**User's choice:** You decide — Claude chose: below GEX walls in right column

| Option | Description | Selected |
|--------|-------------|----------|
| Add to summary dict in compute_ticker() | Single source of truth. Dashboard and email both benefit. | ✓ |
| Compute in run_daily only | Email-only. Creates split where email has data dashboard doesn't. | |

**User's choice:** Add to summary dict in compute_ticker()

**Notes:** Content priority surfaces > walls > OI > gamma means OI is 3rd. Data rows are clean and sufficient — the dashboard already has the visual chart. No need to double up with another kaleido pass.

---

## Evolution narrative placement

| Option | Description | Selected |
|--------|-------------|----------|
| Top section, above ticker cards | Single cross-ticker section leads the report per RPT-05. e.g. "vols rose +1.2pp across SPY/QQQ/IWM over 5 days." | ✓ |
| Embedded per-ticker card | One evolution section per card. Buried — breaks the 'narrative leads' requirement. | |
| Separate section below ticker cards | Clearly separated but doesn't lead — requires scrolling. | |

**User's choice:** Top section, above ticker cards

| Option | Description | Selected |
|--------|-------------|----------|
| Compact table: SPY/QQQ/IWM × 4 scalars | Mini table. Cross-ticker divergence visible at a glance. EVOL-05. | ✓ |
| One scalar row per ticker (bullet list) | Readable but verbose with all 4 scalars per ticker. | |
| Lead sentence only, no scalar table | Cleaner but loses specific scalar data. | |

**User's choice:** Compact table: SPY/QQQ/IWM × 4 scalars

| Option | Description | Selected |
|--------|-------------|----------|
| Omit section entirely when no history | Cleaner cold start — section never appears until history accumulates. | ✓ |
| Show section with 'accumulates from run_daily' note | Consistent with dashboard cold-start pattern. | |

**User's choice:** Omit section entirely when no history

**Notes:** Top lead + compact table is the cleanest implementation of RPT-05. All-None cold start → omit keeps the email lean until real data exists.

---

## Claude's Discretion

- **kaleido camera angle** — specific azimuth/elevation for `plot_vol_surface` and `plot_iv_change_surface` PNG exports. Must be readable as a static frame (isometric-style, e.g. `eye=dict(x=1.5, y=-1.5, z=0.8)`).
- **OI wall row placement** — below GEX-derived Call Wall / Put Wall in the right column. Rationale: adjacent for comparison, no structural change to the card layout.
- **Evolution narrative sentence template** — built at runtime from level/rms/skew_change/term_change values. Cross-ticker lead sentence.
- **Module placement** — whether PNG export is a new `gex/png_export.py` or functions added to an existing module.
- **OI computation location** — whether `oi_call_wall`/`oi_put_wall` is computed in `analytics.py:summarise()` or `exposure_engine.py`.

## Deferred Ideas

- **VRP in email** — `vrp_headline()` is ready (Phase 10 D-15) but not in RPT-01..05 scope. Deferred.
- **Per-ticker OI-by-strike PNG charts** — replaced by data rows. Could be a future enhancement.
- **All-3-tickers ΔIV surfaces** — only SPY ΔIV in Phase 11; cross-ticker ΔIV covered by evolution table.
- **`cid:` inline images** — deferred to v4.x per REQUIREMENTS.md.

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
**Phase siblings:**
- [[_planning/gamma-omm/phases/11-richer-daily-report/11-CONTEXT|11-CONTEXT]]

<!-- LINKS:END -->
