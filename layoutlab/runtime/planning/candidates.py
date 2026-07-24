"""DD-011 Planning v1 — expand candidates, dry-run evaluate, soft rank + DD-017 shortlist."""

from __future__ import annotations

from typing import Any

from .bedroom_basic import (
    RECIPE_GOALS as BEDROOM_GOALS,
    RECIPE_KIND as BEDROOM_KIND,
    RECIPE_NAME as BEDROOM_RECIPE,
    enumerate_bedroom_candidates,
)
from .kids_room_basic import (
    RECIPE_GOALS as KIDS_GOALS,
    RECIPE_KIND as KIDS_KIND,
    RECIPE_NAME as KIDS_RECIPE,
    enumerate_kids_room_candidates,
)
from .requirements import normalize_requirements, requirements_to_plan_params
from .schema import EVALUATION_SCHEMA, SCHEMA_VERSION, build_evaluation

# DD-017 interactive default: at most two internal revision rounds after first evaluate.
MAX_REVISION_ROUNDS = 2

# Backward-compatible aliases used by older call sites / tests.
RECIPE_NAME = BEDROOM_RECIPE
RECIPE_KIND = BEDROOM_KIND
RECIPE_GOALS = BEDROOM_GOALS


def _recipe_meta(recipe: str) -> tuple[str, list[str]]:
    if recipe == KIDS_RECIPE:
        return KIDS_KIND, list(KIDS_GOALS)
    return BEDROOM_KIND, list(BEDROOM_GOALS)


def _enumerate_candidates(recipe: str, flat: dict) -> list[dict]:
    if recipe == BEDROOM_RECIPE:
        return enumerate_bedroom_candidates(flat)
    if recipe == KIDS_RECIPE:
        return enumerate_kids_room_candidates(flat)
    return []


def _flat_plan_params(params: dict | None) -> tuple[dict, dict | None]:
    """Map requirements{} → flat recipe params (same rules as plan_layout)."""
    params = dict(params or {})
    requirements = None
    if isinstance(params.get("requirements"), dict):
        requirements = normalize_requirements(params.get("requirements"))
        mapped = requirements_to_plan_params(requirements)
        for key, value in params.items():
            if key in ("requirements", "recipe", "mode") or value is None:
                continue
            if key.startswith("_"):
                continue
            mapped[key] = value
        if params.get("recipe"):
            mapped["recipe"] = params["recipe"]
        mapped["_requirements"] = requirements
        return mapped, requirements
    # Drop mode from recipe kwargs
    flat = {k: v for k, v in params.items() if k != "mode"}
    return flat, None


def evaluate_candidate_commands(session, commands) -> dict[str, Any]:
    """Clone session → dry-run commands → extract hard/soft quality summary."""
    from ..tools import dry_run_commands
    from .viewer_preview import slim_viewer_preview

    dry = dry_run_commands(
        session,
        {
            "commands": commands,
            "analyze": True,
            "stop_on_invalid": True,
            "include_export": True,
        },
    )
    validation = dry.get("validation") or {}
    analysis = dry.get("analysis") or {}
    summary = analysis.get("summary") or {}
    soft = dry.get("soft_summary") or analysis.get("soft_summary") or {
        "count": 0,
        "warnings": 0,
        "info": 0,
        "types": [],
    }
    findings = analysis.get("findings") or []
    hard_errors = int(summary.get("errors") or 0)
    # Defensive: count severity=error findings even if summary is incomplete.
    hard_from_findings = sum(
        1 for f in findings if str((f or {}).get("severity") or "").lower() == "error"
    )
    hard_errors = max(hard_errors, hard_from_findings)
    apply_ok = bool(dry.get("apply_ok"))
    valid = bool(validation.get("ok", True)) and apply_ok
    has_hard = (not valid) or hard_errors > 0 or not apply_ok
    # Count apply/validation failures as hard errors for ranking.
    if not apply_ok or not validation.get("ok", True):
        hard_errors = max(hard_errors, 1)

    soft_warnings = int(soft.get("warnings") or 0)
    # Preferred clearance warnings live in soft_summary after Evaluation v0.2.
    soft_info = int(soft.get("info") or 0)

    return {
        "ok": bool(dry.get("ok")) and valid and hard_errors == 0,
        "apply_ok": apply_ok,
        "valid": bool(validation.get("ok", True)),
        "has_hard_errors": has_hard,
        "hard_errors": hard_errors,
        "soft_warnings": soft_warnings,
        "soft_info": soft_info,
        "summary": summary,
        "soft_summary": soft,
        "findings": findings,
        "analysis": analysis,
        "errors": dry.get("errors") or [],
        "layout_sketch": dry.get("layout_sketch")
        if isinstance(dry.get("layout_sketch"), dict)
        else None,
        "viewer_preview": slim_viewer_preview(dry.get("export")),
    }


