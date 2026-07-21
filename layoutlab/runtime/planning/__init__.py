"""Deterministic layout recipes (DD-016) — Planning Layer v0."""

from __future__ import annotations

from typing import Any

from .bedroom_basic import RECIPE_GOALS as BEDROOM_BASIC_GOALS
from .bedroom_basic import RECIPE_KIND as BEDROOM_BASIC_KIND
from .bedroom_basic import RECIPE_NAME as BEDROOM_BASIC
from .bedroom_basic import enumerate_bedroom_candidates, plan_bedroom_basic
from .candidates import MAX_REVISION_ROUNDS, plan_layout_candidates, rank_candidates
from .schema import (
    EVALUATION_SCHEMA,
    HIGH_IMPACT_ROLES,
    INTENTIONS,
    PROFILES,
    ROLES,
    SCHEMA_VERSION,
    SCORE_CATEGORIES,
    SEVERE_VETO_THRESHOLD,
    classify_candidate_state,
    default_role_for_profile,
    get_profile,
    is_high_impact,
    list_profiles,
    normalize_role,
    resolve_profile_id,
    score_breakdown,
    soft_findings_to_components,
    validate_intention,
)
from .intent import (
    WORD_COUNTS,
    count_requested_noun,
    is_retry_request,
    opening_kind_counts,
    parse_bed_size_m,
    parse_room_size_m,
    requested_window_count,
    user_mentions_bed_head,
    user_wants_bed,
    user_wants_better_layout,
    user_wants_door,
    user_wants_room,
)
from .recipe_routing import (
    RECIPE_ROOM_TYPES,
    ROOM_TYPE_RECIPES,
    resolve_recipe_id,
    session_wants_bedroom_fallback,
    session_wants_recipe_planning,
    wants_bedroom_layout,
    wants_layout_planning,
)
from .selection_surface import (
    append_plan_layout_trace,
    apply_shortlist_selection,
    format_planning_reply_note,
    merge_planning_into_result,
    planning_summary_from_planned,
    resolve_shortlist_selection,
    shortlist_entries_from_planned,
    slim_candidates,
    stored_shortlist,
    strategy_label_de,
    strip_planning_notes,
    wants_shortlist_selection,
)
from .placement import (
    aabb_overlap_tuple,
    apply_deterministic_placement_fixes,
    apply_improved_bedroom_layout,
    as_xyz,
    gen_xy_aabb,
    last_placement_fp,
    layout_shell_fingerprint,
    mattress_to_bed_axes,
    placement_fingerprint,
    proposal_wants_layout,
    snap_bed_to_wall,
)
from .requirements import (
    REQUIREMENTS_SCHEMA,
    merge_requirements,
    normalize_requirements,
    requirements_to_plan_params,
)

RECIPES = {
    BEDROOM_BASIC: plan_bedroom_basic,
}


def list_recipes():
    return sorted(RECIPES.keys())


def plan_layout(params: dict | None = None) -> dict[str, Any]:
    """Dispatch recipe → commands. Accepts flat params or requirements{}."""
    params = dict(params or {})
    requirements = None
    if isinstance(params.get("requirements"), dict):
        requirements = normalize_requirements(params.get("requirements"))
        mapped = requirements_to_plan_params(requirements)
        # Flat keys on the tool call still override (rare escape hatch)
        for key, value in params.items():
            if key in ("requirements", "recipe") or value is None:
                continue
            if key.startswith("_"):
                continue
            mapped[key] = value
        if params.get("recipe"):
            mapped["recipe"] = params["recipe"]
        params = mapped
        params["_requirements"] = requirements

    recipe = str(params.get("recipe") or BEDROOM_BASIC).strip().lower()
    handler = RECIPES.get(recipe)
    if handler is None:
        return {
            "ok": False,
            "error": f"unknown recipe {recipe!r}",
            "known_recipes": list_recipes(),
            "commands": [],
            "assumes": [],
            "notes": [],
            "requirements": requirements,
        }
    out = handler(params)
    out.setdefault("recipe_kind", BEDROOM_BASIC_KIND if recipe == BEDROOM_BASIC else None)
    out.setdefault(
        "recipe_goals",
        list(BEDROOM_BASIC_GOALS) if recipe == BEDROOM_BASIC else [],
    )
    if requirements is not None:
        out["requirements"] = requirements
        # Prefer requirements assumes + recipe assumes
        assumes = list(requirements.get("assumes") or [])
        for a in out.get("assumes") or []:
            if a not in assumes:
                assumes.append(a)
        out["assumes"] = assumes
    return out


