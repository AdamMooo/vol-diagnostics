"""Behavioral tests for engine/report/card_model.py — CardField + build_card_fields()."""
from __future__ import annotations

import math
import pytest

from engine.report.card_model import (
    CardField,
    CardRead,
    build_card_fields,
    build_card_read,
    compact_primary_fields,
    split_compact_fields,
)
from engine import config


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FULL_SUMMARY = {
    "spot": 530.0,
    "price_change_pct": 0.8,
    "iv30": 18.5,
    "expected_move_pct": 2.1,
    "em_expiry": "2026-06-27",
    "em_dte": 5,
    "zero_gamma_level": 525.0,
    "net_gex": 1.20e9,
    "delta_hedge_flow": 2_500_000.0,
    "front_skew": 3.8,
    "butterfly": 0.8,
    "butterfly_pct": 74,
    "butterfly_pct_n": 252,
    "vrp": 2.7,
    "call_wall": 545.0,
    "put_wall": 515.0,
    "oi_call_wall": 550.0,
    "oi_put_wall": 510.0,
    "rv20": 15.8,
}

PRIOR_SUMMARY = {
    "spot": 525.0,
    "price_change_pct": -0.2,
    "iv30": 18.0,
    "zero_gamma_level": 520.0,
    "net_gex": 1.05e9,
    "delta_hedge_flow": 2_200_000.0,
    "front_skew": 3.0,
    "vrp": 2.3,
    "call_wall": 540.0,
    "put_wall": 510.0,
    "oi_call_wall": 545.0,
    "oi_put_wall": 505.0,
    "rv20": 15.0,
}

EXPECTED_LABELS = [
    "Spot",
    "Day %",
    "IV30 / EM",
    "γ-flip",
    "vs γ-flip",
    "Net GEX",
    "Hedge Shares/$1",
    "Skew (25Δ)",
    "25Δ Fly",
    "VRP",
    "Call Wall (model)",
    "Put Wall (model)",
    "Range",
    "OI Call Wall (raw OI)",
    "OI Put Wall (raw OI)",
]


# ---------------------------------------------------------------------------
# CardField dataclass
# ---------------------------------------------------------------------------

class TestCardField:
    def test_has_label_value_sign(self):
        f = CardField(label="Spot", value="530.00", sign="neutral")
        assert f.label == "Spot"
        assert f.value == "530.00"
        assert f.sign == "neutral"

    def test_sign_values(self):
        for s in ("positive", "negative", "neutral"):
            CardField(label="x", value="y", sign=s)


# ---------------------------------------------------------------------------
# No-prior branch: no delta suffixes, no crashes
# ---------------------------------------------------------------------------

class TestBuildCardFieldsNoPrior:
    def setup_method(self):
        self.fields = build_card_fields(FULL_SUMMARY, None)
        self.by_label = {f.label: f for f in self.fields}

    def test_returns_list_of_card_fields(self):
        assert isinstance(self.fields, list)
        assert all(isinstance(f, CardField) for f in self.fields)

    def test_field_count(self):
        assert len(self.fields) == len(EXPECTED_LABELS)

    def test_field_order(self):
        labels = [f.label for f in self.fields]
        assert labels == EXPECTED_LABELS

    def test_iv30_no_delta_suffix(self):
        v = self.by_label["IV30 / EM"].value
        assert "(+" not in v and "(-" not in v

    def test_iv30_em_contains_expiry_and_dte(self):
        v = self.by_label["IV30 / EM"].value
        assert "±2.1% by Jun 27 (5d)" in v

    def test_net_gex_no_delta_suffix(self):
        v = self.by_label["Net GEX"].value
        assert "(" not in v

    def test_front_skew_no_delta_suffix(self):
        v = self.by_label["Skew (25Δ)"].value
        assert "(" not in v

    def test_front_skew_states_direction(self):
        # FULL_SUMMARY front_skew=3.8 (positive) -> puts richer than calls
        v = self.by_label["Skew (25Δ)"].value
        assert "puts pricier" in v

    def test_fly_full_lookback_format(self):
        v = self.by_label["25Δ Fly"].value
        assert v == "+0.8pp · 74th %ile"

    def test_range_has_no_arrow_style_cues(self):
        v = self.by_label["Range"].value
        assert "→" not in v and "←" not in v

    def test_vrp_formatted_value(self):
        v = self.by_label["VRP"].value
        assert "pp" in v
        assert "2.7" in v

    def test_call_wall_label_contains_model(self):
        assert "model" in self.by_label["Call Wall (model)"].label

    def test_put_wall_label_contains_model(self):
        assert "model" in self.by_label["Put Wall (model)"].label

    def test_oi_call_wall_label_contains_raw_oi(self):
        assert "raw OI" in self.by_label["OI Call Wall (raw OI)"].label

    def test_oi_put_wall_label_contains_raw_oi(self):
        assert "raw OI" in self.by_label["OI Put Wall (raw OI)"].label