def _rank_key(item: dict) -> tuple:
    """Best-first sort key: valid first, fewer hard/soft issues, higher score, stable id."""
    q = item.get("quality") or {}
    ev = item.get("evaluation") or {}
    total = (ev.get("functional") or {}).get("total")
    if total is None:
        total = 0
    invalid = 1 if q.get("has_hard_errors") or not q.get("apply_ok") else 0
    return (
        invalid,
        int(q.get("hard_errors") or 0),
        int(q.get("soft_warnings") or 0),
        int(q.get("soft_info") or 0),
        -int(total),
        str(item.get("candidate_id") or ""),
    )


def rank_candidates(evaluated: list) -> list:
    """Sort evaluated candidates best-first (deterministic)."""
    return sorted(list(evaluated or []), key=_rank_key)


def _functional_shortlist(ranked: list) -> list:
    """Candidates without hard errors and without severe_veto (default shortlist)."""
    out = []
    for c in ranked:
        q = c.get("quality") or {}
        ev = c.get("evaluation") or {}
        if q.get("has_hard_errors"):
            continue
        if ev.get("severe_veto"):
            continue
        out.append(c)
    return out


def _needs_revision(shortlist, ranked) -> bool:
    """True when Core should run a bounded revision pass (allowlisted overlays only)."""
    ranked = list(ranked or [])
    shortlist = list(shortlist or [])
    if not ranked:
        return False
    if shortlist:
        # Happy path: clean preferred shortlist — no revision.
        return False
    if all((c.get("quality") or {}).get("has_hard_errors") for c in ranked):
        return True
    # Empty shortlist (e.g. all severe_veto) with ranked candidates.
    return True


def _majority_failing_bed_wall(ranked: list) -> str:
    """Dominant bed wall among failing candidates."""
    failing = [
        c
        for c in ranked
        if (c.get("quality") or {}).get("has_hard_errors")
        or (c.get("evaluation") or {}).get("severe_veto")
    ]
    if not failing:
        failing = list(ranked)
    counts = {"south": 0, "north": 0, "east": 0, "west": 0}
    for c in failing:
        sid = str(c.get("strategy") or c.get("candidate_id") or "")
        for wall in counts:
            if f"bed_{wall}" in sid:
                counts[wall] += 1
                break
    best = max(counts, key=counts.get)
    return best if counts[best] else "south"


def _revision_overlay(round_num: int, ranked: list) -> tuple[dict[str, Any], str]:
    """Allowlisted param overlay + intention id for one revision round (1-based)."""
    if round_num == 1:
        majority = _majority_failing_bed_wall(ranked)
        opposite = {"south": "north", "north": "south", "east": "west", "west": "east"}
        wall = opposite.get(majority, "north")
        return (
            {"prefer_bed_wall": wall, "bed_wall": wall},
            f"prefer_bed_wall_{wall}",
        )
    if round_num == 2:
        return {"include_desk": False}, "omit_desk"
    return {}, ""


def _evaluate_raw_candidates(session, raw_candidates: list) -> list[dict]:
    """Dry-run evaluate enumerated raw candidates into ranked-ready dicts."""
    evaluated: list[dict] = []
    for cand in raw_candidates:
        quality = evaluate_candidate_commands(session, cand.get("commands") or [])
        evaluation = build_evaluation(
            has_hard_errors=quality["has_hard_errors"],
            soft_warnings=quality["soft_warnings"],
            analysis=quality.get("analysis"),
            soft_summary=quality.get("soft_summary"),
            findings=quality.get("findings"),
        )
        evaluated.append(
            {
                "candidate_id": cand["candidate_id"],
                "strategy": cand["strategy"],
                "commands": cand["commands"],
                "assumes": cand.get("assumes") or [],
                "notes": cand.get("notes") or [],
                "label_de": _strategy_label_de(cand.get("strategy") or cand.get("candidate_id")),
                "layout_sketch": quality.get("layout_sketch"),
                "viewer_preview": quality.get("viewer_preview"),
                "quality": {
                    "apply_ok": quality["apply_ok"],
                    "valid": quality["valid"],
                    "has_hard_errors": quality["has_hard_errors"],
                    "hard_errors": quality["hard_errors"],
                    "soft_warnings": quality["soft_warnings"],
                    "soft_info": quality["soft_info"],
                    "summary": quality["summary"],
                    "soft_summary": quality["soft_summary"],
                },
                "evaluation": evaluation,
            }
        )
    return evaluated


