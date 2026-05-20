#!/usr/bin/env python3
"""Generate and critique one legacy room migration candidate at a time."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import scenario_agent


ROOT = Path(__file__).resolve().parents[1]
GENERATED_DIR = ROOT / "generated"


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def read_text(path: Path, limit: int = 16000) -> str:
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    return text[:limit]


def legacy_room(room_id: str) -> dict[str, Any]:
    rooms = load_json(ROOT / "room_dialogue.json").get("rooms", [])
    for room in rooms:
        if isinstance(room, dict) and room.get("id") == room_id:
            return room
    raise SystemExit(f"Unknown legacy room '{room_id}'")


def legacy_events(room_id: str) -> list[dict[str, Any]]:
    events = load_json(ROOT / "events.json").get("room_events", {}).get(room_id, [])
    return [event for event in events if isinstance(event, dict)]


def active_examples() -> dict[str, Any]:
    rooms = load_json(ROOT / "rooms_post_update.json").get("rooms", [])
    events = load_json(ROOT / "events_post_update.json").get("room_events", {})
    return {
        "rooms": [room for room in rooms[:3] if isinstance(room, dict)],
        "events": {
            room_id: room_events[:1]
            for room_id, room_events in list(events.items())[:4]
            if isinstance(room_events, list)
        },
    }


def candidate_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "design_goal": {"type": "string"},
            "legacy_room_id": {"type": "string"},
            "new_room": {"type": "object"},
            "events": {"type": "array", "items": {"type": "object"}},
            "special_events": {"type": "object"},
            "deck_pools": {"type": "array", "items": {"type": "string"}},
            "migration_notes": {"type": "array", "items": {"type": "string"}},
            "review_questions": {"type": "array", "items": {"type": "string"}},
        },
        "required": [
            "title",
            "design_goal",
            "legacy_room_id",
            "new_room",
            "events",
            "special_events",
            "deck_pools",
            "migration_notes",
            "review_questions",
        ],
        "additionalProperties": False,
    }


def critique_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "accepted": {"type": "boolean"},
            "score": {"type": "integer", "minimum": 0, "maximum": 10},
            "findings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "severity": {"type": "string"},
                        "target": {"type": "string"},
                        "issue": {"type": "string"},
                        "required_fix": {"type": "string"},
                    },
                    "required": ["severity", "target", "issue", "required_fix"],
                    "additionalProperties": False,
                },
            },
            "integration_notes": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["summary", "accepted", "score", "findings", "integration_notes"],
        "additionalProperties": False,
    }


def build_generate_prompt(room_id: str, event_limit: int, required_events: list[str]) -> list[dict[str, str]]:
    system = """
You are the dedicated writing agent for Fleshpunk: Inner Heart.
Generate one legacy room migration candidate as strict JSON.
The main Codex integrator will apply or reject your candidate; do not assume active files are edited.

