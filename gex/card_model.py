"""
Shared card-model layer for per-ticker GEX cards.

CardField + build_card_fields() are the single source of truth for field set,
values, formatting, and deltas. Both gex/report.py and app.py consume
this — neither duplicates the field list or format logic.

Formatting helpers moved here from gex/report.py so both renderers import them
from a common location.
"""
from __future__ import annotations

import math
import dataclasses
from typing import Any

import pandas as pd

from gex import config

# Re-export palette refs used by renderers
LABEL_GRAY = "#94a3b8"


# ── Formatting helpers (canonical — report.py imports from here) ──────────

def _fmt_b(val: float | None) -> str:
    if val is None:
        return "—"
    b = val / 1e9
    return f"{'+' if b >= 0 else ''}{b:.2f}B"


def _fmt_price(val: float | None, dp: int = 2) -> str:
    return f"{val:,.{dp}f}" if val is not None else "—"


def _fmt_pct(val: float | None, signed: bool = True, dp: int = 1) -> str:
    if val is None:
        return "—"
    sign = "+" if signed and val >= 0 else ""
    return f"{sign}{val:.{dp}f}%"


def _fmt_skew(val: float | None) -> str:
    if val is None:
        return "—"
    return f"{val:+.1f}pp"


def _fmt_hedge_shares(val: float | None) -> str:
    if val is None:
        return "—"
    v = abs(val)
    if v >= 1e6:
        return f"{v / 1e6:.1f}M sh/$1"
    elif v >= 1e3:
        return f"{v / 1e3:.0f}K sh/$1"
    return f"{v:.0f} sh/$1"


def _pct_from_spot(spot: float | None, level: float | None) -> float | None:
    if not spot or level is None:
        return None
    return (level - spot) / spot * 100


def _wall_value(level: float | None, pct_from_spot: float | None) -> str:
    """Format a wall as '740  +0.3%' (anchor strike, distance from spot)."""
    if level is None:
        return "—"
    parts = [f"{level:,.0f}"]
    if pct_from_spot is not None:
        parts.append(f" {_fmt_pct(pct_from_spot)}")
    return "".join(parts)


def _expected_1d_range_pct(iv30: float | None) -> float | None:
    """1-sigma 1-day expected move in % of spot, from IV30 (annualized vol in %)."""
    if not iv30:
        return None
    return iv30 / (252 ** 0.5)


def _pin_location(spot: float | None, pw: float | None, cw: float | None) -> str:
    """How close is spot to call wall vs put wall, as a percentage of the range."""
    if spot is None or pw is None or cw is None or cw <= pw:
        return "—"
    pct = (spot - pw) / (cw - pw) * 100
    pct = max(0.0, min(100.0, pct))
    direction = "→ CW" if pct >= 50 else "← PW"
    return f"{pct:.0f}% {direction}"


def _fmt_vrp(vrp: float | None, vrp_pct: int | None, vrp_pct_n: int | None) -> str:
    """VRP card value: scalar (vol points) + labeled percentile, with cold-start/fallback.

    Reads only precomputed values (no I/O). Cases:
      - vrp/pct present, n >= lookback: '+2.7pp - Nth %ile - <lookback>-session lookback'
      - cold-start (n < lookback):      '+2.7pp - Nth %ile - <n> sessions (building to <lookback>)'
      - vrp or pct None:                'insufficient history'
    Lookback comes from config.VRP_PERCENTILE_LOOKBACK, never hard-coded.
    """
    if vrp is None:
        return "insufficient history"
    lookback = config.VRP_PERCENTILE_LOOKBACK
    if vrp_pct is None:
        return f"{vrp:+.1f}pp · insufficient history"
    base = f"{vrp:+.1f}pp · {vrp_pct}th %ile"
    if vrp_pct_n is not None and vrp_pct_n < lookback:
        return f"{base} · {vrp_pct_n} sessions (building to {lookback})"
    return f"{base} · {lookback}-session lookback"


def _signed_color(val: float | None) -> str:
    if val is None or val == 0:
        return LABEL_GRAY
    return config.PALETTE["positive"] if val >= 0 else config.PALETTE["negative"]


# ── Internal helpers ──────────────────────────────────────────────────────

def _get_sign(val: float | None) -> str:
    if val is None or val == 0:
        return "neutral"
    return "positive" if val > 0 else "negative"


