# Vol Diagnostics — Résumé & Profile Copy

Drop-in copy at several lengths. Same positioning as [`INTERVIEW-PREP.md`](INTERVIEW-PREP.md)
and [`LINKEDIN-POST.md`](LINKEDIN-POST.md) — descriptive, non-directional, built for an
option-writing desk.

Every number below is verified against the repo as of 2026-08-09. Don't inflate them;
they're strong as they stand, and each one survives a follow-up question.

Last updated: 2026-08-09

---

## Résumé bullets — full (4 lines)

Use when the project gets its own block.

- Designed and deployed a production volatility-diagnostics platform (Python, Streamlit, Docker, Caddy/TLS) that conditions systematic option-writing decisions across SPY, QQQ and IWM — implied-vol surface, variance risk premium, skew, term structure and dealer-positioning reads, delivered as a live dashboard and an automated daily report.
- Built a variance-risk-premium engine ranking current premium against a 10-year (2,520-session) CBOE volatility history, with credibility gating that suppresses any read whose sample depth can't support it — a thin sample is hidden, not shown with a caveat.
- Removed a headline feature after out-of-sample testing returned a null result (forward-return p = 0.74), and stripped four further unvalidated metrics; every surviving claim is tiered to its evidence with peer-reviewed citations.
- Cut dashboard cold-start latency from 40-60s to 5-7s by profiling Streamlit's eager tab evaluation and bounding an unbounded interpolation window; hardened the pipeline behind a 483-test suite and an unattended daily GitHub Actions job.

## Résumé bullets — compact (2 lines)

Use when space is tight or the project is one of several.

- Built and deployed a production volatility-diagnostics platform (Python, Streamlit, Docker) conditioning systematic option-writing decisions across SPY/QQQ/IWM; variance risk premium ranked against a 10-year CBOE history, 483-test suite, unattended daily data pipeline.
- Enforced evidence tiering over feature count — deleted a headline signal after an out-of-sample null result (p = 0.74) plus four unvalidated metrics, and gated every remaining read on sample depth.

## Résumé bullet — single line

- Built and deployed a production volatility-diagnostics platform (Python, Streamlit, Docker) for systematic option-writing decisions across SPY/QQQ/IWM — variance risk premium ranked against a 10-year CBOE history, 483-test suite, unattended daily pipeline, every claim tiered to peer-reviewed evidence.

---

## Project overview — 3 sentences

For a cover letter, a portfolio page, or the summary field on an application.

> Vol Diagnostics is a volatility and dealer-microstructure platform for systematic option writing across SPY, QQQ and IWM. It reads whether premium is rich or cheap against a decade of CBOE history, where on the implied-vol surface that richness sits, and how large moves tend to run in the prevailing dealer-positioning regime — conditioning how a writing program is run rather than forecasting direction. It is deliberately non-predictive: every claim is tiered to its supporting evidence, reads without sufficient sample depth are suppressed, and features that failed out-of-sample testing were removed rather than shipped with caveats.

## Project overview — 1 sentence

> A production volatility-diagnostics platform for systematic option writing, which conditions how a writing program is run — premium richness, surface shape, regime move-size — without ever forecasting direction.

---

## LinkedIn "Projects" entry

**Title:** Vol Diagnostics — Volatility & Dealer-Microstructure Platform

**Description:**
> Volatility diagnostics for systematic option writing across SPY, QQQ and IWM. Reads the variance risk premium against a 10-year CBOE history, decomposes richness across strike and tenor via an interactive implied-vol surface, and derives a move-size regime from dealer positioning — conditioning how a writing program runs, never forecasting direction.
>
> Descriptive by design: claims are tiered to their evidence with peer-reviewed citations, reads lacking sample depth are suppressed rather than caveated, and features that failed out-of-sample testing were removed. Python, Streamlit, Docker, GitHub Actions; free data sources, no vendor feed; 483-test suite and an unattended daily pipeline.
>
> Live: https://40.233.113.63.nip.io

---

## Skills this evidences

Pull from these when a posting asks for specific keywords. Each is genuinely demonstrated
in the repo — none is a stretch.

| Area | Evidenced by |
|---|---|
| Derivatives / vol modelling | Implied-vol surface (OTM convention, log-moneyness), 25Δ skew and butterfly, term structure, model-free expected move, variance risk premium |
| Statistical rigour | Out-of-sample testing, multiple-testing awareness, ECDF percentile ranking, credibility gating on sample depth, a shipped null result |
| Market microstructure | Dealer gamma exposure, gamma-flip level, open-interest concentration, the index-vs-single-name dealer-positioning distinction |
| Python engineering | Pandas, NumPy, SciPy, Plotly, Streamlit; 483-test suite; atomic parquet writes; a single shared compute path for dashboard and report |
| Data engineering | Daily automated collection, parquet stores, object-storage backup with a verified restore drill, health checks with strict-mode exit codes |
| DevOps | Docker Compose, Caddy with Let's Encrypt TLS, GitHub Actions scheduling, cloud deployment |
| Research communication | Literature review with SSRN/DOI citations, in-app methodology tiering, evidence-graded claims |

---

## Numbers you can defend

Verified 2026-08-09. If asked to back any of these up, you can.

| Claim | Where it comes from |
|---|---|
| 483 tests | Full suite run, `pytest engine/tests` |
| 10-year / 2,520-session VRP lookback | `config.VRP_DEEP_LOOKBACK_SESSIONS` |
| Cold start 40-60s to 5-7s | Measured before/after; one tab body was 31.4s of a 42.3s load |
| Unattended daily pipeline | `.github/workflows/daily-report.yml`, 12 consecutive green scheduled runs |
| Null result, p = 0.74 | Forward-return test on the VRP tilt; feature deleted, not shipped |
| Free data, no vendor feed | CBOE delayed quotes and vol-index CSVs, yfinance, FRED |
| CBOE history depth | VIX to 1990; VXN and RVX to 2009 |

**One caveat to keep straight:** the chain-derived metrics (skew, surface, gamma) only
accrue from this project's own daily snapshots since ~2026-05, and mature toward ~2027.
The decade of depth applies to the VRP percentile, which rides CBOE's own vol-index
history. Say it that way — an informed interviewer will ask, and the precise answer is
much stronger than a vague one.