House voice: empirical observation + accumulated evidence + bodily stakes.
Hymn reports to Chorus. Chorus does not answer in printed text.
Avoid shop/menu language, mystical claims, direct future mechanics, and neutral refusals.
Preserve the legacy room id for compatibility.
Use only existing action ids.
Do not make every room an apparatus. Preserve the legacy room's core role first: enemy, character, symbiote choice, mutation offer, rest, ambush, pool, corridor, toll, or machine. Add only enough setting texture to make that role vivid and playable.
""".strip()
    user = {
        "room_id": room_id,
        "event_limit": event_limit,
        "required_legacy_event_ids": required_events,
        "legacy_room": legacy_room(room_id),
        "legacy_events": legacy_events(room_id),
        "active_examples": active_examples(),
        "existing_actions": sorted(scenario_agent.existing_actions()),
        "event_categories": load_json(ROOT / ".agent-memory" / "event_categories.json").get("categories", []),
        "story_room_contract": read_text(ROOT / ".agent-memory" / "story_room_contract.md"),
        "hymn_corpus_voice": read_text(ROOT / ".agent-memory" / "hymn_corpus_voice.md"),
        "content_strategy": read_text(ROOT / ".agent-memory" / "content_strategy.md"),
        "setting_backbone_excerpt": read_text(ROOT / ".agent-memory" / "setting_backbone.md", limit=10000),
        "lore_critique": load_json(GENERATED_DIR / "legacy_reintegration_lore_critique.json")
        if (GENERATED_DIR / "legacy_reintegration_lore_critique.json").exists()
        else {},
        "fun_critique": load_json(GENERATED_DIR / "legacy_reintegration_fun_critique.json")
        if (GENERATED_DIR / "legacy_reintegration_fun_critique.json").exists()
        else {},
        "hard_requirements": [
            f"Return exactly {event_limit} event records.",
            "If required_legacy_event_ids is non-empty, migrate those legacy events and no others.",
            "Do not invent deck pool names; use only existing active pool names.",
            "If story followups are included, attach them to events using the active post-update event shape.",
            "Do not add extra apparatus/set dressing unless it directly serves the room's legacy role.",
            "For a symbiote room, the core is the body, the organisms, and the bonding/refusal choice.",
        ],
        "active_deck_pools": load_json(ROOT / "encounter_decks_post_update.json").get("room_pools", {}),
        "required_shape": {
            "new_room": [
                "id",
                "environment_id",
                "name",
                "instance_premise",
                "first_visit_description",
                "return_description",
                "tags",
                "source_seed_ids",
                "corpus_influences",
                "faction_ids",
                "storyline_ids",
                "recurring_character_ids",
                "animal_infrastructure",
                "cross_run_story_hooks",
                "environment_echoes",
                "ending_vectors",
                "mutation_hooks",
                "progression_state",
            ],
            "events": [
                "id",
                "type",
                "speaker",
                "line_1",
                "line_2",
                "buttons",
                "action_results",
                "environment_memory_flags",
            ],
        },
    }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(user, indent=2, ensure_ascii=False)},
    ]


def build_critique_prompt(candidate_path: Path) -> list[dict[str, str]]:
    system = """
You are a strict Fleshpunk room migration critic.
Accept only if the candidate is ready for integration with minor mechanical cleanup.
Reject if prose is placeholder, too explanatory, too mystical, not commandable, or lacks post-update room contract metadata.
Return JSON only.
""".strip()
    user = {
        "candidate_path": str(candidate_path),
        "candidate": load_json(candidate_path),
        "existing_actions": sorted(scenario_agent.existing_actions()),
        "story_room_contract": read_text(ROOT / ".agent-memory" / "story_room_contract.md"),
        "hymn_corpus_voice": read_text(ROOT / ".agent-memory" / "hymn_corpus_voice.md"),
        "content_strategy": read_text(ROOT / ".agent-memory" / "content_strategy.md"),
        "lore_critique": load_json(GENERATED_DIR / "legacy_reintegration_lore_critique.json")
        if (GENERATED_DIR / "legacy_reintegration_lore_critique.json").exists()
        else {},
        "fun_critique": load_json(GENERATED_DIR / "legacy_reintegration_fun_critique.json")
        if (GENERATED_DIR / "legacy_reintegration_fun_critique.json").exists()
        else {},
    }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(user, indent=2, ensure_ascii=False)},
    ]


def build_repair_prompt(candidate_path: Path, findings_path: Path) -> list[dict[str, str]]:
    system = """
