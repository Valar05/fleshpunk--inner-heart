#!/usr/bin/env python3
"""Generate, validate, apply, and remember Fleshpunk scenario patches."""

from __future__ import annotations

import argparse
import datetime as dt
import http.client
import json
import os
import re
import sys
import textwrap
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MEMORY_DIR = ROOT / ".agent-memory"
GENERATED_DIR = ROOT / "generated"

EVENTS_PATH = ROOT / "events.json"
ROOMS_PATH = ROOT / "room_dialogue.json"
DECKS_PATH = ROOT / "encounter_decks.json"
ENEMIES_PATH = ROOT / "enemies.json"
MUTATIONS_PATH = ROOT / "mutations.json"
SYMBIOTES_PATH = ROOT / "symbiotes.json"
RUN_MANAGER_PATH = ROOT / "run_manager.gd"
CATEGORIES_PATH = MEMORY_DIR / "event_categories.json"
VIBE_GUIDE_PATH = MEMORY_DIR / "vibe_guide.md"
LORE_GUIDE_PATH = MEMORY_DIR / "lore_guide.md"
CRITIQUE_MEMORY_PATH = MEMORY_DIR / "critic_guidance.jsonl"
BALANCE_MEMORY_PATH = MEMORY_DIR / "balance_guidance.jsonl"
FUN_MEMORY_PATH = MEMORY_DIR / "fun_guidance.jsonl"
LORE_MEMORY_PATH = MEMORY_DIR / "lore_guidance.jsonl"
LORE_BRAINSTORM_MEMORY_PATH = MEMORY_DIR / "lore_brainstorm_guidance.jsonl"

DEFAULT_MODEL = os.environ.get("SCENARIO_AGENT_MODEL", "gpt-5")

EXISTING_ACTION_RE = re.compile(r'^\s*"([^"]+)":\s*$', re.MULTILINE)


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        handle.write("\n")


def room_ids() -> list[str]:
    return [str(room["id"]) for room in load_json(ROOMS_PATH).get("rooms", [])]


def mutation_ids() -> list[str]:
    return [str(item["id"]) for item in load_json(MUTATIONS_PATH).get("mutations", [])]


def symbiote_ids() -> list[str]:
    return [str(item["id"]) for item in load_json(SYMBIOTES_PATH).get("symbiotes", [])]


def enemy_ids() -> list[str]:
    return [str(item["id"]) for item in load_json(ENEMIES_PATH).get("enemies", [])]


def event_categories() -> list[dict[str, Any]]:
    payload = load_json(CATEGORIES_PATH) if CATEGORIES_PATH.exists() else {"categories": []}
    categories = payload.get("categories", [])
    if not isinstance(categories, list):
        return []
    return [category for category in categories if isinstance(category, dict)]


def event_category_ids() -> list[str]:
    return [str(category.get("id", "")) for category in event_categories() if category.get("id")]


def get_event_category(category_id: str) -> dict[str, Any]:
    for category in event_categories():
        if str(category.get("id", "")) == category_id:
            return category
    return {}


def existing_event_ids() -> set[str]:
    payload = load_json(EVENTS_PATH)
    ids: set[str] = set()
    for events in payload.get("room_events", {}).values():
        for event in events:
            if isinstance(event, dict):
                ids.add(str(event.get("id", "")))
    for event_id in payload.get("special_events", {}).keys():
        ids.add(str(event_id))
    return ids


def existing_actions() -> set[str]:
    source = read_text(RUN_MANAGER_PATH)
    action_source = source
    if "func _apply_action_effects" in source:
        action_source = source.split("func _apply_action_effects", 1)[1]
        if "func _with_director_lines" in action_source:
            action_source = action_source.split("func _with_director_lines", 1)[0]
        if "func _add_biomass" in action_source:
            action_source = action_source.split("func _add_biomass", 1)[0]
    actions = set(EXISTING_ACTION_RE.findall(action_source))
    actions.update({"proceed", "combat", "browse_wares", "restart_run"})
    return actions


def load_vibe_guide() -> str:
    return read_text(VIBE_GUIDE_PATH)


def load_lore_guide() -> str:
    return read_text(LORE_GUIDE_PATH)


def load_recent_memory(limit: int = 12, include_core_guides: bool = True) -> str:
    parts = []
    if include_core_guides:
        parts.extend(
            [
                "# Vibe Guide\n" + load_vibe_guide(),
                "# Lore Guide\n" + load_lore_guide(),
                "# Style Memory\n" + read_text(MEMORY_DIR / "fleshpunk_style.md"),
                "# Inspiration Sources\n" + read_text(MEMORY_DIR / "inspiration_sources.md"),
                "# Mechanic Backlog\n" + read_text(MEMORY_DIR / "mechanic_backlog.md"),
            ]
        )
    else:
        parts.extend(
            [
                "# Inspiration Sources\n" + read_text(MEMORY_DIR / "inspiration_sources.md"),
                "# Mechanic Backlog\n" + read_text(MEMORY_DIR / "mechanic_backlog.md"),
            ]
        )
    for name in ("accepted_scenarios.jsonl", "rejected_scenarios.jsonl"):
        path = MEMORY_DIR / name
        if not path.exists():
            continue
        lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        recent = lines[-limit:]
        if recent:
            parts.append("# Recent " + name + "\n" + "\n".join(recent))
    if CRITIQUE_MEMORY_PATH.exists():
        lines = [line for line in CRITIQUE_MEMORY_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
        recent = lines[-limit:]
        if recent:
            parts.append("# Critic Guidance\n" + "\n".join(recent))
    if BALANCE_MEMORY_PATH.exists():
        lines = [line for line in BALANCE_MEMORY_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
        recent = lines[-limit:]
        if recent:
            parts.append("# Balance Guidance\n" + "\n".join(recent))
    if FUN_MEMORY_PATH.exists():
        lines = [line for line in FUN_MEMORY_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
        recent = lines[-limit:]
        if recent:
            parts.append("# Fun Guidance\n" + "\n".join(recent))
    if LORE_MEMORY_PATH.exists():
        lines = [line for line in LORE_MEMORY_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
        recent = lines[-limit:]
        if recent:
            parts.append("# Lore Guidance\n" + "\n".join(recent))
    if LORE_BRAINSTORM_MEMORY_PATH.exists():
        lines = [line for line in LORE_BRAINSTORM_MEMORY_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
        recent = lines[-limit:]
        if recent:
            parts.append("# Lore Brainstorm Guidance\n" + "\n".join(recent))
    return "\n\n".join(parts)


def recent_jsonl_block(path: Path, title: str, limit: int = 6) -> str:
    if not path.exists():
        return ""
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    recent = lines[-limit:]
    if not recent:
        return ""
    return "# " + title + "\n" + "\n".join(recent)


def load_lore_brainstorm_memory(limit: int = 6) -> str:
    parts = [
        "# Inspiration Sources\n" + read_text(MEMORY_DIR / "inspiration_sources.md"),
        "# Mechanic Backlog\n" + read_text(MEMORY_DIR / "mechanic_backlog.md"),
    ]
    for path, title in (
        (LORE_MEMORY_PATH, "Lore Guidance"),
        (LORE_BRAINSTORM_MEMORY_PATH, "Lore Brainstorm Guidance"),
        (FUN_MEMORY_PATH, "Fun Guidance"),
    ):
        block = recent_jsonl_block(path, title, limit=limit)
        if block:
            parts.append(block)
    return "\n\n".join(parts)


def game_context() -> dict[str, Any]:
    decks = load_json(DECKS_PATH)
    return {
        "rooms": room_ids(),
        "existing_actions": sorted(existing_actions()),
        "existing_mutations": mutation_ids(),
        "existing_symbiotes": symbiote_ids(),
        "existing_enemies": enemy_ids(),
        "event_categories": event_categories(),
        "base_player_stats": decks.get("base_player_stats", {}),
        "resource_files": {
            "events": "events.json",
            "rooms": "room_dialogue.json",
            "mutations": "mutations.json",
            "symbiotes": "symbiotes.json",
            "enemies": "enemies.json",
        },
    }


def event_type_counts() -> dict[str, int]:
    payload = load_json(EVENTS_PATH)
    counts: dict[str, int] = {}
    for events in payload.get("room_events", {}).values():
        if not isinstance(events, list):
            continue
        for event in events:
            if isinstance(event, dict):
                event_type = str(event.get("type", "unknown"))
                counts[event_type] = counts.get(event_type, 0) + 1
    for event in payload.get("special_events", {}).values():
        if isinstance(event, dict):
            event_type = str(event.get("type", "unknown"))
            counts[event_type] = counts.get(event_type, 0) + 1
    return dict(sorted(counts.items()))


def room_event_counts() -> dict[str, int]:
    payload = load_json(EVENTS_PATH)
    counts: dict[str, int] = {}
    for room_id, events in payload.get("room_events", {}).items():
        counts[str(room_id)] = len(events) if isinstance(events, list) else 0
    return dict(sorted(counts.items()))


def action_balance_notes() -> dict[str, Any]:
    return {
        "danger": {
            "state_meaning": "attention and response pressure",
            "damage_scaling": "player combat damage is multiplied by 1 + danger * 0.5",
            "enemy_pressure_scaling": "at danger_notice_threshold and above, enemy ambush chance and initiative receive small increases",
            "bpm_scaling": "base_bpm + danger * danger_bpm_step",
            "presentation": "at danger_notice_threshold and above, encounter text adds an attention pressure line by event type",
            "actions_that_raise": ["leave_merchant", "run", "overdraw_amber"],
            "actions_that_lower": ["listen_at_green_split", "mark_red_branch"],
        },
        "corruption": {
            "state_meaning": "identity drift and body-system contamination",
            "actions_that_raise": [
                "take_mutation",
                "take_symbiote",
                "drink_pool",
                "harvest_eggs",
                "seal_amber_wound",
                "take_green_tunnel",
                "open_red_artery",
            ],
            "actions_that_lower": ["study_pool"],
            "trigger": "corruption_spike_room appears each corruption_spike_threshold",
        },
        "resources": {
            "biomass_sources": [
                "combat rewards",
                "harvest_eggs",
                "siphon_amber",
                "overdraw_amber",
                "cut_green_spine",
                "open_red_artery",
            ],
            "recovery_sources": ["drink_pool", "seal_amber_wound", "take_green_tunnel"],
        },
        "cadence": {
            "special_events": ["symbiote_every", "merchant_every", "danger_notice_threshold", "corruption_spike_threshold"],
            "deck_shape": ["starter_rooms", "draw_rules", "room_pools"],
        },
        "instrumentation": {
            "choice_log": "run_manager.gd writes action, event, and before/after run state to user://fleshpunk_run_balance_log.jsonl",
        },
    }


def balance_context() -> dict[str, Any]:
    return {
        "deck_config": load_json(DECKS_PATH),
        "event_type_counts": event_type_counts(),
        "room_event_counts": room_event_counts(),
        "actions": sorted(existing_actions()),
        "action_balance_notes": action_balance_notes(),
        "enemies": load_json(ENEMIES_PATH).get("enemies", []),
        "mutations": load_json(MUTATIONS_PATH).get("mutations", []),
        "symbiotes": load_json(SYMBIOTES_PATH).get("symbiotes", []),
        "strict_action_notes": events_file_errors(strict_actions=True),
    }


def fun_context() -> dict[str, Any]:
    events_payload = load_json(EVENTS_PATH)
    room_events = events_payload.get("room_events", {})
    special_events = events_payload.get("special_events", {})
    pressure_axes = {
        "corruption": {
            "desired_role": "Overusing mutations, symbiotes, pools, or invasive body choices should push the clone toward a corruption ending.",
            "current_signals": ["take_mutation", "take_symbiote", "drink_pool", "harvest_eggs", "seal_amber_wound", "take_green_tunnel", "open_red_artery"],
        },
        "danger": {
            "desired_role": "Fleeing, refusing, greedy noise, and avoiding combat should make the organism notice Hymn until the hunter comes.",
            "current_signals": ["leave_merchant", "run", "rush_red_split", "track_hatchling", "disturb_green_spores"],
        },
        "balance": {
            "desired_role": "The best ending should require staying near neutral: enough power to survive, not enough repeated pressure to be claimed by an ending.",
            "current_gap": "Ending routing and explicit imbalance feedback are not implemented yet.",
        },
    }
    return {
        "deck_config": load_json(DECKS_PATH),
        "event_type_counts": event_type_counts(),
        "room_event_counts": room_event_counts(),
        "events": room_events,
        "special_events": special_events,
        "actions": sorted(existing_actions()),
        "pressure_axes": pressure_axes,
        "enemies": load_json(ENEMIES_PATH).get("enemies", []),
        "mutations": load_json(MUTATIONS_PATH).get("mutations", []),
        "symbiotes": load_json(SYMBIOTES_PATH).get("symbiotes", []),
        "strict_action_notes": events_file_errors(strict_actions=True),
    }


def lore_context() -> dict[str, Any]:
    events_payload = load_json(EVENTS_PATH)
    return {
        "vibe_guide": load_vibe_guide(),
        "lore_guide": load_lore_guide(),
        "style_memory": read_text(MEMORY_DIR / "fleshpunk_style.md"),
        "events": events_payload,
        "event_type_counts": event_type_counts(),
        "actions": sorted(existing_actions()),
        "knowledge_rules": {
            "hymn_clone_ignorance": "Hymn does not know she is a clone. Her narration must not state clone facts.",
            "chorus": "Hymn reports to Chorus frequently, asks for instruction or confirmation, and Chorus is never heard directly.",
            "speaker_labels": "No visible speaker labels such as Her:. All displayed text should read as first-person narration.",
            "tts": "Narration should be phrase-based and suitable for Nova voice TTS.",
        },
        "continuity_risks": [
            "Narration revealing clone knowledge directly.",
            "Game-over copy using outside-the-character language.",
            "Corruption endings that are ambiguous instead of showing loss of boundary and agency.",
            "Events that use fleshy imagery without explaining what the organism functionally does.",
            "Merchant scenes that feel like a shop UI instead of a predatory exchange system.",
        ],
        "strict_action_notes": events_file_errors(strict_actions=True),
    }


def lore_brainstorm_context() -> dict[str, Any]:
    event_samples: list[dict[str, Any]] = []
    events_payload = load_json(EVENTS_PATH)
    for room_id, events in events_payload.get("room_events", {}).items():
        if not isinstance(events, list):
            continue
        for event in events:
            if not isinstance(event, dict):
                continue
            event_samples.append(compact_event(str(room_id), event))
    for event_id, event in events_payload.get("special_events", {}).items():
        if isinstance(event, dict):
            sample = compact_event("special_events", event)
            sample["special_event_id"] = str(event_id)
            event_samples.append(sample)
    return {
        "lore_guide": load_lore_guide(),
        "vibe_guide": load_vibe_guide(),
        "style_memory": read_text(MEMORY_DIR / "fleshpunk_style.md"),
        "deck_config": load_json(DECKS_PATH),
        "event_type_counts": event_type_counts(),
        "room_event_counts": room_event_counts(),
        "rooms": load_json(ROOMS_PATH).get("rooms", []),
        "event_samples": event_samples,
        "enemies": load_json(ENEMIES_PATH).get("enemies", []),
        "mutations": load_json(MUTATIONS_PATH).get("mutations", []),
        "symbiotes": load_json(SYMBIOTES_PATH).get("symbiotes", []),
        "actions": sorted(existing_actions()),
        "required_hook_shape": {
            "safe_reveal": "What Hymn can learn now without breaking her knowledge boundary.",
            "deferred_secret": "What remains hidden for later.",
            "gameplay_hook": "The mechanical consequence or opportunity this lore creates.",
            "related_systems": ["danger", "corruption", "merchant", "deck", "enemy", "symbiote", "mutation", "ending", "lore_fragment"],
        },
        "strict_action_notes": events_file_errors(strict_actions=True),
    }


def compact_event(room_id: str, event: dict[str, Any]) -> dict[str, Any]:
    buttons = event.get("buttons", [])
    actions = []
    if isinstance(buttons, list):
        actions = [button.get("action") for button in buttons if isinstance(button, dict) and button.get("action")]
    compact: dict[str, Any] = {
        "room_id": room_id,
        "id": event.get("id"),
        "type": event.get("type"),
        "line_1": event.get("line_1"),
        "line_2": event.get("line_2"),
        "actions": actions,
    }
    for key in ("enemy_id", "scene_path", "symbiote_choices", "mutation_choices", "reactivate_on_reshuffle"):
        if key in event:
            compact[key] = event[key]
    return compact


def patch_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "design_goal": {"type": "string"},
            "events": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "room_id": {"type": "string"},
                        "event": {"type": "object"},
                    },
                    "required": ["room_id", "event"],
                    "additionalProperties": False,
                },
            },
            "mutations": {"type": "array", "items": {"type": "object"}},
            "symbiotes": {"type": "array", "items": {"type": "object"}},
            "enemies": {"type": "array", "items": {"type": "object"}},
            "required_engine_changes": {"type": "array", "items": {"type": "string"}},
            "inspiration_notes": {"type": "array", "items": {"type": "string"}},
            "self_critique": {"type": "array", "items": {"type": "string"}},
        },
        "required": [
            "title",
            "design_goal",
            "events",
            "mutations",
            "symbiotes",
            "enemies",
            "required_engine_changes",
            "inspiration_notes",
            "self_critique",
        ],
        "additionalProperties": False,
    }


