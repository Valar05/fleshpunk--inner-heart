#!/usr/bin/env python3
"""Brainstorm deeper mechanics for Fleshpunk actions, mutations, and symbiotes."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import textwrap
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MEMORY_DIR = ROOT / ".agent-memory"
GENERATED_DIR = ROOT / "generated"

LEGACY_EVENTS_PATH = ROOT / "events.json"
LEGACY_ROOMS_PATH = ROOT / "room_dialogue.json"
LEGACY_DECKS_PATH = ROOT / "encounter_decks.json"
POST_UPDATE_EVENTS_PATH = ROOT / "events_post_update.json"
POST_UPDATE_ROOMS_PATH = ROOT / "rooms_post_update.json"
POST_UPDATE_DECKS_PATH = ROOT / "encounter_decks_post_update.json"
EVENTS_PATH = POST_UPDATE_EVENTS_PATH if POST_UPDATE_EVENTS_PATH.exists() else LEGACY_EVENTS_PATH
ROOMS_PATH = POST_UPDATE_ROOMS_PATH if POST_UPDATE_ROOMS_PATH.exists() else LEGACY_ROOMS_PATH
DECKS_PATH = POST_UPDATE_DECKS_PATH if POST_UPDATE_DECKS_PATH.exists() else LEGACY_DECKS_PATH
MUTATIONS_PATH = ROOT / "mutations.json"
SYMBIOTES_PATH = ROOT / "symbiotes.json"
RUN_MANAGER_PATH = ROOT / "run_manager.gd"
SETTING_BACKBONE_PATH = MEMORY_DIR / "setting_backbone.md"

DEFAULT_MODEL = os.environ.get("MECHANICS_AGENT_MODEL", os.environ.get("SCENARIO_AGENT_MODEL", "gpt-5"))
ACTION_CASE_RE_TEMPLATE = r'^{indent}"([^"]+)":\s*$'
WORLD_ACTIONS = {"proceed", "combat", "browse_wares"}
TRADEOFF_EXEMPT_EVENT_TYPES = {"transition"}


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        handle.write("\n")


def ids_from_array_file(path: Path, key: str) -> list[str]:
    payload = load_json(path)
    records = payload.get(key, [])
    if not isinstance(records, list):
        return []
    return [str(record["id"]) for record in records if isinstance(record, dict) and record.get("id")]


def room_ids() -> list[str]:
    return ids_from_array_file(ROOMS_PATH, "rooms")


def mutation_ids() -> list[str]:
    return ids_from_array_file(MUTATIONS_PATH, "mutations")


def symbiote_ids() -> list[str]:
    return ids_from_array_file(SYMBIOTES_PATH, "symbiotes")


def existing_actions() -> set[str]:
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
        action_block = action_tail[:default_match.start()] if default_match else action_tail
        action_re = re.compile(ACTION_CASE_RE_TEMPLATE.format(indent=re.escape(case_indent)), re.MULTILINE)
        actions = set(action_re.findall(action_block))
    actions.update(WORLD_ACTIONS)
    return actions


def handler_body(action_id: str) -> str:
    source = read_text(RUN_MANAGER_PATH)
    pattern = re.compile(rf'^\t\t"{re.escape(action_id)}":\s*$', re.MULTILINE)
    match = pattern.search(source)
    if match is None:
        return ""
    tail = source[match.end():]
    next_case = re.search(r'^\t\t("[^"]+"|_):\s*$', tail, re.MULTILINE)
    return tail[:next_case.start()] if next_case else tail


def iter_events() -> list[tuple[str, str, dict[str, Any]]]:
    events_payload = load_json(EVENTS_PATH)
    events: list[tuple[str, str, dict[str, Any]]] = []
    for room_id, room_events in events_payload.get("room_events", {}).items():
        if not isinstance(room_events, list):
            continue
        for event in room_events:
            if isinstance(event, dict):
                events.append((str(room_id), str(event.get("id", "")), event))
    for event_id, event in events_payload.get("special_events", {}).items():
        if isinstance(event, dict):
            events.append(("special", str(event_id), event))
    return events


def action_usage() -> dict[str, list[dict[str, str]]]:
    usage: dict[str, list[dict[str, str]]] = {}
    for room_id, event_id, event in iter_events():
        buttons = event.get("buttons", [])
        if not isinstance(buttons, list):
            continue
        for button in buttons:
            if not isinstance(button, dict):
                continue
            action = str(button.get("action", ""))
            if not action:
                continue
            usage.setdefault(action, []).append({
                "room_id": room_id,
                "event_id": event_id,
                "label": str(button.get("label", "")),
                "type": str(event.get("type", "")),
            })
    return usage


def action_inventory() -> list[dict[str, Any]]:
    usage = action_usage()
    inventory: list[dict[str, Any]] = []
    for action in sorted(existing_actions() | set(usage.keys())):
        body = handler_body(action)
        body_lines = [line.strip() for line in body.splitlines() if line.strip()]
        state_calls = sorted(set(re.findall(r'_(add_[a-z_]+|apply_player_damage|restore_player_[a-z_]+)\(', body)))
        proposal_bias = "deepen"
        if action in {"proceed", "combat"}:
            proposal_bias = "core_flow"
        elif not body and action in WORLD_ACTIONS:
            proposal_bias = "world_handled"
        elif len(state_calls) <= 1 and len(body_lines) <= 10:
            proposal_bias = "placeholder_candidate"
        elif "event_data.get" in body and len(state_calls) <= 2:
            proposal_bias = "simple_data_tuning"

        inventory.append({
            "action_id": action,
            "usage_count": len(usage.get(action, [])),
            "usages": usage.get(action, [])[:5],
            "state_calls": state_calls,
            "handler_lines": len(body_lines),
            "proposal_bias": proposal_bias,
        })
    return inventory


def load_memory() -> str:
    parts = [
        "# Style Memory\n" + read_text(MEMORY_DIR / "fleshpunk_style.md"),
        "# Setting Backbone\n" + read_text(SETTING_BACKBONE_PATH),
        "# Mechanic Backlog\n" + read_text(MEMORY_DIR / "mechanic_backlog.md"),
    ]
    path = MEMORY_DIR / "accepted_mechanics.jsonl"
    if path.exists():
        lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if lines:
            parts.append("# Recent Accepted Mechanics\n" + "\n".join(lines[-8:]))
    path = MEMORY_DIR / "rejected_mechanics.jsonl"
    if path.exists():
        lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if lines:
            parts.append("# Recent Rejected Mechanics\n" + "\n".join(lines[-8:]))
    return "\n\n".join(parts)


def game_context() -> dict[str, Any]:
    decks = load_json(DECKS_PATH)
    mutations = load_json(MUTATIONS_PATH).get("mutations", [])
    symbiotes = load_json(SYMBIOTES_PATH).get("symbiotes", [])
    return {
        "rooms": room_ids(),
        "actions": action_inventory(),
        "single_choice_room_gaps": room_tradeoff_findings(),
        "room_depth_gaps": room_depth_findings(),
        "existing_mutation_ids": mutation_ids(),
        "existing_symbiote_ids": symbiote_ids(),
        "mutations": mutations if isinstance(mutations, list) else [],
        "symbiotes": symbiotes if isinstance(symbiotes, list) else [],
        "base_player_stats": decks.get("base_player_stats", {}),
        "existing_resources": {
            "biomass": "currency/reward counter",
            "corruption": "risk/escalation counter",
            "danger": "encounter pressure counter that raises BPM",
            "health": "player survivability",
            "shield": "pre-health buffer",
        },
    }


def room_tradeoff_findings() -> list[dict[str, Any]]:
    payload = load_json(EVENTS_PATH)
    findings: list[dict[str, Any]] = []
    room_events = payload.get("room_events", {})
    if not isinstance(room_events, dict):
        return findings

    for room_id, events in room_events.items():
        if not isinstance(events, list):
            continue
        for event in events:
            if not isinstance(event, dict):
                continue
            event_type = str(event.get("type", ""))
            if event_type in TRADEOFF_EXEMPT_EVENT_TYPES:
                continue
            buttons = event.get("buttons", [])
            commandable_buttons = sum(1 for button in buttons if isinstance(button, dict)) if isinstance(buttons, list) else 0
            if event_type == "symbiote":
                symbiote_choices = event.get("symbiote_choices", [])
                if isinstance(symbiote_choices, list):
                    commandable_buttons += sum(1 for choice in symbiote_choices if str(choice) != "")
            if commandable_buttons < 2:
                findings.append({
                    "room_id": str(room_id),
                    "event_id": str(event.get("id", "unknown")),
                    "event_type": event_type or "unknown",
                    "button_count": commandable_buttons,
                    "label": str(event.get("line_1", "")),
                })
    return findings


def has_delayed_consequence(event: dict[str, Any]) -> bool:
    delayed_keys = {
        "delayed_consequence",
        "reaction",
        "reaction_tags",
        "on_repeat",
        "director_hook",
        "room_state_changes",
        "future_effect",
        "memory_key",
        "pressure_axis",
        "character_state_change",
        "beast_state_change",
        "infrastructure_state_change",
        "story_followups",
    }
    if any(key in event for key in delayed_keys):
        return True
    text = "%s %s" % (event.get("line_1", ""), event.get("line_2", ""))
    return any(term in text.lower() for term in ("later", "again", "return", "remembers", "learns", "claim", "debt", "scent", "future", "next"))


def room_depth_findings() -> list[dict[str, Any]]:
    payload = load_json(EVENTS_PATH)
    findings: list[dict[str, Any]] = []
    room_events = payload.get("room_events", {})
    if not isinstance(room_events, dict):
        return findings

    for room_id, events in room_events.items():
        if not isinstance(events, list):
            continue
        if len(events) < 3:
            findings.append({
                "room_id": str(room_id),
                "issue": "thin room",
                "event_count": len(events),
                "mechanic_need": "Add action/reaction situations and delayed consequence hooks before considering this room complete.",
            })
        if not any(isinstance(event, dict) and has_delayed_consequence(event) for event in events):
            findings.append({
                "room_id": str(room_id),
                "issue": "no delayed consequence hook",
                "event_count": len(events),
                "mechanic_need": "Add room memory, actor state, route state, deck pressure, debt, claim, scent, pursuit, or changed return text.",
            })
    return findings


def brainstorm_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "design_goal": {"type": "string"},
            "target_actions": {"type": "array", "items": {"type": "string"}},
            "action_mechanics": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "action_id": {"type": "string"},
                        "current_problem": {"type": "string"},
                        "proposed_rule": {"type": "string"},
                        "player_facing_summary": {"type": "string"},
                        "state_changes": {"type": "array", "items": {"type": "string"}},
                        "data_fields": {"type": "array", "items": {"type": "string"}},
                        "implementation_notes": {"type": "array", "items": {"type": "string"}},
                        "test_plan": {"type": "array", "items": {"type": "string"}},
                        "risks": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": [
                        "action_id",
                        "current_problem",
                        "proposed_rule",
                        "player_facing_summary",
                        "state_changes",
                        "data_fields",
                        "implementation_notes",
                        "test_plan",
                        "risks",
                    ],
                    "additionalProperties": False,
                },
            },
            "mutation_ideas": {"type": "array", "items": {"type": "object"}},
            "symbiote_ideas": {"type": "array", "items": {"type": "object"}},
            "event_patch_suggestions": {"type": "array", "items": {"type": "object"}},
            "required_engine_changes": {"type": "array", "items": {"type": "string"}},
            "self_critique": {"type": "array", "items": {"type": "string"}},
        },
        "required": [
            "title",
            "design_goal",
            "target_actions",
            "action_mechanics",
            "mutation_ideas",
            "symbiote_ideas",
            "event_patch_suggestions",
            "required_engine_changes",
            "self_critique",
        ],
        "additionalProperties": False,
    }


def build_prompt(args: argparse.Namespace) -> list[dict[str, str]]:
    requested_actions = args.action or []
    system = """
