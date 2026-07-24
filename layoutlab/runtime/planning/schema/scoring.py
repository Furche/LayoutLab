"""DD-017 Evaluation — signed score components, veto, candidate state.

Evaluation v0.2 — calibrated soft→component map:
- preferred / informational ``zone_must_be_clear`` → object_usability (Stage B)
- required clearance errors stay Stage A (hard), not score components
- soft packing also nudges circulation
- light context weights for bed/desk/wardrobe access zones

Provisional numbers remain labeled; no preference/aesthetics engine.
"""

from __future__ import annotations

from typing import Any

SCORE_CATEGORIES = ("circulation", "accessibility", "comfort", "object_usability")

# Veto: any component with severity "severe" OR value <= threshold blocks
# default top recommendation (anti-compensation).
SEVERE_VETO_THRESHOLD = -50

# Optional soft cap on positive contribution per category when summing total.
POSITIVE_CAP_PER_CATEGORY = 40

# Calibrated DD-015 → component map (Evaluation v0.2).
_OPENING_ACCESS_VALUE = -40
_SOFT_PACKING_WARNING_VALUE = -15
_SOFT_PACKING_INFO_VALUE = -5
_SOFT_PACKING_CIRCULATION_WARN = -8
_SOFT_PACKING_CIRCULATION_INFO = -3
_PREFERRED_CLEARANCE_WARNING = -24
_PREFERRED_CLEARANCE_INFO = -8

# Hard / non-negotiable types — validity only, never score components.
_HARD_CONSTRAINT_TYPES = frozenset(
    {
        "solid_wall_penetration",
    }
)


def _empty_category_vector() -> dict[str, int]:
    return {cat: 0 for cat in SCORE_CATEGORIES}


def _finding_text_blob(finding: dict) -> str:
    cref = finding.get("clearance_ref") if isinstance(finding.get("clearance_ref"), dict) else {}
    parts = [
        finding.get("message"),
        finding.get("clearance_name"),
        finding.get("furniture_name"),
        cref.get("clearance_name"),
        cref.get("furniture_name"),
    ]
    return " ".join(str(p) for p in parts if p).lower()


def _context_multiplier(finding: dict) -> float:
    """Stage-C style nudge from clearance / furniture hints (Evaluation v0.2)."""
    blob = _finding_text_blob(finding)
    if "bed_entry" in blob or ("bed" in blob and "entry" in blob):
        return 1.5
    if "chair_access" in blob or ("desk" in blob and "chair" in blob):
        return 1.35
    if "front_access" in blob or "wardrobe" in blob:
        return 1.25
    return 1.0


def _scaled_penalty(base: int, finding: dict) -> int:
    """Apply context multiplier; keep signed integers, never flip sign."""
    raw = float(base) * _context_multiplier(finding)
    if raw >= 0:
        return int(round(raw))
    return -int(round(abs(raw)))


