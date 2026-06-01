# Requirements — v3.4 Email-First Daily Report Polish

*Last updated: 2026-06-01 — milestone v3.4 defined; phases assigned*

## Milestone Goal

Stop building accumulation-dependent features and instead show off the parts already built. Curate the daily email into a tight, single-snapshot diagnostic, render the same canonical card in the local dashboard so the two stop drifting, and hide history-dependent UI until enough sessions accrue. Every requirement is single-snapshot or near-it — favouring metrics computable from today's chain (plus at most yesterday's) over ones that need a long history.

**Non-reversal note:** the 1-day ΔIV surface in the email is a DESCRIPTIVE "vs last session" daily glance, not a signal. It does not feed or alter the evolution engine's {5,10,20} horizons and does not reverse the locked 2026-05-30 "no 1d in evolution" decision.

---

## Requirements

### Canonical Card (email ↔ dashboard consistency)

- [x] **CARD-01** — A single canonical per-ticker card definition is the source of truth for both the email and the Streamlit dashboard; the dashboard card renders the same fields as the (richer) email card so the two surfaces cannot drift apart.
- [x] **CARD-02** — VRP (IV30 − RV20) appears as a scalar field on the canonical card. It is already computed in `compute_ticker`; this closes the gap where VRP shows in the dashboard but is entirely absent from the email.
- [x] **CARD-03** — IV30, front skew (25Δ), and net GEX each display a signed 1-session delta versus the prior stored snapshot (raw signed number, e.g. `18.5% (+0.8)`). This is distinct from the retired categorical regime badge — it is the honest scalar change, not a thresholded label. The delta gracefully omits its suffix when no prior snapshot exists.
- [x] **CARD-04** — GEX-derived walls are labelled "(model)" and open-interest walls "(raw OI)", with a one-line inline distinction, consistently in both the email and the dashboard, so the two wall types are never confused.

### Daily Report PNG (email)

- [ ] **RPT-06** — The daily email attaches exactly one PNG type: a 1-day ΔIV surface render per index (SPY, QQQ, IWM) showing the surface change versus the last trading session with a stored snapshot. This replaces — 1:1 — the 3 static surface PNGs and the old SPY-only 5-day ΔIV PNG. If no prior snapshot exists for a ticker, that ticker's PNG is omitted gracefully (email still sends).
- [ ] **RPT-07** — The 1-day ΔIV render is framed as a descriptive "vs last session" view: it is labelled with the real prior date and resolved via `nth_trading_day_back(ticker, today, 1)` (gap-safe — "last session with a snapshot", not a calendar day). It does not feed or alter the evolution engine.

### Accumulation Gating

- [ ] **GATE-01** — Dashboard UI elements that require accumulated history (evolution-tab small-multiples, VRP/skew percentiles, the VRP sparkline, the 42-session spot-vs-levels chart) are hidden behind an explicit "needs ≥N sessions" guard with a clear caption until enough stored sessions exist. The underlying engines and stores are left untouched — only the display is gated.
- [ ] **GATE-02** — The email is cold-start clean: any history-dependent content (evolution section, ΔIV PNGs) is omitted rather than rendered empty/NaN when its required history does not yet exist, and the send never fails on missing history.

---

## Future Requirements (deferred)

- **Large OI blocks expiring soon** — flag near-dated expiries carrying large open interest. Deferred from v3.4: needs a parameter-free design (no hand-tuned "large" cutoff — the trap that retired the GEX-weighted wall cluster). Candidate parameter-free form: report the single largest-OI strike + its days-to-expiry, and the front-expiry share of total chain OI; let the reader judge "soon."
- **Inline `cid:` email images** instead of attachments — requires Outlook COM PropertyAccessor plumbing; v4.x.
- **Bloomberg data swap** — one-class change in `data_loader.py`; v4.x.

---

## Out of Scope

| Feature | Reason |
|---------|--------|
| Reversing the "no 1d in evolution" decision | The 1d ΔIV is an email-only descriptive view; the evolution engine keeps its {5,10,20} horizons. These are separate concerns and both stand. |
| New metrics requiring data accumulation | Directly counter to the milestone thesis — v3.4 reduces dependency on accumulated data, it does not add to it. |
| Dashboard surface (3D) page rework | Explicitly left untouched per user — the interactive 3D surface + Compare tab stay as-is; the 1d highlight is an email concern only. |
| New tickers beyond SPY/QQQ/IWM | Dealer-positioning convention is only defensible for these. |
| Predictive / "fair value" forecasting | Descriptive-only constraint stands. |

---

## Traceability

| REQ-ID | Phase | Status |
|--------|-------|--------|
| CARD-01 | Phase 12 | Complete |
| CARD-02 | Phase 12 | Complete |
| CARD-03 | Phase 12 | Complete |
| CARD-04 | Phase 12 | Complete |
| RPT-06 | Phase 13 | Pending |
| RPT-07 | Phase 13 | Pending |
| GATE-01 | Phase 14 | Pending |
| GATE-02 | Phase 14 | Pending |

**Coverage:** 8/8 requirements mapped. ✓

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
<!-- LINKS:END -->
