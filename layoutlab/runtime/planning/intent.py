"""Conversation intent heuristics (bedroom / openings / sizes)."""

from __future__ import annotations

import re

WORD_COUNTS = {
    "ein": 1,
    "eine": 1,
    "einem": 1,
    "einen": 1,
    "einer": 1,
    "zwei": 2,
    "drei": 3,
    "vier": 4,
    "fünf": 5,
    "fuenf": 5,
    "sechs": 6,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
}


def user_wants_bed(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in ("bett", "bed"))


def wants_bedroom_layout(text: str) -> bool:
    """True when Core should use bedroom recipe, not kids-room demo."""
    t = (text or "").lower()
    return "schlafzimmer" in t or "bedroom" in t or user_wants_bed(t)


def is_retry_request(text: str) -> bool:
    t = (text or "").lower()
    return any(
        k in t
        for k in ("nochmal", "nochmals", "erneut", "retry", "versuch es noch", "noch einmal")
    )


def session_wants_bedroom_fallback(session, text: str) -> bool:
    if wants_bedroom_layout(text):
        return True
    if not is_retry_request(text):
        return False
    state = getattr(session, "agent_state", None) or {}
    req = state.get("requirements") if isinstance(state, dict) else None
    if isinstance(req, dict) and str(req.get("room_type") or "").lower() == "bedroom":
        return True
    goal = str((state or {}).get("goal") or "").lower()
    return "schlafzimmer" in goal


def user_wants_door(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in ("tür", "tur", "door", "eingang"))


def user_wants_room(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in ("raum", "zimmer", "room", "erstell", "bau"))


def count_requested_noun(text: str, nouns: tuple[str, ...]) -> int:
    """Best-effort count for 'zwei fenster' / '2 windows' / bare 'fenster' → 1."""
    t = text.lower()
    best = 0
    for noun in nouns:
        npat = re.escape(noun)
        scored = []
        for m in re.finditer(rf"(\d+)\s*x?\s*{npat}\b", t):
            scored.append(max(1, int(m.group(1))))
        for word, n in WORD_COUNTS.items():
            if re.search(rf"\b{re.escape(word)}\s+{npat}\b", t):
                scored.append(n)
        if scored:
            best = max(best, sum(scored))
        elif re.search(rf"\b{npat}\b", t):
            best = max(best, 1)
    return best


def requested_window_count(text: str) -> int:
    return count_requested_noun(text, ("fenstern", "fenster", "windows", "window"))


def opening_kind_counts(commands: list) -> tuple[int, int]:
    doors = 0
    windows = 0
    for cmd in commands or []:
        if cmd.get("action") != "add_opening":
            continue
        params = cmd.get("params") if isinstance(cmd.get("params"), dict) else {}
        kind = str(params.get("kind") or cmd.get("kind") or "").lower()
        if kind == "window":
            windows += 1
        elif kind == "door":
            doors += 1
    return doors, windows


def user_mentions_bed_head(text: str) -> bool:
    t = (text or "").lower()
    return any(
        k in t
        for k in (
            "kopfende",
            "kopfseite",
            "kopfteile",
            "headboard",
            "head of the bed",
            "head of bed",
            "bett dreh",
            "bett rotier",
            "rotate the bed",
            "turn the bed",
        )
    )


def user_wants_better_layout(text: str) -> bool:
    t = (text or "").lower()
    return any(
        k in t
        for k in (
            "besser",
            "bessere",
            "besseren",
            "andere lösung",
            "andere losung",
            "anders stellen",
            "umstellen",
            "neu platz",
            "neuplatz",
            "verbesser",
            "optimize",
            "optimier",
            "better",
            "rearrange",
            "umräumen",
            "umraumen",
            "schickere",
            "geeignetere",
        )
    )


def parse_bed_size_m(text: str) -> tuple[float, float] | None:
    """Parse human mattress size as (width, length) in meters.

    '120x200' / '120 × 200' → 1.2 × 2.0 (Breite × Länge). Order matters.
    Does not treat room sizes like '3x5m' as mattress dims.
    """
    t = (text or "").lower().replace(",", ".")
    m = re.search(r"(\d+(?:\.\d+)?)\s*[x×]\s*(\d+(?:\.\d+)?)", t)
    if not m:
        return None
    a = float(m.group(1))
    b = float(m.group(2))
    # Centimeters (typical mattress labels)
    if a >= 10 and b >= 10:
        a, b = a / 100.0, b / 100.0
        if a < 0.5 or b < 0.5 or a > 3.5 or b > 3.5:
            return None
        return round(a, 3), round(b, 3)
    # Meter mattress only when the user is talking about a bed
    if not any(k in t for k in ("bett", "bed", "matratze", "mattress")):
        return None
    if a < 0.8 or b < 1.5 or a > 3.0 or b > 3.0:
        return None
    return round(a, 3), round(b, 3)


def parse_room_size_m(text: str) -> tuple[float, float] | None:
    """Parse room size as (width, depth) in meters from phrases like '3x5m' / '3 x 5 m'.

    First number → width (X), second → depth (Y). Does not treat bed cm sizes
    (both ≥ 10 without 'm' and looking like mattress) — those go to parse_bed_size_m.
    """
    t = (text or "").lower().replace(",", ".")
    # Prefer explicit meter markers
    m = re.search(
        r"(\d+(?:\.\d+)?)\s*[x×]\s*(\d+(?:\.\d+)?)\s*m\b",
        t,
    )
    if not m:
        m = re.search(
            r"(\d+(?:\.\d+)?)\s*m\s*[x×]\s*(\d+(?:\.\d+)?)\s*m\b",
            t,
        )
    if not m:
        # '3x5' / '4.0 x 3.5' only when values look like room meters (not 120x200)
        m = re.search(r"(\d+(?:\.\d+)?)\s*[x×]\s*(\d+(?:\.\d+)?)", t)
        if not m:
            return None
        a, b = float(m.group(1)), float(m.group(2))
        if a >= 10 or b >= 10:
            return None
    else:
        a, b = float(m.group(1)), float(m.group(2))
    if a < 2.0 or b < 2.0 or a > 20 or b > 20:
        return None
    return round(a, 3), round(b, 3)