def _strategy_label_de(strategy: str | None) -> str:
    """Human German label for bedroom strategy ids (Viewer / reply)."""
    from .selection_surface import strategy_label_de

    return strategy_label_de(strategy)


def _merge_evaluated(
    pool: list[dict], newcomers: list[dict]
) -> tuple[list[dict], list[str]]:
    """Merge newcomers into pool; skip same id+commands; replace if commands differ."""
    by_id: dict[str, dict] = {str(c.get("candidate_id")): c for c in pool}
    order = [str(c.get("candidate_id")) for c in pool]
    added: list[str] = []
    for item in newcomers:
        cid = str(item.get("candidate_id") or "")
        if not cid:
            continue
        existing = by_id.get(cid)
        if existing is not None and existing.get("commands") == item.get("commands"):
            continue
        if existing is None:
            order.append(cid)
        by_id[cid] = item
        added.append(cid)
    return [by_id[cid] for cid in order if cid in by_id], added


def _assign_ranks(ranked: list) -> list:
    for i, item in enumerate(ranked):
        item["rank"] = i + 1
    return ranked


def _selection_reason_de(
    selected: dict,
    ranked: list,
    *,
    shortlist: list,
    fallback_risk: bool,
) -> str:
    """Short German why-string from soft/hard comparison + shortlist/veto."""
    q = selected.get("quality") or {}
    ev = selected.get("evaluation") or {}
    strategy = selected.get("strategy") or selected.get("candidate_id") or "?"
    if q.get("has_hard_errors"):
        return (
            f"Keine fehlerfreie Variante; gewählt: {strategy} "
            f"({int(q.get('hard_errors') or 0)} Hard-Fehler)."
        )
    if fallback_risk and ev.get("severe_veto"):
        return (
            f"Shortlist leer (alle mit Hard-Fehler oder severe_veto); "
            f"gewählt trotz Veto: {strategy}."
        )
    soft_w = int(q.get("soft_warnings") or 0)
    soft_i = int(q.get("soft_info") or 0)
    others = [c for c in ranked if c.get("candidate_id") != selected.get("candidate_id")]
    shortlist_note = ""
    if shortlist:
        shortlist_note = f" Shortlist {len(shortlist)} ohne Veto."
    if not others:
        return f"Einzige Variante: {strategy} (0 Hard-Fehler).{shortlist_note}"
    best_other = others[0]
    oq = best_other.get("quality") or {}
    if soft_w < int(oq.get("soft_warnings") or 0):
        return (
            f"Gewählt aus Shortlist: {strategy} — weniger Soft-Warnungen "
            f"({soft_w} vs {int(oq.get('soft_warnings') or 0)}).{shortlist_note}"
        )
    if soft_i < int(oq.get("soft_info") or 0):
        return (
            f"Gewählt aus Shortlist: {strategy} — bessere Packungs-/Info-Metriken "
            f"({soft_i} vs {int(oq.get('soft_info') or 0)} Info).{shortlist_note}"
        )
    if soft_w == 0 and soft_i == 0:
        return (
            f"Gewählt aus Shortlist: {strategy} — 0 Hard-Fehler, "
            f"keine Soft-Warnungen.{shortlist_note}"
        )
    return (
        f"Gewählt aus Shortlist: {strategy} — 0 Hard-Fehler, "
        f"{soft_w} Soft-Warnung(en), {soft_i} Soft-Info.{shortlist_note}"
    )


def _pick_selected(ranked: list, shortlist: list) -> tuple[dict | None, bool, list[str]]:
    """Select winner from shortlist or fallback; return (selected, fallback_risk, risks)."""
    fallback_risk = False
    expected_risks: list[str] = []
    if shortlist:
        return shortlist[0], False, []
    fallback_risk = True
    no_hard = [c for c in ranked if not (c.get("quality") or {}).get("has_hard_errors")]
    selected = no_hard[0] if no_hard else (ranked[0] if ranked else None)
    if selected:
        hints = list((selected.get("evaluation") or {}).get("expected_risk_hints") or [])
        if hints:
            expected_risks = hints
        elif (selected.get("evaluation") or {}).get("severe_veto"):
            expected_risks = ["severe_veto: default shortlist empty"]
        elif (selected.get("quality") or {}).get("has_hard_errors"):
            expected_risks = ["hard_errors: no valid candidate"]
    return selected, fallback_risk, expected_risks


