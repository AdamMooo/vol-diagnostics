"""Risk Lens — synthetic-data tests. No network, no out/ stores."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from engine import config
from engine.insight import base_rates as br
from engine.insight import events as ev
from engine.insight import render
from engine.insight.exposure import backtest, exposure_weight, weight_series
from engine.insight.lens import SCHEMA, build_lens
from engine.insight.panel import build_panel, known_by, latest_asof

H = config.RISK_LENS_HORIZON


def _synthetic(n: int = 3000, seed: int = 0) -> tuple[pd.Series, dict]:
    """Regime-switching vol so high-VIX periods genuinely precede high realized vol."""
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2000-01-03", periods=n)
    regime = (np.sin(np.arange(n) / 120) > 0.6).astype(float)
    daily_vol = np.where(regime == 1, 0.025, 0.007)
    spx = pd.Series(1000 * np.exp(np.cumsum(rng.normal(0, daily_vol))), index=idx)
    vix = pd.Series(np.where(regime == 1, 38.0, 13.0) + rng.normal(0, 1, n), index=idx)
    vix3m = vix * np.where(regime == 1, 0.9, 1.15)
    return spx, {"VIX": vix, "VIX3M": pd.Series(vix3m, index=idx)}


@pytest.fixture(scope="module")
def panel():
    spx, vols = _synthetic()
    return build_panel(spx, vols)


# ── panel ──────────────────────────────────────────────────────────────────

def test_forward_outcomes_are_nan_where_window_unfinished(panel):
    assert panel["fwd_rv"].iloc[-H:].isna().all()
    assert panel["fwd_rv"].iloc[-H - 1:-H].notna().all()


def test_fwd_mdd_is_never_positive(panel):
    assert (panel["fwd_mdd"].dropna() <= 0).all()


def test_known_by_excludes_windows_still_open(panel):
    asof = panel.index[2000]
    hist = known_by(panel, asof)
    assert hist.index[-1] == panel.index[2000 - H]
    # every row's forward window ended on or before asof
    assert panel.index.get_loc(hist.index[-1]) + H <= panel.index.get_loc(asof)


def test_vol_indices_are_not_forward_filled():
    spx, vols = _synthetic(800)
    vols["VIX"] = vols["VIX"].drop(vols["VIX"].index[500])
    p = build_panel(spx, vols)
    assert np.isnan(p["VIX"].iloc[500])


def test_latest_asof_requires_vix(panel):
    p = panel.copy()
    p.loc[p.index[-1], "VIX"] = np.nan
    assert latest_asof(p) == p.index[-2]


# ── base rates ─────────────────────────────────────────────────────────────

def test_level_cell_edges_match_right_closed_bins():
    assert br.level_cell(0.2) == 0
    assert br.level_cell(0.21) == 1
    assert br.level_cell(0.95) == 4
    assert br.level_cell(0.96) == 5
    assert br.level_cell(1.0) == 5
    assert br.level_cell(float("nan")) is None


def test_term_cell():
    assert br.term_cell(0.85) == 0
    assert br.term_cell(0.97) == 1
    assert br.term_cell(1.0) == 2
    assert br.term_cell(None) is None


def test_effective_n_counts_non_overlapping_windows():
    idx = pd.bdate_range("2020-01-01", periods=200)
    # 63 consecutive days with a 21-day horizon → 3 independent windows, not 63
    assert br.effective_n(idx[:63], idx, 21) == 3
    assert br.effective_n(idx[::21], idx, 21) == len(idx[::21])
    assert br.effective_n(idx[:0], idx, 21) == 0


def test_block_bootstrap_ci_brackets_the_mean():
    x = (np.random.default_rng(1).random(500) < 0.3).astype(float)
    lo, hi = br.block_bootstrap_ci(x, 21, 300)
    assert lo < x.mean() < hi
    assert 0 <= lo and hi <= 1


def test_high_vol_cell_shows_more_forward_risk(panel):
    hist = known_by(panel, panel.index[-1])
    hi = br.conditional_read(hist, panel.dropna(subset=["vix_pct"]).loc[panel["VIX"] > 30].iloc[-1], reps=20)
    lo = br.conditional_read(hist, panel.dropna(subset=["vix_pct"]).loc[panel["VIX"] < 15].iloc[-1], reps=20)
    assert hi["level"].fwd_rv_med > 2 * lo["level"].fwd_rv_med


def test_primary_falls_back_when_specific_cell_is_thin(panel, monkeypatch):
    monkeypatch.setattr(config, "RISK_LENS_MIN_EFF_N", 10**6)
    hist = known_by(panel, panel.index[-1])
    r = br.conditional_read(hist, panel.dropna(subset=["vix_pct"]).iloc[-1], reps=5)
    assert r["primary"] == "unconditional"


def test_cell_stats_to_dict_is_json_safe(panel):
    hist = known_by(panel, panel.index[-1])
    cs = br.cell_stats(hist, hist["VIX"] > 1000, "empty")
    json.dumps(cs.to_dict())
    assert cs.n == 0 and cs.eff_n == 0 and not cs.credible


# ── exposure ───────────────────────────────────────────────────────────────

def test_exposure_weight_caps_and_scales():
    assert exposure_weight(7.5, target=15, cap=1.0) == 1.0          # never levers up
    assert exposure_weight(30, target=15, cap=1.0) == pytest.approx(0.5)
    assert exposure_weight(None) is None and exposure_weight(0) is None


def test_weight_series_has_no_lookahead(panel):
    w = weight_series(panel)
    raw = (config.RISK_LENS_TARGET_VOL / panel["forecast_vol"]).clip(upper=config.RISK_LENS_MAX_WEIGHT)
    # the first session after a Friday close uses that Friday's weight
    fri = [d for d in panel.index[300:400] if d.weekday() == 4][0]
    nxt = panel.index[panel.index.get_loc(fri) + 1]
    assert w.loc[nxt] == pytest.approx(raw.loc[fri])


def test_backtest_vol_managed_cuts_vol(panel):
    bt = backtest(panel, start="2001-01-01")
    full = bt["periods"]["full"]
    assert full["vol_managed"]["vol"] < full["buy_hold"]["vol"]
    assert set(bt["periods"]) == {"full", "early", "late"}


# ── events ─────────────────────────────────────────────────────────────────

def _feat(**cols) -> pd.DataFrame:
    n = len(next(iter(cols.values())))
    idx = pd.bdate_range("2021-01-04", periods=n)
    base = {"VIX": [20.0] * n, "vix_pct": [0.5] * n, "term": [0.9] * n, "vrp": [3.0] * n,
            "vix_chg1": [0.0] * n, "vix_chg5": [0.0] * n, "forecast_vol": [15.0] * n}
    base.update(cols)
    return pd.DataFrame(base, index=idx)


def test_hysteresis_no_flicker_between_thresholds():
    # 0.81 enters, 0.70 is between exit (0.65) and entry (0.80): must stay in, no re-fire
    f = _feat(vix_pct=[0.5, 0.81, 0.70, 0.82, 0.70, 0.60, 0.81])
    e = ev.detect_events(f)
    e = e[e["key"] == "vol_elevated"]
    assert list(e["kind"]) == ["enter", "exit", "enter"]


def test_curve_inversion_enter_and_exit():
    f = _feat(term=[0.9, 1.02, 0.97, 0.94])
    e = ev.detect_events(f)
    e = e[e["key"] == "curve_inverted"]
    assert list(e["kind"]) == ["enter", "exit"]
    assert e.iloc[1]["date"] == f.index[3]


def test_high_vrp_alone_never_fires_carry_flip():
    # The regime_alert scar: rich implied vs realized is calm, not stress.
    f = _feat(vrp=[15.0] * 10, vix_pct=[0.9] * 10)
    assert "carry_flip" not in set(ev.detect_events(f)["key"])
    f2 = _feat(vrp=[3.0, -3.0], vix_pct=[0.6, 0.6])
    assert "carry_flip" in set(ev.detect_events(f2)["key"])


def test_carry_flip_requires_elevated_tape():
    f = _feat(vrp=[3.0, -3.0], vix_pct=[0.3, 0.3])
    assert "carry_flip" not in set(ev.detect_events(f)["key"])


def test_vol_shock_refractory():
    f = _feat(vix_chg1=[0, 0.25, 0.25, 0.25] + [0] * 10 + [0.25])
    e = ev.detect_events(f)
    shocks = e[e["key"] == "vol_shock"]
    assert len(shocks) == 2   # day 1, then not again until 10 sessions later


def test_exposure_moves_never_trigger_an_event():
    """The vol-managed scalar is dashboard context only — a big swing in it must not email."""
    f = _feat(forecast_vol=[15.0, 20.0, 21.0, 30.0, 60.0])
    assert ev.detect_events(f).empty
    assert "exposure_shift" not in ev.EVENT_BY_KEY


def test_events_are_single_series_family():
    """Every event definition reads SPX-complex fields only — no per-ticker votes."""
    f = _feat(vix_pct=[0.5, 0.99])
    f["vxn_pct"] = [0.99, 0.99]
    f["rvx_pct"] = [0.99, 0.99]
    keys = set(ev.detect_events(f)["key"])
    f2 = f.drop(columns=["vxn_pct", "rvx_pct"])
    assert keys == set(ev.detect_events(f2)["key"])


# ── lens + render ──────────────────────────────────────────────────────────

def test_build_lens_schema_and_json(panel):
    asof = panel.dropna(subset=["vix_pct"]).index[-1]
    lens = build_lens(panel, asof=asof, reps=10)
    assert lens["schema"] == SCHEMA
    assert lens["asof"] == str(asof.date())
    assert lens["base_rates"]["primary"] in lens["base_rates"]["cells"]
    assert "forecast_vol" in lens["state"]          # dashboard derives context from this
    json.dumps(lens, default=str)


def test_no_exposure_in_handoff_or_email(panel):
    asof = panel.dropna(subset=["vix_pct"]).index[-1]
    lens = build_lens(panel, asof=asof, reps=5)
    assert "exposure" not in lens                    # risk_lens.json carries no scalar
    assert not any("exposure" in i["topic"].lower() for i in lens["ideas"])
    assert not any("exposure" in c.lower() for c in lens["caveats"])
    blob = (render.to_html(lens) + render.to_text(lens)).lower()
    assert "exposure" not in blob and "of full" not in blob


def test_emailed_events_carry_an_evidence_grade(panel):
    all_ev = ev.detect_events(panel)
    target = all_ev.iloc[-1]["date"]
    lens = build_lens(panel, asof=target, all_events=all_ev, reps=5)
    assert lens["events"]
    for e in lens["events"]:
        assert e["evidence"] in (None, "established", "supported", "suggestive")


def test_evidence_grade_renders_in_email(panel):
    asof = panel.dropna(subset=["vix_pct"]).index[-1]
    lens = build_lens(panel, asof=asof, reps=5)
    base = {"date": lens["asof"], "key": "vol_elevated", "kind": "enter", "title": "t",
            "direction": "risk rising", "historically_followed_by": None, "history": None, "learn": "x"}
    lens["events"] = [{**base, "evidence": "suggestive"}]
    assert "Suggestive only" in render.to_html(lens)
    assert "(evidence: suggestive)" in render.to_text(lens)
    lens["events"] = [{**base, "evidence": "established"}]
    assert "Well-established" in render.to_html(lens)
    lens["events"] = [{**base, "evidence": None}]
    assert "Evidence:" not in render.to_html(lens)


def test_tldr_is_three_plain_lines(panel):
    asof = panel.dropna(subset=["vix_pct"]).index[-1]
    lens = build_lens(panel, asof=asof, reps=5)
    lines = render.tldr(lens)
    assert len(lines) == 3
    assert lines[0].startswith("VIX is ")
    assert "normally" in lines[1]
    assert lines[2] == "Nothing changed today, so no email was sent."
    lens["events"] = [{"title": "VIX spiked", "evidence": "suggestive", "key": "vol_shock",
                       "kind": "enter", "date": lens["asof"], "direction": "risk rising",
                       "history": None, "learn": ""}]
    assert render.tldr(lens)[2] == "Changed: VIX spiked. Evidence: suggestive only."
    assert "TL;DR" in render.to_html(lens) and "TL;DR" in render.to_text(lens)


def test_evidence_by_event_maps_corrections():
    sig = pd.DataFrame({"event": ["a:enter", "b:enter", "c:exit"],
                        "survives_holm": [True, False, False], "survives_bh": [True, True, False]})
    assert ev.evidence_by_event(sig) == {"a:enter": "established", "b:enter": "supported",
                                        "c:exit": "suggestive"}
    assert ev.evidence_by_event(pd.DataFrame()) == {}


def test_calm_state_odds_render_as_floor():
    from engine.insight.lens import dd_odds
    assert dd_odds(0.04) == "at least 4%"
    assert dd_odds(0.25) == "25%"
    assert render._dd(0.04) == "≥4%" and render._dd(0.37) == "37%"


def test_event_significance_corrections_are_monotone(panel):
    from engine.insight.backtest import event_significance
    hist = known_by(panel, panel.index[-1])
    sig = event_significance(ev.detect_events(panel), hist)
    assert len(sig)
    assert (sig["p_holm"] >= sig["p_value"] - 1e-12).all()
    assert (sig["p_bh"] >= sig["p_value"] - 1e-12).all()
    assert (sig["p_holm"] >= sig["p_bh"] - 1e-12).all()


def test_build_lens_reports_events_since_last_run(panel):
    all_ev = ev.detect_events(panel)
    target = all_ev.iloc[len(all_ev) // 2]["date"]
    asof = panel.index[panel.index.get_loc(target) + 3]
    since = panel.index[panel.index.get_loc(target) - 1]
    lens = build_lens(panel, asof=asof, since=since, all_events=all_ev, reps=5)
    assert any(e["date"] == str(target.date()) for e in lens["events"])
    # default window = only the as-of day
    lens2 = build_lens(panel, asof=asof, all_events=all_ev, reps=5)
    assert all(e["date"] == str(asof.date()) for e in lens2["events"])


def test_lens_event_history_uses_only_closed_windows(panel):
    all_ev = ev.detect_events(panel)
    first = all_ev.iloc[0]
    lens = build_lens(panel, asof=first["date"], all_events=all_ev, reps=5)
    for e in lens["events"]:
        # nothing fired before the first event → no history to cite
        assert e["history"] is None or e["history"]["n"] == 0 or e["key"] != first["key"]


def test_render_html_and_text(panel):
    asof = panel.dropna(subset=["vix_pct"]).index[-1]
    lens = build_lens(panel, asof=asof, reps=5)
    lens["events"] = [{"date": lens["asof"], "key": "vol_elevated", "kind": "enter",
                       "title": "VIX <test> & co", "direction": "risk rising",
                       "historically_followed_by": "above-normal drawdown risk",
                       "history": {"n": 10, "eff_n": 8, "fwd_rv_med": 20.0, "base_fwd_rv_med": 13.0,
                                   "p_dd5": 0.3, "base_p_dd5": 0.17, "p_dd10": 0.1, "ret_med": 0.01},
                       "learn": "why"}]
    html = render.to_html(lens)
    assert "VIX &lt;test&gt; &amp; co" in html          # escaped
    assert "effective N 8" in html
    assert render.subject(lens).startswith("Risk Lens — VIX <test>")
    assert "RISK LENS" in render.to_text(lens)


# ── run: send / silence / ledger ───────────────────────────────────────────

@pytest.fixture
def run_env(tmp_path, monkeypatch):
    from engine.insight import run as R
    from engine.report import emailer

    monkeypatch.setattr(R, "STORE_DIR", tmp_path)
    monkeypatch.setattr(R, "LEDGER", tmp_path / "sent.json")
    monkeypatch.setattr(R, "load_panel", lambda refresh=False: None)
    monkeypatch.setattr(R, "save_lens", lambda lens: None)
    state = {"events": [], "asof": "2026-11-02", "sent": [], "fail": False, "since": "unset"}

    def fake_build(panel, asof=None, since=None):
        state["since"] = since
        return {"asof": state["asof"], "events": state["events"], "state": {}, "base_rates": {},
                "ideas": [], "caveats": []}

    def fake_send(subject, html_body, attachments=None, **kw):
        if state["fail"]:
            raise RuntimeError("smtp down")
        state["sent"].append(subject)

    monkeypatch.setattr(R, "build_lens", fake_build)
    monkeypatch.setattr(R.render, "to_text", lambda lens: "")
    monkeypatch.setattr(R.render, "to_html", lambda lens: "<p/>")
    monkeypatch.setattr(emailer, "send", fake_send)
    return R, state


def _event():
    return [{"title": "x", "date": "2026-11-02", "key": "vol_elevated", "kind": "enter"}]


def test_run_silent_without_events_but_advances_ledger(run_env):
    R, s = run_env
    assert R.run(send=True, refresh=False) == 0
    assert s["sent"] == []
    assert json.loads(R.LEDGER.read_text())["last_asof"] == "2026-11-02"


def test_run_sends_once_per_asof(run_env):
    R, s = run_env
    s["events"] = _event()
    R.run(send=True, refresh=False)
    R.run(send=True, refresh=False)       # second workflow firing, same session
    assert len(s["sent"]) == 1


def test_run_passes_last_asof_as_since(run_env):
    R, s = run_env
    R.LEDGER.write_text(json.dumps({"last_asof": "2026-10-28"}))
    R.run(send=True, refresh=False)
    assert s["since"] == pd.Timestamp("2026-10-28")


def test_run_email_failure_keeps_ledger_for_retry(run_env):
    R, s = run_env
    s["events"], s["fail"] = _event(), True
    assert R.run(send=True, refresh=False) == 2
    assert not R.LEDGER.exists()
    s["fail"] = False
    R.run(send=True, refresh=False)
    assert len(s["sent"]) == 1


def test_run_without_send_never_emails(run_env):
    R, s = run_env
    s["events"] = _event()
    R.run(send=False, refresh=False)
    assert s["sent"] == [] and not R.LEDGER.exists()


# ── strategy payoffs ──────────────────────────────────────────────────────

from engine.insight import payoffs as pay  # noqa: E402


def test_price_satisfies_put_call_parity():
    s, k, sd = 100.0, 95.0, 0.05
    assert pay._price(s, k, sd, "call") - pay._price(s, k, sd, "put") == pytest.approx(s - k)


def test_flat_market_seller_keeps_premium_and_buyer_loses_it():
    spot, vol = np.array([100.0]), np.array([20.0])
    straddle = pay.structure_return(spot, vol, spot, "short_straddle", H)[0]
    # ATM straddle ≈ 0.8·σ√T of spot
    assert straddle == pytest.approx(0.8 * 0.20 * np.sqrt(H / 252), rel=0.01)
    assert pay.structure_return(spot, vol, spot, "long_put", H)[0] == pytest.approx(-1.0)


@pytest.mark.parametrize("key", ["short_put", "put_spread", "iron_condor", "long_put"])
def test_defined_risk_returns_never_exceed_capital(key):
    spot, vol = np.full(5, 100.0), np.full(5, 25.0)
    spot_T = np.array([0.0, 60.0, 100.0, 140.0, 400.0])
    r = pay.structure_return(spot, vol, spot_T, key, H)
    assert r.min() == pytest.approx(-1.0)  # capital is exactly the worst case


def test_crash_hits_put_spread_max_loss_and_pays_the_hedge():
    spot, vol, crash = np.array([100.0]), np.array([15.0]), np.array([70.0])
    assert pay.structure_return(spot, vol, crash, "put_spread", H)[0] == pytest.approx(-1.0)
    assert pay.structure_return(spot, vol, crash, "long_put", H)[0] > 10


def test_payoffs_are_nan_where_window_unfinished(panel):
    for key in pay.STRUCTURES:
        assert panel[f"pnl_{key}"].iloc[-H:].isna().all()
        assert panel[f"pnl_{key}"].iloc[:-H].notna().any()


def test_strategy_read_reports_ci_and_matches_base_rate_cells(panel):
    asof = latest_asof(panel)
    hist, row = known_by(panel, asof), panel.loc[asof]
    primary = br.conditional_read(hist, row, reps=50)["primary"]
    read = pay.strategy_read(hist, row, primary, reps=50)
    assert read["cell"] == primary and "unconditional" in read["cells"]
    for r in read["cells"][primary]["rows"]:
        lo, hi = r["mean_ci"]
        assert lo <= r["mean"] <= hi
        assert 0 <= r["win_rate"] <= 1
    json.dumps(read)


def test_sellers_earn_in_the_calm_regime_where_implied_beats_realized(panel):
    # synthetic calm regime: VIX 13 vs ~11 realized → short vol should pay on average
    hist = panel.dropna(subset=["fwd_rv"])
    calm = hist["VIX"] < 20
    stats = pay.strategy_stats(hist, calm, "calm", None, H, 50)
    assert next(r for r in stats["rows"] if r["key"] == "short_straddle")["mean"] > 0