def _safe_prior(prior_summary: Any, key: str) -> float | None:
    """Extract a float from prior_summary (dict or pd.Series), returning None if absent/NaN."""
    if prior_summary is None:
        return None
    try:
        val = prior_summary.get(key) if hasattr(prior_summary, "get") else prior_summary[key]
    except (KeyError, IndexError):
        return None
    if val is None:
        return None
    try:
        f = float(val)
        return None if math.isnan(f) else f
    except (TypeError, ValueError):
        return None


def _delta_suffix_b(today_val: float | None, prior_val: float | None) -> str:
    """Delta suffix for B-unit values: ' (+0.15B)' or ''."""
    if today_val is None or prior_val is None:
        return ""
    d = today_val - prior_val
    sign = "+" if d >= 0 else ""
    return f" ({sign}{d / 1e9:.2f}B)"


def _delta_suffix_pp(today_val: float | None, prior_val: float | None) -> str:
    """Delta suffix for pp/scalar values: ' (+0.8)' or ''."""
    if today_val is None or prior_val is None:
        return ""
    d = today_val - prior_val
    return f" ({d:+.1f})"


# ── CardField ─────────────────────────────────────────────────────────────

@dataclasses.dataclass
class CardField:
    label: str
    value: str
    sign: str  # "positive" | "negative" | "neutral"


# ── build_card_fields ─────────────────────────────────────────────────────

def build_card_fields(
    today_summary: dict,
    prior_summary: dict | None,
    extras: dict | None = None,
) -> list[CardField]:
    """Return ordered list of CardField for one ticker's card.

    today_summary: summary sub-dict from compute_ticker.
    prior_summary: dict/pd.Series from load_prior_snapshot, or None.
    extras: reserved; ignored.
    """
    s = today_summary

    spot = s.get("spot")
    price_change_pct = s.get("price_change_pct")
    iv30 = s.get("iv30")
    zgl = s.get("zero_gamma_level")
    net_gex = s.get("net_gex")
    delta_hedge_flow = s.get("delta_hedge_flow")
    front_skew = s.get("front_skew")
    vrp = s.get("vrp")
    vrp_pct = s.get("vrp_pct")
    vrp_pct_n = s.get("vrp_pct_n")
    call_wall = s.get("call_wall")
    put_wall = s.get("put_wall")
    oi_call_wall = s.get("oi_call_wall")
    oi_put_wall = s.get("oi_put_wall")

    # Prior values (None when absent/NaN)
    p_iv30 = _safe_prior(prior_summary, "iv30")
    p_net_gex = _safe_prior(prior_summary, "net_gex")
    p_front_skew = _safe_prior(prior_summary, "front_skew")

    # Derived
    vs_zgl_pct = _pct_from_spot(spot, zgl)
    vs_zgl_spot = (-vs_zgl_pct) if vs_zgl_pct is not None else None

    iv30_str = f"{iv30:.1f}%" if iv30 else "—"
    iv30_delta = _delta_suffix_pp(iv30, p_iv30)
    expected_1d = _expected_1d_range_pct(iv30)
    expected_str = f"±{expected_1d:.2f}%" if expected_1d else "—"

    cw_pct = _pct_from_spot(spot, call_wall)
    pw_pct = _pct_from_spot(spot, put_wall)
    oi_cw_pct = _pct_from_spot(spot, oi_call_wall)
    oi_pw_pct = _pct_from_spot(spot, oi_put_wall)

    range_width_pct = (
        (call_wall - put_wall) / spot * 100
        if (call_wall is not None and put_wall is not None and spot)
        else None
    )

    fields = [
        CardField(
            label="Spot",
            value=_fmt_price(spot),
            sign="neutral",
        ),
        CardField(
            label="Day %",
            value=_fmt_pct(price_change_pct) if price_change_pct is not None else "—",
            sign=_get_sign(price_change_pct),
        ),
        CardField(
            label="IV30 / 1d σ",
            value=f"{iv30_str}{iv30_delta} · {expected_str}",
            sign="neutral",
        ),
        CardField(
            label="γ-flip",
            value=_fmt_price(zgl, dp=1) if zgl is not None else "—",
            sign="neutral",
        ),
        CardField(
            label="vs γ-flip",
            value=_fmt_pct(vs_zgl_spot) if vs_zgl_spot is not None else "—",
            sign=_get_sign(vs_zgl_spot),
        ),
        CardField(
            label="Net GEX",
            value=_fmt_b(net_gex) + _delta_suffix_b(net_gex, p_net_gex),
            sign=_get_sign(net_gex),
        ),
        CardField(
            label="Hedge Shares/$1",
            value=_fmt_hedge_shares(delta_hedge_flow),
            sign="neutral",
        ),
        CardField(
            label="Skew (25Δ)",
            value=_fmt_skew(front_skew) + _delta_suffix_pp(front_skew, p_front_skew),
            sign="neutral",
        ),
        CardField(
            label="VRP",
            value=_fmt_vrp(vrp, vrp_pct, vrp_pct_n),
            sign=_get_sign(vrp),
        ),
        CardField(
            label="Call Wall (model)",
            value=_wall_value(call_wall, cw_pct),
            sign="neutral",
        ),
        CardField(
            label="Put Wall (model)",
            value=_wall_value(put_wall, pw_pct),
            sign="neutral",
        ),
        CardField(
            label="Range",
            value=(
                f"{range_width_pct:.1f}% · {_pin_location(spot, put_wall, call_wall)}"
                if range_width_pct is not None else "—"
            ),
            sign="neutral",
        ),
        CardField(
            label="OI Call Wall (raw OI)",
            value=_wall_value(oi_call_wall, oi_cw_pct),
            sign="neutral",
        ),
        CardField(
            label="OI Put Wall (raw OI)",
            value=_wall_value(oi_put_wall, oi_pw_pct),
            sign="neutral",
        ),
    ]

    return fields


