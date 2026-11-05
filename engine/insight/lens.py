"""
Assemble the Risk Lens read — one JSON-able dict, schema `vol-risk-lens-v1`.

This dict is the product. The email renders it, the CLI prints it, and
`out/insight/risk_lens.json` exports it for portfolio-manager to adopt one-way (Option A:
facts + base rates flow down; nothing here moves a mandate weight). The vol-managed
exposure scalar is deliberately NOT in this dict — it is a market-timing rule, so it is
dashboard context only (decided 2026-11-03); the dashboard computes it from `state`.
"""
from __future__ import annotations

import datetime
import json
import pathlib

import numpy as np
import pandas as pd

from engine import config
from engine.insight import base_rates as br
from engine.insight import events as ev
from engine.insight.panel import STORE_DIR, known_by, latest_asof

SCHEMA = "vol-risk-lens-v1"
LENS_JSON = STORE_DIR / "risk_lens.json"
LENS_HISTORY = STORE_DIR / "lens_history.parquet"
GEX_STORE = pathlib.Path(__file__).resolve().parents[2] / "out" / "gex_snapshots.parquet"

CAVEATS = [
    "Historical base rates, not forecasts. 'Effective N' counts non-overlapping 21-session "
    "windows — the real number of independent observations behind each figure.",
    "Every cell is re-estimated on the early and late half of history; 'unstable' means the "
    "halves disagree and the figure should be read as weak.",
    "Drawdown = worst SPX close vs. today's close over the next 21 sessions.",
    "Calm-state drawdown odds are a floor, not a point: in the point-in-time replay the "
    "lowest bucket predicted ~4% and ~9% happened. Figures under 10% are shown as 'at least'.",
]


def _num(x) -> float | None:
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return x if np.isfinite(x) else None


def _state(row: pd.Series) -> dict:
    term = _num(row.get("term"))
    tc = br.term_cell(term)
    lc = br.level_cell(_num(row.get("vix_pct")))
    return {
        "spx": _num(row.get("spx")),
        "vix": _num(row.get("VIX")),
        "vix_pct": _num(row.get("vix_pct")),
        "vix_level_cell": br.LEVEL_LABELS[lc] if lc is not None else None,
        "vix3m": _num(row.get("VIX3M")),
        "term_ratio": term,
        "term_shape": br.TERM_LABELS[tc] if tc is not None else None,
        "rv20": _num(row.get("rv20")),
        "vrp": _num(row.get("vrp")),
        "vvix": _num(row.get("VVIX")),
        "vix_chg5": _num(row.get("vix_chg5")),
        "qqq_vxn_pct": _num(row.get("vxn_pct")),
        "iwm_rvx_pct": _num(row.get("rvx_pct")),
        "forecast_vol": _num(row.get("forecast_vol")),
    }


def _tier2_gamma(asof: pd.Timestamp) -> dict | None:
    """Dealer gamma — shown, never scored (only ~6 months of chain history; no base rate)."""
    try:
        g = pd.read_parquet(GEX_STORE, columns=["date", "ticker", "net_gex", "spot", "zero_gamma_level"])
    except Exception:
        return None
    g["date"] = pd.to_datetime(g["date"])
    g = g[(g["ticker"] == "SPY") & (g["date"] <= asof)].sort_values("date")
    if g.empty:
        return None
    last = g.iloc[-1]
    stale = (asof - last["date"]).days > 5
    return {
        "asof": str(last["date"].date()),
        "net_gex_bn": _num(last["net_gex"] / 1e9),
        "dealers": "long gamma (dampening)" if last["net_gex"] > 0 else "short gamma (amplifying)",
        "spot_vs_zero_gamma": _num(last["spot"] / last["zero_gamma_level"] - 1) if last["zero_gamma_level"] else None,
        "stale": bool(stale),
        "note": "Descriptive only — chain history too short for a base rate.",
    }


FLOOR_BELOW = 0.10


def dd_odds(p: float | None) -> str:
    """Drawdown odds as text. Below 10% the replay under-predicts (~4% predicted, ~9%
    realized), so low figures are stated as a floor."""
    if p is None:
        return "—"
    return f"at least {p:.0%}" if p < FLOOR_BELOW else f"{p:.0%}"


def _ideas(state: dict, primary: dict, uncond: dict) -> list[dict]:
    """A menu, not a recommendation: each idea states the historical numbers behind it
    in this state so the reader can disagree with the framing. No idea may recommend
    changing equity exposure — that is a timing rule, outside this lens's remit."""
    out: list[dict] = []
    pdd, bdd = primary.get("p_dd5"), uncond.get("p_dd5")
    cw, edge = primary.get("carry_win"), primary.get("carry_edge_med")
    if cw is not None and edge is not None:
        tail = primary.get("p_dd10") or 0
        rich = edge > (uncond.get("carry_edge_med") or 0)
        out.append({
            "topic": "Selling premium (covered calls / cash-secured puts)",
            "read": (f"In this state, 1-month implied exceeded the vol actually delivered "
                     f"{cw:.0%} of the time (median margin {edge:+.1f} vol pts"
                     f"{', richer than usual' if rich else ''}); "
                     f"{tail:.0%} of windows still saw a >10% drawdown."),
            "evidence": "Carry is usually there; the question is whether the tail is affordable.",
        })
    vpct = state.get("vix_pct")
    if vpct is not None:
        cheap = vpct <= 0.25 and (state.get("term_shape") == "contango")
        out.append({
            "topic": "Protection (puts / collars)",
            "read": ("Protection is historically cheap here (low VIX, steep contango) — the "
                     "lowest-cost time to own convexity, though drawdowns are also rarest."
                     if cheap else
                     f"Protection is priced off a VIX in its {state.get('vix_level_cell')}; "
                     f"next-month drawdown odds here are {dd_odds(pdd)} vs {bdd:.0%} normally."
                     if pdd is not None and bdd is not None else "—"),
            "evidence": ("When vol is already high, puts already price the fear — weigh the "
                         "drawdown odds above against what the protection costs."),
        })
    return out


