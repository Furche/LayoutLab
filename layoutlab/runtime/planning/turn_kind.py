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

# Known room-use labels (alone ≠ mutation; need planning intent alongside).
_ROOM_TYPE_CUES = (
    "schlafzimmer",
    "kinderzimmer",
    "bedroom",
    "kids room",
    "kidsroom",
    "kindzimmer",
    "schlafgemach",
    "wohnzimmer",
    "büro",
    "buero",
    "home office",
    "homeoffice",
)

# With a room type (or "zimmer/raum"), these mark a layout/planning ask.
_PLAN_INTENT_CUES = (
    "gestalt",
    "planen",
    "plane ",
    "brauch",
    "benötig",
    "benoetig",
    "einrichten",
    "möblier",
    "moblier",
    "furnished",
    "furniture",
    "fenster",
    "window",
    "möbel",
    "mobel",
    "variante",
    "layout",
    "für zwei",
    "fuer zwei",
    "für 2",
    "fuer 2",
)

# Explicit mutate verbs — avoid bare "einricht" / "richte" (hit "eingerichtet").
_MUTATE_CUES = (
    "bau",
    "erstell",
    "neu einricht",
    "anders einricht",
    "um einricht",
    "einrichten",
    "gestalt",
    "planen",
    "lösch",
    "losch",
    "clear",
    "leeren",
    "platzi",
    "verschieb",
    "austausch",
    "vertausch",
    "tausche",
    "tauschen",
    "swap",
    "dreh",
    "rotier",
    "rückgängig",
    "ruckgangig",
    "änder",
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
    "richte mir",
    "richte ein",
    "möblier",
    "moblier",
)

_FURNITURE_NOUNS = (
    "zimmer",
    "raum",
    "room",
    "bett",
    "schrank",
    "tisch",
    "desk",
    "wardrobe",
    "bed",
    "möbel",
    "mobel",
    "lampe",
    "stuhl",
)

_STYLING_CUES = (
    "dekorie",
    "dekorier",
    "decorate",
    "styling",
    "einrichten gemütlich",
    "gemütlicher machen",
    "gemutlicher machen",
    "wohnlicher",
    "wohnlich machen",
    "aufhübsch",
    "aufhubsch",
    "schöner machen",
    "schoner machen",
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
    r"\bsieht .+ (stimmig|ok|gut|richtig)\b",
)

_OPINION_PATTERNS = (
    r"\bwas meinst du\b",
    r"\bwie findest du\b",
    r"\bwie wirkt\b",
    r"\bfinde .{0,60}(kühl|kuehl|eng|leer|voll|schön|schon|hässlich|haesslich|gemütlich|gemutlich|eingerichtet)",
    r"\b(wirkt|sieht).{0,20}(kühl|kuehl|eng|leer|voll)\b",
    r"\bnicht besonders (schön|schon)\b",
    r"\b(schön|schon|hässlich|haesslich)\s+eingerichtet\b",
    r"\beingerichtet oder\b",
    r"\bnur ideen\b",
    r"\beinschätz",
    r"\beinschaetz",
    r"\bmeinung\b",
    r"\btipps?\b",
)

# Accept / proceed after an AI offer ("soll ich ausprobieren?").
_ACCEPT_ACTION_PATTERNS = (
    r"\b(kannst|könntest|konntest)\s+du\s+(das|es|das mal)\s+(tun|machen|ausprobieren)\b",
    r"\b(mach|macht)\s+(das|es|ruhig|bitte)\b",
    r"\bja[,.]?\s*(bitte|mach|gern|gerne)\b",
    r"\bbitte\s+(mach|ausprobieren|probieren)\b",
    r"\bkann\s+losgehen\b",
    r"\blosgehen\b",
    r"\bleg(e)?\s+los\b",
    r"\bloslegen\b",
    r"\bprobier",
    r"\bausprobieren\b",
    r"\bdann\s+mach\b",
    r"\bdo\s+it\b",
    r"\bgo\s+ahead\b",
    r"\btry\s+it\b",
    r"\bnimm\s+(?:die\s+|den\s+)?(?:variante|option|vorschlag)\s+\w+",
    r"\b(?:variante|option|vorschlag)\s+\d+\b",
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


def _is_opinion(text: str) -> bool:
    return any(re.search(p, text) for p in _OPINION_PATTERNS)


def _is_accept_action(text: str) -> bool:
    return any(re.search(p, text) for p in _ACCEPT_ACTION_PATTERNS)


def _has_room_type(text: str) -> bool:
    return any(k in text for k in _ROOM_TYPE_CUES)


def _is_planning_request(text: str) -> bool:
    """Room layout goal: room type + planning/requirement language (not bare label)."""
    has_space = _has_room_type(text) or any(
        k in text for k in ("zimmer", "raum", "room")
    )
    if not has_space:
        return False
    if any(k in text for k in _PLAN_INTENT_CUES):
        return True
    # "Schlafzimmer mit 2 Fenstern" / "mit zwei Fenstern"
    if re.search(r"\bmit\s+(\d+|zwei|drei|ein|einem|einer)\b", text):
        return True
    if "gestalt" in text:
        return True
    return False


def infer_turn_kind(message: str, history: list | None = None) -> str:
    """Infer FC-002 turn kind from a user message (deterministic v0).

    Priority: observation/opinion → accept → styling → planning → action →
    feedback/clarify/question → conversation default.
    """
    _ = history  # reserved for offer-context
    t = (message or "").strip().lower()
    if not t:
        return TURN_CLARIFY

    # 1) Assessment / observation (no mutation)
    if any(re.search(p, t) for p in _OBSERVATION_PATTERNS):
        return TURN_OBSERVATION
    if _is_opinion(t):
        return TURN_CONVERSATION

    # Soft aesthetic remarks without verbs
    if any(
        k in t
        for k in ("kühl", "kuehl", "eng", "leer", "vollgestellt")
    ) and not _is_planning_request(t):
        return TURN_CONVERSATION

    # 2) Explicit accept / proceed
    if _is_accept_action(t):
        return TURN_ACTION

    # 3) Styling (WP-A: acknowledge only — commands blocked via NON_MUTATING)
    if any(k in t for k in _STYLING_CUES):
        return TURN_STYLING

    # 4) Layout / room planning goals
    if _is_planning_request(t):
        return TURN_PLANNING

    # 5) Targeted furniture mutations
    if any(k in t for k in _MUTATE_CUES) and any(k in t for k in _FURNITURE_NOUNS):
        return TURN_ACTION
    if any(k in t for k in _MUTATE_CUES):
        return TURN_ACTION
    if re.search(
        r"\b(kannst|könntest|konntest)\s+du\b.+\b(austausch|vertausch|tausch|verschieb|dreh|rotier|swap)\w*\b",
        t,
    ):
        return TURN_ACTION

    # 6) Feedback / ambiguity
    if any(k in t for k in _FEEDBACK_CUES):
        return TURN_FEEDBACK
    if any(re.search(p, t) for p in _CLARIFY_AMBIGUOUS):
        return TURN_CLARIFY

    # 7) Factual questions (not planning — planning already handled)
    if "?" in t or _QUESTION_START.search(t):
        if _is_opinion(t):
            return TURN_CONVERSATION
        if any(k in t for k in ("warum", "wieso", "weshalb", "clearance", "abstand")):
            return TURN_QUESTION
        if any(k in t for k in ("raum", "zimmer", "scene", "szene", "möbel", "mobel", "bett")):
            return TURN_QUESTION
        return TURN_QUESTION

    # 8) Safe default: conversation (bare "Schlafzimmer" alone stays here)
    return TURN_CONVERSATION
