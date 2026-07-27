---
phase: 27-microstructure-monitor-ui
plan: 04
subsystem: report
tags: [email, alerts, event-shaped, monitor, cold-start, hybrid, methodology-link]

# Dependency graph
requires:
  - phase: 27-microstructure-monitor-ui (plan 01)
    provides: monitor_reader.load_recent_alert_events + load_rank_trail (prior-rank lookup)
provides:
  - "Event-shaped alerts banner (alerts_section_html) riding above the rich descriptive email — one row per band entry/escalation, empty string on quiet days"
  - "build_email alert_events / prior_rank_lookup params (backward-compatible defaults)"
  - "Delta-vs-yesterday fragment per alert (rank now vs prior stored rank), via load_rank_trail(n=2)"
  - "Single Methodology link (config.DASHBOARD_METHODOLOGY_URL), placeholder-safe"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Banner returns '' on empty/None events — quiet-day cold-start norm; the rich email is untouched"
    - "Prior-rank lookup keyed by (ticker, metric, rank_kind) → prior rank column via _ALERT_RANK_KIND_COLUMN map"
    - "No new math/signal — rank_at_transition + prior ranks are read straight from stored structs (SC-6)"
    - "run_daily alert-event gather wrapped non-blocking (cold-start / corrupt store degrades to no banner)"

key-files:
  created: []
  modified:
    - engine/config.py
    - engine/report/report.py
    - engine/run_daily.py
    - engine/tests/test_report.py

key-decisions:
  - "DEVIATION from 27-04-PLAN (Adam-approved): plan specified gutting the email to alerts-only ('nothing unusual' on quiet days) + deleting OI table / key-levels / descriptive cards. Since ZERO alerts have ever fired (~2 days of monitor history), that would render a near-empty email every day for weeks — contradicting the rich VRP/evolution email Adam had just validated this session. Chose the HYBRID: keep the full descriptive report, ADD an alerts banner that is invisible on quiet days and fires loudly only on a real band entry/escalation."
  - "OI-by-expiry table and key-levels block RETAINED (plan wanted them deleted) — they are part of the rich email Adam values; revisit if the monitor accumulates real alert history and the email genuinely shifts to event-first."
  - "Methodology link points at config.DASHBOARD_METHODOLOGY_URL (Oracle-hosted dashboard, https://40.233.113.63.nip.io); '' omits the link gracefully."
  - "Banner ordered above the VRP strip so alerts lead when present."

# Verification
tests:
  before: 493
  after: 501
  delta: +8 (ordinal suffixes, empty→blank, event row + delta, escalation badge, quiet-day no banner, banner when events, methodology link on/off)
  status: 100% green
commits:
  - "148c2b0 feat(27-04): event-shaped alerts banner (hybrid) + methodology link"
previews:
  - out_preview_alerts.html (synthetic 2-alert banner: SPY skew entry, IWM vrp escalation)
  - out_preview_quiet.html (no banner — rich email unchanged)

# Requirements
requirements: [SC-4, SC-6]
notes: >
  SC-4 (event-shaped surfacing) satisfied via the hybrid banner rather than a full
  email rewrite. SC-6 (no new signal) satisfied — all values are stored structs.
  Cold-start reality: the banner will be empty in production until a real alert
  fires; out_preview_alerts.html demonstrates the fired state with a synthetic fixture.
---