# ── Card read (the "so what") ─────────────────────────────────────────────

@dataclasses.dataclass
class CardRead:
    """A plain-English synthesis sitting on top of the card fields.

    chips: ordered (text, sign) state tags — each maps ONE number through a labeled
    band (no hidden score). lean: a soft, hedged write-decision read templated from
    VRP + skew. Stays inside the 'descriptive, no prescription' rule via 'favors'.
    """
    chips: list[tuple[str, str]]
    lean: str


def _lean_text(vrp_pct, skew_pct, vrp, vrp_pct_n) -> str:
    lookback = config.VRP_PERCENTILE_LOOKBACK
    if vrp_pct is None:
        if vrp is not None and vrp_pct_n:
            return (f"Percentile still building ({vrp_pct_n}/{lookback} sessions) — "
                    "read the VRP level, not the rank yet.")
        return "Not enough history yet for a premium read."
    rich, cheap = vrp_pct >= 67, vrp_pct <= 33
    steep = skew_pct is not None and skew_pct >= 67
    if cheap:
        base = "Premium's cheap — writing is poorly paid; owning protection is relatively attractive."
    elif rich and steep:
        base = "Protection's expensive and bid up front — favors writing calls; don't sell downside cheap here."
    elif rich:
        base = "Premium's rich — broad premium-selling is favored."
    else:
        base = "Premium's middling — no strong write edge today."
    if vrp_pct_n is not None and vrp_pct_n < lookback:
        base += f" (history thin — {vrp_pct_n} sessions)"
    return base


def build_card_read(
    today_summary: dict,
    *,
    skew_pct: int | None = None,
    move_5d: float | None = None,
) -> CardRead:
    """Synthesize the per-ticker read. I/O-free: callers pass skew_pct / move_5d.

    Each chip is a deterministic band on one metric — VRP percentile, skew percentile,
    5-day surface drift, net-GEX sign. Clauses with no data are simply omitted.
    """
    s = today_summary
    vrp, vrp_pct, vrp_pct_n = s.get("vrp"), s.get("vrp_pct"), s.get("vrp_pct_n")
    net_gex, front_skew = s.get("net_gex"), s.get("front_skew")

    chips: list[tuple[str, str]] = []
    if vrp_pct is not None:
        if vrp_pct >= 67:
            chips.append(("premium rich", "positive"))
        elif vrp_pct <= 33:
            chips.append(("premium cheap", "negative"))
        else:
            chips.append(("premium fair", "neutral"))

    if skew_pct is not None:
        if skew_pct >= 67:
            chips.append(("skew steep", "negative"))
        elif skew_pct <= 33:
            chips.append(("skew flat", "positive"))
        else:
            chips.append(("skew moderate", "neutral"))
    elif front_skew is not None:
        chips.append(("downside skew", "neutral"))

    if move_5d is not None:
        if move_5d > 0.3:
            chips.append(("vol lifting (5d)", "negative"))
        elif move_5d < -0.3:
            chips.append(("vol easing (5d)", "positive"))
        else:
            chips.append(("vol steady (5d)", "neutral"))

    if net_gex is not None:
        chips.append(("dealers stabilizing", "positive") if net_gex >= 0
                     else ("dealers amplifying", "negative"))

    return CardRead(chips=chips, lean=_lean_text(vrp_pct, skew_pct, vrp, vrp_pct_n))