def build_lens(panel: pd.DataFrame, asof: pd.Timestamp | None = None,
               since: pd.Timestamp | None = None, all_events: pd.DataFrame | None = None,
               reps: int | None = None) -> dict:
    """Read as of `asof` (default: latest session with SPX+VIX). Events dated in
    (since, asof] are reported — so a run that skipped days still reports what it missed."""
    asof = pd.Timestamp(asof) if asof is not None else latest_asof(panel)
    if asof is None:
        raise ValueError("panel has no session with both SPX and VIX")
    asof = panel.index[panel.index.searchsorted(asof, side="right") - 1]
    row = panel.loc[asof]
    hist = known_by(panel, asof)
    state = _state(row)

    cond = br.conditional_read(hist, row, reps=reps)
    rates = {k: v.to_dict() for k, v in cond.items() if isinstance(v, br.CellStats)}
    primary_key = cond["primary"]

    all_events = ev.detect_events(panel.loc[:asof]) if all_events is None else all_events
    lo = pd.Timestamp(since) if since is not None else asof - pd.Timedelta(days=1)
    todays = all_events[(all_events["date"] > lo) & (all_events["date"] <= asof)]
    study = ev.event_study(panel, all_events[all_events["date"] <= hist.index[-1]] if len(hist) else all_events.iloc[0:0], hist)
    past = all_events[all_events["date"] <= hist.index[-1]] if len(hist) else all_events.iloc[0:0]
    grades = ev.evidence_by_event(ev.event_significance(past, hist)) if len(todays) else {}
    events_out = []
    for _, e in todays.iterrows():
        s = study[(study["key"] == e["key"]) & (study["kind"] == e["kind"])]
        hist_d = s.iloc[0].to_dict() if not s.empty else None
        if hist_d:
            hist_d = {k: (_num(v) if not isinstance(v, str) else v) for k, v in hist_d.items()}
            ratio = (hist_d["p_dd5"] or 0) / max(hist_d["base_p_dd5"] or 1e-9, 1e-9)
            after = ("above-normal" if ratio > 1.3 else "below-normal" if ratio < 0.75 else "near-normal")
        else:
            after = None
        defn = ev.EVENT_BY_KEY.get(e["key"])
        events_out.append({
            "date": str(e["date"].date()), "key": e["key"], "kind": e["kind"],
            "title": e["title"], "direction": e["lean"],
            "historically_followed_by": f"{after} drawdown risk" if after else None,
            "history": hist_d,
            "evidence": grades.get(f"{e['key']}:{e['kind']}"),
            "learn": defn.learn if defn else "",
        })

    return {
        "schema": SCHEMA,
        "asof": str(asof.date()),
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "horizon_sessions": config.RISK_LENS_HORIZON,
        "state": state,
        "base_rates": {"primary": primary_key, "cells": rates},
        "events": events_out,
        "recent_events": [
            {"date": str(r["date"].date()), "key": r["key"], "kind": r["kind"], "title": r["title"]}
            for _, r in all_events[(all_events["date"] > asof - pd.Timedelta(days=90))
                                   & (all_events["date"] <= asof)].iterrows()
        ],
        "ideas": _ideas(state, rates.get(primary_key, {}), rates.get("unconditional", {})),
        "tier2_gamma": _tier2_gamma(asof),
        "caveats": CAVEATS,
    }


def save_lens(lens: dict) -> None:
    """Latest read → risk_lens.json (the portfolio-manager handoff); one flat row per
    as-of date → lens_history.parquet, the point-in-time record a future validation of
    the lens itself will need (idempotent per date)."""
    from engine.data.store import atomic_to_parquet
    from engine.insight.exposure import exposure_weight

    STORE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = LENS_JSON.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(lens, indent=2, default=str), encoding="utf-8")
    tmp.replace(LENS_JSON)

    p = lens["base_rates"]["cells"].get(lens["base_rates"]["primary"], {})
    flat = {"asof": lens["asof"], **{f"state_{k}": v for k, v in lens["state"].items()},
            "primary_cell": p.get("label"), "primary_eff_n": p.get("eff_n"),
            "primary_fwd_rv_med": p.get("fwd_rv_med"), "primary_p_dd5": p.get("p_dd5"),
            # internal research record only — never exported in risk_lens.json
            "exposure_weight": exposure_weight(lens["state"].get("forecast_vol")),
            "events": ",".join(f"{e['key']}:{e['kind']}" for e in lens["events"])}
    new = pd.DataFrame([flat])
    if LENS_HISTORY.exists():
        old = pd.read_parquet(LENS_HISTORY)
        new = pd.concat([old[old["asof"] != lens["asof"]], new], ignore_index=True).sort_values("asof")
    atomic_to_parquet(new, LENS_HISTORY)
