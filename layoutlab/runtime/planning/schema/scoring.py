"""DD-017 Evaluation v0.1 — signed score components, veto, candidate state.

Provisional numbers — labeled Evaluation v0.1. Maps known DD-015 soft findings
into explainable signed components. No preference/aesthetics engine.
"""

from __future__ import annotations

from typing import Any

SCORE_CATEGORIES = ("circulation", "accessibility", "comfort", "object_usability")

# Veto: any component with severity "severe" OR value <= threshold blocks
# default top recommendation (anti-compensation).
SEVERE_VETO_THRESHOLD = -50

# Optional soft cap on positive contribution per category when summing total.
POSITIVE_CAP_PER_CATEGORY = 40

# Provisional DD-015 → component map (Evaluation v0.1).
_OPENING_ACCESS_VALUE = -40
_SOFT_PACKING_WARNING_VALUE = -15
_SOFT_PACKING_INFO_VALUE = -5

# Hard / non-negotiable types — validity only, never score components.
_HARD_CONSTRAINT_TYPES = frozenset(
    {
        "solid_wall_penetration",
        "zone_must_be_clear",  # required clearance failures stay Stage A
    }
)


def _empty_category_vector() -> dict[str, int]:
    return {cat: 0 for cat in SCORE_CATEGORIES}


def soft_findings_to_components(
    analysis_or_soft_summary: Any = None,
    findings: list | None = None,
) -> list[dict]:
    """Map known DD-015 soft findings into signed explainable components.

    Accepts either:
    - an analysis dict with ``findings`` / ``soft_summary``, or
    - a soft_summary dict, plus optional explicit ``findings``.
    Hard errors (e.g. solid_wall_penetration) are skipped — they are invalid,
    not score components.
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

    for f in raw_findings or []:
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

    # Fallback when only soft_summary counts/types are available (no findings).
    if not components and soft_summary:
        types = set(soft_summary.get("types") or [])
        warnings = int(soft_summary.get("warnings") or 0)
        info = int(soft_summary.get("info") or 0)
        if "opening_access" in types and seen_opening == 0:
            # Attribute at least one severe opening_access if type is present.
            n_open = max(1, warnings) if warnings else 1
            # Prefer assigning warnings to opening_access when both types present;
            # remaining warnings → packing.
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

    # Apply positive soft caps when computing total (provisional v0.1).
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
