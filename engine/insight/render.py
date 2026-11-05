"""
Render a Risk Lens read as an exception email (inline-styled HTML, phone-width safe)
or as terminal text. Pure functions of the lens dict.

Layout order is the reading order of someone with 30 seconds: what changed → what it
meant last time → where we are → what that implies → fine print.
"""
from __future__ import annotations

from html import escape

_RISE, _EASE, _INK, _MUTED, _RULE = "#b42318", "#067647", "#101828", "#667085", "#eaecf0"
_FONT = "font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif"


def _pct(x, digits: int = 0) -> str:
    return "—" if x is None else f"{x * 100:.{digits}f}%"


def _dd(x) -> str:
    """P(drawdown>5%) — below 10% the replay under-predicts, so show it as a floor."""
    return "—" if x is None else (f"≥{x * 100:.0f}%" if x < 0.10 else _pct(x))


def _v(x, fmt: str = "{:.1f}") -> str:
    return "—" if x is None else fmt.format(x)


def subject(lens: dict) -> str:
    evs = lens.get("events") or []
    if not evs:
        return f"Risk Lens — {lens['asof']} (no events)"
    lead = evs[0]["title"]
    more = f" (+{len(evs) - 1} more)" if len(evs) > 1 else ""
    return f"Risk Lens — {lead}{more}"


_GRADE = {"established": ("Well-established", "#067647"),
          "supported": ("Supported", "#b54708"),
          "suggestive": ("Suggestive only", "#667085")}


def _evidence_line(e: dict) -> str:
    from engine.insight.events import EVIDENCE_LABELS
    g = e.get("evidence")
    if g not in _GRADE:
        return ""
    name, color = _GRADE[g]
    return (f"<p style='margin:8px 0 0;font-size:13px'><span style='color:{color};font-weight:600'>"
            f"Evidence: {name}.</span> <span style='color:{_MUTED}'>This event's track record "
            f"{escape(EVIDENCE_LABELS[g])}.</span></p>")


def _event_block(e: dict) -> str:
    color = _RISE if e["direction"] == "risk rising" else _EASE
    h = e.get("history") or {}
    rows = ""
    if h:
        def row(label, val, base):
            return (f"<tr><td style='padding:3px 10px 3px 0;color:{_MUTED}'>{label}</td>"
                    f"<td style='padding:3px 10px 3px 0'><b>{val}</b></td>"
                    f"<td style='padding:3px 0;color:{_MUTED}'>{base}</td></tr>")
        rows = (
            f"<p style='margin:10px 0 4px;color:{_MUTED};font-size:13px'>The previous "
            f"{int(h['n'])} times (effective N {int(h['eff_n'])}), over the next month:</p>"
            "<table style='font-size:14px;border-collapse:collapse'>"
            + row("Median realized vol", _v(h.get("fwd_rv_med")), f"normal {_v(h.get('base_fwd_rv_med'))}")
            + row("P(drawdown &gt; 5%)", _dd(h.get("p_dd5")), f"normal {_pct(h.get('base_p_dd5'))}")
            + row("P(drawdown &gt; 10%)", _pct(h.get("p_dd10")), "")
            + row("Median SPX return", _pct(h.get("ret_med"), 1), "")
            + "</table>"
        )
    after = e.get("historically_followed_by")
    return (
        f"<div style='border-left:4px solid {color};padding:8px 0 8px 14px;margin:0 0 18px'>"
        f"<div style='font-size:12px;color:{color};text-transform:uppercase;letter-spacing:.04em'>"
        f"{escape(e['direction'])}{' · historically ' + escape(after) if after else ''}</div>"
        f"<div style='font-size:17px;font-weight:600;margin:2px 0 0'>{escape(e['title'])}</div>"
        f"{rows}"
        f"{_evidence_line(e)}"
        f"<p style='margin:10px 0 0;font-size:13px;line-height:1.5;background:#f9fafb;"
        f"padding:8px 10px;border-radius:6px'><b>Why it matters.</b> {escape(e['learn'])}</p>"
        "</div>"
    )