# ---------------------------------------------------------------------------
# With-prior branch: delta suffixes appear on net_gex, front_skew, iv30
# ---------------------------------------------------------------------------

class TestBuildCardFieldsWithPrior:
    def setup_method(self):
        self.fields = build_card_fields(FULL_SUMMARY, PRIOR_SUMMARY)
        self.by_label = {f.label: f for f in self.fields}

    def test_net_gex_delta_positive(self):
        v = self.by_label["Net GEX"].value
        # delta = 1.20B - 1.05B = +0.15B
        assert "(+" in v
        assert "0.15" in v

    def test_front_skew_delta_positive(self):
        v = self.by_label["Skew (25Δ)"].value
        # delta = 3.8 - 3.0 = +0.8
        assert "(+0.8)" in v

    def test_iv30_delta_positive(self):
        v = self.by_label["IV30 / EM"].value
        # delta = 18.5 - 18.0 = +0.5
        assert "(+0.5)" in v

    def test_field_order_unchanged_with_prior(self):
        labels = [f.label for f in self.fields]
        assert labels == EXPECTED_LABELS


# ---------------------------------------------------------------------------
# NaN / absent prior values — delta omitted, no fabricated zero
# ---------------------------------------------------------------------------

class TestDeltaSuffixNaNGuard:
    def test_iv30_nan_prior_no_delta(self):
        prior = dict(PRIOR_SUMMARY)
        prior["iv30"] = float("nan")
        fields = build_card_fields(FULL_SUMMARY, prior)
        iv30_field = next(f for f in fields if f.label == "IV30 / EM")
        assert "(+" not in iv30_field.value
        assert "(-" not in iv30_field.value

    def test_iv30_missing_key_prior_no_delta(self):
        prior = {k: v for k, v in PRIOR_SUMMARY.items() if k != "iv30"}
        fields = build_card_fields(FULL_SUMMARY, prior)
        iv30_field = next(f for f in fields if f.label == "IV30 / EM")
        assert "(+" not in iv30_field.value

    def test_no_fabricated_zero_delta(self):
        prior = dict(PRIOR_SUMMARY)
        prior["iv30"] = None
        fields = build_card_fields(FULL_SUMMARY, prior)
        iv30_field = next(f for f in fields if f.label == "IV30 / EM")
        assert "(+0.0)" not in iv30_field.value
        assert "(+" not in iv30_field.value


# ---------------------------------------------------------------------------
# Sign hints
# ---------------------------------------------------------------------------

class TestVRPCardField:
    def test_vrp_only_scalar_no_percentile(self):
        # FULL_SUMMARY has vrp but no vrp_pct -> scalar only, no percentile suffix
        fields = build_card_fields(FULL_SUMMARY, None)
        v = next(f for f in fields if f.label == "VRP").value
        assert "+2.7pp" in v
        assert "%ile" not in v

    def test_vrp_full_lookback_label(self):
        s = dict(FULL_SUMMARY)
        s["vrp_pct"] = 74
        s["vrp_pct_n"] = config.VRP_DEEP_LOOKBACK_SESSIONS
        v = next(f for f in build_card_fields(s, None) if f.label == "VRP").value
        assert "+2.7pp" in v
        assert "74th %ile" in v
        assert f"{config.VRP_DEEP_LOOKBACK_SESSIONS}-session (~10yr) lookback" in v
        assert "building to" not in v

    def test_vrp_cold_start_label(self):
        s = dict(FULL_SUMMARY)
        s["vrp_pct"] = 74
        s["vrp_pct_n"] = 120
        v = next(f for f in build_card_fields(s, None) if f.label == "VRP").value
        assert "74th %ile" in v
        assert "120 sessions" in v
        assert f"building to {config.VRP_DEEP_LOOKBACK_SESSIONS}" in v

    def test_vrp_insufficient_history_fallback(self):
        s = dict(FULL_SUMMARY)
        s["vrp"] = None
        s["vrp_pct"] = None
        s["vrp_pct_n"] = 0
        f = next(f for f in build_card_fields(s, None) if f.label == "VRP")
        assert "insufficient history" in f.value
        assert "nan" not in f.value.lower()

    def test_vrp_pct_none_with_scalar_fallback(self):
        s = dict(FULL_SUMMARY)
        s["vrp"] = 2.7
        s["vrp_pct"] = None
        s["vrp_pct_n"] = 0
        f = next(f for f in build_card_fields(s, None) if f.label == "VRP")
        assert "insufficient history" in f.value
        assert "nan" not in f.value.lower()

    def test_vrp_sign_positive(self):
        f = next(f for f in build_card_fields(FULL_SUMMARY, None) if f.label == "VRP")
        assert f.sign == "positive"

    def test_vrp_sign_negative(self):
        s = dict(FULL_SUMMARY)
        s["vrp"] = -1.5
        f = next(f for f in build_card_fields(s, None) if f.label == "VRP")
        assert f.sign == "negative"