def critique_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "vibe_alignment_score": {"type": "integer", "minimum": 0, "maximum": 10},
            "findings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "severity": {"type": "string"},
                        "target": {"type": "string"},
                        "issue": {"type": "string"},
                        "recommendation": {"type": "string"},
                    },
                    "required": ["severity", "target", "issue", "recommendation"],
                    "additionalProperties": False,
                },
            },
            "event_type_suggestions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "label": {"type": "string"},
                        "purpose": {"type": "string"},
                        "why": {"type": "string"},
                    },
                    "required": ["id", "label", "purpose", "why"],
                    "additionalProperties": False,
                },
            },
            "encounter_suggestions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "category": {"type": "string"},
                        "room_id": {"type": "string"},
                        "concept": {"type": "string"},
                        "tradeoff": {"type": "string"},
                        "required_engine_changes": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["category", "room_id", "concept", "tradeoff", "required_engine_changes"],
                    "additionalProperties": False,
                },
            },
            "vibe_doc_updates": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "section": {"type": "string"},
                        "current_gap": {"type": "string"},
                        "suggested_text": {"type": "string"},
                    },
                    "required": ["section", "current_gap", "suggested_text"],
                    "additionalProperties": False,
                },
            },
            "action_system_suggestions": {"type": "array", "items": {"type": "string"}},
            "next_generation_prompt": {"type": "string"},
        },
        "required": [
            "summary",
            "vibe_alignment_score",
            "findings",
            "event_type_suggestions",
            "encounter_suggestions",
            "vibe_doc_updates",
            "action_system_suggestions",
            "next_generation_prompt",
        ],
        "additionalProperties": False,
    }


def balance_critique_schema() -> dict[str, Any]:
    lever_item = {
        "type": "object",
        "properties": {
            "lever": {"type": "string"},
            "current_value": {"type": "string"},
            "run_feel_effect": {"type": "string"},
            "vibe_effect": {"type": "string"},
            "tweak_direction": {"type": "string"},
            "risk": {"type": "string"},
        },
        "required": ["lever", "current_value", "run_feel_effect", "vibe_effect", "tweak_direction", "risk"],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "run_feel_score": {"type": "integer", "minimum": 0, "maximum": 10},
            "vibe_balance_score": {"type": "integer", "minimum": 0, "maximum": 10},
            "balance_findings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "severity": {"type": "string"},
                        "target": {"type": "string"},
                        "issue": {"type": "string"},
                        "recommendation": {"type": "string"},
                    },
                    "required": ["severity", "target", "issue", "recommendation"],
                    "additionalProperties": False,
                },
            },
            "levers": {"type": "array", "items": lever_item},
            "tuning_experiments": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "goal": {"type": "string"},
                        "changes": {"type": "array", "items": {"type": "string"}},
                        "success_signals": {"type": "array", "items": {"type": "string"}},
                        "rollback_signals": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["name", "goal", "changes", "success_signals", "rollback_signals"],
                    "additionalProperties": False,
                },
            },
            "data_patch_suggestions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "file": {"type": "string"},
                        "path": {"type": "string"},
                        "suggested_change": {"type": "string"},
                        "reason": {"type": "string"},
                    },
                    "required": ["file", "path", "suggested_change", "reason"],
                    "additionalProperties": False,
                },
            },
            "instrumentation_suggestions": {"type": "array", "items": {"type": "string"}},
            "vibe_doc_updates": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "section": {"type": "string"},
                        "current_gap": {"type": "string"},
                        "suggested_text": {"type": "string"},
                    },
                    "required": ["section", "current_gap", "suggested_text"],
                    "additionalProperties": False,
                },
            },
            "next_balance_prompt": {"type": "string"},
        },
        "required": [
            "summary",
            "run_feel_score",
            "vibe_balance_score",
            "balance_findings",
            "levers",
            "tuning_experiments",
            "data_patch_suggestions",
            "instrumentation_suggestions",
            "vibe_doc_updates",
            "next_balance_prompt",
        ],
        "additionalProperties": False,
    }


def fun_critique_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "fun_score": {"type": "integer", "minimum": 0, "maximum": 10},
            "organism_pressure_score": {"type": "integer", "minimum": 0, "maximum": 10},
            "core_loop_diagnosis": {"type": "string"},
            "not_fun_findings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "severity": {"type": "string"},
                        "target": {"type": "string"},
                        "why_it_is_not_fun": {"type": "string"},
                        "recommendation": {"type": "string"},
                    },
                    "required": ["severity", "target", "why_it_is_not_fun", "recommendation"],
                    "additionalProperties": False,
                },
            },
            "organism_director_findings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "axis": {"type": "string"},
                        "current_behavior": {"type": "string"},
                        "desired_push": {"type": "string"},
                        "missing_feedback": {"type": "string"},
                        "recommended_change": {"type": "string"},
                    },
                    "required": ["axis", "current_behavior", "desired_push", "missing_feedback", "recommended_change"],
                    "additionalProperties": False,
                },
            },
            "decision_loop_rewrites": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "loop": {"type": "string"},
                        "current_problem": {"type": "string"},
                        "fun_version": {"type": "string"},
                        "needed_system_hooks": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["loop", "current_problem", "fun_version", "needed_system_hooks"],
                    "additionalProperties": False,
                },
            },
            "ending_pressure_plan": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "ending": {"type": "string"},
                        "player_pattern_that_drives_it": {"type": "string"},
                        "warnings_before_lock": {"type": "array", "items": {"type": "string"}},
                        "lock_condition": {"type": "string"},
                    },
                    "required": ["ending", "player_pattern_that_drives_it", "warnings_before_lock", "lock_condition"],
                    "additionalProperties": False,
                },
            },
            "content_priorities": {"type": "array", "items": {"type": "string"}},
            "system_priorities": {"type": "array", "items": {"type": "string"}},
            "vibe_doc_updates": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "section": {"type": "string"},
                        "current_gap": {"type": "string"},
                        "suggested_text": {"type": "string"},
                    },
                    "required": ["section", "current_gap", "suggested_text"],
                    "additionalProperties": False,
                },
            },
            "next_fun_prompt": {"type": "string"},
        },
        "required": [
            "summary",
            "fun_score",
            "organism_pressure_score",
            "core_loop_diagnosis",
            "not_fun_findings",
            "organism_director_findings",
            "decision_loop_rewrites",
            "ending_pressure_plan",
            "content_priorities",
            "system_priorities",
            "vibe_doc_updates",
            "next_fun_prompt",
        ],
        "additionalProperties": False,
    }