def reconcile_plan_layout_params(
    args: dict | None,
    *,
    window_count: int = 0,
    room_size: tuple[float, float] | None = None,
    bed_size: tuple[float, float] | None = None,
    wants_door: bool = True,
    requirements: dict | None = None,
    recipe: str | None = None,
) -> dict:
    """Build plan_layout args from requirements and/or conversation fallbacks."""
    args = dict(args or {})
    base_req = None
    if isinstance(requirements, dict):
        base_req = normalize_requirements(requirements)
    elif isinstance(args.get("requirements"), dict):
        base_req = normalize_requirements(args.get("requirements"))

    overlay: dict[str, Any] = {}
    if room_size is not None:
        overlay["width"] = float(room_size[0])
        overlay["depth"] = float(room_size[1])
    if window_count > 0:
        overlay["windows"] = int(window_count)
    if bed_size is not None:
        overlay["bed_width"] = float(bed_size[0])
        overlay["bed_length"] = float(bed_size[1])
    if wants_door and (base_req is None or base_req.get("doors", 1) < 1):
        overlay["doors"] = 1

    recipe_id = (
        recipe
        or (str(args.get("recipe") or "").strip().lower() or None)
        or (
            ROOM_TYPE_RECIPES.get(str((base_req or {}).get("room_type") or "").lower())
            if base_req
            else None
        )
        or BEDROOM_BASIC
    )

    if base_req is not None or overlay:
        req = merge_requirements(base_req, overlay if overlay else None)
        return {
            "requirements": req,
            "recipe": recipe_id,
            "mode": "candidates",
        }

    # Legacy flat-arg path
    out = dict(args)
    out["recipe"] = recipe_id
    out.setdefault("mode", "candidates")
    if room_size is not None:
        out["width"] = float(room_size[0])
        out["depth"] = float(room_size[1])
    if window_count > 0:
        out["window_count"] = int(window_count)
        out.pop("windows", None)
    if bed_size is not None:
        out["bed_width"] = float(bed_size[0])
        out["bed_length"] = float(bed_size[1])
    if wants_door and not isinstance(out.get("door"), dict):
        out["door"] = {"wall_side": "east", "width": 0.9}
    return out


__all__ = [
    "BEDROOM_BASIC",
    "BEDROOM_BASIC_GOALS",
    "BEDROOM_BASIC_KIND",
    "EVALUATION_SCHEMA",
    "HIGH_IMPACT_ROLES",
    "INTENTIONS",
    "MAX_REVISION_ROUNDS",
    "PROFILES",
    "RECIPE_ROOM_TYPES",
    "REQUIREMENTS_SCHEMA",
    "ROLES",
    "ROOM_TYPE_RECIPES",
    "SCHEMA_VERSION",
    "SCORE_CATEGORIES",
    "SEVERE_VETO_THRESHOLD",
    "WORD_COUNTS",
    "aabb_overlap_tuple",
    "apply_deterministic_placement_fixes",
    "apply_improved_bedroom_layout",
    "as_xyz",
    "classify_candidate_state",
    "count_requested_noun",
    "default_role_for_profile",
    "enumerate_bedroom_candidates",
    "gen_xy_aabb",
    "get_profile",
    "is_high_impact",
    "is_retry_request",
    "last_placement_fp",
    "layout_shell_fingerprint",
    "list_profiles",
    "list_recipes",
    "mattress_to_bed_axes",
    "merge_requirements",
    "normalize_requirements",
    "normalize_role",
    "opening_kind_counts",
    "parse_bed_size_m",
    "parse_room_size_m",
    "placement_fingerprint",
    "plan_layout",
    "plan_layout_candidates",
    "proposal_wants_layout",
    "rank_candidates",
    "reconcile_plan_layout_params",
    "requested_window_count",
    "requirements_to_plan_params",
    "resolve_profile_id",
    "resolve_recipe_id",
    "score_breakdown",
    "session_wants_bedroom_fallback",
    "session_wants_recipe_planning",
    "slim_candidates",
    "snap_bed_to_wall",
    "soft_findings_to_components",
    "strip_planning_notes",
    "user_mentions_bed_head",
    "user_wants_bed",
    "user_wants_better_layout",
    "user_wants_door",
    "user_wants_room",
    "validate_intention",
    "wants_bedroom_layout",
    "wants_layout_planning",
    "append_plan_layout_trace",
    "apply_shortlist_selection",
    "format_planning_reply_note",
    "merge_planning_into_result",
    "planning_summary_from_planned",
    "resolve_shortlist_selection",
    "shortlist_entries_from_planned",
    "stored_shortlist",
    "strategy_label_de",
    "wants_shortlist_selection",
]
