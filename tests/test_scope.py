"""Scope boundary + form-logic tests — the track's hard constraints, encoded."""

import pytest

from calculator.funnel import Step
from calculator.scope import (
    Coverage, Insured, Tariff, Route, route, is_conversion,
    ONLINE_TARIFFS, ADVISORY_TARIFFS, ADDON_IS_INSCOPE,
    validate_step, FORM_FIELDS, _valid_sv_number,
)


# ── helper: build a checksum-valid Austrian SV number ─────────────────────────
def _make_valid_sv(serial="123", ddmmyy="010180"):
    weights = [3, 7, 9, 0, 5, 8, 4, 2, 1, 6]
    base = [int(c) for c in serial] + [0] + [int(c) for c in ddmmyy]
    total = sum(di * wi for di, wi in zip(base, weights))
    check = total % 11
    assert check != 10, "pick a different ddmmyy"
    base[3] = check
    return "".join(str(x) for x in base)


# ─── Routing / scope boundary ─────────────────────────────────────────────────

def test_in_scope_path():
    d = route(Coverage.DOCTOR_VISITS, Insured.SELF, Tariff.OPTIMAL)
    assert d.route is Route.IN_SCOPE and d.in_scope


@pytest.mark.parametrize("cov,ins,tar,why", [
    (Coverage.HOSPITAL,      Insured.SELF,   Tariff.START,    "hospital"),
    (Coverage.DOCTOR_VISITS, Insured.OTHERS, Tariff.START,    "other persons"),
    (Coverage.DOCTOR_VISITS, Insured.SELF,   Tariff.PREMIUM,  "premium"),
    (Coverage.DOCTOR_VISITS, Insured.SELF,   Tariff.OPT_PLUS, "opt_plus"),
])
def test_out_of_scope_routes_to_advisor(cov, ins, tar, why):
    d = route(cov, ins, tar)
    assert d.route is Route.ADVISOR_HANDOFF
    assert why in d.reason


def test_conversion_only_for_online_tariffs_on_inscope_path():
    assert is_conversion(Coverage.DOCTOR_VISITS, Insured.SELF, Tariff.START)
    assert is_conversion(Coverage.DOCTOR_VISITS, Insured.SELF, Tariff.OPTIMAL)
    # advisory tariff is never a conversion, even on the doctor path
    assert not is_conversion(Coverage.DOCTOR_VISITS, Insured.SELF, Tariff.PREMIUM)
    # hospital is never a conversion
    assert not is_conversion(Coverage.HOSPITAL, Insured.SELF, Tariff.START)


def test_tariff_partitions_are_disjoint_and_complete():
    assert ONLINE_TARIFFS | ADVISORY_TARIFFS == set(Tariff)
    assert ONLINE_TARIFFS & ADVISORY_TARIFFS == set()


def test_addon_step_flagged_out_of_scope():
    # Documents finding F1: add-on selection is the hospital path, not Privatarzt.
    assert ADDON_IS_INSCOPE is False


# ─── Form logic / field validation ───────────────────────────────────────────

def test_personal_info_requires_dob_and_sv():
    names = {f.name for f in FORM_FIELDS[Step.PERSONAL_INFO]}
    assert names == {"date_of_birth", "sv_number"}


def test_validate_step_missing_fields():
    r = validate_step(Step.PERSONAL_INFO, {})
    assert not r.ok
    assert set(r.missing) == {"date_of_birth", "sv_number"}


def test_validate_step_invalid_then_valid():
    bad = validate_step(Step.PERSONAL_INFO, {"date_of_birth": "1980-13-40", "sv_number": "abc"})
    # dob regex is structural (passes 1980-13-40) but sv must be 10 digits
    assert "sv_number" in bad.invalid

    sv = _make_valid_sv()
    good = validate_step(Step.PERSONAL_INFO, {"date_of_birth": "1980-01-01", "sv_number": sv})
    assert good.ok, good


def test_sv_checksum():
    sv = _make_valid_sv(serial="123", ddmmyy="010180")
    assert _valid_sv_number(sv)
    # corrupt the check digit → must fail
    wrong = list(sv)
    wrong[3] = str((int(wrong[3]) + 1) % 10)
    assert not _valid_sv_number("".join(wrong))
    # wrong length
    assert not _valid_sv_number("12345")
    assert not _valid_sv_number("")


def test_final_step_requires_contact_and_health():
    names = {f.name for f in FORM_FIELDS[Step.PERSONAL_DATA]}
    assert {"email", "sv_number", "health_answers"} <= names
    r = validate_step(Step.PERSONAL_DATA, {
        "first_name": "Franz", "last_name": "Huber",
        "email": "franz@example.at", "sv_number": _make_valid_sv(),
        "health_answers": "no conditions",
    })
    assert r.ok, r
    r2 = validate_step(Step.PERSONAL_DATA, {"first_name": "Franz", "email": "bad-email"})
    assert not r2.ok and "email" in r2.invalid
