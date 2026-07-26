"""Conversational turn kinds (FC-002/WP-A + WP-02) — product intent, not UI modes."""

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
        TURN_STYLING,  # ack only until WP-06
    }
)

DEFAULT_CLARIFY_QUESTION = (
    "Möchtest du nur meine Einschätzung, oder soll ich eine Variante ausprobieren?"
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

_ASSESSMENT_ONLY_PATTERNS = (
    r"\bnur\s+(eine?\s+)?(einschätz|meinung|idee|tipp)",
    r"\bnur\s+(anschauen|anschau|schauen|reden|sprechen)\b",
    r"\bkeine?\s+(änderung|aenderung|variante|vorschlag)\b",
    r"\bnicht\s+(ändern|aendern|umbauen|ausprobieren)\b",
    r"\bnoch\s+nicht\b",
    r"\bspaeter\b",
    r"\bspäter\b",
    r"\blass\s+(es\s+)?so\b",
    r"\bnein[,.]?\s*(danke|bitte)?\b",
    r"\bloss\s+(einschätz|reden|ideen)",
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
    r"\b(kannst|könntest|konntest)\s+du\s+(etwas|was|irgendwas)\b",
    r"\b(kannst|könntest|konntest)\s+du\s+(das|es)\s+(verbessern|optimieren)\b",
    r"\bmach(e|t)?\s+(es|das)?\s*(bitte\s+)?(besser|schöner|schoner|anders)\b",
    r"\bverbesser",
    r"\boptimier",
    r"\betwas\s+änder",
    r"\betwas\s+aender",
    r"\banders\s+machen\b",
    r"\bwas\s+(kannst|könntest|könnten)\s+du\s+(tun|machen)\b",
    r"\birgendwie\s+(besser|anders|schöner|schoner)\b",
)

_OFFER_IN_ASSISTANT = (
    r"\bvariante\b",
    r"\bausprobieren\b",
    r"\bvorschlagen\b",
    r"\bsoll ich\b",
    r"\bapply[- ]?gate\b",
    r"\beinschätzung\b.*\boder\b",
    r"\beinschaetzung\b.*\boder\b",
    r"\bnur\s+.*\boder\b",
)


def allows_commands(turn_kind: str | None) -> bool:
    kind = str(turn_kind or "").strip()
    return kind not in NON_MUTATING_KINDS and kind != ""


def clarification_open_question() -> str:
    return DEFAULT_CLARIFY_QUESTION


def _is_opinion(text: str) -> bool:
    return any(re.search(p, text) for p in _OPINION_PATTERNS)


def _is_accept_action(text: str) -> bool:
    return any(re.search(p, text) for p in _ACCEPT_ACTION_PATTERNS)


def _is_assessment_only(text: str) -> bool:
    return any(re.search(p, text) for p in _ASSESSMENT_ONLY_PATTERNS)


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


def _last_assistant_text(history: list | None) -> str:
    for item in reversed(history or []):
        if not isinstance(item, dict):
            continue
        if item.get("role") != "assistant":
            continue
        content = item.get("content")
        if isinstance(content, str) and content.strip():
            return content.strip().lower()
    return ""


def _assistant_offered_choice(history: list | None, agent_state: dict | None) -> bool:
    state = agent_state if isinstance(agent_state, dict) else {}
    last_kind = str(state.get("last_turn_kind") or "").strip()
    if last_kind in (TURN_CLARIFY, TURN_CONVERSATION, TURN_STYLING, TURN_FEEDBACK):
        reply = str(state.get("last_reply") or "").lower()
        if reply and any(re.search(p, reply) for p in _OFFER_IN_ASSISTANT):
            return True
        if last_kind == TURN_CLARIFY:
            return True
    assistant = _last_assistant_text(history)
    if assistant and any(re.search(p, assistant) for p in _OFFER_IN_ASSISTANT):
        return True
    return False


def _resolve_followup_after_offer(text: str) -> str | None:
    """Map short answers after an AI offer/clarification to a concrete kind."""
    if _is_assessment_only(text):
        return TURN_CONVERSATION
    if text in ("ja", "ok", "okay", "gerne", "gern", "yes", "mach", "machen"):
        return TURN_ACTION
    if _is_accept_action(text):
        return TURN_ACTION
    if any(k in text for k in ("variante", "vorschlag", "ausprobieren", "probieren")):
        return TURN_ACTION
    if any(k in text for k in ("änder", "aender")) and not _is_opinion(text):
        return TURN_ACTION
    return None


def _is_vague_mutation_ask(text: str) -> bool:
    """Mutate-ish language without a clear target → clarify, don't guess."""
    if any(re.search(p, text) for p in _CLARIFY_AMBIGUOUS):
        return True
    has_mutate = any(k in text for k in _MUTATE_CUES)
    has_noun = any(k in text for k in _FURNITURE_NOUNS)
    if has_mutate and not has_noun:
        vague = (
            "besser",
            "schöner",
            "schoner",
            "anders",
            "etwas",
            "irgend",
            "verbesser",
            "optimier",
        )
        if any(k in text for k in vague):
            return True
    return False


def infer_turn_kind(
    message: str,
    history: list | None = None,
    agent_state: dict | None = None,
) -> str:
    """Infer FC-002 turn kind from a user message (deterministic WP-02).

    Priority: follow-up after offer → observation/opinion → accept → styling →
    planning → action → feedback/clarify/question → conversation default.
    """
    t = (message or "").strip().lower()
    if not t:
        return TURN_CLARIFY

    # 0) Short answer after AI asked assessment vs try / offered a variant
    if _assistant_offered_choice(history, agent_state):
        follow = _resolve_followup_after_offer(t)
        if follow:
            return follow

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

    # 2) Ambiguous mutation asks → clarify before accept heuristics (WP-02)
    #    ("mach es bitte besser" must not look like accept-of-offer)
    if _is_vague_mutation_ask(t):
        return TURN_CLARIFY

    # 3) Explicit accept / proceed
    if _is_accept_action(t):
        return TURN_ACTION

    # 4) Styling (ack only — commands blocked via NON_MUTATING)
    if any(k in t for k in _STYLING_CUES):
        return TURN_STYLING

    # 5) Layout / room planning goals
    if _is_planning_request(t):
        return TURN_PLANNING

    # 6) Targeted furniture mutations
    if any(k in t for k in _MUTATE_CUES) and any(k in t for k in _FURNITURE_NOUNS):
        return TURN_ACTION
    if any(k in t for k in _MUTATE_CUES):
        return TURN_ACTION
    if re.search(
        r"\b(kannst|könntest|konntest)\s+du\b.+\b(austausch|vertausch|tausch|verschieb|dreh|rotier|swap)\w*\b",
        t,
    ):
        return TURN_ACTION

    # 7) Feedback / ambiguity
    if any(k in t for k in _FEEDBACK_CUES):
        return TURN_FEEDBACK
    if any(re.search(p, t) for p in _CLARIFY_AMBIGUOUS):
        return TURN_CLARIFY

    # 8) Factual questions (not planning — planning already handled)
    if "?" in t or _QUESTION_START.search(t):
        if _is_opinion(t):
            return TURN_CONVERSATION
        if any(k in t for k in ("warum", "wieso", "weshalb", "clearance", "abstand")):
            return TURN_QUESTION
        if any(k in t for k in ("raum", "zimmer", "scene", "szene", "möbel", "mobel", "bett")):
            return TURN_QUESTION
        return TURN_QUESTION

    # 9) Safe default: conversation (bare "Schlafzimmer" alone stays here)
    return TURN_CONVERSATION
