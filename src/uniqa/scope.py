"""
UNIQA Coach — Scope boundary + form logic (single source of truth).

The track defines a HARD scope boundary. The Coach only operates on the path a
user can complete online themselves:

  IN SCOPE  ✅                          OUT OF SCOPE ❌ (clean advisor handoff)
  ─────────────────────────────────    ───────────────────────────────────────
  Coverage "Bei Arztbesuchen"           Coverage "Im Krankenhaus" (hospital)
  Insured  "Ich selbst"                 Insured  "Andere Personen"
  Tariffs  Start, Optimal (online)      Tariffs  Opt. Plus, Premium (advisory)
  Conversion = ONLINE purchase          Advisor handoff is NOT a conversion

This module encodes:
  1. The scope registries + a `route()` decision (in-scope vs advisor handoff).
  2. The funnel FORM LOGIC for the in-scope online Privatarzt path — required
     fields per step + field validators (DOB, Austrian SV number).
  3. Field-level validation so the simulation/coach never violate the boundary.

⚠️ SCOPE NOTE — add-on step (see docs/HARDENING_PLAN.md, finding F1):
  The official funnel doc marks "Step 5 — Add-on coverage selection (24% drop)"
  as the HOSPITAL path → OUT OF SCOPE. The in-scope Privatarzt path does NOT
  include that add-on screen; its real flow is:
      coverage → insured → personal(DOB+SV) → tariff(66%) → health Qs → final price(78%)
  Our `Step.ADDON_SELECT` is retained for calibration continuity but is flagged
  as `ADDON_IS_INSCOPE = False`. Treat the S5 ~24% anchor as provisional.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from uniqa.funnel import Step


# ─── Scope registries ─────────────────────────────────────────────────────────

class Coverage(Enum):
    DOCTOR_VISITS = "bei_arztbesuchen"   # Privatarzt — IN SCOPE
    HOSPITAL      = "im_krankenhaus"     # OUT OF SCOPE


class Insured(Enum):
    SELF   = "ich_selbst"        # IN SCOPE
    OTHERS = "andere_personen"   # OUT OF SCOPE


class Tariff(Enum):
    START   = "start"      # online — conversion target ✅
    OPTIMAL = "optimal"    # online — conversion target ✅
    OPT_PLUS = "opt_plus"  # advisory only ❌
    PREMIUM  = "premium"   # advisory only ❌


IN_SCOPE_COVERAGE = {Coverage.DOCTOR_VISITS}
IN_SCOPE_INSURED  = {Insured.SELF}
ONLINE_TARIFFS    = {Tariff.START, Tariff.OPTIMAL}      # conversion targets
ADVISORY_TARIFFS  = {Tariff.OPT_PLUS, Tariff.PREMIUM}   # out-of-scope handoff

# Official monthly premium (age ~27, ÖGK) — kept as a back-compat reference point.
TARIFF_PRICE_EUR = {
    Tariff.START:   38.74,
    Tariff.OPTIMAL: 68.14,
    Tariff.OPT_PLUS: 96.66,
    Tariff.PREMIUM: 140.15,
}

# Real age→monthly-premium curve (Chrome-CDP recon 2026, ÖGK, gender-neutral). Findings:
# price = f(age, tariff) ONLY — SV, gender and HEALTH answers do NOT change the online
# premium, and there is NO online price-jump after the health questionnaire (the binding
# premium is confirmed offline via underwriting). See research/findings/pricing_recon.md.
# Dense knots from the CDP sweep (ages 18–70, ÖGK 2026). NOTE the youth band: age 18 is
# ~half price, 21 jumps to the normal curve. Confirmed NO effect: SV, gender, health/BMI/smoker.
_AGE_KNOTS = [18, 21, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70]
_PREMIUM_CURVE = {
    Tariff.START:    [25.53, 35.42, 37.75, 39.91, 41.10, 42.24, 43.90, 45.97, 48.26, 50.77, 53.12, 55.01],
    Tariff.OPTIMAL:  [35.40, 62.34, 66.40, 70.29, 72.62, 74.82, 77.74, 81.10, 84.74, 88.81, 92.90, 96.30],
    Tariff.OPT_PLUS: [51.92, 88.29, 94.06, 100.06, 104.29, 108.55, 113.98, 119.27, 124.57, 130.85, 137.83, 143.58],
    Tariff.PREMIUM:  [75.29, 128.03, 136.39, 145.09, 151.23, 157.41, 165.27, 172.94, 180.63, 189.73, 199.86, 208.19],
}


def premium(tariff: Tariff, age: float) -> float:
    """Real online monthly premium = f(age, tariff), linearly interpolated on the recon
    curve. SV / gender / health answers do NOT affect it; final == provisional online."""
    ks, ys = _AGE_KNOTS, _PREMIUM_CURVE[tariff]
    if age <= ks[0]:
        return ys[0]
    if age >= ks[-1]:
        return ys[-1]
    for i in range(len(ks) - 1):
        if ks[i] <= age <= ks[i + 1]:
            f = (age - ks[i]) / (ks[i + 1] - ks[i])
            return round(ys[i] + f * (ys[i + 1] - ys[i]), 2)
    return ys[0]

# In-scope online steps (Privatarzt path). ADDON_SELECT flagged — see SCOPE NOTE.
ADDON_IS_INSCOPE = False
IN_SCOPE_STEPS = (
    Step.COVERAGE_TYPE, Step.INSURED, Step.PERSONAL_INFO,
    Step.TARIFF_SELECT, Step.PERSONAL_DATA, Step.PURCHASE,
)


# ─── Routing decision ─────────────────────────────────────────────────────────

class Route(Enum):
    IN_SCOPE        = "in_scope"          # coach may operate
    ADVISOR_HANDOFF = "advisor_handoff"   # clean exit, NOT a conversion


@dataclass
class RouteDecision:
    route:  Route
    reason: str

    @property
    def in_scope(self) -> bool:
        return self.route is Route.IN_SCOPE


def route(coverage: Coverage, insured: Insured, tariff: Tariff | None = None) -> RouteDecision:
    """
    Decide whether a (coverage, insured, tariff) combination is coachable online
    or must be handed off to an advisor. Order matches the funnel: coverage (S1),
    insured (S2), then tariff (S4).
    """
    if coverage not in IN_SCOPE_COVERAGE:
        return RouteDecision(Route.ADVISOR_HANDOFF, "hospital path → advisor (out of scope)")
    if insured not in IN_SCOPE_INSURED:
        return RouteDecision(Route.ADVISOR_HANDOFF, "other persons → advisor (out of scope)")
    if tariff is not None and tariff in ADVISORY_TARIFFS:
        return RouteDecision(Route.ADVISOR_HANDOFF, f"{tariff.value} requires consultation → advisor")
    return RouteDecision(Route.IN_SCOPE, "online-completable Privatarzt path")


def is_conversion(coverage: Coverage, insured: Insured, tariff: Tariff) -> bool:
    """Conversion = ONLINE purchase of Start/Optimal on the in-scope path."""
    return route(coverage, insured, tariff).in_scope and tariff in ONLINE_TARIFFS


# ─── Form logic: required fields + validators ─────────────────────────────────

@dataclass
class FieldSpec:
    name:      str
    required:  bool
    validator: str   # key into VALIDATORS


# Required fields per in-scope step. No step may be REMOVED (track rule) — the
# coach may only assist, never skip collection.
FORM_FIELDS: dict[Step, list[FieldSpec]] = {
    Step.COVERAGE_TYPE: [FieldSpec("coverage", True, "coverage")],
    Step.INSURED:       [FieldSpec("insured", True, "insured")],
    Step.PERSONAL_INFO: [
        FieldSpec("date_of_birth", True, "dob"),
        FieldSpec("sv_number",     True, "sv_number"),
    ],
    Step.TARIFF_SELECT: [FieldSpec("tariff", True, "tariff")],
    # S6 in our model conflates health questions + personal/contact data (both
    # required, in scope). Health answers must still be collected — coach assists only.
    Step.PERSONAL_DATA: [
        FieldSpec("first_name", True, "nonempty"),
        FieldSpec("last_name",  True, "nonempty"),
        FieldSpec("email",      True, "email"),
        FieldSpec("sv_number",  True, "sv_number"),
        FieldSpec("health_answers", True, "nonempty"),
    ],
}


# ── validators ────────────────────────────────────────────────────────────────

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_SV_RE    = re.compile(r"^\d{10}$")   # AT Sozialversicherungsnummer: 10 digits
_DOB_RE   = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _valid_sv_number(value: str) -> bool:
    """
    Austrian SV number: 4-digit running number + check digit + 6-digit DDMMYY.
    Structural check (10 digits) + the official weighted checksum.
    digits[0..2]=running, digits[3]=check, digits[4..9]=DDMMYY.
    """
    if not _SV_RE.match(value or ""):
        return False
    d = [int(c) for c in value]
    weights = [3, 7, 9, 0, 5, 8, 4, 2, 1, 6]  # check digit position weight = 0
    total = sum(di * wi for di, wi in zip(d, weights))
    check = total % 11
    if check == 10:   # invalid combination, never issued
        return False
    return check == d[3]


def _valid_coverage(v) -> bool:
    return _coerce(Coverage, v) is not None

def _valid_insured(v) -> bool:
    return _coerce(Insured, v) is not None

def _valid_tariff(v) -> bool:
    return _coerce(Tariff, v) is not None

def _coerce(enum_cls, v):
    if isinstance(v, enum_cls):
        return v
    try:
        return enum_cls(v)
    except (ValueError, TypeError):
        return None


VALIDATORS = {
    "nonempty": lambda v: bool(v) and str(v).strip() != "",
    "email":    lambda v: bool(_EMAIL_RE.match(v or "")),
    "dob":      lambda v: bool(_DOB_RE.match(v or "")),
    "sv_number": _valid_sv_number,
    "coverage": _valid_coverage,
    "insured":  _valid_insured,
    "tariff":   _valid_tariff,
}


@dataclass
class ValidationResult:
    ok:      bool
    missing: list[str]
    invalid: list[str]


def validate_step(step: Step, data: dict) -> ValidationResult:
    """Validate a step's submitted form data against its required-field spec."""
    missing: list[str] = []
    invalid: list[str] = []
    for spec in FORM_FIELDS.get(step, []):
        if spec.name not in data or data[spec.name] in (None, ""):
            if spec.required:
                missing.append(spec.name)
            continue
        if not VALIDATORS[spec.validator](data[spec.name]):
            invalid.append(spec.name)
    return ValidationResult(ok=not missing and not invalid, missing=missing, invalid=invalid)
