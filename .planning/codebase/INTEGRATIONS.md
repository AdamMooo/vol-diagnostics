# External Integrations

**Analysis Date:** 2026-05-06

## APIs & External Services

**Options Chain Data:**
- CBOE Delayed Quotes API — 15-minute delayed options chains for US equity/ETF
  - Endpoint: `https://cdn.cboe.com/api/global/delayed_quotes/options/{ticker}.json`
  - Auth: None (public endpoint, no API key)
  - Client: raw `requests.get` in `gex/data_loader.py`
  - Returns: spot price, IV30, price change %, full chain with OPRA symbols

**Historical Price Data:**
- yfinance (Yahoo Finance) — used only in `gex/validation.py` for `event_study()`
  - Called as: `yf.download(ticker, start=..., end=..., auto_adjust=True, progress=False)`
  - Auth: None
  - Not called in the live daily pipeline; only for offline event study analysis

**Macroeconomic Data (parked — v2.1 sleeve engine):**
- FRED via pandas-datareader — `local_data.py` (`FreeCon` class)
  - Auth: None for public series

## Data Storage

**Databases:**
- None. All persistence is flat files.

**File Storage:**
- Local filesystem only
- Snapshot store: `out/gex_snapshots.parquet` — append-only parquet via pyarrow
  - Written by `gex/validation.py:save_snapshot()`
  - Read by `gex/validation.py:load_yesterday()`, `load_history()`
  - Columns: `date, ticker, spot, net_gex, gamma_regime, zero_gamma_level, call_wall, put_wall, vanna_exposure`
- Report output: `out/gex_YYYYMMDD.html` (dry-run) or `out/sleeve_report_YYYYMMDD.html` (v2.1)
- Chart output: `out/gex_strikes_{TICKER}_{DATE}.png`, `out/gex_profile_{TICKER}_{DATE}.png` (single-ticker run)

**Caching:**
- Streamlit in-memory cache via `@st.cache_data(ttl=300)` on `fetch_ticker()` in `streamlit_app.py`
- Historical data cached with `@st.cache_data(ttl=1800)` on `_load_history_cached()`
- No persistent external cache

## Authentication & Identity

**Dashboard Auth:**
- Streamlit password gate in `streamlit_app.py:_check_password()`
- Password stored in `.streamlit/secrets.toml` under key `PASSWORD`
- Session state: `st.session_state.authenticated` flag

**Email:**
- No auth managed in code — delegates entirely to logged-in Outlook client via COM
- Recipients loaded from `.env` → `GEX_EMAIL_TO`

## Monitoring & Observability

**Error Tracking:**
- None (no Sentry, Datadog, etc.)

**Logs:**
- `print()` statements to stdout throughout pipeline
- `process_ticker()` in `gex/run_daily.py` catches all exceptions and continues — errors logged to stdout only

## CI/CD & Deployment

**Hosting:**
- Local Windows machine (primary)
- Streamlit Community Cloud — devcontainer config suggests Codespaces deployment is possible

**CI Pipeline:**
- None

**Scheduled Execution:**
- Windows Task Scheduler — `runners/gex_daily.ps1` registers task "GEX Daily Report"
- Trigger: daily at 16:30 (no market-day guard in scheduler; `is_trading_day()` check inside script)
- Executable: `.venv/Scripts/python.exe -m gex.run_daily`

## Email Delivery

**Mechanism:**
- `gex/emailer.py` — `win32com.client` COM automation against local Outlook
- Tries `GetActiveObject` first (Outlook already running), falls back to `Dispatch` with 3s sleep
- No SMTP, no API key, no third-party mail service

**Template:**
- HTML built in `gex/report.py:build_email()` — inline CSS tables, no external assets
- Two sections: Index tickers (SPY/QQQ/IWM/XLF/GLD/TLT), Purpose Yield Shares (NVDA/TSLA/AAPL/etc.)

## Webhooks & Callbacks

**Incoming:** None

**Outgoing:** None

## Environment Configuration

**Required environment variables:**
- `GEX_EMAIL_TO` — comma-separated email recipients (in `.env` at project root)

**Secrets location:**
- `.env` — email recipients (loaded by `gex/emailer.py` via python-dotenv)
- `.streamlit/secrets.toml` — dashboard password (`PASSWORD` key); in `.gitignore`

---

*Integration audit: 2026-05-06*

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
<!-- LINKS:END -->