def lore_critique_schema() -> dict[str, Any]:
    finding_item = {
        "type": "object",
        "properties": {
            "severity": {"type": "string"},
            "target": {"type": "string"},
            "issue": {"type": "string"},
            "rewrite_direction": {"type": "string"},
        },
        "required": ["severity", "target", "issue", "rewrite_direction"],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "lore_integrity_score": {"type": "integer", "minimum": 0, "maximum": 10},
            "voice_integrity_score": {"type": "integer", "minimum": 0, "maximum": 10},
            "continuity_findings": {"type": "array", "items": finding_item},
            "voice_findings": {"type": "array", "items": finding_item},
            "knowledge_boundary_findings": {"type": "array", "items": finding_item},
            "chorus_usage_plan": {"type": "array", "items": {"type": "string"}},
            "lore_expansion_seeds": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "topic": {"type": "string"},
                        "purpose": {"type": "string"},
                        "safe_reveal": {"type": "string"},
                        "deferred_secret": {"type": "string"},
                    },
                    "required": ["topic", "purpose", "safe_reveal", "deferred_secret"],
                    "additionalProperties": False,
                },
            },
            "rewrite_priorities": {"type": "array", "items": {"type": "string"}},
            "vibe_doc_updates": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "section": {"type": "string"},
                        "current_gap": {"type": "string"},
                        "suggested_text": {"type": "string"},
                    },
                    "required": ["section", "current_gap", "suggested_text"],
                    "additionalProperties": False,
                },
            },
            "next_lore_prompt": {"type": "string"},
        },
        "required": [
            "summary",
            "lore_integrity_score",
            "voice_integrity_score",
            "continuity_findings",
            "voice_findings",
            "knowledge_boundary_findings",
            "chorus_usage_plan",
            "lore_expansion_seeds",
            "rewrite_priorities",
            "vibe_doc_updates",
            "next_lore_prompt",
        ],
        "additionalProperties": False,
    }


def lore_brainstorm_schema() -> dict[str, Any]:
    concept_item = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "kind": {"type": "string"},
            "pitch": {"type": "string"},
            "safe_reveal": {"type": "string"},
            "hymn_misread": {"type": "string"},
            "deferred_secret": {"type": "string"},
            "gameplay_hook": {"type": "string"},
            "related_systems": {"type": "array", "items": {"type": "string"}},
            "sample_fragment": {"type": "string"},
            "implementation_notes": {"type": "array", "items": {"type": "string"}},
        },
        "required": [
            "name",
            "kind",
            "pitch",
            "safe_reveal",
            "hymn_misread",
            "deferred_secret",
            "gameplay_hook",
            "related_systems",
            "sample_fragment",
            "implementation_notes",
        ],
        "additionalProperties": False,
    }
    relationship_item = {
        "type": "object",
        "properties": {
            "a": {"type": "string"},
            "b": {"type": "string"},
            "visible_relationship": {"type": "string"},
            "hidden_truth": {"type": "string"},
            "gameplay_expression": {"type": "string"},
        },
        "required": ["a", "b", "visible_relationship", "hidden_truth", "gameplay_expression"],
        "additionalProperties": False,
    }
    reveal_path_item = {
        "type": "object",
        "properties": {
            "thread": {"type": "string"},
            "early_reveal": {"type": "string"},
            "mid_reveal": {"type": "string"},
            "late_reveal": {"type": "string"},
            "player_pressure": {"type": "string"},
            "ending_connection": {"type": "string"},
        },
        "required": ["thread", "early_reveal", "mid_reveal", "late_reveal", "player_pressure", "ending_connection"],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "design_thesis": {"type": "string"},
            "factions": {"type": "array", "items": concept_item},
            "recurring_characters": {"type": "array", "items": concept_item},
            "organism_lore": {"type": "array", "items": concept_item},
            "lore_fragments": {"type": "array", "items": concept_item},
            "relationships": {"type": "array", "items": relationship_item},
            "reveal_paths": {"type": "array", "items": reveal_path_item},
            "mechanic_hooks": {"type": "array", "items": {"type": "string"}},
            "guardrails": {"type": "array", "items": {"type": "string"}},
            "next_lore_prompt": {"type": "string"},
        },
        "required": [
            "summary",
            "design_thesis",
            "factions",
            "recurring_characters",
            "organism_lore",
            "lore_fragments",
            "relationships",
            "reveal_paths",
            "mechanic_hooks",
            "guardrails",
            "next_lore_prompt",
        ],
        "additionalProperties": False,
    }


def build_prompt(args: argparse.Namespace) -> list[dict[str, str]]:
    context = game_context()
    room = args.room or "any existing room"
    category = args.category or "any defined category"
    category_rules = get_event_category(args.category) if args.category else {}
    system = """
You are a scenario designer for a Godot roguelike called Fleshpunk: Inner Heart.
Generate JSON patches only. Do not write prose outside the JSON object.

Your scenarios should fit the existing data-driven event system:
- Add events under events.json room_events[room_id].
- Each event should include id, type, speaker, line_1, line_2, and buttons.
- Event type must be one of the defined category ids.
- Buttons need label and action.
- Prefer existing actions unless the user explicitly asks for new mechanics.
- If you invent an action, include it in required_engine_changes and explain what run_manager.gd must do.
- Keep UI text short and playable.
- Follow the vibe guide: first-person internal field report, short clipped phrasing, purpose-built biology, reactive systems, transactional choices.
- Do not write visible speaker labels such as Her:. Use first-person narration only; if speaker metadata is required, use Hymn.
- Use inspiration structurally, never as copied text.
""".strip()
    if not args.allow_new_actions:
        system += "\n- Do not invent new actions. Use existing actions only."

    user = {
        "request": args.prompt,
        "target_room": room,
        "target_category": category,
        "target_category_rules": category_rules,
        "count": args.count,
        "allow_new_actions": bool(args.allow_new_actions),
        "game_context": context,
        "memory": load_recent_memory(),
        "output_contract": {
            "format": "scenario_patch",
            "schema_notes": [
                "events is a list of {room_id, event}",
                "event may include existing keys such as mutation_id, symbiote_id, enemy_id, damage, heal, shield, biomass",
                "required_engine_changes must be empty if only existing actions are used",
            ],
        },
    }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(user, indent=2, ensure_ascii=False)},
    ]


def build_critique_prompt(args: argparse.Namespace) -> list[dict[str, str]]:
    target_payload: dict[str, Any]
    if args.patch:
        target_payload = {
            "kind": "scenario_patch",
            "path": args.patch,
            "content": load_patch(Path(args.patch)),
        }
    else:
        target_payload = {
            "kind": "current_events",
            "path": "events.json",
            "content": load_json(EVENTS_PATH),
        }

    system = """
You are a strict creative director and systems designer for Fleshpunk: Inner Heart.
Critique content against the vibe guide and existing mechanics.
Return JSON only.

Critique priorities:
- Does each event read like first-person degraded field-report monologue?
- Is the object purpose-built, reactive, and transactional?
- Does the choice create hesitation through a clear tradeoff?
- Are buttons instructions to the character rather than spoken dialogue?
- Are proposed additions implementable with current actions, or clearly marked as engine work?
- Suggest new event categories, encounter patterns, mechanics, and vibe-guide updates only when they clarify future generation.
""".strip()

    user = {
        "focus": args.focus,
        "vibe_guide": load_vibe_guide(),
        "game_context": game_context(),
        "strict_action_notes": events_file_errors(strict_actions=True),
        "target": target_payload,
        "output_contract": {
            "summary": "Brief overall judgement.",
            "vibe_alignment_score": "0-10 integer.",
            "findings": "Concrete issues and fixes, ordered by severity.",
            "event_type_suggestions": "New broad categories only if useful.",
            "encounter_suggestions": "Playable concepts with tradeoffs.",
            "vibe_doc_updates": "Suggested additions or clarifications for the guide.",
            "action_system_suggestions": "Engine/action changes that would unlock better choices.",
            "next_generation_prompt": "A compact prompt to feed back into generate.",
        },
    }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(user, indent=2, ensure_ascii=False)},
    ]


def build_balance_critique_prompt(args: argparse.Namespace) -> list[dict[str, str]]:
    system = """
You are a balance critic for Fleshpunk: Inner Heart.
Evaluate run feel through the vibe guide: pressure, transaction, hesitation, attention, and bodily cost.
Return JSON only.

Balance priorities:
- Does danger feel like the system noticing the player, not just a difficulty number?
- Do corruption, biomass, health, shield, mutations, and symbiotes create real tradeoffs?
- Does deck cadence create descent pressure without pure repetition?
- Do rewards and recovery carry cost, contamination, attention, or future pressure?
- Are combat and non-combat choices both viable but never clean?
- Suggest conservative tuning experiments first. Prefer data tweaks before new systems.
""".strip()

    user = {
        "focus": args.focus,
        "vibe_guide": load_vibe_guide(),
        "balance_context": balance_context(),
        "memory": load_recent_memory(),
        "output_contract": {
            "summary": "Short judgement of current run feel.",
            "run_feel_score": "0-10 score for play pressure, cadence, and decision texture.",
            "vibe_balance_score": "0-10 score for whether the balance supports the vibe guide.",
            "balance_findings": "Concrete risks and recommendations.",
            "levers": "Specific knobs to tweak and expected run-feel effects.",
            "tuning_experiments": "Small experiments with success and rollback signals.",
            "data_patch_suggestions": "Concrete data/script change suggestions, not applied automatically.",
            "instrumentation_suggestions": "Metrics/logs to add before heavier tuning.",
            "vibe_doc_updates": "Balance-oriented guide additions.",
            "next_balance_prompt": "Compact prompt for the next balance critique.",
        },
    }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(user, indent=2, ensure_ascii=False)},
    ]


