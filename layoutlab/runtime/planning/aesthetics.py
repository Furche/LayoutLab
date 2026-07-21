"""Optional, experimental LLM comparison of an already functional shortlist.

Visual evidence prefers standardized blueprint PNGs (DD-017 §7); ASCII is fallback.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request

from ..chat import resolve_llm_settings
from .blueprint_png import evidence_from_candidate

RUBRIC_VERSION = "0.2"
RUBRIC_KEYS = (
    "visual_balance",
    "composition_clarity",
    "spacing_rhythm",
    "visual_hierarchy",
    "perceived_clutter",
    "residual_spaces",
)
_TRUE_VALUES = {"1", "true", "yes", "on"}


def aesthetics_enabled(params=None, llm_config=None, env=os.environ) -> bool:
    """Return whether the explicitly opt-in experimental comparison is enabled."""
    return (
        str(env.get("LAYOUTLAB_AI_AESTHETICS") or "").strip().lower() in _TRUE_VALUES
        or bool((params or {}).get("aesthetics") is True)
        or bool((llm_config or {}).get("aesthetics") is True)
    )


def _extract_json_object(text: str) -> dict:
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            raise ValueError("no JSON object")
        data = json.loads(match.group(0))
    if not isinstance(data, dict):
        raise ValueError("JSON root must be object")
    return data


def _build_user_content(evidence: list[dict], style_context: str, ids: set[str], *, use_images: bool) -> list | str:
    """Multimodal content blocks when images exist; else plain text + ASCII."""
    header = (
        "Du vergleichst ausschließlich die bereits funktional validierte Shortlist "
        "von Raumlayouts. Dies ist eine experimentelle, probabilistische ästhetische "
        "Einschätzung; erfinde niemals weitere Kandidaten. "
        f"Stilkontext: {style_context!r}. "
        "Bilder sind standardisierte Top-Down-Grundrisse (Norden oben): Wände weiß, "
        "Tür blau mit Schwenkbogen, Fenster grün, Möbel farbige Rechtecke. "
        "Bewerte Layout-Ästhetik, nicht Renderqualität. "
        f"Antworte strikt als JSON mit recommended_id (muss einer von {sorted(ids)} sein), "
        "confidence (0..1), style_context, candidates [{candidate_id, scores {"
        + ", ".join(RUBRIC_KEYS)
        + "}, reason}], summary_de. Scores floats 0..1; reason/summary_de kurz Deutsch."
    )
    if not use_images:
        ascii_payload = [
            {
                "candidate_id": e["candidate_id"],
                "label_de": e.get("label_de"),
                "strategy": e.get("strategy"),
                "soft_warnings": e.get("soft_warnings"),
                "layout_sketch_ascii": e.get("layout_sketch_ascii"),
            }
            for e in evidence
        ]
        return (
            header
            + " Evidence-Modus: ASCII-Skizzen (Fallback).\n\nKandidaten:\n"
            + json.dumps(ascii_payload, ensure_ascii=False)
        )

    parts: list = [{"type": "text", "text": header + " Evidence-Modus: Blueprint-PNG (identische Kamera/Maßstab)."}]
    for e in evidence:
        label = e.get("label_de") or e.get("candidate_id")
        parts.append(
            {
                "type": "text",
                "text": (
                    f"\nKandidat {e['candidate_id']} — {label} "
                    f"(soft_warnings={e.get('soft_warnings')})"
                ),
            }
        )
        if e.get("image_data_url"):
            parts.append(
                {
                    "type": "image_url",
                    "image_url": {"url": e["image_data_url"], "detail": "low"},
                }
            )
        elif e.get("layout_sketch_ascii"):
            parts.append(
                {
                    "type": "text",
                    "text": "ASCII-Fallback:\n" + str(e["layout_sketch_ascii"]),
                }
            )
    return parts


def _chat_completion(llm_settings: dict, user_content) -> dict:
    body = {
        "model": llm_settings["model"],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": "Beurteile nur gelieferte Shortlist-Kandidaten anhand der Visual Evidence.",
            },
            {"role": "user", "content": user_content},
        ],
    }
    req = urllib.request.Request(
        f"{llm_settings['base_url']}/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {llm_settings['api_key']}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))


def _parse_assessment(
    raw: dict, ids: set[str], style_context: str, llm_settings: dict, *, evidence_kind: str
) -> dict | None:
    parsed = _extract_json_object(
        ((raw.get("choices") or [{}])[0].get("message") or {}).get("content")
    )
    recommended_id = str(parsed.get("recommended_id") or "")
    if recommended_id not in ids:
        return None
    rows = []
    for row in parsed.get("candidates") or []:
        if not isinstance(row, dict) or str(row.get("candidate_id") or "") not in ids:
            continue
        scores = row.get("scores") if isinstance(row.get("scores"), dict) else {}
        clean_scores = {}
        for key in RUBRIC_KEYS:
            value = scores.get(key)
            if isinstance(value, (int, float)) and 0 <= float(value) <= 1:
                clean_scores[key] = float(value)
        rows.append(
            {
                "candidate_id": str(row["candidate_id"]),
                "scores": clean_scores,
                "reason": str(row.get("reason") or "")[:400],
            }
        )
    confidence = parsed.get("confidence")
    confidence = float(confidence) if isinstance(confidence, (int, float)) else 0.0
    return {
        "experimental": True,
        "provider": llm_settings.get("base_url"),
        "model": llm_settings.get("model"),
        "rubric_version": RUBRIC_VERSION,
        "style_context": str(parsed.get("style_context") or style_context),
        "recommended_id": recommended_id,
        "confidence": max(0.0, min(1.0, confidence)),
        "candidates": rows,
        "summary_de": str(parsed.get("summary_de") or "")[:600],
        "evidence_kind": evidence_kind,
    }


def assess_shortlist_aesthetics(
    *, shortlist_candidates: list[dict], style_context: str, llm_settings: dict
) -> dict | None:
    """Ask an OpenAI-compatible LLM to compare *only* supplied shortlist members."""
    try:
        candidates = [
            c for c in shortlist_candidates if isinstance(c, dict) and c.get("candidate_id")
        ]
        ids = {str(c["candidate_id"]) for c in candidates}
        if not candidates or not llm_settings.get("api_key"):
            return None

        evidence = [evidence_from_candidate(c) for c in candidates]
        has_images = any(e.get("image_data_url") for e in evidence)

        def run(use_images: bool, kind: str) -> dict | None:
            raw = _chat_completion(
                llm_settings,
                _build_user_content(evidence, style_context, ids, use_images=use_images),
            )
            return _parse_assessment(
                raw, ids, style_context, llm_settings, evidence_kind=kind
            )

        if has_images:
            try:
                parsed = run(True, "blueprint_png")
                if parsed:
                    return parsed
            except (urllib.error.HTTPError, urllib.error.URLError, ValueError, KeyError, TypeError):
                pass

        return run(False, "ascii")
    except (ValueError, KeyError, TypeError, urllib.error.URLError, urllib.error.HTTPError, OSError):
        return None


def apply_aesthetic_recommendation(planned: dict, aesthetic: dict) -> dict:
    """Attach a safe recommendation and switch only to an existing shortlist winner."""
    planned = dict(planned or {})
    shortlist_ids = {str(value) for value in planned.get("shortlist_ids") or []}
    recommended_id = str((aesthetic or {}).get("recommended_id") or "")
    if recommended_id not in shortlist_ids:
        return planned
    planned["aesthetic"] = dict(aesthetic)
    planned["selected_id"] = recommended_id
    for candidate in planned.get("candidates") or []:
        if not isinstance(candidate, dict):
            continue
        candidate["recommended"] = candidate.get("candidate_id") == recommended_id
        if candidate.get("candidate_id") == recommended_id:
            planned["commands"] = list(candidate.get("commands") or [])
            planned["strategy"] = candidate.get("strategy")
            planned["assumes"] = list(candidate.get("assumes") or [])
            planned["notes"] = list(candidate.get("notes") or [])
    kind = aesthetic.get("evidence_kind") or "ascii"
    planned["selection_reason"] = (
        f"{planned.get('selection_reason') or ''} "
        f"Ästhetik (experimentell, evidence={kind}) hat eine Shortlist-Variante empfohlen."
    ).strip()
    return planned