def _state_strip(s: dict, g: dict | None) -> str:
    items = [
        ("VIX", f"{_v(s.get('vix'))} <span style='color:{_MUTED}'>({_pct(s.get('vix_pct'))} pct)</span>"),
        ("Curve 1m/3m", f"{_v(s.get('term_ratio'), '{:.2f}')} <span style='color:{_MUTED}'>{escape(s.get('term_shape') or '—')}</span>"),
        ("Implied − realized", f"{_v(s.get('vrp'), '{:+.1f}')} pts"),
        ("Realized 20d", _v(s.get("rv20"))),
        ("VVIX", _v(s.get("vvix"), "{:.0f}")),
        ("QQQ / IWM vol pct", f"{_pct(s.get('qqq_vxn_pct'))} / {_pct(s.get('iwm_rvx_pct'))}"),
    ]
    if g:
        items.append(("SPY dealer gamma", f"{escape(g['dealers'])}"
                      f"{' (stale)' if g.get('stale') else ''}"))
    cells = "".join(
        f"<tr><td style='padding:3px 12px 3px 0;color:{_MUTED}'>{k}</td><td style='padding:3px 0'>{v}</td></tr>"
        for k, v in items)
    return f"<table style='font-size:14px;border-collapse:collapse'>{cells}</table>"


def _rates_table(br: dict) -> str:
    order = ["unconditional", "level", "level_term", "level_vrp"]
    cells = br["cells"]
    head = "".join(f"<th style='text-align:left;padding:4px 8px 4px 0;font-weight:500;color:{_MUTED}'>{h}</th>"
                   for h in ("State", "Eff N", "Fwd vol (10–90%)", "P(dd&gt;5%) [90% CI]", "P(dd&gt;10%)", "Carry won", "OOS"))
    body = ""
    for k in order:
        c = cells.get(k)
        if not c:
            continue
        prim = k == br["primary"]
        ci = c.get("p_dd5_ci") or [None, None]
        oos = "—" if c.get("stable") is None else ("stable" if c["stable"] else "unstable")
        style = "font-weight:600;background:#f2f4f7" if prim else ""
        thin = "" if c.get("credible") or k == "unconditional" else f" <span style='color:{_MUTED}'>(thin)</span>"
        body += (
            f"<tr style='{style}'>"
            f"<td style='padding:4px 8px 4px 0'>{escape(c['label'])}{thin}</td>"
            f"<td style='padding:4px 8px 4px 0'>{c['eff_n']}</td>"
            f"<td style='padding:4px 8px 4px 0'>{_v(c.get('fwd_rv_med'))} ({_v(c.get('fwd_rv_p10'), '{:.0f}')}–{_v(c.get('fwd_rv_p90'), '{:.0f}')})</td>"
            f"<td style='padding:4px 8px 4px 0'>{_dd(c.get('p_dd5'))} [{_pct(ci[0])}–{_pct(ci[1])}]</td>"
            f"<td style='padding:4px 8px 4px 0'>{_pct(c.get('p_dd10'))}</td>"
            f"<td style='padding:4px 8px 4px 0'>{_pct(c.get('carry_win'))}</td>"
            f"<td style='padding:4px 0'>{oos}</td></tr>")
    return (f"<div style='overflow-x:auto'><table style='font-size:13px;border-collapse:collapse;min-width:520px'>"
            f"<tr>{head}</tr>{body}</table></div>")


def _h2(t: str) -> str:
    return (f"<h2 style='font-size:13px;text-transform:uppercase;letter-spacing:.05em;color:{_MUTED};"
            f"margin:26px 0 10px;padding-top:14px;border-top:1px solid {_RULE}'>{t}</h2>")