def build_fun_critique_prompt(args: argparse.Namespace) -> list[dict[str, str]]:
    system = """
You are the fun-factor critic for Fleshpunk: Inner Heart.
Your job is not to praise vibe. Your job is to find why the run is not fun yet.
Return JSON only.

Fun-factor doctrine:
- The living organism is the director of the run.
- Its job is to notice player patterns, unbalance the player, and push the clone toward an outcome.
- Every repeated decision should create a gravitational pull: corruption, danger/hunter, starvation, injury, debt, or a narrowed route.
- Taking too many mutations raises corruption and pushes the corruption ending.
- Fleeing or dodging too much combat raises danger until the hunter comes.
- Greedy extraction, repeated healing, repeated refusal, repeated bonding, and repeated safety should each have a pressure track or explicit cost.
- The best ending should require balance and neutrality, not maximal power or maximal avoidance.
- Critique whether the game has a repeatable loop of temptation, pressure, feedback, adaptation, and payoff.
- Prefer concrete loop/system/content fixes over broad mood advice.
""".strip()

    user = {
        "focus": args.focus,
        "vibe_guide": load_vibe_guide(),
        "memory": load_recent_memory(),
        "fun_context": fun_context(),
        "output_contract": {
            "summary": "Blunt judgement of current fun factor.",
            "fun_score": "0-10 score for whether the current game loop creates desire to keep playing.",
            "organism_pressure_score": "0-10 score for whether the organism behaves like a director that pushes outcomes.",
            "core_loop_diagnosis": "One paragraph naming the current loop and why it fails or works.",
            "not_fun_findings": "Concrete reasons the current game feels like stats instead of a living organism.",
            "organism_director_findings": "How each pressure axis should notice and push repeated decisions.",
            "decision_loop_rewrites": "Specific loops to rewrite, such as mutation shopping, combat avoidance, extraction, healing, symbiote dependence.",
            "ending_pressure_plan": "How player patterns warn, then lock, into endings.",
            "content_priorities": "Content to add first for fun, not just lore.",
            "system_priorities": "Engine/data hooks that create the fun loop.",
            "vibe_doc_updates": "Guide additions that prevent future content from becoming stat soup.",
            "next_fun_prompt": "Compact prompt for the next fun critique.",
        },
    }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(user, indent=2, ensure_ascii=False)},
    ]


def build_lore_critique_prompt(args: argparse.Namespace) -> list[dict[str, str]]:
    system = """
You are the lore master for Fleshpunk: Inner Heart.
Your job is to preserve flavor, continuity, mystery discipline, and knowledge boundaries.
Return JSON only.

Lore doctrine:
- Hymn narrates first person and does not know she is a clone.
- Never let Hymn explain the run structure, clone premise, or future instances.
- Hymn reports to Chorus frequently, asking for instruction, confirmation, signal checks, or acknowledgement.
- Chorus is never heard directly.
- Visible narration should not include speaker labels such as Her:.
- Corruption should read as bodily boundary loss and agency drift, not as a vague bad ending.
- The merchant is a predatory exchange system and future big bad, not a friendly shopkeeper.
- Lore fragments can reveal the world, cult, organism, facility, and Chorus relationship, but each reveal should carry a secondary effect or cost.
- Expand context through concrete fragments, functional biology, and operational reports. Avoid lore dumps.
""".strip()

    user = {
        "focus": args.focus,
        "lore_context": lore_context(),
        "memory": load_recent_memory(),
        "output_contract": {
            "summary": "Short lore-master judgement.",
            "lore_integrity_score": "0-10 score for continuity and world coherence.",
            "voice_integrity_score": "0-10 score for Hymn/Chorus narration discipline.",
            "continuity_findings": "Lore or world-rule problems.",
            "voice_findings": "Narration, phrasing, speaker-label, or TTS problems.",
            "knowledge_boundary_findings": "Places where Hymn knows too much or the narration leaks meta truth.",
            "chorus_usage_plan": "Concrete places and patterns for Chorus reports.",
            "lore_expansion_seeds": "New lore topics with safe reveals and deferred secrets.",
            "rewrite_priorities": "Highest-value text rewrites.",
            "vibe_doc_updates": "Additions to the guide that prevent drift.",
            "next_lore_prompt": "Compact prompt for the next lore pass.",
        },
    }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(user, indent=2, ensure_ascii=False)},
    ]