def plan_layout_candidates(session, params: dict | None = None) -> dict[str, Any]:
    """Enumerate → evaluate → shortlist; up to MAX_REVISION_ROUNDS allowlisted revisions."""
    flat, requirements = _flat_plan_params(params)
    recipe = str(flat.get("recipe") or BEDROOM_RECIPE).strip().lower()
    kind, goals = _recipe_meta(recipe)
    raw = _enumerate_candidates(recipe, flat)
    if not raw:
        return {
            "ok": False,
            "mode": "candidates",
            "error": f"candidates mode not implemented for recipe {recipe!r}",
            "commands": [],
            "candidates": [],
            "selected_id": None,
            "selection_reason": "",
            "assumes": [],
            "notes": [],
            "recipe": recipe,
            "recipe_kind": kind,
            "recipe_goals": goals,
            "requirements": requirements,
            "schema_version": SCHEMA_VERSION,
            "evaluation_schema": EVALUATION_SCHEMA,
            "shortlist_ids": [],
            "revision_rounds": 0,
            "revision_trace": [],
        }

    working_flat = dict(flat)
    evaluated = _evaluate_raw_candidates(session, raw)
    ranked = _assign_ranks(rank_candidates(evaluated))
    shortlist = _functional_shortlist(ranked)

    revision_trace: list[dict[str, Any]] = []
    revision_rounds = 0

    while revision_rounds < MAX_REVISION_ROUNDS and _needs_revision(shortlist, ranked):
        round_num = revision_rounds + 1
        overlay, intention = _revision_overlay(round_num, ranked)
        if not overlay or not intention:
            break
        working_flat = {**working_flat, **overlay}
        newcomers = _evaluate_raw_candidates(
            session, _enumerate_candidates(recipe, working_flat)
        )
        evaluated, added_ids = _merge_evaluated(evaluated, newcomers)
        ranked = _assign_ranks(rank_candidates(evaluated))
        shortlist = _functional_shortlist(ranked)
        revision_rounds = round_num
        revision_trace.append(
            {
                "round": round_num,
                "intention": intention,
                "added_candidate_ids": added_ids,
                "shortlist_after": len(shortlist),
            }
        )
        if shortlist:
            break

    selected, fallback_risk, expected_risks = _pick_selected(ranked, shortlist)
    shortlist_ids = [c["candidate_id"] for c in shortlist]

    selected_id = selected["candidate_id"] if selected else None
    reason = (
        _selection_reason_de(
            selected, ranked, shortlist=shortlist, fallback_risk=fallback_risk
        )
        if selected
        else "Keine Kandidaten."
    )
    if revision_rounds > 0 and shortlist:
        reason = f"{reason} Nach Revision ({revision_rounds} Runde(n))."
    elif revision_rounds > 0 and selected:
        reason = f"{reason} Nach Revision ({revision_rounds} Runde(n), Shortlist weiter leer)."

    room = None
    if selected:
        for cmd in selected.get("commands") or []:
            if cmd.get("action") == "create_room":
                p = cmd.get("params") or {}
                room = {
                    "width": p.get("width"),
                    "depth": p.get("depth"),
                    "height": p.get("height"),
                    "name": p.get("name") or "ROOM",
                }
                break

    out = {
        "ok": bool(selected) and not (selected.get("quality") or {}).get("has_hard_errors"),
        "mode": "candidates",
        "recipe": recipe,
        "recipe_kind": kind,
        "recipe_goals": goals,
        "commands": list(selected.get("commands") or []) if selected else [],
        "candidates": ranked,
        "selected_id": selected_id,
        "selection_reason": reason,
        "assumes": list(selected.get("assumes") or []) if selected else [],
        "notes": list(selected.get("notes") or []) if selected else [],
        "strategy": selected.get("strategy") if selected else None,
        "room": room,
        "schema_version": SCHEMA_VERSION,
        "evaluation_schema": EVALUATION_SCHEMA,
        "shortlist_ids": shortlist_ids,
        "revision_rounds": revision_rounds,
        "revision_trace": revision_trace,
    }
    if expected_risks:
        out["expected_risks"] = expected_risks
    if requirements is not None:
        out["requirements"] = requirements
        assumes = list(requirements.get("assumes") or [])
        for a in out.get("assumes") or []:
            if a not in assumes:
                assumes.append(a)
        out["assumes"] = assumes
    return out
