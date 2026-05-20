#!/usr/bin/env python3
"""Repair active style-lint findings through the OpenAI writing-agent path."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import scenario_agent


ROOT = Path(__file__).resolve().parents[1]
ROOMS_PATH = ROOT / "rooms_post_update.json"
EVENTS_PATH = ROOT / "events_post_update.json"
GENERATED_DIR = ROOT / "generated"


ROOM_EVENT_RE = re.compile(r"^room_events\.([^.]+)\.([^.]+)")
SPECIAL_EVENT_RE = re.compile(r"^special_events\.([^.]+)")
ROOM_RE = re.compile(r"^rooms\.([^.]+)\.([^.]+)")


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def read_text(path: Path, limit: int = 18000) -> str:
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    return text[:limit]


def repair_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "room_event_updates": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "room_id": {"type": "string"},
                        "event_id": {"type": "string"},
                        "event": {"type": "object"},
                    },
                    "required": ["room_id", "event_id", "event"],
                    "additionalProperties": False,
                },
            },
            "special_event_updates": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "event_id": {"type": "string"},
                        "event": {"type": "object"},
                    },
                    "required": ["event_id", "event"],
                    "additionalProperties": False,
                },
            },
            "room_updates": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "room_id": {"type": "string"},
                        "fields": {"type": "object"},
                    },
                    "required": ["room_id", "fields"],
                    "additionalProperties": False,
                },
            },
            "notes": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["summary", "room_event_updates", "special_event_updates", "room_updates", "notes"],
        "additionalProperties": False,
    }


def _find_room_event(events_payload: dict[str, Any], room_id: str, event_id: str) -> dict[str, Any]:
    for event in events_payload.get("room_events", {}).get(room_id, []):
        if isinstance(event, dict) and str(event.get("id", "")) == event_id:
            return event
    return {}


def _find_room(rooms_payload: dict[str, Any], room_id: str) -> dict[str, Any]:
    for room in rooms_payload.get("rooms", []):
        if isinstance(room, dict) and str(room.get("id", "")) == room_id:
            return room
    return {}


def collect_context() -> dict[str, Any]:
    findings = scenario_agent.event_writing_findings()
    events_payload = load_json(EVENTS_PATH)
    rooms_payload = load_json(ROOMS_PATH)

    room_event_keys: set[tuple[str, str]] = set()
    special_event_ids: set[str] = set()
    room_ids: set[str] = set()

    for finding in findings:
        location = str(finding.get("location", ""))
        match = ROOM_EVENT_RE.match(location)
        if match:
            room_event_keys.add((match.group(1), match.group(2)))
            continue
        match = SPECIAL_EVENT_RE.match(location)
        if match:
            special_event_ids.add(match.group(1))
            continue
        match = ROOM_RE.match(location)
        if match:
            room_ids.add(match.group(1))

    return {
        "findings": findings,
        "room_events": [
            {
                "room_id": room_id,
                "event_id": event_id,
                "event": _find_room_event(events_payload, room_id, event_id),
            }
            for room_id, event_id in sorted(room_event_keys)
        ],
        "special_events": [
            {
                "event_id": event_id,
                "event": events_payload.get("special_events", {}).get(event_id, {}),
            }
            for event_id in sorted(special_event_ids)
        ],
        "rooms": [
            {
                "room_id": room_id,
                "room": {
                    key: value
                    for key, value in _find_room(rooms_payload, room_id).items()
                    if key
                    in {
                        "id",
                        "environment_id",
                        "room_role",
                        "name",
                        "instance_premise",
                        "first_visit_description",
                        "return_description",
                        "tags",
                        "corpus_influences",
                        "animal_infrastructure",
                    }
                },
            }
            for room_id in sorted(room_ids)
        ],
        "existing_actions": sorted(scenario_agent.existing_actions()),
        "event_categories": scenario_agent.event_categories(),
    }


def build_prompt(context: dict[str, Any]) -> list[dict[str, str]]:
    system = """
