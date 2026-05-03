#!/usr/bin/env python3
"""Print project orientation and validate common Fleshpunk data wiring."""

from __future__ import annotations

import argparse
import configparser
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

EVENTS_PATH = ROOT / "events.json"
ROOMS_PATH = ROOT / "room_dialogue.json"
DECKS_PATH = ROOT / "encounter_decks.json"
ENEMIES_PATH = ROOT / "enemies.json"
MUTATIONS_PATH = ROOT / "mutations.json"
SYMBIOTES_PATH = ROOT / "symbiotes.json"
PROJECT_PATH = ROOT / "project.godot"
RUN_MANAGER_PATH = ROOT / "run_manager.gd"

ACTION_CASE_RE_TEMPLATE = r'^{indent}"([^"]+)":\s*$'
WORLD_HANDLED_ACTIONS = {"proceed", "combat", "browse_wares"}


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return payload


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def read_project_config() -> dict[str, Any]:
    parser = configparser.ConfigParser(strict=False)
    parser.optionxform = str
    parser.read_string("[root]\n" + read_text(PROJECT_PATH))
    return {
        "name": parser.get("application", "config/name", fallback="unknown").strip('"'),
        "main_scene": parser.get("application", "run/main_scene", fallback="unknown").strip('"'),
        "features": parser.get("application", "config/features", fallback="unknown"),
        "autoloads": list(parser["autoload"].keys()) if parser.has_section("autoload") else [],
        "viewport": "%sx%s" % (
            parser.get("display", "window/size/viewport_width", fallback="?"),
            parser.get("display", "window/size/viewport_height", fallback="?"),
        ),
    }