def build_lore_brainstorm_prompt(args: argparse.Namespace) -> list[dict[str, str]]:
    system = """
You are the lore brainstormer for Fleshpunk: Inner Heart.
Your job is to create usable story architecture: factions, recurring characters, relationships, lore fragments, reveal paths, and gameplay hooks.
Return JSON only.

Brainstorm doctrine:
- New lore must create gameplay pressure, future content, or ending texture.
- Never make lore a standalone encyclopedia entry.
- Each concept must include a safe reveal, Hymn misread, deferred secret, and gameplay hook.
- Hymn does not know she is a clone. Do not put clone facts in sample first-person narration.
- Hymn reports to Chorus. Chorus is never heard directly.
- Do not write visible speaker labels such as Her:. Keep sample fragments in first person.
- The merchant is a predatory exchange system and future big bad.
- The organism is a living director that notices repeated player behavior and pushes outcomes.
- Prefer concrete factions, recurring figures, and relationship tensions over generic atmosphere.
""".strip()

    user = {
        "focus": args.focus,
        "count": args.count,
        "lore_brainstorm_context": lore_brainstorm_context(),
        "memory": load_lore_brainstorm_memory(),
        "output_contract": {
            "summary": "Short judgement of the brainstorm direction.",
            "design_thesis": "One sentence tying the lore ideas into gameplay.",
            "factions": "Faction concepts, each with reveal boundaries and hooks.",
            "recurring_characters": "Recurring figures or voices, not necessarily dialogue NPCs.",
            "organism_lore": "Ideas about the organism, facility, ecology, and response logic.",
            "lore_fragments": "Findable fragments with secondary effects or costs.",
            "relationships": "Interconnected relationships with visible and hidden layers.",
            "reveal_paths": "Early/mid/late reveal paths tied to pressure and endings.",
            "mechanic_hooks": "Concrete systems these ideas suggest.",
            "guardrails": "Rules to preserve mystery and prevent lore drift.",
            "next_lore_prompt": "Compact prompt for the next brainstorm or generation pass.",
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


def call_openai(
    messages: list[dict[str, str]],
    model: str,
    output_schema: dict[str, Any],
    schema_name: str,
) -> dict[str, Any]:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY is not set. Export it or use --mock.")

    max_output_tokens = int(os.environ.get("SCENARIO_AGENT_MAX_OUTPUT_TOKENS", "6000"))
    reasoning_effort = os.environ.get("SCENARIO_AGENT_REASONING_EFFORT", "minimal")
    request_payload = {
        "model": model,
        "input": messages,
        "max_output_tokens": max_output_tokens,
        "text": {
            "format": {
                "type": "json_schema",
                "name": schema_name,
                "strict": False,
                "schema": output_schema,
            }
        },
    }
    if reasoning_effort and reasoning_effort.lower() != "none" and (model.startswith("gpt-5") or model.startswith("o")):
        request_payload["reasoning"] = {"effort": reasoning_effort}
    data = json.dumps(request_payload).encode("utf-8")
    raw = ""
    errors: list[str] = []
    attempts = int(os.environ.get("SCENARIO_AGENT_API_ATTEMPTS", "3"))
    timeout = int(os.environ.get("SCENARIO_AGENT_API_TIMEOUT", "240"))
    for attempt in range(1, attempts + 1):
        request = urllib.request.Request(
            "https://api.openai.com/v1/responses",
            data=data,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "fleshpunk-scenario-agent/1.0",
                "Connection": "close",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read().decode("utf-8")
            break
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise SystemExit(f"OpenAI API error {exc.code}: {body}") from exc
        except urllib.error.URLError as exc:
            errors.append(f"attempt {attempt}: request failed: {exc}")
        except (http.client.HTTPException, TimeoutError) as exc:
            errors.append(f"attempt {attempt}: connection failed: {exc}")
        if attempt < attempts:
            time.sleep(min(2 ** attempt, 8))
    if not raw:
        detail = "\n".join(errors) if errors else "no response body"
        raise SystemExit(
            "OpenAI API connection failed after "
            f"{attempts} attempts. model={model} schema={schema_name} "
            f"payload_bytes={len(data)} max_output_tokens={max_output_tokens}\n{detail}"
        )

    try:
        response_payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"OpenAI response was not JSON:\n{raw[:2000]}") from exc

    text = extract_response_text(response_payload)
    if not text:
        raise SystemExit(f"OpenAI response did not contain output text:\n{raw[:2000]}")
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Model returned non-JSON output:\n{text}") from exc


def mock_patch(room: str, category: str = "choice") -> dict[str, Any]:
    return {
        "title": "The Listening Valve",
        "design_goal": "Add one compact risk-reward event using existing actions.",
        "events": [
            {
                "room_id": room,
                "event": {
                    "id": f"{room}_listening_valve",
                    "type": category,
                    "speaker": "Hymn",
                    "line_1": "A valve in the wall opens when I breathe near it.",
                    "line_2": "It sounds hungry, but the pulse behind it is clean.",
                    "buttons": [
                        {"label": "Drink the clean pulse", "action": "drink_pool"},
                        {"label": "Study the rhythm", "action": "study_pool"},
                        {"label": "Back away", "action": "retreat"},
                    ],
                },
            }
        ],
        "mutations": [],
        "symbiotes": [],
        "enemies": [],
        "required_engine_changes": [],
        "inspiration_notes": ["Uses shrine/fountain event structure without copying any source."],
        "self_critique": ["Safe first patch; it reuses healing-pool actions, so no engine change is needed."],
    }


def mock_critique() -> dict[str, Any]:
    return {
        "summary": "Offline critique sample. The pass is focused on vibe fit, choice pressure, and future mechanics.",
        "vibe_alignment_score": 7,
        "findings": [
            {
                "severity": "medium",
                "target": "events.json",
                "issue": "Several older choices use placeholder actions, so the button promises more than the engine currently resolves.",
                "recommendation": "Either implement those actions or retune the buttons to existing actions before using them as generation examples.",
            },
            {
                "severity": "medium",
                "target": "event voice",
                "issue": "Some lines are descriptive but not yet field-report sharp.",
                "recommendation": "Prefer contact reports: object, function, risk, decision. Keep emotion as a second beat.",
            },
        ],
        "event_type_suggestions": [
            {
                "id": "echo",
                "label": "Delayed Echo",
                "purpose": "A prior choice returns as a later room consequence.",
                "why": "The vibe guide says every decision should echo forward.",
            }
        ],
        "encounter_suggestions": [
            {
                "category": "hazard",
                "room_id": "spiked_red_corridor",
                "concept": "A pressure valve marks the player and makes the next two rooms more reactive.",
                "tradeoff": "Take damage now to lower danger, or leave pressure rising for later.",
                "required_engine_changes": ["Track short-lived room-count consequences from actions."],
            }
        ],
        "vibe_doc_updates": [
            {
                "section": "Event Design Philosophy",
                "current_gap": "Delayed consequences are a goal but not yet described as a reusable event shape.",
                "suggested_text": "Some choices should create delayed echoes: a cost, pursuer, merchant reaction, or room mutation that appears one to three rooms later.",
            }
        ],
        "action_system_suggestions": [
            "Add an action-result field for delayed effects measured in rooms.",
            "Add merchant barter actions once shop content becomes real.",
        ],
        "next_generation_prompt": "Generate one hazard event with a readable immediate cost and one delayed echo. Use existing actions unless engine changes are explicitly requested.",
    }


def mock_balance_critique() -> dict[str, Any]:
    return {
        "summary": "Offline balance sample. Current levers can already shape pressure, recovery, and attention without new UI.",
        "run_feel_score": 6,
        "vibe_balance_score": 7,
        "balance_findings": [
            {
                "severity": "medium",
                "target": "danger scaling",
                "issue": "Danger is powerful but narrow: it boosts player combat damage and BPM, while several danger increases are framed as pressure.",
                "recommendation": "Decide whether danger is attention, tempo, or aggression. Then make its effects match that identity.",
            },
            {
                "severity": "medium",
                "target": "resource actions",
                "issue": "Biomass gains are easy to tune, but there is little persistent room-state consequence.",
                "recommendation": "Use damage, corruption, danger, and room cadence as first-pass costs before adding new systems.",
            },
        ],
        "levers": [
            {
                "lever": "danger_notice_threshold",
                "current_value": str(load_json(DECKS_PATH).get("danger_notice_threshold", "")),
                "run_feel_effect": "Controls how often the game reminds the player the system has noticed them.",
                "vibe_effect": "Lower values make the living machine feel more reactive.",
                "tweak_direction": "Lower for more pressure; raise for calmer exploration.",
                "risk": "Too low can become repetitive warning noise.",
            }
        ],
        "tuning_experiments": [
            {
                "name": "Sharper Attention Loop",
                "goal": "Make greedy actions feel noticed quickly.",
                "changes": ["Lower danger_notice_threshold by 1 for testing.", "Watch overdraw_amber frequency and player survival."],
                "success_signals": ["Players hesitate before greedy extraction.", "Danger notices feel earned."],
                "rollback_signals": ["Every run feels interrupted by warnings.", "Greedy options become obvious traps."],
            }
        ],
        "data_patch_suggestions": [],
        "instrumentation_suggestions": ["Log rooms_cleared, danger, corruption, health, shield, biomass, event_id, and chosen action after every choice."],
        "vibe_doc_updates": [
            {
                "section": "Balance",
                "current_gap": "The guide defines tone but not how tuning should support it.",
                "suggested_text": "Balance should make the player feel watched, tempted, and taxed. Clean power gains should be rare.",
            }
        ],
        "next_balance_prompt": "Critique whether danger, corruption, healing, and resource rewards make each run feel like a transactional descent.",
    }


def mock_fun_critique() -> dict[str, Any]:
    return {
        "summary": "Offline fun critique sample. The current risk is stat soup: choices move numbers, but the organism does not yet feel like it is steering the run.",
        "fun_score": 4,
        "organism_pressure_score": 3,
        "core_loop_diagnosis": "The loop needs to become temptation, repeated pattern, visible pressure, adaptation, and outcome. Right now many actions reward or punish once, but repeated behavior rarely makes the organism change its strategy.",
        "not_fun_findings": [
            {
                "severity": "high",
                "target": "run loop",
                "why_it_is_not_fun": "The player can read choices as isolated stat trades instead of a living system building a case against them.",
                "recommendation": "Add pressure tracks and visible warnings for repeated behavior: mutation/corruption, flee/danger, greed/hunger, healing/dependence, merchant/debt.",
            },
            {
                "severity": "high",
                "target": "endings",
                "why_it_is_not_fun": "Without ending gravity, the run has no strategic identity beyond surviving the next card.",
                "recommendation": "Define warning thresholds and lock thresholds for corruption, danger/hunter, and balanced/neutral ending eligibility.",
            },
        ],
        "organism_director_findings": [
            {
                "axis": "corruption",
                "current_behavior": "Mutation and body-use choices raise a number.",
                "desired_push": "The organism should offer more power as corruption rises, then narrow the route toward body-loss ending.",
                "missing_feedback": "Intermediate warnings that Hymn is being rewritten.",
                "recommended_change": "Add corruption warning beats and mutation offers that become stronger, uglier, and less optional.",
            },
            {
                "axis": "danger",
                "current_behavior": "Danger changes cadence and pressure, but the hunter threat is not yet the run's answer to avoidance.",
                "desired_push": "Repeated fleeing or combat avoidance should summon the hunter and make future rooms more predatory.",
                "missing_feedback": "Clear pursuit escalation before the hunter arrives.",
                "recommended_change": "Track avoidance and make danger rooms announce that something has learned Hymn's route.",
            },
            {
                "axis": "balance",
                "current_behavior": "Neutral play has no special identity.",
                "desired_push": "Balanced play should be tense restraint: enough risk to continue, not enough repetition to be claimed.",
                "missing_feedback": "No sign that restraint is being recognized.",
                "recommended_change": "Add balance eligibility flags and rare neutral-route information when danger and corruption both stay low.",
            },
        ],
        "decision_loop_rewrites": [
            {
                "loop": "Mutation shopping",
                "current_problem": "Buying is just power for biomass and corruption.",
                "fun_version": "Each purchase makes future mutation offers more tempting and more invasive, while pushing corruption ending warnings.",
                "needed_system_hooks": ["corruption warning thresholds", "offer weighting by corruption", "ending lock flags"],
            },
            {
                "loop": "Combat avoidance",
                "current_problem": "Skipping fights mostly feels like selecting the safer button.",
                "fun_version": "Avoidance raises danger/pursuit; after enough avoidance the hunter interrupts the deck.",
                "needed_system_hooks": ["avoidance counter", "hunter interrupt event", "danger warning text"],
            },
        ],
        "ending_pressure_plan": [
            {
                "ending": "corruption",
                "player_pattern_that_drives_it": "Repeated mutation, symbiote dependence, invasive healing, and body-gain choices.",
                "warnings_before_lock": ["body narration changes", "merchant offers become more intimate", "rooms recognize altered tissue"],
                "lock_condition": "corruption crosses high threshold or too many corruption actions happen in one run.",
            },
            {
                "ending": "hunter/danger",
                "player_pattern_that_drives_it": "Repeated fleeing, combat avoidance, noisy extraction, and merchant refusal.",
                "warnings_before_lock": ["distant buzzing", "routes closing behind Hymn", "enemy cards increasing"],
                "lock_condition": "danger or avoidance crosses high threshold; hunter becomes forced encounter.",
            },
            {
                "ending": "balanced",
                "player_pattern_that_drives_it": "Alternating risk types, limiting mutations, fighting when necessary, and keeping danger/corruption moderate.",
                "warnings_before_lock": ["neutral route hints", "clearer facility/cult lore", "merchant unable to price Hymn cleanly"],
                "lock_condition": "reach ending state with neither danger nor corruption over lock threshold.",
            },
        ],
        "content_priorities": [
            "Warning events for corruption and danger that are playable, not flavor-only.",
            "Hunter escalation events tied to combat avoidance.",
            "Neutral-route lore rewards for balanced play.",
        ],
        "system_priorities": [
            "Track repeated action patterns, not just resource totals.",
            "Add ending warning and lock thresholds.",
            "Let deck composition react to pressure axes.",
        ],
        "vibe_doc_updates": [
            {
                "section": "Core Loop",
                "current_gap": "The guide describes tone and tradeoffs, but not why decisions become fun across a run.",
                "suggested_text": "The organism is the run director. It notices repetition, unbalances the player, and pushes toward endings. Every repeated strategy should create pressure and feedback.",
            }
        ],
        "next_fun_prompt": "Critique whether each repeated player pattern has a pressure response, warning beat, and ending consequence. Find stat-only choices and rewrite them into living-system pushes.",
    }


def mock_lore_critique() -> dict[str, Any]:
    return {
        "summary": "Offline lore-master sample. The key risks are meta leakage, weak Chorus cadence, and corruption copy that explains too much from outside Hymn.",
        "lore_integrity_score": 6,
        "voice_integrity_score": 6,
        "continuity_findings": [
            {
                "severity": "high",
                "target": "game-over narration",
                "issue": "Any line that says clone or next clone breaks Hymn's knowledge boundary.",
                "rewrite_direction": "Use sensory loss, signal breakup, or memory uncertainty instead of explaining the clone cycle.",
            }
        ],
        "voice_findings": [
            {
                "severity": "high",
                "target": "visible speaker labels",
                "issue": "Her: is a UI label, not first-person narration.",
                "rewrite_direction": "Render only the narrated phrases. Keep speaker metadata internal if validation still needs it.",
            }
        ],
        "knowledge_boundary_findings": [
            {
                "severity": "high",
                "target": "clone premise",
                "issue": "Hymn can feel memory leakage but cannot understand herself as a clone.",
                "rewrite_direction": "Use lines like 'This memory is not seated right' instead of direct clone language.",
            }
        ],
        "chorus_usage_plan": [
            "Open new threat, merchant, threshold, and lore-fragment events with a brief Chorus report.",
            "Use Chorus requests to create mission pressure without ever printing Chorus replies.",
            "Let unanswered Chorus checks become tension when corruption or danger rises.",
        ],
        "lore_expansion_seeds": [
            {
                "topic": "Chorus signal discipline",
                "purpose": "Make Hymn feel like an operative under remote instruction.",
                "safe_reveal": "Chorus receives field reports and issues orders offscreen.",
                "deferred_secret": "Why Chorus accepts repeated memory bleed between runs.",
            },
            {
                "topic": "Organism exchange logic",
                "purpose": "Tie merchant, mutations, and biomass into one predatory economy.",
                "safe_reveal": "The organism prices repetition and appetite.",
                "deferred_secret": "The merchant is an expression of the organism's long-term will.",
            },
        ],
        "rewrite_priorities": [
            "Remove visible Her: labels.",
            "Replace clone-aware game-over text.",
            "Rewrite corruption ending as boundary loss.",
            "Add Chorus report phrasing to recurring special events.",
        ],
        "vibe_doc_updates": [
            {
                "section": "Knowledge Boundaries",
                "current_gap": "The guide needs a hard rule for Hymn's clone ignorance.",
                "suggested_text": "Hymn does not know she is a clone. She may experience memory leakage, but narration must not explain the clone cycle.",
            }
        ],
        "next_lore_prompt": "Audit current events for clone knowledge leaks, missing Chorus reports, speaker labels, and corruption ambiguity. Rewrite toward first-person field-report mystery.",
    }


def mock_lore_brainstorm() -> dict[str, Any]:
    return {
        "summary": "Offline lore brainstorm sample. The strongest direction is to treat lore as operational truth with pressure hooks, not backstory collection.",
        "design_thesis": "Every faction teaches Hymn something useful while also letting the organism, Chorus, or merchant gain leverage.",
        "factions": [
            {
                "name": "The Chorus Signal Office",
                "kind": "faction",
                "pitch": "Remote command structure that filters what Hymn is allowed to know.",
                "safe_reveal": "Chorus receives reports and authorizes route choices.",
                "hymn_misread": "Hymn reads silence as signal damage or operational caution.",
                "deferred_secret": "Chorus may recognize memory bleed and withhold why.",
                "gameplay_hook": "Signal-check lore fragments can lower danger but raise suspicion or corruption if the organism listens through the channel.",
                "related_systems": ["lore_fragment", "danger", "corruption", "ending"],
                "sample_fragment": "Chorus, signal test. My last report is already stamped received.",
                "implementation_notes": ["Add Chorus report events", "Track signal degradation at corruption thresholds"],
            },
            {
                "name": "The Choir of Intake",
                "kind": "faction",
                "pitch": "Former facility cult/operators who treated feeding the organism as maintenance.",
                "safe_reveal": "They built rituals around biomass accounting and route control.",
                "hymn_misread": "Hymn reads their records as cult worship, not operational procedure.",
                "deferred_secret": "Their rituals may be old containment protocols that still work.",
                "gameplay_hook": "Reading their marks can unlock safer routes while raising danger from reactivated monitoring.",
                "related_systems": ["lore_fragment", "danger", "deck"],
                "sample_fragment": "Intake hymn scratched into bone. Not prayer. Procedure.",
                "implementation_notes": ["Add cult record fragments", "Let some fragments modify next deck draw"],
            },
        ],
        "recurring_characters": [
            {
                "name": "Quartermaster Null",
                "kind": "recurring shadow",
                "pitch": "A name on old supply tags that may predate Chorus involvement.",
                "safe_reveal": "Null cataloged symbiotes as equipment, not organisms.",
                "hymn_misread": "Hymn assumes Null was a dead operator.",
                "deferred_secret": "Null may be a Chorus role, not one person.",
                "gameplay_hook": "Null tags reveal noncombat symbiote uses and damaged activation risks.",
                "related_systems": ["symbiote", "lore_fragment", "corruption"],
                "sample_fragment": "Null tag. Barrier unit. Field note says it bites when overtrusted.",
                "implementation_notes": ["Add symbiote lore fragments", "Expose cooldown/health hints diegetically"],
            }
        ],
        "organism_lore": [
            {
                "name": "Pattern Hunger",
                "kind": "organism principle",
                "pitch": "The organism does not punish choices; it feeds on repeated solutions.",
                "safe_reveal": "Rooms respond more sharply when Hymn repeats behavior.",
                "hymn_misread": "Hymn thinks the facility is getting louder or faster.",
                "deferred_secret": "The organism is modeling her across more than one entry.",
                "gameplay_hook": "Repeated action warnings become lore fragments that explain pressure tracks.",
                "related_systems": ["danger", "corruption", "ending", "deck"],
                "sample_fragment": "Same door muscle. Same hesitation. It opens before I touch it.",
                "implementation_notes": ["Tie director warnings to lore text variants"],
            }
        ],
        "lore_fragments": [
            {
                "name": "Received Before Sent",
                "kind": "fragment",
                "pitch": "A Chorus receipt timestamp predates Hymn's report.",
                "safe_reveal": "Something is wrong with signal timing.",
                "hymn_misread": "Hymn blames facility distortion.",
                "deferred_secret": "Chorus may already have prior-instance reports.",
                "gameplay_hook": "Study fragment to lower danger by 1, but add one memory-pressure flag.",
                "related_systems": ["lore_fragment", "danger", "ending"],
                "sample_fragment": "Receipt time is wrong. Chorus had this before I said it.",
                "implementation_notes": ["Needs lore-fragment action with mixed effects"],
            }
        ],
        "relationships": [
            {
                "a": "Chorus",
                "b": "Merchant",
                "visible_relationship": "Chorus treats him as an unknown hazard.",
                "hidden_truth": "Chorus may know his pattern and avoid naming him.",
                "gameplay_expression": "Merchant offers change if Hymn reports him versus ignores him.",
            },
            {
                "a": "Symbiotes",
                "b": "Facility Operators",
                "visible_relationship": "Symbiotes cling to dead hosts.",
                "hidden_truth": "They may be old operator tools that learned survival.",
                "gameplay_expression": "Operator tags reveal alternate symbiote activation effects.",
            },
        ],
        "reveal_paths": [
            {
                "thread": "Chorus timing",
                "early_reveal": "Chorus receives reports and gives orders offscreen.",
                "mid_reveal": "Some receipts and route approvals arrive too early.",
                "late_reveal": "Hymn finds references to prior reports she cannot remember writing.",
                "player_pressure": "Following Chorus lowers danger but may restrict neutral ending information.",
                "ending_connection": "Balanced ending requires noticing Chorus omissions without fully rejecting the mission.",
            }
        ],
        "mechanic_hooks": [
            "Lore fragments with mixed effects: lower danger, raise memory pressure, unlock route tags.",
            "Chorus report events at thresholds for danger, corruption, and merchant contact.",
            "Symbiote provenance tags that reveal noncombat uses.",
            "Merchant offer variants based on whether Hymn reports him to Chorus.",
        ],
        "guardrails": [
            "Do not let Hymn say clone or understand the run cycle.",
            "Chorus does not speak onscreen.",
            "Every lore fragment must touch a system.",
            "Do not make factions into exposition NPCs.",
        ],
        "next_lore_prompt": "Generate lore fragments and faction hooks that reveal operational truth, preserve Hymn's ignorance, and create concrete changes to danger, corruption, merchant offers, symbiote use, or ending eligibility.",
    }


def validation_errors(
    patch: dict[str, Any],
    allow_new_actions: bool = False,
    expected_category: str = "",
) -> list[str]:
    errors: list[str] = []
    rooms = set(room_ids())
    actions = existing_actions()
    event_ids = existing_event_ids()
    categories = set(event_category_ids())

    events = patch.get("events", [])
    if not isinstance(events, list) or not events:
        errors.append("patch.events must be a non-empty list")
        return errors

    seen_ids: set[str] = set()
    for index, item in enumerate(events):
        if not isinstance(item, dict):
            errors.append(f"events[{index}] is not an object")
            continue
        room_id = str(item.get("room_id", ""))
        event = item.get("event")
        if room_id not in rooms:
            errors.append(f"events[{index}].room_id '{room_id}' is not in room_dialogue.json")
        if not isinstance(event, dict):
            errors.append(f"events[{index}].event is not an object")
            continue
        event_id = str(event.get("id", ""))
        if not event_id:
            errors.append(f"events[{index}].event.id is empty")
        if event_id in event_ids:
            errors.append(f"event id already exists: {event_id}")
        if event_id in seen_ids:
            errors.append(f"duplicate event id in patch: {event_id}")
        seen_ids.add(event_id)
        for key in ("type", "speaker", "line_1", "line_2"):
            if not str(event.get(key, "")).strip():
                errors.append(f"{event_id or index}: missing {key}")
        event_type = str(event.get("type", ""))
        if categories and event_type not in categories:
            errors.append(f"{event_id or index}: event type '{event_type}' is not a defined category")
        if expected_category and event_type != expected_category:
            errors.append(f"{event_id or index}: event type '{event_type}' does not match requested category '{expected_category}'")
        buttons = event.get("buttons", [])
        if not isinstance(buttons, list) or not buttons:
            errors.append(f"{event_id or index}: buttons must be a non-empty list")
            continue
        for button_index, button in enumerate(buttons):
            if not isinstance(button, dict):
                errors.append(f"{event_id}: button {button_index} is not an object")
                continue
            label = str(button.get("label", "")).strip()
            action = str(button.get("action", "")).strip()
            if not label:
                errors.append(f"{event_id}: button {button_index} missing label")
            if not action:
                errors.append(f"{event_id}: button {button_index} missing action")
            elif action not in actions and not allow_new_actions:
                errors.append(f"{event_id}: unknown action '{action}'")

        mutation_id = event.get("mutation_id")
        if mutation_id and str(mutation_id) not in mutation_ids():
            errors.append(f"{event_id}: unknown mutation_id '{mutation_id}'")
        symbiote_id = event.get("symbiote_id")
        if symbiote_id and str(symbiote_id) not in symbiote_ids():
            errors.append(f"{event_id}: unknown symbiote_id '{symbiote_id}'")
        enemy_id = event.get("enemy_id")
        if enemy_id and str(enemy_id) not in enemy_ids():
            errors.append(f"{event_id}: unknown enemy_id '{enemy_id}'")

    if not allow_new_actions:
        required_changes = patch.get("required_engine_changes", [])
        if required_changes:
            errors.append("required_engine_changes is not empty, but new actions are not allowed")
    return errors


def events_file_errors(strict_actions: bool = False) -> list[str]:
    errors: list[str] = []
    payload = load_json(EVENTS_PATH)
    rooms = set(room_ids())
    categories = set(event_category_ids())
    actions = existing_actions()
    seen_ids: set[str] = set()

    def check_event(event: dict[str, Any], location: str) -> None:
        event_id = str(event.get("id", ""))
        if not event_id:
            errors.append(f"{location}: missing id")
        elif event_id in seen_ids:
            errors.append(f"{location}: duplicate event id '{event_id}'")
        seen_ids.add(event_id)

        event_type = str(event.get("type", ""))
        if not event_type:
            errors.append(f"{location}: missing type")
        elif categories and event_type not in categories:
            errors.append(f"{location}: event type '{event_type}' is not a defined category")

        for key in ("speaker", "line_1", "line_2"):
            if not str(event.get(key, "")).strip():
                errors.append(f"{location}: missing {key}")

        buttons = event.get("buttons", [])
        if not isinstance(buttons, list) or not buttons:
            errors.append(f"{location}: buttons must be a non-empty list")
            return
        for button_index, button in enumerate(buttons):
            if not isinstance(button, dict):
                errors.append(f"{location}: button {button_index} is not an object")
                continue
            if not str(button.get("label", "")).strip():
                errors.append(f"{location}: button {button_index} missing label")
            action = str(button.get("action", "")).strip()
            if not action:
                errors.append(f"{location}: button {button_index} missing action")
            elif strict_actions and action not in actions:
                errors.append(f"{location}: unknown action '{action}'")

    room_events = payload.get("room_events", {})
    if not isinstance(room_events, dict):
        errors.append("room_events must be an object")
    else:
        for room_id, events in room_events.items():
            if room_id not in rooms:
                errors.append(f"room_events.{room_id}: room is not in room_dialogue.json")
            if not isinstance(events, list):
                errors.append(f"room_events.{room_id}: must be a list")
                continue
            for index, event in enumerate(events):
                if isinstance(event, dict):
                    check_event(event, f"room_events.{room_id}[{index}]")
                else:
                    errors.append(f"room_events.{room_id}[{index}]: event is not an object")

    special_events = payload.get("special_events", {})
    if not isinstance(special_events, dict):
        errors.append("special_events must be an object")
    else:
        for event_key, event in special_events.items():
            if isinstance(event, dict):
                if str(event.get("id", event_key)) != event_key:
                    errors.append(f"special_events.{event_key}: id does not match key")
                check_event(event, f"special_events.{event_key}")
            else:
                errors.append(f"special_events.{event_key}: event is not an object")

    return errors


def event_writing_findings() -> list[dict[str, str]]:
    payload = load_json(EVENTS_PATH)
    findings: list[dict[str, str]] = []
    generic_labels = {
        "Proceed.",
        "Proceed",
        "Move on",
        "Leave it",
        "Leave it alone",
        "Back off",
        "Back away",
        "Walk past",
        "Leave",
    }
    weak_line_patterns = [
        ("what should i do", "generic prompt language"),
        ("i can ", "choice list reads like a menu instead of pressure"),
        ("could be", "uncertain phrasing without field interpretation"),
        ("maybe", "uncertain phrasing without field interpretation"),
    ]
    pressure_words = {
        "cost",
        "debt",
        "danger",
        "corruption",
        "claim",
        "noise",
        "quiet",
        "scent",
        "price",
        "wants",
        "learn",
        "carry",
        "blood",
        "biomass",
        "before",
        "if",
        "pay",
        "risk",
        "chorus",
    }
    chorus_expected = {"merchant", "danger", "corruption", "symbiote"}
    cause_effect_types = {"amber", "choice", "combat", "boss", "corruption", "danger", "healing", "merchant", "symbiote"}

    def add(location: str, severity: str, issue: str, recommendation: str) -> None:
        findings.append({
            "location": location,
            "severity": severity,
            "issue": issue,
            "recommendation": recommendation,
        })

    def check_event(event: dict[str, Any], location: str) -> None:
        event_type = str(event.get("type", ""))
        line_1 = str(event.get("line_1", ""))
        line_2 = str(event.get("line_2", ""))
        combined = f"{line_1} {line_2}"
        combined_lower = combined.lower()

        for pattern, issue in weak_line_patterns:
            if pattern in combined_lower:
                add(location, "medium", issue, "Rewrite as observation, interpretation, and pressure instead of a neutral option list.")

        if event_type in chorus_expected and "chorus" not in combined_lower:
            add(location, "medium", "missing Chorus field-report cadence", "Add a short Hymn-to-Chorus check without printing a Chorus reply.")

        if event_type in cause_effect_types and not any(word in combined_lower for word in pressure_words):
            add(location, "medium", "weak cause/effect telegraph", "Add a concrete cost, delayed consequence, or organism intent cue.")

        if str(event.get("enemy_id", "")) and event_type in {"combat", "boss"} and "scene_path" not in event:
            add(location, "low", "combat event relies on enemy scene fallback", "Add scene_path if this encounter needs a specific visible sprite.")

        buttons = event.get("buttons", [])
        if not isinstance(buttons, list):
            return
        for index, button in enumerate(buttons):
            if not isinstance(button, dict):
                continue
            label = str(button.get("label", ""))
            action = str(button.get("action", ""))
            button_location = f"{location}.buttons[{index}]"
            if label in generic_labels:
                add(button_location, "low", f"generic button label '{label}'", "Use embodied instruction: carry the noise, withdraw, force the route, break contact.")
            if action == "proceed" and label.lower() in {"proceed.", "proceed", "move on", "walk past"}:
                add(button_location, "low", "neutral proceed choice", "Name what the refusal preserves or costs.")
            if "wares" in label.lower() or "shop" in label.lower():
                add(button_location, "high", "shop/menu language in merchant-facing UI", "Use scale/exchange/body language instead.")

    room_events = payload.get("room_events", {})
    if isinstance(room_events, dict):
        for room_id, events in room_events.items():
            if not isinstance(events, list):
                continue
            for event in events:
                if isinstance(event, dict):
                    event_id = str(event.get("id", "unknown"))
                    check_event(event, f"room_events.{room_id}.{event_id}")

    special_events = payload.get("special_events", {})
    if isinstance(special_events, dict):
        for event_id, event in special_events.items():
            if isinstance(event, dict):
                check_event(event, f"special_events.{event_id}")

    return findings


def load_patch(path: Path) -> dict[str, Any]:
    return load_json(path)


def cmd_generate(args: argparse.Namespace) -> int:
    GENERATED_DIR.mkdir(exist_ok=True)
    room = args.room or room_ids()[0]
    if room not in room_ids():
        raise SystemExit(f"Unknown room '{room}'. Known rooms: {', '.join(room_ids())}")
    if args.category and args.category not in event_category_ids():
        raise SystemExit(f"Unknown category '{args.category}'. Known categories: {', '.join(event_category_ids())}")

    if args.mock:
        patch = mock_patch(room, args.category or "choice")
    else:
        patch = call_openai(build_prompt(args), args.model, patch_schema(), "scenario_patch")

    errors = validation_errors(
        patch,
        allow_new_actions=args.allow_new_actions,
        expected_category=args.category or "",
    )
    if errors:
        patch["_validation_errors"] = errors

    out = Path(args.out) if args.out else GENERATED_DIR / "scenario_patch.json"
    if not out.is_absolute():
        out = ROOT / out
    write_json(out, patch)
    print(out)
    if errors:
        print("Validation errors:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 2
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    patch = load_patch(Path(args.patch))
    errors = validation_errors(patch, allow_new_actions=args.allow_new_actions)
    if not errors:
        print("ok")
        return 0
    for error in errors:
        print(error, file=sys.stderr)
    return 1


def cmd_critique(args: argparse.Namespace) -> int:
    GENERATED_DIR.mkdir(exist_ok=True)
    if args.mock:
        critique = mock_critique()
    else:
        critique = call_openai(build_critique_prompt(args), args.model, critique_schema(), "content_critique")

    out = Path(args.out) if args.out else GENERATED_DIR / "content_critique.json"
    if not out.is_absolute():
        out = ROOT / out
    write_json(out, critique)
    print(out)
    return 0


def cmd_balance_critique(args: argparse.Namespace) -> int:
    GENERATED_DIR.mkdir(exist_ok=True)
    if args.mock:
        critique = mock_balance_critique()
    else:
        critique = call_openai(
            build_balance_critique_prompt(args),
            args.model,
            balance_critique_schema(),
            "balance_critique",
        )

    out = Path(args.out) if args.out else GENERATED_DIR / "balance_critique.json"
    if not out.is_absolute():
        out = ROOT / out
    write_json(out, critique)
    print(out)
    return 0


def cmd_fun_critique(args: argparse.Namespace) -> int:
    GENERATED_DIR.mkdir(exist_ok=True)
    if args.mock:
        critique = mock_fun_critique()
    else:
        critique = call_openai(
            build_fun_critique_prompt(args),
            args.model,
            fun_critique_schema(),
            "fun_critique",
        )

    out = Path(args.out) if args.out else GENERATED_DIR / "fun_critique.json"
    if not out.is_absolute():
        out = ROOT / out
    write_json(out, critique)
    print(out)
    return 0


def cmd_lore_critique(args: argparse.Namespace) -> int:
    GENERATED_DIR.mkdir(exist_ok=True)
    if args.mock:
        critique = mock_lore_critique()
    else:
        critique = call_openai(
            build_lore_critique_prompt(args),
            args.model,
            lore_critique_schema(),
            "lore_critique",
        )

    out = Path(args.out) if args.out else GENERATED_DIR / "lore_critique.json"
    if not out.is_absolute():
        out = ROOT / out
    write_json(out, critique)
    print(out)
    return 0


def cmd_lore_brainstorm(args: argparse.Namespace) -> int:
    GENERATED_DIR.mkdir(exist_ok=True)
    if args.mock:
        brainstorm = mock_lore_brainstorm()
    else:
        brainstorm = call_openai(
            build_lore_brainstorm_prompt(args),
            args.model,
            lore_brainstorm_schema(),
            "lore_brainstorm",
        )

    out = Path(args.out) if args.out else GENERATED_DIR / "lore_brainstorm.json"
    if not out.is_absolute():
        out = ROOT / out
    write_json(out, brainstorm)
    print(out)
    return 0


def cmd_validate_events(args: argparse.Namespace) -> int:
    errors = events_file_errors(strict_actions=args.strict_actions)
    if not errors:
        print("ok")
        return 0
    for error in errors:
        print(error, file=sys.stderr)
    return 1


def cmd_audit_writing(args: argparse.Namespace) -> int:
    findings = event_writing_findings()
    if args.json:
        print(json.dumps({"findings": findings}, indent=2, ensure_ascii=False))
        return 0
    if not findings:
        print("ok")
        return 0
    for finding in findings:
        print(
            "{severity}: {location}: {issue} -> {recommendation}".format(
                severity=finding["severity"],
                location=finding["location"],
                issue=finding["issue"],
                recommendation=finding["recommendation"],
            )
        )
    return 0


def cmd_apply(args: argparse.Namespace) -> int:
    patch_path = Path(args.patch)
    patch = load_patch(patch_path)
    errors = validation_errors(patch, allow_new_actions=args.allow_new_actions)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    events_payload = load_json(EVENTS_PATH)
    room_events = events_payload.setdefault("room_events", {})
    for item in patch["events"]:
        room_id = item["room_id"]
        room_events.setdefault(room_id, [])
        room_events[room_id].append(item["event"])

    if args.dry_run:
        print("dry-run ok")
        return 0

    write_json(EVENTS_PATH, events_payload)
    print(f"applied {len(patch['events'])} event(s) to events.json")
    return 0


def cmd_remember(args: argparse.Namespace) -> int:
    patch = load_patch(Path(args.patch))
    record = {
        "timestamp": dt.datetime.now(dt.UTC).isoformat(),
        "patch": patch,
        "notes": args.notes or "",
    }
    if args.accepted:
        append_jsonl(MEMORY_DIR / "accepted_scenarios.jsonl", record)
        print("remembered accepted scenario")
    elif args.rejected:
        append_jsonl(MEMORY_DIR / "rejected_scenarios.jsonl", record)
        print("remembered rejected scenario")
    else:
        raise SystemExit("Use --accepted or --rejected.")
    return 0


def cmd_remember_critique(args: argparse.Namespace) -> int:
    critique = load_json(Path(args.critique))
    record = {
        "timestamp": dt.datetime.now(dt.UTC).isoformat(),
        "summary": critique.get("summary", ""),
        "vibe_alignment_score": critique.get("vibe_alignment_score"),
        "findings": critique.get("findings", [])[:5],
        "event_type_suggestions": critique.get("event_type_suggestions", []),
        "encounter_suggestions": critique.get("encounter_suggestions", []),
        "vibe_doc_updates": critique.get("vibe_doc_updates", []),
        "action_system_suggestions": critique.get("action_system_suggestions", []),
        "next_generation_prompt": critique.get("next_generation_prompt", ""),
        "notes": args.notes or "",
    }
    append_jsonl(CRITIQUE_MEMORY_PATH, record)
    print("remembered critic guidance")
    return 0


def cmd_remember_balance(args: argparse.Namespace) -> int:
    critique = load_json(Path(args.critique))
    record = {
        "timestamp": dt.datetime.now(dt.UTC).isoformat(),
        "summary": critique.get("summary", ""),
        "run_feel_score": critique.get("run_feel_score"),
        "vibe_balance_score": critique.get("vibe_balance_score"),
        "balance_findings": critique.get("balance_findings", [])[:6],
        "levers": critique.get("levers", []),
        "tuning_experiments": critique.get("tuning_experiments", []),
        "data_patch_suggestions": critique.get("data_patch_suggestions", []),
        "instrumentation_suggestions": critique.get("instrumentation_suggestions", []),
        "vibe_doc_updates": critique.get("vibe_doc_updates", []),
        "next_balance_prompt": critique.get("next_balance_prompt", ""),
        "notes": args.notes or "",
    }
    append_jsonl(BALANCE_MEMORY_PATH, record)
    print("remembered balance guidance")
    return 0


def cmd_remember_fun(args: argparse.Namespace) -> int:
    critique = load_json(Path(args.critique))
    record = {
        "timestamp": dt.datetime.now(dt.UTC).isoformat(),
        "summary": critique.get("summary", ""),
        "fun_score": critique.get("fun_score"),
        "organism_pressure_score": critique.get("organism_pressure_score"),
        "core_loop_diagnosis": critique.get("core_loop_diagnosis", ""),
        "not_fun_findings": critique.get("not_fun_findings", [])[:6],
        "organism_director_findings": critique.get("organism_director_findings", []),
        "decision_loop_rewrites": critique.get("decision_loop_rewrites", []),
        "ending_pressure_plan": critique.get("ending_pressure_plan", []),
        "content_priorities": critique.get("content_priorities", []),
        "system_priorities": critique.get("system_priorities", []),
        "vibe_doc_updates": critique.get("vibe_doc_updates", []),
        "next_fun_prompt": critique.get("next_fun_prompt", ""),
        "notes": args.notes or "",
    }
    append_jsonl(FUN_MEMORY_PATH, record)
    print("remembered fun guidance")
    return 0


def cmd_remember_lore(args: argparse.Namespace) -> int:
    critique = load_json(Path(args.critique))
    record = {
        "timestamp": dt.datetime.now(dt.UTC).isoformat(),
        "summary": critique.get("summary", ""),
        "lore_integrity_score": critique.get("lore_integrity_score"),
        "voice_integrity_score": critique.get("voice_integrity_score"),
        "continuity_findings": critique.get("continuity_findings", [])[:6],
        "voice_findings": critique.get("voice_findings", [])[:6],
        "knowledge_boundary_findings": critique.get("knowledge_boundary_findings", [])[:6],
        "chorus_usage_plan": critique.get("chorus_usage_plan", []),
        "lore_expansion_seeds": critique.get("lore_expansion_seeds", []),
        "rewrite_priorities": critique.get("rewrite_priorities", []),
        "vibe_doc_updates": critique.get("vibe_doc_updates", []),
        "next_lore_prompt": critique.get("next_lore_prompt", ""),
        "notes": args.notes or "",
    }
    append_jsonl(LORE_MEMORY_PATH, record)
    print("remembered lore guidance")
    return 0


def cmd_remember_lore_brainstorm(args: argparse.Namespace) -> int:
    brainstorm = load_json(Path(args.brainstorm))
    record = {
        "timestamp": dt.datetime.now(dt.UTC).isoformat(),
        "summary": brainstorm.get("summary", ""),
        "design_thesis": brainstorm.get("design_thesis", ""),
        "factions": brainstorm.get("factions", [])[:6],
        "recurring_characters": brainstorm.get("recurring_characters", [])[:6],
        "organism_lore": brainstorm.get("organism_lore", [])[:6],
        "lore_fragments": brainstorm.get("lore_fragments", [])[:8],
        "relationships": brainstorm.get("relationships", []),
        "reveal_paths": brainstorm.get("reveal_paths", []),
        "mechanic_hooks": brainstorm.get("mechanic_hooks", []),
        "guardrails": brainstorm.get("guardrails", []),
        "next_lore_prompt": brainstorm.get("next_lore_prompt", ""),
        "notes": args.notes or "",
    }
    append_jsonl(LORE_BRAINSTORM_MEMORY_PATH, record)
    print("remembered lore brainstorm guidance")
    return 0


def cmd_context(_: argparse.Namespace) -> int:
    print(json.dumps(game_context(), indent=2, ensure_ascii=False))
    return 0


def cmd_balance_context(_: argparse.Namespace) -> int:
    print(json.dumps(balance_context(), indent=2, ensure_ascii=False))
    return 0


def cmd_fun_context(_: argparse.Namespace) -> int:
    print(json.dumps(fun_context(), indent=2, ensure_ascii=False))
    return 0


def cmd_lore_context(_: argparse.Namespace) -> int:
    print(json.dumps(lore_context(), indent=2, ensure_ascii=False))
    return 0


def cmd_lore_brainstorm_context(_: argparse.Namespace) -> int:
    print(json.dumps(lore_brainstorm_context(), indent=2, ensure_ascii=False))
    return 0


def cmd_vibe(_: argparse.Namespace) -> int:
    print(load_vibe_guide())
    return 0


def cmd_lore_guide(_: argparse.Namespace) -> int:
    print(load_lore_guide())
    return 0


def cmd_categories(_: argparse.Namespace) -> int:
    print(json.dumps({"categories": event_categories()}, indent=2, ensure_ascii=False))
    return 0


def cmd_sources(_: argparse.Namespace) -> int:
    print(read_text(MEMORY_DIR / "inspiration_sources.md"))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    generate = sub.add_parser("generate", help="Generate a scenario patch.")
    generate.add_argument("--room", help="Target room id.")
    generate.add_argument("--category", help="Target event category id.")
    generate.add_argument("--count", type=int, default=1, help="Number of events to request.")
    generate.add_argument("--prompt", default="Create playable Fleshpunk room scenarios.")
    generate.add_argument("--out", help="Output patch path.")
    generate.add_argument("--model", default=DEFAULT_MODEL)
    generate.add_argument("--allow-new-actions", action="store_true")
    generate.add_argument("--mock", action="store_true", help="Generate a local sample without calling OpenAI.")
    generate.set_defaults(func=cmd_generate)

    critique = sub.add_parser("critique", help="Critique content against the vibe guide.")
    critique.add_argument("--patch", help="Optional scenario patch to critique instead of events.json.")
    critique.add_argument("--focus", default="Critique vibe fit, choice pressure, event categories, encounter opportunities, and missing guide rules.")
    critique.add_argument("--out", help="Output critique JSON path.")
    critique.add_argument("--model", default=DEFAULT_MODEL)
    critique.add_argument("--mock", action="store_true", help="Generate a local sample without calling OpenAI.")
    critique.set_defaults(func=cmd_critique)

    balance_critique = sub.add_parser("balance-critique", help="Critique balance and run feel against the vibe guide.")
    balance_critique.add_argument("--focus", default="Critique run feel, balance levers, pressure cadence, reward costs, and how tuning supports the vibe.")
    balance_critique.add_argument("--out", help="Output balance critique JSON path.")
    balance_critique.add_argument("--model", default=DEFAULT_MODEL)
    balance_critique.add_argument("--mock", action="store_true", help="Generate a local sample without calling OpenAI.")
    balance_critique.set_defaults(func=cmd_balance_critique)

    fun_critique = sub.add_parser("fun-critique", help="Critique fun factor and organism pressure against the vibe guide.")
    fun_critique.add_argument("--focus", default="Critique fun loop, organism pressure, repeated-choice consequences, ending gravity, and stat-only choices.")
    fun_critique.add_argument("--out", help="Output fun critique JSON path.")
    fun_critique.add_argument("--model", default=DEFAULT_MODEL)
    fun_critique.add_argument("--mock", action="store_true", help="Generate a local sample without calling OpenAI.")
    fun_critique.set_defaults(func=cmd_fun_critique)

    lore_critique = sub.add_parser("lore-critique", help="Critique lore continuity, voice, Chorus usage, and knowledge boundaries.")
    lore_critique.add_argument("--focus", default="Critique lore continuity, Hymn's knowledge boundaries, Chorus report cadence, corruption clarity, and flavor preservation.")
    lore_critique.add_argument("--out", help="Output lore critique JSON path.")
    lore_critique.add_argument("--model", default=DEFAULT_MODEL)
    lore_critique.add_argument("--mock", action="store_true", help="Generate a local sample without calling OpenAI.")
    lore_critique.set_defaults(func=cmd_lore_critique)

    lore_brainstorm = sub.add_parser("lore-brainstorm", help="Brainstorm lore concepts with reveal boundaries and gameplay hooks.")
    lore_brainstorm.add_argument("--focus", default="Brainstorm factions, recurring characters, relationships, lore fragments, reveal paths, and gameplay hooks.")
    lore_brainstorm.add_argument("--count", type=int, default=6, help="Approximate number of concepts to request per major section.")
    lore_brainstorm.add_argument("--out", help="Output lore brainstorm JSON path.")
    lore_brainstorm.add_argument("--model", default=DEFAULT_MODEL)
    lore_brainstorm.add_argument("--mock", action="store_true", help="Generate a local sample without calling OpenAI.")
    lore_brainstorm.set_defaults(func=cmd_lore_brainstorm)

    validate = sub.add_parser("validate", help="Validate a scenario patch.")
    validate.add_argument("patch")
    validate.add_argument("--allow-new-actions", action="store_true")
    validate.set_defaults(func=cmd_validate)

    validate_events = sub.add_parser("validate-events", help="Validate events.json against broad categories.")
    validate_events.add_argument("--strict-actions", action="store_true")
    validate_events.set_defaults(func=cmd_validate_events)

    audit_writing = sub.add_parser("audit-writing", help="Audit events.json for weak cause/effect, generic buttons, and voice drift.")
    audit_writing.add_argument("--json", action="store_true", help="Print JSON findings.")
    audit_writing.set_defaults(func=cmd_audit_writing)

    apply = sub.add_parser("apply", help="Apply a valid JSON-only scenario patch.")
    apply.add_argument("patch")
    apply.add_argument("--allow-new-actions", action="store_true")
    apply.add_argument("--dry-run", action="store_true")
    apply.set_defaults(func=cmd_apply)

    remember = sub.add_parser("remember", help="Record accepted or rejected feedback.")
    remember.add_argument("patch")
    remember.add_argument("--accepted", action="store_true")
    remember.add_argument("--rejected", action="store_true")
    remember.add_argument("--notes", default="")
    remember.set_defaults(func=cmd_remember)

    remember_critique = sub.add_parser("remember-critique", help="Store critique guidance for future generation.")
    remember_critique.add_argument("critique")
    remember_critique.add_argument("--notes", default="")
    remember_critique.set_defaults(func=cmd_remember_critique)

    remember_balance = sub.add_parser("remember-balance", help="Store balance critique guidance for future generation.")
    remember_balance.add_argument("critique")
    remember_balance.add_argument("--notes", default="")
    remember_balance.set_defaults(func=cmd_remember_balance)

    remember_fun = sub.add_parser("remember-fun", help="Store fun-factor critique guidance for future generation.")
    remember_fun.add_argument("critique")
    remember_fun.add_argument("--notes", default="")
    remember_fun.set_defaults(func=cmd_remember_fun)

    remember_lore = sub.add_parser("remember-lore", help="Store lore-master critique guidance for future generation.")
    remember_lore.add_argument("critique")
    remember_lore.add_argument("--notes", default="")
    remember_lore.set_defaults(func=cmd_remember_lore)

    remember_lore_brainstorm = sub.add_parser("remember-lore-brainstorm", help="Store lore brainstorm guidance for future generation.")
    remember_lore_brainstorm.add_argument("brainstorm")
    remember_lore_brainstorm.add_argument("--notes", default="")
    remember_lore_brainstorm.set_defaults(func=cmd_remember_lore_brainstorm)

    context = sub.add_parser("context", help="Print compact game context.")
    context.set_defaults(func=cmd_context)

    balance_context_parser = sub.add_parser("balance-context", help="Print balance levers and run-feel context.")
    balance_context_parser.set_defaults(func=cmd_balance_context)

    fun_context_parser = sub.add_parser("fun-context", help="Print fun-factor and organism pressure context.")
    fun_context_parser.set_defaults(func=cmd_fun_context)

    lore_context_parser = sub.add_parser("lore-context", help="Print lore continuity and voice context.")
    lore_context_parser.set_defaults(func=cmd_lore_context)

    lore_brainstorm_context_parser = sub.add_parser("lore-brainstorm-context", help="Print lore brainstorm context.")
    lore_brainstorm_context_parser.set_defaults(func=cmd_lore_brainstorm_context)

    vibe = sub.add_parser("vibe", help="Print the vibe and design guide.")
    vibe.set_defaults(func=cmd_vibe)

    lore_guide = sub.add_parser("lore-guide", help="Print the lore guide.")
    lore_guide.set_defaults(func=cmd_lore_guide)

    categories = sub.add_parser("categories", help="Print broad event categories.")
    categories.set_defaults(func=cmd_categories)

    sources = sub.add_parser("sources", help="Print inspiration source notes.")
    sources.set_defaults(func=cmd_sources)
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
