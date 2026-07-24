"""Conversational turn kinds (FC-002/WP-A) — product intent, not UI modes."""

from __future__ import annotations

import re

# Stable product kinds from FC-002 §4 (subset shipped in WP-A).
TURN_CONVERSATION = "conversation"
TURN_QUESTION = "question"
TURN_OBSERVATION = "observation_request"
TURN_FEEDBACK = "feedback"
TURN_PLANNING = "planning_request"
TURN_ACTION = "action_request"
TURN_STYLING = "styling_request"
TURN_CLARIFY = "clarification"

NON_MUTATING_KINDS = frozenset(
    {
        TURN_CONVERSATION,
        TURN_QUESTION,
        TURN_OBSERVATION,
        TURN_FEEDBACK,
        TURN_CLARIFY,
        TURN_STYLING,  # WP-A: acknowledge + ask; no styling loop yet
    }
)

_MUTATE_CUES = (
    "bau",
    "erstell",
    "einricht",
    "lösch",
    "losch",
    "clear",
    "leeren",
    "platzi",
    "verschieb",
    "rückgängig",
    "ruckgangig",
    "änder",
    "ander",
    "add ",
    "remove",
    "put ",
    "make ",
    "create",
    "delete",
    "move ",
    "neu plan",
    "neuplan",
    "umplan",
    "nochmal versuch",
    "nochmal plan",
    "richte",
    "möblier",
    "moblier",
)

_STYLING_CUES = (
    "dekorie",
    "dekorier",
    "decorate",
    "styling",
    "einrichten gemütlich",
    "gemütlicher machen",
    "gemutlicher machen",
    "aufhübsch",
    "aufhubsch",
    "schöner machen",
    "schoner machen",
)

_PLANNING_CUES = (
    "schlafzimmer",
    "kinderzimmer",
    "plan_layout",
    "variante",
    "layout",
    "einrichten",
    "einricht",
    "möbel",
    "mobel",
    "furniture",
)

_OBSERVATION_PATTERNS = (
    r"\b(kannst|kann)\b.*\b(sehen|siehst)\b",
    r"\bsiehst du\b",
    r"\bwas (ist|steht|siehst|hast)\b",
    r"\bbeschreib",
    r"\baktuell\w*\s+(scene|szene|raum|zimmer)\b",
    r"\b(scene|szene)\s+(sehen|zeigen|beschreib)",
    r"\bcurrent scene\b",
    r"\bwhat('?s| is)\b.*\b(scene|room)\b",
    r"\bwelche m[oö]bel\b",
    r"\bwas siehst du\b",
    r"\bproblematisch\b",
    r"\bproblem\b",
    r"\bkollision\b",
    r"\büberlapp",
    r"\buberlapp",
    r"\bim bett\b",
    r"\bfalsch\b",
    r"\bstimmt (das|etwas|was)\b",
    r"\bso ungefähr\b",
    r"\bso ungefaehr\b",
    r"\bhast du dir\b",
    r"\bwie vorgestellt\b",
)

_OPINION_PATTERNS = (
    r"\bwas meinst du\b",
    r"\bwie findest du\b",
    r"\bwie wirkt\b",
    r"\bfinde .{0,40}(kühl|kuehl|eng|leer|voll|schön|schon|gemütlich|gemutlich)",
    r"\b(wirkt|sieht).{0,20}(kühl|kuehl|eng|leer|voll)\b",
    r"\bnur ideen\b",
    r"\beinschätz",
    r"\beinschaetz",
    r"\bmeinung\b",
    r"\btipps?\b",
)

_QUESTION_START = re.compile(
    r"^(wer|was|wann|wo|warum|wieso|weshalb|wie|welche|welcher|welches|ob)\b",
    re.I,
)

_FEEDBACK_CUES = (
    "gefällt mir",
    "gefallt mir",
    "gefällt nicht",
    "gefallt nicht",
    "zu voll",
    "zu leer",
    "lass so",
    "lass es so",
    "so lassen",
    "passt",
    "lieber nicht",
    "doch nicht",
)

_CLARIFY_AMBIGUOUS = (
    r"\bvielleicht\b.*\b(gemütlich|gemutlich|anders|schöner|schoner)\b",
    r"\bkönnte\b.*\b(besser|schöner|schoner|gemütlich)\b",
    r"\bkonnte\b.*\b(besser|schoner|schöner|gemütlich)\b",
    r"\betwas (gemütlicher|gemutlicher|wärmer|warmer|aufgeräumter|aufgeraeumter)\b",
)


def allows_commands(turn_kind: str | None) -> bool:
    kind = str(turn_kind or "").strip()
    return kind not in NON_MUTATING_KINDS and kind != ""


def infer_turn_kind(message: str) -> str:
    """Infer FC-002 turn kind from a single user message (deterministic v0)."""
    t = (message or "").strip().lower()
    if not t:
        return TURN_CLARIFY

    if any(k in t for k in _MUTATE_CUES) and any(
        k in t for k in ("zimmer", "raum", "room", "bett", "schrank", "tisch", "möbel", "mobel")
    ):
        if any(k in t for k in _STYLING_CUES):
            return TURN_STYLING
        return TURN_ACTION

    if any(k in t for k in _STYLING_CUES):
        return TURN_STYLING

    if any(k in t for k in _MUTATE_CUES):
        return TURN_ACTION

    if any(re.search(p, t) for p in _OBSERVATION_PATTERNS):
        return TURN_OBSERVATION

    if any(k in t for k in _FEEDBACK_CUES):
        return TURN_FEEDBACK

    if any(re.search(p, t) for p in _CLARIFY_AMBIGUOUS):
        return TURN_CLARIFY

    if any(re.search(p, t) for p in _OPINION_PATTERNS):
        return TURN_CONVERSATION

    if any(k in t for k in _PLANNING_CUES) and (
        "plan" in t or "einricht" in t or "richte" in t or "variante" in t
    ):
        return TURN_PLANNING

    if "?" in t or _QUESTION_START.search(t):
        # Design opinion questions stay conversation; factual → question
        if any(re.search(p, t) for p in _OPINION_PATTERNS):
            return TURN_CONVERSATION
        if any(k in t for k in ("warum", "wieso", "weshalb", "clearance", "abstand")):
            return TURN_QUESTION
        if any(k in t for k in ("raum", "zimmer", "scene", "szene", "möbel", "mobel", "bett")):
            return TURN_QUESTION
        return TURN_QUESTION

    if any(k in t for k in ("kühl", "kuehl", "eng", "leer", "vollgestellt", "gemütlich", "gemutlich")):
        return TURN_CONVERSATION

    # Default: treat as conversation so we do not invent mutations
    return TURN_CONVERSATION