You are the dedicated Fleshpunk: Inner Heart style repair writing agent.
Repair only the supplied active style-lint findings and return strict JSON.
Do not invent new action ids, room ids, event ids, or event categories.
Preserve every supplied event's id, type, speaker, actions, result structure, story_followups, trigger_key, reactivate_on_reshuffle, enemy/mutation/symbiote ids, and state-change metadata unless a finding directly requires a wording fix.
You may revise player-facing line_1, line_2, button labels, voice_aliases, previews, echo_notes, result lines, and room first_visit_description/return_description.
Keep Hymn's voice consistent: first-person field report, concrete actor/organ/material/mark, visible pressure, body position, evidence, cost. No menu summaries, no abstract system labels, no fake extra choices.
Do not use the phrase "I can" in line_1 or line_2. Avoid list-like option sentences such as "choose hurry, force, or loss".
When a finding says "abstract situation", make line_1 or line_2 include a concrete visible actor/material term such as wall, tissue, plate, pore, seam, bone, blood, blister, cord, teeth, valve, or wound.
When a room description lacks apparatus pressure, include a concrete living mechanism term such as pore, valve, tissue, cord, seam, teeth, or bell, and state what it does now.
For one-command transition/story special events, keep their existing type and button count; do not add fake tradeoff buttons.
Return full replacement event objects only for changed events, and room field patches only for changed room text fields.
""".strip()
    user = {
        "style_findings": context["findings"],
        "flagged_room_events": context["room_events"],
        "flagged_special_events": context["special_events"],
        "flagged_rooms": context["rooms"],
        "existing_actions": context["existing_actions"],
        "event_categories": context["event_categories"],
        "hymn_corpus_voice": read_text(ROOT / ".agent-memory" / "hymn_corpus_voice.md"),
        "story_room_contract": read_text(ROOT / ".agent-memory" / "story_room_contract.md", limit=12000),
        "content_strategy": read_text(ROOT / ".agent-memory" / "content_strategy.md", limit=12000),
    }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(user, indent=2, ensure_ascii=False)},
    ]


def cmd_generate(args: argparse.Namespace) -> int:
    context = collect_context()
    context_out = Path(args.context_out) if args.context_out else GENERATED_DIR / "style_lint_repair_context.json"
    if not context_out.is_absolute():
        context_out = ROOT / context_out
    write_json(context_out, context)

    if not context["findings"]:
        patch = {
            "summary": "No style-lint findings.",
            "room_event_updates": [],
            "special_event_updates": [],
            "room_updates": [],
            "notes": [],
        }
    else:
        patch = scenario_agent.call_openai(
            build_prompt(context),
            args.model,
            repair_schema(),
            "style_lint_repair",
        )

    out = Path(args.out) if args.out else GENERATED_DIR / "style_lint_repair_patch.json"
    if not out.is_absolute():
        out = ROOT / out
    write_json(out, patch)
    print(out)
    return 0


def _replace_room_event(events_payload: dict[str, Any], room_id: str, event_id: str, replacement: dict[str, Any]) -> None:
    events = events_payload.get("room_events", {}).get(room_id, [])
    if not isinstance(events, list):
        raise ValueError(f"room_events.{room_id} is not a list")
    for index, event in enumerate(events):
        if isinstance(event, dict) and str(event.get("id", "")) == event_id:
            if str(replacement.get("id", "")) != event_id:
                raise ValueError(f"replacement id mismatch for room event {room_id}.{event_id}")
            events[index] = replacement
            return
    raise ValueError(f"room event not found: {room_id}.{event_id}")


def _replace_special_event(events_payload: dict[str, Any], event_id: str, replacement: dict[str, Any]) -> None:
    special_events = events_payload.get("special_events", {})
    if not isinstance(special_events, dict) or event_id not in special_events:
        raise ValueError(f"special event not found: {event_id}")
    if str(replacement.get("id", "")) != event_id:
        raise ValueError(f"replacement id mismatch for special event {event_id}")
    special_events[event_id] = replacement


def _patch_room(rooms_payload: dict[str, Any], room_id: str, fields: dict[str, Any]) -> None:
    for room in rooms_payload.get("rooms", []):
        if isinstance(room, dict) and str(room.get("id", "")) == room_id:
            for key, value in fields.items():
                if key == "id":
                    continue
                room[key] = value
            return
    raise ValueError(f"room not found: {room_id}")


def cmd_apply(args: argparse.Namespace) -> int:
    patch_path = Path(args.patch)
    if not patch_path.is_absolute():
        patch_path = ROOT / patch_path
    patch = load_json(patch_path)
    events_payload = load_json(EVENTS_PATH)
    rooms_payload = load_json(ROOMS_PATH)

    for update in patch.get("room_event_updates", []):
        _replace_room_event(
            events_payload,
            str(update.get("room_id", "")),
            str(update.get("event_id", "")),
            update.get("event", {}),
        )
    for update in patch.get("special_event_updates", []):
        _replace_special_event(events_payload, str(update.get("event_id", "")), update.get("event", {}))
    for update in patch.get("room_updates", []):
        _patch_room(rooms_payload, str(update.get("room_id", "")), update.get("fields", {}))

    if args.dry_run:
        print(
            "dry-run ok: %d room event(s), %d special event(s), %d room patch(es)"
            % (
                len(patch.get("room_event_updates", [])),
                len(patch.get("special_event_updates", [])),
                len(patch.get("room_updates", [])),
            )
        )
        return 0

    write_json(EVENTS_PATH, events_payload)
    write_json(ROOMS_PATH, rooms_payload)
    print(
        "applied: %d room event(s), %d special event(s), %d room patch(es)"
        % (
            len(patch.get("room_event_updates", [])),
            len(patch.get("special_event_updates", [])),
            len(patch.get("room_updates", [])),
        )
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    generate = sub.add_parser("generate")
    generate.add_argument("--out")
    generate.add_argument("--context-out")
    generate.add_argument("--model", default=scenario_agent.DEFAULT_MODEL)
    generate.set_defaults(func=cmd_generate)

    apply = sub.add_parser("apply")
    apply.add_argument("patch")
    apply.add_argument("--dry-run", action="store_true")
    apply.set_defaults(func=cmd_apply)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