You are a systems designer for a Godot roguelike called Fleshpunk: Inner Heart.
Return one JSON object only.

Your job is to turn placeholder-ish event actions into richer mechanics.
Prefer rules that can be implemented in run_manager.gd and JSON data without a large refactor.
Make every mechanic legible to the player through short result text, but do not stop at stat consequences.
Prioritize action/reaction loops, delayed consequences, room memory, actor state, route state, deck pressure, debt, claim, scent, and pursuit.
Treat characters, beasts, animals, parasites, organs, markets, and tools as interactable infrastructure.
Beasts should not exist only as attacks; give them jobs such as valve, courier, immune sensor, toll collector, route cleaner, womb guard, memory carrier, or living tool.
Mechanics should support setting stories across rooms and runs: faction posture, recurring character traces, animal infrastructure state, altered prices, route memory, and ending pressure.
Use story follow-up insertion for progression: a room event can enqueue a one-shot special event, and character/faction beats should not retrigger in the same run.
Leave explicit hooks for new mutations and symbiotes that interact with the proposed mechanic.
Do not propose a mutation or symbiote as pure stat filler; each one needs a mechanic hook.
Use the current single-choice and room-depth gaps as targets for mechanics that create immediate and delayed tradeoffs.
If you require engine work beyond action handlers or JSON fields, list it in required_engine_changes.
Keep the tone bodily, bio-industrial, and practical.
""".strip()
    user = {
        "request": args.prompt,
        "count": args.count,
        "target_actions": requested_actions,
        "include_mutations": bool(args.include_mutations),
        "include_symbiotes": bool(args.include_symbiotes),
        "game_context": game_context(),
        "memory": load_memory(),
        "output_contract": {
            "format": "mechanics_brainstorm",
            "schema_notes": [
                "action_mechanics should reference existing action ids unless required_engine_changes explains a new action.",
                "mutation_ideas and symbiote_ideas should include id, name, description, mechanic_hook, effects, and required_engine_changes.",
                "event_patch_suggestions should stay descriptive; this tool does not apply patches.",
            ],
        },
    }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(user, indent=2, ensure_ascii=False)},
    ]


def extract_response_text(payload: dict[str, Any]) -> str:
    if isinstance(payload.get("output_text"), str):
        return payload["output_text"]
    chunks: list[str] = []
    for item in payload.get("output", []):
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []):
            if not isinstance(content, dict):
                continue
            if content.get("type") in {"output_text", "text"} and isinstance(content.get("text"), str):
                chunks.append(content["text"])
    return "\n".join(chunks)


def call_openai(messages: list[dict[str, str]], model: str) -> dict[str, Any]:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY is not set. Export it or use --mock.")

    payload = {
        "model": model,
        "input": messages,
        "text": {
            "format": {
                "type": "json_schema",
                "name": "mechanics_brainstorm",
                "strict": False,
                "schema": brainstorm_schema(),
            }
        },
    }
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"OpenAI API error {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"OpenAI API request failed: {exc}") from exc

    text = extract_response_text(json.loads(raw))
    if not text:
        raise SystemExit("OpenAI response did not contain output text.")
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Model returned non-JSON output:\n{text}") from exc


def mock_brainstorm(actions: list[str], include_mutations: bool = True, include_symbiotes: bool = True) -> dict[str, Any]:
    target_actions = actions or ["break_spike_lane", "probe_amber_cache"]
    return {
        "title": "Pressure Debt",
        "design_goal": "Turn simple choice outcomes into short-term pressure management hooks.",
        "target_actions": target_actions,
        "action_mechanics": [
            {
                "action_id": target_actions[0],
                "current_problem": "The action is mostly damage plus biomass, so it resolves and disappears.",
                "proposed_rule": "Breaking a hazard creates a temporary pressure debt. The player gains biomass now, but the next two rooms add danger unless they take a listening or sealing action.",
                "player_facing_summary": "Gain material now, carry a pulse that makes the next rooms louder.",
                "state_changes": ["add biomass", "add pressure_debt counter", "danger rises after future rooms until cleared"],
                "data_fields": ["pressure_debt", "pressure_debt_rooms", "pressure_debt_danger"],
                "implementation_notes": [
                    "Add pending pressure state to RunManager.",
                    "Tick it in advance_to_next_encounter after counting rooms.",
                    "Let calm actions reduce it.",
                ],
                "test_plan": ["Trigger action, advance rooms, verify danger changes and counter clears."],
                "risks": ["Delayed consequences need clear result text or they feel arbitrary."],
            }
        ],
        "mutation_ideas": [
            {
                "id": "pressure_callus",
                "name": "Pressure Callus",
                "description": "First pressure debt each floor converts 1 danger into 2 shield.",
                "mechanic_hook": "pressure_debt",
                "effects": {"danger_to_shield_once_per_floor": 1},
                "required_engine_changes": ["Track per-floor mutation trigger state."],
            }
        ] if include_mutations else [],
        "symbiote_ideas": [
            {
                "id": "vent_lung",
                "name": "Vent Lung",
                "description": "Can inhale one pressure debt and later exhale it as damage in combat.",
                "mechanic_hook": "pressure_debt",
                "effects": {"stores_pressure_debt": 1, "combat_damage_on_release": 4},
                "required_engine_changes": ["Add active symbiote state and optional combat release hook."],
            }
        ] if include_symbiotes else [],
        "event_patch_suggestions": [
            {
                "room_id": "spiked_red_corridor",
                "event_id": "spiked_red_corridor_pressure",
                "changes": ["Add result text warning that breaking the path leaves pressure in the ribs."],
            }
        ],
        "required_engine_changes": [
            "Add delayed pressure_debt state to RunManager.",
            "Add result text when pressure debt ticks down or raises danger.",
        ],
        "self_critique": [
            "This is larger than a simple action handler but creates reusable hooks for items and events.",
            "Needs UI language that explains delayed danger without long tutorial text.",
        ],
    }


def validate_brainstorm(payload: dict[str, Any], allow_new_actions: bool = False) -> list[str]:
    errors: list[str] = []
    required = {
        "title",
        "design_goal",
        "target_actions",
        "action_mechanics",
        "mutation_ideas",
        "symbiote_ideas",
        "event_patch_suggestions",
        "required_engine_changes",
        "self_critique",
    }
    missing = sorted(required - set(payload.keys()))
    for key in missing:
        errors.append(f"missing top-level key: {key}")

    known_actions = existing_actions()
    mechanics = payload.get("action_mechanics", [])
    if not isinstance(mechanics, list) or not mechanics:
        errors.append("action_mechanics must be a non-empty list")
    elif not allow_new_actions:
        for index, mechanic in enumerate(mechanics):
            if not isinstance(mechanic, dict):
                errors.append(f"action_mechanics[{index}] is not an object")
                continue
            action_id = str(mechanic.get("action_id", ""))
            if action_id not in known_actions:
                errors.append(f"unknown action_id in action_mechanics[{index}]: {action_id}")

    for list_key in ("mutation_ideas", "symbiote_ideas"):
        values = payload.get(list_key, [])
        if not isinstance(values, list):
            errors.append(f"{list_key} must be a list")
            continue
        for index, item in enumerate(values):
            if not isinstance(item, dict):
                errors.append(f"{list_key}[{index}] is not an object")
                continue
            for key in ("id", "name", "description", "mechanic_hook", "effects", "required_engine_changes"):
                if key not in item:
                    errors.append(f"{list_key}[{index}] missing {key}")

    return errors


def cmd_context(_: argparse.Namespace) -> int:
    print(json.dumps(game_context(), indent=2, ensure_ascii=False))
    return 0


def cmd_brainstorm(args: argparse.Namespace) -> int:
    GENERATED_DIR.mkdir(exist_ok=True)
    if args.mock:
        payload = mock_brainstorm(args.action or [], args.include_mutations, args.include_symbiotes)
    else:
        payload = call_openai(build_prompt(args), args.model)

    errors = validate_brainstorm(payload, allow_new_actions=args.allow_new_actions)
    if errors:
        payload["_validation_errors"] = errors

    out = Path(args.out) if args.out else GENERATED_DIR / "mechanics_brainstorm.json"
    if not out.is_absolute():
        out = ROOT / out
    write_json(out, payload)
    print(out)
    if errors:
        print("Validation errors:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 2
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    payload = load_json(Path(args.path))
    errors = validate_brainstorm(payload, allow_new_actions=args.allow_new_actions)
    if not errors:
        print("ok")
        return 0
    for error in errors:
        print(error, file=sys.stderr)
    return 1


def cmd_remember(args: argparse.Namespace) -> int:
    payload = load_json(Path(args.path))
    record = {
        "timestamp": dt.datetime.now(dt.UTC).isoformat(),
        "proposal": payload,
        "notes": args.notes or "",
    }
    if args.accepted:
        append_jsonl(MEMORY_DIR / "accepted_mechanics.jsonl", record)
        print("remembered accepted mechanic")
    elif args.rejected:
        append_jsonl(MEMORY_DIR / "rejected_mechanics.jsonl", record)
        print("remembered rejected mechanic")
    else:
        raise SystemExit("Use --accepted or --rejected.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    context = sub.add_parser("context", help="Print mechanics-oriented project context.")
    context.set_defaults(func=cmd_context)

    brainstorm = sub.add_parser("brainstorm", help="Generate a mechanics brainstorm JSON file.")
    brainstorm.add_argument("--action", action="append", help="Existing action id to focus on. Repeatable.")
    brainstorm.add_argument("--count", type=int, default=3, help="Number of mechanic directions to request.")
    brainstorm.add_argument("--prompt", default="Deepen placeholder-ish actions into reusable mechanics.")
    brainstorm.add_argument("--include-mutations", dest="include_mutations", action="store_true", default=True)
    brainstorm.add_argument("--no-mutations", dest="include_mutations", action="store_false")
    brainstorm.add_argument("--include-symbiotes", dest="include_symbiotes", action="store_true", default=True)
    brainstorm.add_argument("--no-symbiotes", dest="include_symbiotes", action="store_false")
    brainstorm.add_argument("--allow-new-actions", action="store_true")
    brainstorm.add_argument("--mock", action="store_true", help="Generate a local sample without calling OpenAI.")
    brainstorm.add_argument("--model", default=DEFAULT_MODEL)
    brainstorm.add_argument("--out", help="Output path.")
    brainstorm.set_defaults(func=cmd_brainstorm)

    validate = sub.add_parser("validate", help="Validate a mechanics brainstorm JSON file.")
    validate.add_argument("path")
    validate.add_argument("--allow-new-actions", action="store_true")
    validate.set_defaults(func=cmd_validate)

    remember = sub.add_parser("remember", help="Record accepted or rejected mechanic feedback.")
    remember.add_argument("path")
    remember.add_argument("--accepted", action="store_true")
    remember.add_argument("--rejected", action="store_true")
    remember.add_argument("--notes", default="")
    remember.set_defaults(func=cmd_remember)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130
    except json.JSONDecodeError as exc:
        print(textwrap.fill(f"JSON error: {exc}", width=88), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
