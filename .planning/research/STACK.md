# Stack Additions — GEX Interactive Dashboard v3.0

**Project:** options-quant / GEX module
**Researched:** 2026-05-05
**Scope:** NEW additions only. Existing stack (pandas, numpy, scipy, matplotlib, yfinance, pyarrow, pywin32, etc.) is validated — not re-researched.

---

## Version Table — New Additions

| Package | Pin | Purpose | Confidence |
|---------|-----|---------|------------|
| `streamlit` | `>=1.45,<2.0` | Dashboard framework | HIGH — 1.57.0 is current stable (2026-04-28) |
| `plotly` | `>=6.0,<7.0` | Interactive charts in Streamlit | HIGH — 6.7.0 current; 6.x series is stable |

That's it. Two packages. No others are justified (see Rejections below).

---

## Streamlit

**Version to pin:** `>=1.45,<2.0`

Current release is 1.57.0 (2026-04-28). Requires Python >=3.10 — confirmed compatible with this venv. The `<2.0` ceiling is a safety guard; no 2.x is imminent but the API surface changes between majors.

**Why 1.45 as floor:** `st.plotly_chart` received `use_container_width` and fragment support in the 1.4x range. No hard dependency on a specific minor feature; floor keeps the install range wide enough that pip resolves cleanly.

**Companion packages — do NOT add:**
- `streamlit-extras` — brings 20+ components; we use none of them. Zero value, added transitive deps.
- `watchdog` — Streamlit installs it automatically as an optional dep when available. Do not pin it explicitly.
- `altair`, `vega-altair` — Streamlit bundles its own Altair copy. Explicit pin creates version conflict risk.

---

## Matplotlib in Streamlit — Backend and Thread Safety

**Backend:** Streamlit forces matplotlib onto the `Agg` (non-GUI) backend automatically when it starts. Do NOT set `backend: TkAgg` in `matplotlibrc` — this is only needed for local GUI windows, which Streamlit does not use. The Agg warning users see ("non-GUI backend, cannot show figure") is benign and only appears when `plt.show()` is called; we never call `plt.show()`.

**Figure lifecycle — required pattern:**
```python
fig, ax = plt.subplots()
ax.plot(...)
st.pyplot(fig)
plt.close(fig)   # MANDATORY — prevents memory accumulation across reruns
```

Never use `st.pyplot()` without an explicit figure argument. The global-figure overload is deprecated since ~1.20 and will be removed.

**Thread safety:** Streamlit runs each user session in a separate thread sharing the global matplotlib state. For a single-user local dashboard this is not a practical problem. If the app is ever deployed to Streamlit Cloud (multi-user), wrap figure creation with `threading.RLock()`. Flag this in the implementation phase but do not over-engineer it for a local tool.

**No new backend package needed.** matplotlib >=3.9 (already pinned) ships Agg in the base install.

---

## Second-Order Greeks — Vanna and Charm

**No new library required.** Both are pure closed-form expressions derivable from d1/d2 already computed in `greeks_engine.py`. The existing `scipy.stats.norm` import is sufficient.

**Exact formulas (from Wikipedia Greeks (finance), confirmed HIGH confidence):**

Vanna (∂Δ/∂σ = ∂Vega/∂S), no dividend (q=0):
```
vanna = -norm.pdf(d1) * (d2 / iv)
```
where `d1` and `d2` are the standard BS terms already in `greeks_engine.bs_gamma`.

Charm (∂Δ/∂τ, rate of delta decay), no dividend (q=0):
```
charm = -norm.pdf(d1) * (2*r*T - d2*iv*sqrt(T)) / (2*T*iv*sqrt(T))
```
Note: charm sign convention varies in the literature. The formula above is `dDelta/dT` (positive = delta grows with time). Some sources negate it to express as decay per day; pick one convention and document it in the code.

**Implementation path:** add `bs_vanna()` and `bs_charm()` alongside `bs_gamma()` in `gex/greeks_engine.py`, then extend `add_greeks()` to append `vanna` and `charm` columns. No new dependencies.

---

## Parquet / PyArrow

**No change.** `pyarrow>=15.0` (already pinned) handles everything needed:
- Schema evolution (adding vanna/charm columns to `gex_snapshots.parquet`) is handled by `read_table` with `schema=` or by pandas `merge` with fill.
- No extension libraries (`deltalake`, `fastparquet`, etc.) are warranted at this data volume.

The only implementation note: when appending new columns to existing snapshots, use `pd.concat` + `drop_duplicates(subset=["date","ticker"])` rather than a schema migration — simpler and idempotent.

---

## pywin32 Coexistence

**No concern for local use.** The pywin32 venv compatibility issue is specific to Windows Service installation (running the post-install script inside a venv). Outlook COM dispatch (`win32com.client.Dispatch("Outlook.Application")`) works correctly from within a venv — it is a pure Python import path operation. The existing `pywin32>=306` pin is fine; Streamlit running concurrently in the same venv does not interfere.

**Deployment caveat (not relevant to v3.0):** If this app were ever pushed to Streamlit Cloud (Linux), `pywin32` would fail to install. For local-only use, ignore. If Cloud deployment ever comes up, move Outlook dispatch to a Windows-only conditional import.

---

## Rejections

| Package | Reason |
|---------|--------|
| `plotly-express` | Bundled inside `plotly` since v5. Separate install is a no-op or version conflict. |
| `kaleido` | Static image export only. Not needed for interactive Streamlit charts. Heavy new-arch dep (requires Chrome). Add only if PNG export from plotly is explicitly requested. |
| `streamlit-extras` | No specific component from this library is needed. Avoid. |
| `bokeh` | Third charting library with no advantage over plotly here. |
| `dash` / `panel` | Dashboard frameworks — we already chose Streamlit. |
| `mibian` / `py_vollib` | Options Greeks libraries. All needed Greeks derive from existing scipy.stats.norm — no library justified. |
| `greeks-package` (PyPI) | Pulls in yfinance + plotly as hard deps — circular, heavier than writing two 3-line functions. |
| `flashalpha` | Commercial/research package for Greeks + GEX analytics. We implement this ourselves — that's the point of the project. |
| `numba` / `cython` | No performance case. Vectorised numpy over a 10-ticker chain is microseconds. |
| `fastparquet` | pyarrow already present and superior. Avoid dual Parquet backends. |
| `watchdog` | Streamlit manages this as optional dep. Explicit pin risks version conflict. |

---

## Updated requirements.txt Delta

Add to existing `requirements.txt`:

```
streamlit>=1.45,<2.0
plotly>=6.0,<7.0
```

No removals. No other changes.

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
<!-- LINKS:END -->