def get_git_status() -> list[str]:
    try:
        result = subprocess.run(
            ["git", "status", "--short"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return ["git unavailable"]
    if result.returncode != 0:
        return [line for line in result.stderr.splitlines() if line.strip()] or ["git status failed"]
    return [line for line in result.stdout.splitlines() if line.strip()]


def ids_from_array_file(path: Path, key: str) -> set[str]:
    payload = load_json(path)
    records = payload.get(key, [])
    if not isinstance(records, list):
        return set()
    return {str(record.get("id", "")) for record in records if isinstance(record, dict) and record.get("id")}


def implemented_actions() -> set[str]:
    source = read_text(RUN_MANAGER_PATH)
    match_start = source.find("match action_id:")
    if match_start == -1:
        actions: set[str] = set()
    else:
        action_tail = source[match_start:]
        match_line = re.search(r'^([ \t]*)match action_id:\s*$', action_tail, re.MULTILINE)
        first_case = re.search(r'^([ \t]*)"[^"]+":\s*$', action_tail, re.MULTILINE)
        case_indent = first_case.group(1) if first_case else (match_line.group(1) + "\t") if match_line else "\t\t"
        default_re = re.compile(rf'^{re.escape(case_indent)}_:\s*$', re.MULTILINE)
        default_match = default_re.search(action_tail)
        if default_match:
            action_block = action_tail[:default_match.start()]
        else:
            action_block = action_tail
        action_re = re.compile(ACTION_CASE_RE_TEMPLATE.format(indent=re.escape(case_indent)), re.MULTILINE)
        actions = set(action_re.findall(action_block))
    actions.update(WORLD_HANDLED_ACTIONS)
    return actions


def iter_events(events_payload: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    events: list[tuple[str, dict[str, Any]]] = []
    room_events = events_payload.get("room_events", {})
    if isinstance(room_events, dict):
        for room_id, room_event_list in room_events.items():
            if not isinstance(room_event_list, list):
                continue
            for event in room_event_list:
                if isinstance(event, dict):
                    events.append((f"{room_id}/{event.get('id', '<missing-id>')}", event))

    special_events = events_payload.get("special_events", {})
    if isinstance(special_events, dict):
        for event_id, event in special_events.items():
            if isinstance(event, dict):
                events.append((f"special/{event_id}", event))
    return events


def collect_event_facts() -> dict[str, Any]:
    events_payload = load_json(EVENTS_PATH)
    rooms_payload = load_json(ROOMS_PATH)
    decks_payload = load_json(DECKS_PATH)

    rooms = rooms_payload.get("rooms", [])
    room_ids = {str(room.get("id", "")) for room in rooms if isinstance(room, dict) and room.get("id")}
    enemies = ids_from_array_file(ENEMIES_PATH, "enemies")
    mutations = ids_from_array_file(MUTATIONS_PATH, "mutations")
    symbiotes = ids_from_array_file(SYMBIOTES_PATH, "symbiotes")
    actions = implemented_actions()

    unhandled_actions: dict[str, list[str]] = {}
    missing_refs: list[str] = []
    grail_warnings: list[str] = []
    duplicate_event_ids: list[str] = []
    event_ids: set[str] = set()

    for location, event in iter_events(events_payload):
        event_id = str(event.get("id", ""))
        if event_id:
            if event_id in event_ids:
                duplicate_event_ids.append(event_id)
            event_ids.add(event_id)

        for key, known_ids in (
            ("enemy_id", enemies),
            ("mutation_id", mutations),
            ("symbiote_id", symbiotes),
        ):
            ref = str(event.get(key, ""))
            if ref and ref not in known_ids:
                missing_refs.append(f"{location}: unknown {key} '{ref}'")

        if str(event.get("speaker", "")) == "Merchant":
            grail_warnings.append(f"{location}: direct Merchant speaker is legacy; new text should be Hymn narration")

        buttons = event.get("buttons", [])
        if not isinstance(buttons, list):
            continue
        for button in buttons:
            if not isinstance(button, dict):
                continue
            action = str(button.get("action", ""))
            if action and action not in actions:
                unhandled_actions.setdefault(action, []).append(location)
            if action == "take_mutation" and not location.startswith("special/merchant"):
                grail_warnings.append(f"{location}: room-level take_mutation is legacy; new mutations should come through shop/merchant flow")

    return {
        "rooms": sorted(room_ids),
        "event_count": len(iter_events(events_payload)),
        "implemented_actions": sorted(actions),
        "unhandled_actions": unhandled_actions,
        "missing_refs": missing_refs,
        "grail_warnings": grail_warnings,
        "duplicate_event_ids": sorted(duplicate_event_ids),
        "opening_room": str(decks_payload.get("opening_room_id", "")),
        "opening_event": str(decks_payload.get("opening_event_id", "")),
    }


def print_section(title: str) -> None:
    print(f"\n{title}")
    print("-" * len(title))


def print_bootstrap() -> int:
    config = read_project_config()
    facts = collect_event_facts()
    status = get_git_status()

    print("Fleshpunk: Inner Heart bootstrap")

    print_section("Project")
    print(f"Root: {ROOT}")
    print(f"Name: {config['name']}")
    print(f"Main scene: {config['main_scene']}")
    print(f"Autoloads: {', '.join(config['autoloads']) or 'none'}")
    print(f"Viewport: {config['viewport']}")
    print(f"Opening: {facts['opening_room']} / {facts['opening_event']}")

    print_section("Core Files")
    for path in (
        "world.gd",
        "run_manager.gd",
        "fleshpunk_dashboard.gd",
        "combat_system.gd",
        "heart_manager.gd",
        "events.json",
        "room_dialogue.json",
        "encounter_decks.json",
    ):
        print(f"- {path}")

    print_section("Data Summary")
    print(f"Rooms: {len(facts['rooms'])} ({', '.join(facts['rooms'])})")
    print(f"Events: {facts['event_count']}")
    print(f"Implemented actions: {len(facts['implemented_actions'])}")

    print_section("Current Gaps")
    gap_count = 0
    if facts["duplicate_event_ids"]:
        gap_count += len(facts["duplicate_event_ids"])
        print("Duplicate event ids:")
        for event_id in facts["duplicate_event_ids"]:
            print(f"- {event_id}")
    if facts["missing_refs"]:
        gap_count += len(facts["missing_refs"])
        print("Missing references:")
        for issue in facts["missing_refs"]:
            print(f"- {issue}")
    if facts["unhandled_actions"]:
        gap_count += len(facts["unhandled_actions"])
        print("Unhandled button actions:")
        for action, locations in sorted(facts["unhandled_actions"].items()):
            sample = locations[0]
            extra = "" if len(locations) == 1 else f" (+{len(locations) - 1} more)"
            print(f"- {action}: {sample}{extra}")
    if gap_count == 0:
        print("No duplicate ids, missing refs, or unhandled button actions found.")

    print_section("Grail Warnings")
    if facts["grail_warnings"]:
        for warning in facts["grail_warnings"]:
            print(f"- {warning}")
    else:
        print("No vibe/current-state conflicts found.")

    print_section("Worktree")
    if status:
        for line in status:
            print(f"- {line}")
    else:
        print("Clean")

    print_section("Useful Commands")
    print("python tools/project_bootstrap.py --strict")
    print("python tools/scenario_agent.py context")
    print("python tools/scenario_agent.py validate generated/scenario_patch.json")
    print("../bin/godot --headless --quit --path .")

    return 1 if gap_count else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true", help="Exit nonzero when gaps are found.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = print_bootstrap()
    return result if args.strict else 0


if __name__ == "__main__":
    raise SystemExit(main())