def to_html(lens: dict) -> str:
    evs = lens.get("events") or []
    ev_html = "".join(_event_block(e) for e in evs) or \
        f"<p style='color:{_MUTED}'>No events today — this is a manual/preview render.</p>"
    ideas = "".join(
        f"<div style='margin:0 0 12px'><b>{escape(i['topic'])}.</b> {escape(i['read'])}"
        f"<div style='color:{_MUTED};font-size:13px;margin-top:2px'>{escape(i['evidence'])}</div></div>"
        for i in lens.get("ideas", []))
    caveats = "".join(f"<li style='margin:0 0 4px'>{escape(c)}</li>" for c in lens.get("caveats", []))
    return (
        f"<div style='{_FONT};color:{_INK};max-width:640px;margin:0 auto;padding:16px;font-size:15px'>"
        f"<div style='font-size:12px;color:{_MUTED}'>RISK LENS · SPX vol complex · as of {lens['asof']}</div>"
        f"<h1 style='font-size:21px;margin:4px 0 18px'>{len(evs)} change{'s' if len(evs) != 1 else ''} worth knowing about</h1>"
        f"{ev_html}"
        f"{_h2('Where we are')}{_state_strip(lens['state'], lens.get('tier2_gamma'))}"
        f"{_h2('What usually happens next from here (21 sessions)')}{_rates_table(lens['base_rates'])}"
        f"<p style='font-size:12px;color:{_MUTED};margin:6px 0 0'>Bold row = the most specific state with enough "
        f"independent history. More conditions = closer analogs but fewer of them; that's the trade-off. "
        f"≥ marks calm-state odds, which history shows are a floor, not a point.</p>"
        f"{_h2('What it implies')}{ideas}"
        f"{_h2('Fine print')}<ul style='font-size:12px;color:{_MUTED};padding-left:18px;margin:0'>{caveats}</ul>"
        "</div>")


def to_text(lens: dict) -> str:
    s, br = lens["state"], lens["base_rates"]
    lines = [f"RISK LENS  as of {lens['asof']}", ""]
    lines.append(f"  VIX {_v(s['vix'])} ({_pct(s['vix_pct'])} pct, {s['vix_level_cell']})  "
                 f"curve {_v(s['term_ratio'], '{:.2f}')} {s['term_shape'] or ''}  "
                 f"IV-RV {_v(s['vrp'], '{:+.1f}')}  RV20 {_v(s['rv20'])}  VVIX {_v(s['vvix'], '{:.0f}')}")
    lines += ["", "  EVENTS" if lens["events"] else "  No events — no email would be sent."]
    for e in lens["events"]:
        h = e.get("history") or {}
        grade = f"  (evidence: {e['evidence']})" if e.get("evidence") else ""
        lines.append(f"   [{e['direction']}] {e['date']} {e['title']}{grade}")
        if h:
            lines.append(f"      prior {int(h['n'])}x (effN {int(h['eff_n'])}): fwd vol {_v(h['fwd_rv_med'])} "
                         f"vs {_v(h['base_fwd_rv_med'])}, P(dd>5%) {_dd(h['p_dd5'])} vs {_pct(h['base_p_dd5'])}")
    lines += ["", "  NEXT 21 SESSIONS, HISTORICALLY"]
    for k in ("unconditional", "level", "level_term", "level_vrp"):
        c = br["cells"].get(k)
        if not c:
            continue
        mark = "*" if k == br["primary"] else " "
        lines.append(f"  {mark} {c['label'][:58]:58s} effN {c['eff_n']:4d}  vol {_v(c['fwd_rv_med']):>5}  "
                     f"P(dd>5%) {_dd(c['p_dd5']):>4}  P(dd>10%) {_pct(c['p_dd10']):>4}  "
                     f"{'' if c.get('stable') is None else ('stable' if c['stable'] else 'UNSTABLE')}"
                     f"{'' if c.get('credible') or k == 'unconditional' else '  (thin)'}")
    lines += ["", "  IMPLICATIONS"]
    for i in lens["ideas"]:
        lines.append(f"   - {i['topic']}: {i['read']}")
    return "\n".join(lines)