def soft_findings_to_components(
    analysis_or_soft_summary: Any = None,
    findings: list | None = None,
) -> list[dict]:
    """Map known soft / preferred findings into signed explainable components.

    Accepts either:
    - an analysis dict with ``findings`` / ``soft_summary``, or
    - a soft_summary dict, plus optional explicit ``findings``.
    Hard errors (solid wall; required clearance severity=error) are skipped —
    they are invalid, not score components.
    """
    analysis: dict = {}
    soft_summary: dict = {}
    if isinstance(analysis_or_soft_summary, dict):
        if "findings" in analysis_or_soft_summary or "soft_summary" in analysis_or_soft_summary:
            analysis = analysis_or_soft_summary
            soft_summary = analysis.get("soft_summary") or {}
        elif "types" in analysis_or_soft_summary or "warnings" in analysis_or_soft_summary:
            soft_summary = analysis_or_soft_summary
        else:
            analysis = analysis_or_soft_summary
            soft_summary = analysis.get("soft_summary") or {}

    raw_findings = findings
    if raw_findings is None:
        raw_findings = analysis.get("findings") or []

    components: list[dict] = []
    seen_opening = 0
    seen_packing_warn = 0
    seen_packing_info = 0
    seen_preferred = 0

    for f in raw_findings or []:
        if not isinstance(f, dict):
            continue
        ctype = str(f.get("constraint_type") or "")
        if ctype in _HARD_CONSTRAINT_TYPES:
            continue
        sev = str(f.get("severity") or "").lower()
        msg = str(f.get("message") or "")

        if ctype == "opening_access":
            seen_opening += 1
            components.append(
                {
                    "id": "opening_access",
                    "category": "accessibility",
                    "value": _OPENING_ACCESS_VALUE,
                    "severity": "severe",
                    "label": msg or "Opening access blocked",
                }
            )
        elif ctype == "soft_packing":
            if sev == "warning":
                seen_packing_warn += 1
                components.append(
                    {
                        "id": "soft_packing",
                        "category": "comfort",
                        "value": _SOFT_PACKING_WARNING_VALUE,
                        "severity": "ordinary",
                        "label": msg or "High packing density",
                    }
                )
                components.append(
                    {
                        "id": "soft_packing_circulation",
                        "category": "circulation",
                        "value": _SOFT_PACKING_CIRCULATION_WARN,
                        "severity": "ordinary",
                        "label": "Dense packing reduces circulation",
                    }
                )
            elif sev == "info":
                seen_packing_info += 1
                components.append(
                    {
                        "id": "soft_packing",
                        "category": "comfort",
                        "value": _SOFT_PACKING_INFO_VALUE,
                        "severity": "ordinary",
                        "label": msg or "Elevated packing density",
                    }
                )
                components.append(
                    {
                        "id": "soft_packing_circulation",
                        "category": "circulation",
                        "value": _SOFT_PACKING_CIRCULATION_INFO,
                        "severity": "ordinary",
                        "label": "Elevated packing nudges circulation",
                    }
                )
        elif ctype == "zone_must_be_clear":
            # Required (error) → Stage A invalidity via hard_errors, not a soft component.
            if sev == "error":
                continue
            if sev == "warning":
                seen_preferred += 1
                components.append(
                    {
                        "id": "preferred_clearance",
                        "category": "object_usability",
                        "value": _scaled_penalty(_PREFERRED_CLEARANCE_WARNING, f),
                        "severity": "ordinary",
                        "label": msg or "Preferred clearance blocked",
                    }
                )
            elif sev == "info":
                seen_preferred += 1
                components.append(
                    {
                        "id": "preferred_clearance",
                        "category": "object_usability",
                        "value": _scaled_penalty(_PREFERRED_CLEARANCE_INFO, f),
                        "severity": "ordinary",
                        "label": msg or "Informational clearance blocked",
                    }
                )

    # Fallback when only soft_summary counts/types are available (no findings).
    if not components and soft_summary:
        types = set(soft_summary.get("types") or [])
        warnings = int(soft_summary.get("warnings") or 0)
        info = int(soft_summary.get("info") or 0)
        if "opening_access" in types and seen_opening == 0:
            n_open = max(1, warnings) if warnings else 1
            for _ in range(n_open if "soft_packing" not in types else 1):
                components.append(
                    {
                        "id": "opening_access",
                        "category": "accessibility",
                        "value": _OPENING_ACCESS_VALUE,
                        "severity": "severe",
                        "label": "Opening access blocked (soft_summary)",
                    }
                )
            if "opening_access" in types:
                warnings = max(0, warnings - 1)
        if "soft_packing" in types:
            for _ in range(max(0, warnings)):
                components.append(
                    {
                        "id": "soft_packing",
                        "category": "comfort",
                        "value": _SOFT_PACKING_WARNING_VALUE,
                        "severity": "ordinary",
                        "label": "High packing density (soft_summary)",
                    }
                )
                components.append(
                    {
                        "id": "soft_packing_circulation",
                        "category": "circulation",
                        "value": _SOFT_PACKING_CIRCULATION_WARN,
                        "severity": "ordinary",
                        "label": "Dense packing reduces circulation",
                    }
                )
            for _ in range(max(0, info)):
                components.append(
                    {
                        "id": "soft_packing",
                        "category": "comfort",
                        "value": _SOFT_PACKING_INFO_VALUE,
                        "severity": "ordinary",
                        "label": "Elevated packing density (soft_summary)",
                    }
                )
                components.append(
                    {
                        "id": "soft_packing_circulation",
                        "category": "circulation",
                        "value": _SOFT_PACKING_CIRCULATION_INFO,
                        "severity": "ordinary",
                        "label": "Elevated packing nudges circulation",
                    }
                )
        if "zone_must_be_clear" in types and seen_preferred == 0:
            # Prefer warnings count for preferred clearances when findings absent.
            for _ in range(max(1, warnings) if warnings else 1):
                components.append(
                    {
                        "id": "preferred_clearance",
                        "category": "object_usability",
                        "value": _PREFERRED_CLEARANCE_WARNING,
                        "severity": "ordinary",
                        "label": "Preferred clearance blocked (soft_summary)",
                    }
                )

    return components


