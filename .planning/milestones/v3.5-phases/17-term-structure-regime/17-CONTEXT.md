# Phase 17: Term-Structure Regime - Context

**Gathered:** 2026-06-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Add VIX term-structure ratios (VIX9D/VIX, VIX/VIX3M) to the SPY card and
dashboard as raw labeled numbers. QQQ/IWM gracefully degrade because CBOE does
not publish 9D/3M siblings for VXN/RVX. No categorical label, no scoring, no
hidden weighting — the PM reads the ratio and judges contango vs backwardation.

</domain>

<decisions>
## Implementation Decisions

### Data availability (verified 2026-06-23)
- **D-01:** CBOE publishes VIX9D and VIX3M for SPY. No VXN9D/VXN3M or RVX9D/RVX3M
  exists — confirmed by the `out/vol_index/` store containing only VIX.parquet,
  VIX9D.parquet, VIX3M.parquet, VXN.parquet, RVX.parquet.
- **D-02:** For QQQ/IWM the term-structure row is omitted or labeled "N/A — single
  point only" rather than fabricated.

### Ratio computation
- **D-03:** Two ratios for SPY: VIX9D/VIX (short-term vs 30d) and VIX/VIX3M
  (30d vs 3-month). Values <1 = contango; >1 = backwardation.
- **D-04:** Ratios use the latest available close from the vol-index store (same
  session alignment as VRP).
- **D-05:** When any input is missing (fetch failure, empty store), return None —
  never fabricate a ratio from chain-derived IV.

### Display framing
- **D-06:** Card shows ratios as raw decimals (e.g. "0.87 / 1.03") with inline
  contango/backwardation hint (word only, not categorical regime label).
- **D-07:** No percentile on term ratios this phase — pure current-state descriptive.

### Claude's Discretion
- Exact label wording for the card field.
- Where in the existing compute_ticker pipeline to inject the vol-index lookup.
- Whether to expose as one CardField or two separate fields.

</decisions>

<canonical_refs>
## Canonical References

### Vol-index data layer
- `engine/data/vol_index.py` — `load_vol_index(symbol)` returns DataFrame with
  date/close columns; already caches VIX, VIX9D, VIX3M.
- `engine/config.py` — `DEFAULT_VOL_INDICES` lists all symbols fetched daily.

### Compute pipeline
- `engine/compute.py` — `compute_ticker()` assembles the summary dict consumed by
  card_model and dashboard; term_structure (chain-based ATM IV curve) already lives
  at `summary["term_structure"]`.
- `engine/vol/vol_metrics.py` — `compute_term_structure()` is the chain-derived ATM
  IV curve (different from the vol-index term ratios this phase adds).

### Card model + rendering
- `engine/report/card_model.py` — `build_card_fields()` / `build_card_read()` are
  the single source of truth for both email and dashboard.
- `app.py` — scorecard rendering via `render_regime_card()`.
- `engine/report/report.py` — email card renderer consuming card_model output.

### Prior locked context
- `.planning/phases/16-vrp-percentile/16-CONTEXT.md` — VRP series consistency.
- `.planning/phases/15-vol-index-data-layer/15-CONTEXT.md` — vol-index store semantics.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `load_vol_index(symbol)` already returns the full history with `close` column.
- `compute_ticker()` already calls `vrp_percentile(ticker)` which reads the vol-index
  store — the same pattern can load VIX9D/VIX3M closes.
- `CardField` dataclass and `build_card_fields()` already support trust_tag and
  conditional omission.

### Ticker → Vol-Index mapping
- SPY → VIX (30d), VIX9D (9d), VIX3M (3m)
- QQQ → VXN (30d only)
- IWM → RVX (30d only)

### Integration Points
- `engine/compute.py`: add term-ratio keys to summary dict.
- `engine/report/card_model.py`: add CardField for term structure.
- `app.py`: render the field (already iterates card_fields).
- `engine/report/report.py`: email card renders via the same card_model fields.

</code_context>

<specifics>
## Specific Ideas

- A single function `compute_term_ratios(ticker)` in `engine/vol/vol_metrics.py`
  that returns `{"vix9d_vix": float|None, "vix_vix3m": float|None}` handles the
  ticker → symbol mapping and graceful None on missing data.
- The card field label could be "VIX Term" for SPY with value like
  "9D/30: 0.87 · 30/3M: 1.03" — compact single-line.
- For QQQ/IWM: field omitted entirely (not shown) since there's nothing to display.

</specifics>

<deferred>
## Deferred Ideas

- Term-structure percentile (ranking today's ratio vs history) — could be Phase 18
  or later if useful.
- Sparkline of term ratio over time.
- Backwardation alert/chip on the read — requires defining a meaningful threshold.

</deferred>

---

*Phase: 17-term-structure-regime*
*Context gathered: 2026-06-23*
