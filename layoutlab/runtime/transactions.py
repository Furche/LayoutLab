"""Semantic transactions, revision and session Undo/Redo (DD-018 / FC-001/WP-02)."""

from __future__ import annotations

import copy
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

DEFAULT_UNDO_DEPTH = 50

VALID_ACTORS = frozenset({"user", "ai", "planner", "system", "import"})

ERROR_STALE_BASE_REVISION = "stale_base_revision"
ERROR_MISSING_BASE_REVISION = "missing_base_revision"
ERROR_PROTECTED_FROM_AI = "protected_from_ai"
ERROR_PREVIEW_ACTIVE = "preview_active"
ERROR_NO_PREVIEW = "no_active_preview"
ERROR_NOTHING_TO_UNDO = "nothing_to_undo"
ERROR_NOTHING_TO_REDO = "nothing_to_redo"
ERROR_INVALID_ACTOR = "invalid_actor"
ERROR_COMMIT_FAILED = "commit_failed"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


@dataclass
class TransactionRecord:
    """One committed semantic transaction (DD-018)."""

    actor: str
    action: str
    base_revision: int
    result_revision: int
    operations: list
    description: str = ""
    timestamp: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict:
        data = asdict(self)
        data["operations"] = copy.deepcopy(self.operations)
        return data


@dataclass
class UndoEntry:
    record: TransactionRecord
    before: dict


class TransactionHistory:
    """Session-scoped Undo stack with configurable depth (default ≥ 50)."""

    def __init__(self, max_depth: int = DEFAULT_UNDO_DEPTH):
        if max_depth < 1:
            raise ValueError("max_depth must be >= 1")
        self.max_depth = int(max_depth)
        self._stack: list[UndoEntry] = []

    def clear(self) -> None:
        self._stack.clear()

    def __len__(self) -> int:
        return len(self._stack)

    @property
    def can_undo(self) -> bool:
        return bool(self._stack)

    def push(self, entry: UndoEntry) -> None:
        self._stack.append(entry)
        while len(self._stack) > self.max_depth:
            self._stack.pop(0)

    def pop(self) -> UndoEntry | None:
        if not self._stack:
            return None
        return self._stack.pop()

    def peek(self) -> UndoEntry | None:
        if not self._stack:
            return None
        return self._stack[-1]


def normalize_actor(actor: str | None, *, default: str = "user") -> str:
    value = str(actor or default).strip().lower()
    if value not in VALID_ACTORS:
        raise ValueError(f"{ERROR_INVALID_ACTOR}: {actor!r} (allowed: {sorted(VALID_ACTORS)})")
    return value


def domain_snapshot(rooms: dict, mesh_store, revision: int, agent_state: dict | None = None) -> dict:
    """Capture authoritative domain state for Undo (rooms + furniture)."""
    snap = {
        "rooms": copy.deepcopy(rooms),
        "mesh_store": mesh_store.clone(),
        "revision": int(revision),
    }
    if agent_state is not None:
        snap["agent_state"] = copy.deepcopy(agent_state)
    return snap


def collect_protected_from_ai(rooms: dict, mesh_store) -> dict[str, list[str]]:
    """Return protected room_ids and object_ids (hard constraint for AI Apply)."""
    room_ids = []
    for room_id, model in (rooms or {}).items():
        if model.get("protected_from_ai"):
            room_ids.append(room_id)
    object_ids = []
    for obj in getattr(mesh_store, "objects", []) or []:
        props = getattr(obj, "props", None) or {}
        if props.get("protected_from_ai") or props.get("layoutlab_protected_from_ai"):
            oid = props.get("layoutlab_object_id") or getattr(obj, "name", None)
            if oid:
                object_ids.append(str(oid))
    return {"rooms": room_ids, "objects": object_ids}


def ai_protection_violations(rooms: dict, mesh_store, commands: list) -> list[dict[str, Any]]:
    """Detect AI Apply commands that would touch protected rooms/objects."""
    protected = collect_protected_from_ai(rooms, mesh_store)
    prot_rooms = set(protected["rooms"])
    prot_objects = set(protected["objects"])
    if not prot_rooms and not prot_objects:
        return []

    room_by_name = {
        (m.get("name") or ""): rid for rid, m in (rooms or {}).items() if m.get("name")
    }
    violations: list[dict[str, Any]] = []

    for index, cmd in enumerate(commands or []):
        if not isinstance(cmd, dict):
            continue
        action = cmd.get("action")
        params = cmd.get("params") if isinstance(cmd.get("params"), dict) else {}
        hits: list[str] = []

        object_id = cmd.get("object_id") or params.get("object_id")
        if object_id and str(object_id) in prot_objects:
            hits.append(f"object:{object_id}")

        room_id = cmd.get("room_id") or params.get("room_id")
        room_name = (
            cmd.get("room")
            or cmd.get("room_name")
            or params.get("room")
            or params.get("room_name")
            or params.get("name")
            or cmd.get("name")
        )
        resolved_room = None
        if room_id and room_id in (rooms or {}):
            resolved_room = room_id
        elif room_name and room_name in room_by_name:
            resolved_room = room_by_name[room_name]
        if resolved_room and resolved_room in prot_rooms:
            hits.append(f"room:{resolved_room}")

        if action in (
            "update_room",
            "delete_room",
            "add_opening",
            "update_opening",
            "remove_opening",
            "add_fixed_element",
            "update_fixed_element",
            "remove_fixed_element",
        ):
            if resolved_room and resolved_room in prot_rooms:
                hits.append(f"room:{resolved_room}")

        if action == "delete_collection":
            collection = cmd.get("collection") or params.get("collection")
            if collection:
                for rid, model in (rooms or {}).items():
                    if rid in prot_rooms and (model.get("collection") or "layoutlab_room") == collection:
                        hits.append(f"room:{rid}")
                for obj in getattr(mesh_store, "objects", []) or []:
                    props = getattr(obj, "props", None) or {}
                    oid = props.get("layoutlab_object_id") or obj.name
                    if (
                        str(oid) in prot_objects
                        and getattr(obj, "collection", None) == collection
                    ):
                        hits.append(f"object:{oid}")

        if action == "delete_prefix":
            prefix = cmd.get("prefix") or params.get("prefix") or ""
            if prefix:
                for obj in getattr(mesh_store, "objects", []) or []:
                    props = getattr(obj, "props", None) or {}
                    oid = props.get("layoutlab_object_id") or obj.name
                    if str(oid) in prot_objects and str(obj.name).startswith(prefix):
                        hits.append(f"object:{oid}")

        if action == "run_generator":
            # Same object_id overwrite / replace of a protected instance.
            if object_id and str(object_id) in prot_objects:
                hits.append(f"object:{object_id}")

        if hits:
            violations.append(
                {
                    "index": index,
                    "action": action,
                    "protected": sorted(set(hits)),
                }
            )

    return violations