You are the dedicated Fleshpunk room migration repair writer.
Revise only what is necessary to clear the supplied audit findings.
Keep the same candidate JSON shape, same room id, and same intended event ids unless the findings explicitly require otherwise.
Return the full repaired candidate JSON only.
""".strip()
    user = {
        "candidate_path": str(candidate_path),
        "candidate": load_json(candidate_path),
        "audit_findings": load_json(findings_path),
        "existing_actions": sorted(scenario_agent.existing_actions()),
        "active_examples": active_examples(),
        "story_room_contract": read_text(ROOT / ".agent-memory" / "story_room_contract.md"),
        "hymn_corpus_voice": read_text(ROOT / ".agent-memory" / "hymn_corpus_voice.md"),
        "repair_constraints": [
            "Clear the audit-writing findings without broad rewrite.",
            "Honor the content_strategy anti-overmechanization rule; do not add machinery just to satisfy metadata.",
            "For symbiote events, remember the engine auto-builds specific take buttons from symbiote_choices; any explicit fallback button must not break that behavior.",
            "Avoid probability words like may/might in player-facing lines.",
            "Add concrete accumulated evidence to room description if requested.",
        "Use only existing action ids.",
            "Do not leave story_followups as design notes. Every story_followups event_id must either be removed or have a matching special_events record in the same candidate.",
            "Every special_events record must include id, type, speaker, line_1, line_2, buttons, trigger_key, and reactivate_on_reshuffle=false.",
            "Prefer one to three concrete story follow-ups per room over one follow-up per action. Keep only the strongest delayed beats needed to clear the audit findings.",
            "Use existing actions for special event buttons, usually proceed, retreat, run, or a room-appropriate existing verb.",
            "If a special follow-up is only a one-shot narrative beat with one command, set type to transition so the tradeoff audit does not require fake choices.",
            "Do not add more than one new special event unless the findings explicitly require multiple distinct delayed beats.",
        ],
    }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(user, indent=2, ensure_ascii=False)},
    ]


def cmd_generate(args: argparse.Namespace) -> int:
    out = Path(args.out) if args.out else GENERATED_DIR / f"legacy_room_{args.room}_candidate.json"
    if not out.is_absolute():
        out = ROOT / out
    candidate = scenario_agent.call_openai(
        build_generate_prompt(args.room, args.event_limit, args.required_event),
        args.model,
        candidate_schema(),
        "legacy_room_candidate",
    )
    write_json(out, candidate)
    print(out)
    return 0


def cmd_repair(args: argparse.Namespace) -> int:
    candidate_path = Path(args.candidate)
    if not candidate_path.is_absolute():
        candidate_path = ROOT / candidate_path
    findings_path = Path(args.findings)
    if not findings_path.is_absolute():
        findings_path = ROOT / findings_path
    out = Path(args.out) if args.out else candidate_path
    if not out.is_absolute():
        out = ROOT / out
    repaired = scenario_agent.call_openai(
        build_repair_prompt(candidate_path, findings_path),
        args.model,
        candidate_schema(),
        "legacy_room_candidate_repair",
    )
    write_json(out, repaired)
    print(out)
    return 0


def cmd_critique(args: argparse.Namespace) -> int:
    candidate_path = Path(args.candidate)
    if not candidate_path.is_absolute():
        candidate_path = ROOT / candidate_path
    out = Path(args.out) if args.out else candidate_path.with_name(candidate_path.stem + "_critique.json")
    if not out.is_absolute():
        out = ROOT / out
    critique = scenario_agent.call_openai(
        build_critique_prompt(candidate_path),
        args.model,
        critique_schema(),
        "legacy_room_critique",
    )
    write_json(out, critique)
    print(out)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    generate = sub.add_parser("generate")
    generate.add_argument("room")
    generate.add_argument("--event-limit", type=int, default=2)
    generate.add_argument("--required-event", action="append", default=[])
    generate.add_argument("--out")
    generate.add_argument("--model", default=scenario_agent.DEFAULT_MODEL)
    generate.set_defaults(func=cmd_generate)

    repair = sub.add_parser("repair")
    repair.add_argument("candidate")
    repair.add_argument("--findings", required=True)
    repair.add_argument("--out")
    repair.add_argument("--model", default=scenario_agent.DEFAULT_MODEL)
    repair.set_defaults(func=cmd_repair)

    critique = sub.add_parser("critique")
    critique.add_argument("candidate")
    critique.add_argument("--out")
    critique.add_argument("--model", default=scenario_agent.DEFAULT_MODEL)
    critique.set_defaults(func=cmd_critique)

    return parser


def main() -> int:
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