class TestSkewDirectionWording:
    def test_positive_skew_says_puts_pricier(self):
        s = dict(FULL_SUMMARY, front_skew=3.8)
        v = next(f for f in build_card_fields(s, None) if f.label == "Skew (25Δ)").value
        assert "puts pricier" in v

    def test_negative_skew_says_calls_pricier(self):
        s = dict(FULL_SUMMARY, front_skew=-1.2)
        v = next(f for f in build_card_fields(s, None) if f.label == "Skew (25Δ)").value
        assert "calls pricier" in v

    def test_zero_skew_says_flat(self):
        s = dict(FULL_SUMMARY, front_skew=0.0)
        v = next(f for f in build_card_fields(s, None) if f.label == "Skew (25Δ)").value
        assert "flat" in v


class TestCardFieldSigns:
    def test_day_pct_positive_sign(self):
        fields = build_card_fields(FULL_SUMMARY, None)
        day_field = next(f for f in fields if f.label == "Day %")
        assert day_field.sign == "positive"

    def test_day_pct_negative_sign(self):
        summary = dict(FULL_SUMMARY)
        summary["price_change_pct"] = -0.5
        fields = build_card_fields(summary, None)
        day_field = next(f for f in fields if f.label == "Day %")
        assert day_field.sign == "negative"

    def test_net_gex_positive_sign(self):
        fields = build_card_fields(FULL_SUMMARY, None)
        f = next(x for x in fields if x.label == "Net GEX")
        assert f.sign == "positive"

    def test_net_gex_negative_sign(self):
        summary = dict(FULL_SUMMARY)
        summary["net_gex"] = -0.5e9
        fields = build_card_fields(summary, None)
        f = next(x for x in fields if x.label == "Net GEX")
        assert f.sign == "negative"

    def test_spot_neutral(self):
        fields = build_card_fields(FULL_SUMMARY, None)
        f = next(x for x in fields if x.label == "Spot")
        assert f.sign == "neutral"


# ---------------------------------------------------------------------------
# build_card_read — the "so what" + credibility gating
# ---------------------------------------------------------------------------

_DEEP = config.CARD_READ_MIN_SESSIONS + 200   # clears the floor (e.g. 252)
_THIN = config.CARD_READ_MIN_SESSIONS - 40    # below the floor (e.g. 20)


def _chip_texts(read: CardRead) -> list[str]:
    return [t for t, _ in read.chips]


class TestCardReadVRPGating:
    def test_deep_vrp_shows_premium_chip(self):
        s = {"vrp": 2.7, "vrp_pct": 82, "vrp_pct_n": _DEEP, "net_gex": 1e9}
        r = build_card_read(s)
        assert "premium rich" in _chip_texts(r)
        assert "rich" in r.lean.lower()

    def test_deep_cheap(self):
        s = {"vrp": -2.0, "vrp_pct": 5, "vrp_pct_n": _DEEP, "net_gex": 1e9}
        r = build_card_read(s)
        assert "premium cheap" in _chip_texts(r)
        assert "cheap" in r.lean.lower()

    def test_thin_vrp_hides_premium_chip(self):
        s = {"vrp": 2.7, "vrp_pct": 82, "vrp_pct_n": _THIN, "net_gex": 1e9}
        r = build_card_read(s)
        assert not any("premium" in t for t in _chip_texts(r))
        assert "building" in r.lean.lower()

    def test_missing_vrp_pct_hides_premium(self):
        s = {"vrp": 2.7, "vrp_pct": None, "vrp_pct_n": _DEEP, "net_gex": 1e9}
        r = build_card_read(s)
        assert not any("premium" in t for t in _chip_texts(r))