def score_breakdown(components: list | None) -> dict:
    """Sum signed components with optional positive per-category caps.

    Returns total, category_vector, severe_veto, expected_risk_hints.
    """
    category_vector = _empty_category_vector()
    severe_veto = False
    hints: list[str] = []

    for comp in components or []:
        cat = str(comp.get("category") or "")
        if cat not in category_vector:
            continue
        value = int(comp.get("value") or 0)
        category_vector[cat] += value
        sev = str(comp.get("severity") or "").lower()
        if sev == "severe" or value <= SEVERE_VETO_THRESHOLD:
            severe_veto = True
            label = str(comp.get("label") or comp.get("id") or "severe penalty")
            hint = f"{comp.get('id')}: {label}"
            if hint not in hints:
                hints.append(hint)

    # Apply positive soft caps when computing total (provisional).
    total = 0
    for cat, raw in category_vector.items():
        if raw > POSITIVE_CAP_PER_CATEGORY:
            total += POSITIVE_CAP_PER_CATEGORY
        else:
            total += raw

    return {
        "total": total,
        "category_vector": category_vector,
        "severe_veto": severe_veto,
        "expected_risk_hints": hints,
    }


def classify_candidate_state(
    *,
    has_hard_errors: bool,
    severe_veto: bool,
    soft_warnings: int = 0,
) -> str:
    """Ordered gate classification (DD-017 Stage A/B).

    Returns one of:
    ``invalid`` | ``valid_with_severe_penalty`` | ``valid_but_suboptimal`` | ``preferred``
    """
    if has_hard_errors:
        return "invalid"
    if severe_veto:
        return "valid_with_severe_penalty"
    if int(soft_warnings or 0) > 0:
        return "valid_but_suboptimal"
    return "preferred"


def build_evaluation(
    *,
    has_hard_errors: bool,
    soft_warnings: int = 0,
    analysis: dict | None = None,
    soft_summary: dict | None = None,
    findings: list | None = None,
) -> dict:
    """Assemble the per-candidate evaluation block (DD-017 sketch, no aesthetics)."""
    source = analysis if isinstance(analysis, dict) else {}
    if soft_summary and "soft_summary" not in source:
        source = dict(source)
        source["soft_summary"] = soft_summary
    components = soft_findings_to_components(source, findings=findings)
    breakdown = score_breakdown(components)
    state = classify_candidate_state(
        has_hard_errors=bool(has_hard_errors),
        severe_veto=bool(breakdown["severe_veto"]),
        soft_warnings=int(soft_warnings or 0),
    )
    return {
        "valid": not bool(has_hard_errors),
        "functional": {
            "total": breakdown["total"],
            "components": components,
        },
        "category_vector": breakdown["category_vector"],
        "severe_veto": breakdown["severe_veto"],
        "state": state,
        "expected_risk_hints": list(breakdown["expected_risk_hints"]),
    }
