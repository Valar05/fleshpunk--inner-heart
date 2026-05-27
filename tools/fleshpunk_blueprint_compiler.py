#!/usr/bin/env python3
"""Compile compact Fleshpunk blueprints into scenario_agent patches."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EVENTS_PATH = ROOT / "events_post_update.json"
ROOMS_PATH = ROOT / "rooms_post_update.json"

IMPLEMENTED_ACTIONS = {
    "brace_through_red_split",
    "break_marked_pattern",
    "combat",
    "follow_marked_plates",
    "listen_red_wall",
    "mark_red_branch",
    "observe_organ_chamber",
    "pay_resin_toll",
    "probe_bones",
    "proceed",
    "push_through_spikes",
    "retreat",
    "scavenge_bones",
}


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise SystemExit(f"{path}: expected JSON object")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "scenario"


def known_room_ids() -> set[str]:
    return {
        str(room.get("id"))
        for room in load_json(ROOMS_PATH).get("rooms", [])
        if isinstance(room, dict) and room.get("id")
    }


def existing_event_ids() -> set[str]:
    payload = load_json(EVENTS_PATH)
    ids: set[str] = set()
    room_events = payload.get("room_events", {})
    if isinstance(room_events, dict):
        for events in room_events.values():
            if isinstance(events, list):
                for event in events:
                    if isinstance(event, dict) and event.get("id"):
                        ids.add(str(event["id"]))
    special_events = payload.get("special_events", {})
    if isinstance(special_events, dict):
        ids.update(str(event_id) for event_id in special_events.keys())
    return ids


def unique_id(base: str, used: set[str]) -> str:
    stem = slugify(base)
    candidate = stem
    suffix = 2
    while candidate in used:
        candidate = f"{stem}_{suffix}"
        suffix += 1
    used.add(candidate)
    return candidate


def validate_blueprint(blueprint: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    room_id = str(blueprint.get("room_id", "")).strip()
    if room_id not in known_room_ids():
        errors.append(f"unknown room_id: {room_id}")
    anchors = blueprint.get("corpus_anchors", [])
    if not isinstance(anchors, list) or not anchors:
        errors.append("corpus_anchors must be a non-empty list")
    else:
        for index, anchor in enumerate(anchors):
            if not isinstance(anchor, dict):
                errors.append(f"corpus_anchors[{index}] is not an object")
                continue
            for key in ("tier", "source_id", "source_title", "source_author", "source_moment", "story_element", "scenario_application"):
                if not str(anchor.get(key, "")).strip():
                    errors.append(f"corpus_anchors[{index}] missing {key}")
    event = blueprint.get("event", {})
    if not isinstance(event, dict):
        errors.append("event must be an object")
        return errors
    for key in ("id", "line_1", "line_2", "primary_pressure", "body_path_pressure", "avoidance_route", "recognition_effect"):
        if not str(event.get(key, "")).strip():
            errors.append(f"event missing {key}")
    choices = event.get("choices", [])
    if not isinstance(choices, list) or len(choices) < 2:
        errors.append("event.choices must have at least two choices")
    else:
        for index, choice in enumerate(choices):
            if not isinstance(choice, dict):
                errors.append(f"choices[{index}] is not an object")
                continue
            action = str(choice.get("action", "")).strip()
            if action not in IMPLEMENTED_ACTIONS:
                errors.append(f"choices[{index}] unknown action: {action}")
            for key in ("label", "result_lines"):
                if not choice.get(key):
                    errors.append(f"choices[{index}] missing {key}")
    return errors


def compile_patch(blueprint: dict[str, Any]) -> dict[str, Any]:
    used_ids = existing_event_ids()
    room_id = str(blueprint["room_id"])
    event_blueprint = blueprint["event"]
    event_id = unique_id(str(event_blueprint["id"]), used_ids)
    anchors = blueprint.get("corpus_anchors", [])
    room_update = {
        "room_role": blueprint.get("room_role", "corpus_anchored_scenario"),
        "instance_premise": blueprint.get("instance_premise", ""),
        "first_visit_description": blueprint.get("first_visit_description", ""),
        "return_description": blueprint.get("return_description", ""),
        "corpus_anchors": anchors,
        "corpus_influences": [
            {
                "source_id": anchor.get("source_id", ""),
                "source_title": anchor.get("source_title", ""),
                "source_author": anchor.get("source_author", ""),
                "source_moment": anchor.get("source_moment", ""),
                "writing_influence": anchor.get("story_element", ""),
                "scenario_application": anchor.get("scenario_application", ""),
            }
            for anchor in anchors
            if isinstance(anchor, dict)
        ],
        "environment_echoes": blueprint.get("environment_echoes", []),
        "progression_state": blueprint.get("progression_state", {}),
    }
    if blueprint.get("ending_vectors"):
        room_update["ending_vectors"] = blueprint["ending_vectors"]
    if blueprint.get("mutation_hooks"):
        room_update["mutation_hooks"] = blueprint["mutation_hooks"]

    special_id_map: dict[str, str] = {}
    for followup in blueprint.get("special_events", []):
        if isinstance(followup, dict) and followup.get("id"):
            original_id = str(followup["id"])
            special_id_map[original_id] = unique_id(original_id, used_ids)

    buttons: list[dict[str, Any]] = []
    action_results: dict[str, Any] = {}
    story_followups: dict[str, Any] = {}
    for choice in event_blueprint.get("choices", []):
        action = str(choice["action"])
        buttons.append({
            "label": choice["label"],
            "action": action,
            "voice_aliases": choice.get("voice_aliases", [choice["label"].lower(), action.replace("_", " ")]),
        })
        action_results[action] = {
            "preview": choice.get("preview", ""),
            "lines": choice.get("result_lines", []),
            "environment_state_changes": choice.get("environment_state_changes", []),
            "pressure_axis_changes": choice.get("pressure_axis_changes", []),
        }
        if choice.get("actor_state_changes"):
            action_results[action]["actor_state_changes"] = choice["actor_state_changes"]
        followup = choice.get("story_followup")
        if isinstance(followup, dict) and followup.get("event_id"):
            rewritten_followup = dict(followup)
            original_followup_id = str(rewritten_followup["event_id"])
            rewritten_followup["event_id"] = special_id_map.get(original_followup_id, original_followup_id)
            story_followups[action] = rewritten_followup

    event = {
        "id": event_id,
        "type": event_blueprint.get("type", "choice"),
        "speaker": "Hymn",
        "environment_id": event_blueprint.get("environment_id", ""),
        "infrastructure_actor": event_blueprint.get("infrastructure_actor", ""),
        "primary_pressure": event_blueprint.get("primary_pressure", ""),
        "body_path_pressure": event_blueprint.get("body_path_pressure", ""),
        "avoidance_route": event_blueprint.get("avoidance_route", ""),
        "recognition_effect": event_blueprint.get("recognition_effect", ""),
        "line_1": event_blueprint["line_1"],
        "line_2": event_blueprint["line_2"],
        "environment_memory_flags": event_blueprint.get("environment_memory_flags", [event_id + "_seen"]),
        "buttons": buttons,
        "action_results": action_results,
        "story_followups": story_followups,
        "character_change": event_blueprint.get("character_change", "both"),
        "possibility_tree": event_blueprint.get("possibility_tree", []),
        "progression_vector": event_blueprint.get("progression_vector", ""),
        "corpus_influences": room_update["corpus_influences"],
    }

    special_events = []
    for followup in blueprint.get("special_events", []):
        if isinstance(followup, dict):
            rewritten_followup = dict(followup)
            original_id = str(rewritten_followup.get("id", ""))
            if original_id:
                rewritten_followup["id"] = special_id_map.get(original_id, original_id)
            special_events.append(rewritten_followup)

    return {
        "title": blueprint.get("title", event_id.replace("_", " ").title()),
        "design_goal": blueprint.get("design_goal", ""),
        "room_updates": [{"room_id": room_id, "update": room_update}],
        "events": [{"room_id": room_id, "event": event}],
        "special_events": special_events,
        "mutations": blueprint.get("mutations", []),
        "symbiotes": [],
        "enemies": [],
        "scenario_design_notes": [
            {
                "room_id": room_id,
                "event_id": event_id,
                "scenario_role": event_blueprint.get("scenario_role", "corpus anchored scenario"),
                "primary_pressure": event_blueprint.get("primary_pressure", ""),
                "body_path_pressure": event_blueprint.get("body_path_pressure", ""),
                "avoidance_route": event_blueprint.get("avoidance_route", ""),
                "recognition_effect": event_blueprint.get("recognition_effect", ""),
                "character_change": event["character_change"],
                "possibility_tree": event["possibility_tree"],
                "progression_vector": event["progression_vector"],
                "corpus_anchors": anchors,
                "research_influences": room_update["corpus_influences"],
            }
        ],
        "required_engine_changes": blueprint.get("required_engine_changes", []),
        "inspiration_notes": blueprint.get("inspiration_notes", []),
        "self_critique": blueprint.get("self_critique", []),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("blueprint")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    blueprint_path = Path(args.blueprint)
    if not blueprint_path.is_absolute():
        blueprint_path = ROOT / blueprint_path
    blueprint = load_json(blueprint_path)
    errors = validate_blueprint(blueprint)
    if errors:
        for error in errors:
            print(error)
        return 2
    out = Path(args.out)
    if not out.is_absolute():
        out = ROOT / out
    write_json(out, compile_patch(blueprint))
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