class TestCardReadOtherChips:
    BASE = {"vrp": 2.7, "vrp_pct": 50, "vrp_pct_n": _DEEP, "net_gex": 1e9}

    def test_net_gex_sign_always_shown(self):
        assert "dealers stabilizing" in _chip_texts(build_card_read(self.BASE))
        neg = dict(self.BASE, net_gex=-1e9)
        assert "dealers amplifying" in _chip_texts(build_card_read(neg))

    def test_skew_chip_only_when_passed(self):
        # not passed -> no skew chip (caller gates on sample size)
        assert not any("skew" in t for t in _chip_texts(build_card_read(self.BASE)))
        steep = build_card_read(self.BASE, skew_pct=80)
        assert "skew steep" in _chip_texts(steep)
        flat = build_card_read(self.BASE, skew_pct=10)
        assert "skew flat" in _chip_texts(flat)

    def test_move_chip_bands(self):
        assert "vol lifting (5d)" in _chip_texts(build_card_read(self.BASE, move_5d=0.9))
        assert "vol easing (5d)" in _chip_texts(build_card_read(self.BASE, move_5d=-0.9))
        assert "vol steady (5d)" in _chip_texts(build_card_read(self.BASE, move_5d=0.0))

    def test_rich_and_steep_lean_favors_calls(self):
        s = dict(self.BASE, vrp_pct=85)
        r = build_card_read(s, skew_pct=80)
        assert "call writing" in r.lean.lower()

    def test_chips_are_text_sign_tuples(self):
        r = build_card_read(self.BASE)
        assert all(isinstance(t, str) and sgn in ("positive", "negative", "neutral")
                   for t, sgn in r.chips)


class TestFlyCardField:
    def test_fly_cold_start_label(self):
        s = dict(FULL_SUMMARY)
        s["butterfly_pct"] = 74
        s["butterfly_pct_n"] = 42
        v = next(f for f in build_card_fields(s, None) if f.label == "25Δ Fly").value
        assert v == "+0.8pp · 74th %ile · 42 sessions (building to 252)"

    def test_fly_below_minimum_hides_percentile(self):
        s = dict(FULL_SUMMARY)
        s["butterfly_pct"] = None
        s["butterfly_pct_n"] = config.BUTTERFLY_PERCENTILE_MIN_SESSIONS - 1
        v = next(f for f in build_card_fields(s, None) if f.label == "25Δ Fly").value
        assert v == "+0.8pp"

    def test_fly_missing_scalar_fallback(self):
        s = dict(FULL_SUMMARY)
        s["butterfly"] = None
        v = next(f for f in build_card_fields(s, None) if f.label == "25Δ Fly").value
        assert v == "—"


class TestExpectedMoveFallback:
    def test_em_missing_fields_shows_dash(self):
        s = dict(FULL_SUMMARY)
        s["expected_move_pct"] = None
        s["em_expiry"] = None
        s["em_dte"] = None
        v = next(f for f in build_card_fields(s, None) if f.label == "IV30 / EM").value
        assert v.endswith("· —")

class TestCompactCardContract:
    def test_compact_primary_fields_exact_five(self):
        labels = [f.label for f in compact_primary_fields(build_card_fields(FULL_SUMMARY, None))]
        assert labels == [
            "Spot",
            "IV30 / EM",
            "VRP",
            "Skew (25Δ)",
            "25Δ Fly",
        ]

    def test_split_compact_fields_returns_primary_then_detail(self):
        primary, detail = split_compact_fields(build_card_fields(FULL_SUMMARY, None))
        assert len(primary) == 5
        assert len(primary) + len(detail) == len(EXPECTED_LABELS)


class TestTrustTagContract:
    def test_market_model_oi_smile_tags(self):
        by = {f.label: f for f in build_card_fields(FULL_SUMMARY, None)}
        assert by["Spot"].trust_tag == "market"
        assert by["Net GEX"].trust_tag == "model"
        assert by["OI Call Wall (raw OI)"].trust_tag == "oi"
        assert by["Skew (25Δ)"].trust_tag == "smile"

    def test_vrp_tag_building_when_sample_thin(self):
        s = dict(FULL_SUMMARY, vrp_pct=70, vrp_pct_n=80)
        f = next(x for x in build_card_fields(s, None) if x.label == "VRP")
        assert f.trust_tag == "building"

    def test_vrp_tag_history_when_lookback_met(self):
        s = dict(FULL_SUMMARY, vrp_pct=70, vrp_pct_n=config.VRP_DEEP_LOOKBACK_SESSIONS)
        f = next(x for x in build_card_fields(s, None) if x.label == "VRP")
        assert f.trust_tag == "history"
