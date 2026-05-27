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
CORPUS_SEEDS_PATH = GENERATED_DIR / "corpus" / "fleshpunk_seeds.json"

LEGACY_EVENTS_PATH = ROOT / "events.json"
LEGACY_ROOMS_PATH = ROOT / "room_dialogue.json"
LEGACY_DECKS_PATH = ROOT / "encounter_decks.json"
POST_UPDATE_EVENTS_PATH = ROOT / "events_post_update.json"
POST_UPDATE_ROOMS_PATH = ROOT / "rooms_post_update.json"
POST_UPDATE_DECKS_PATH = ROOT / "encounter_decks_post_update.json"
EVENTS_PATH = POST_UPDATE_EVENTS_PATH if POST_UPDATE_EVENTS_PATH.exists() else LEGACY_EVENTS_PATH
ROOMS_PATH = POST_UPDATE_ROOMS_PATH if POST_UPDATE_ROOMS_PATH.exists() else LEGACY_ROOMS_PATH
DECKS_PATH = POST_UPDATE_DECKS_PATH if POST_UPDATE_DECKS_PATH.exists() else LEGACY_DECKS_PATH
ENEMIES_PATH = ROOT / "enemies.json"
MUTATIONS_PATH = ROOT / "mutations.json"
SYMBIOTES_PATH = ROOT / "symbiotes.json"
RUN_MANAGER_PATH = ROOT / "run_manager.gd"
CATEGORIES_PATH = MEMORY_DIR / "event_categories.json"
VIBE_GUIDE_PATH = MEMORY_DIR / "vibe_guide.md"
LORE_GUIDE_PATH = MEMORY_DIR / "lore_guide.md"
SETTING_BACKBONE_PATH = MEMORY_DIR / "setting_backbone.md"
STORY_ROOM_CONTRACT_PATH = MEMORY_DIR / "story_room_contract.md"
BODY_OPTION_CONTRACT_PATH = MEMORY_DIR / "body_option_contract.md"
GLUE_LAYER_CONTRACT_PATH = MEMORY_DIR / "glue_layer_contract.md"
ENDING_MAZE_ARCHITECTURE_PATH = MEMORY_DIR / "ending_maze_architecture.md"
HYMN_CORPUS_VOICE_PATH = MEMORY_DIR / "hymn_corpus_voice.md"
RESEARCH_STACK_PATH = MEMORY_DIR / "fleshpunk_corpus_research_stack.md"
RESEARCH_GUIDE_PATHS = [
    MEMORY_DIR / "fleshpunk_research_combat_intelligence.md",
    MEMORY_DIR / "fleshpunk_research_biology_mutation.md",
    MEMORY_DIR / "fleshpunk_research_roguelike_systems.md",
    MEMORY_DIR / "fleshpunk_research_atmosphere_progression.md",
    MEMORY_DIR / "fleshpunk_research_pulp_before_1930.md",
]
PULP_RETRIEVAL_INDEX_PATH = GENERATED_DIR / "corpus" / "pulp_pre_1930" / "retrieval_index.md"
CONTENT_AUTHORSHIP_WORKFLOW_PATH = MEMORY_DIR / "content_authorship_workflow.md"
ACCESSIBILITY_GUIDE_PATH = MEMORY_DIR / "accessibility_guide.md"
CRITIQUE_MEMORY_PATH = MEMORY_DIR / "critic_guidance.jsonl"
BALANCE_MEMORY_PATH = MEMORY_DIR / "balance_guidance.jsonl"
FUN_MEMORY_PATH = MEMORY_DIR / "fun_guidance.jsonl"
LORE_MEMORY_PATH = MEMORY_DIR / "lore_guidance.jsonl"
LORE_BRAINSTORM_MEMORY_PATH = MEMORY_DIR / "lore_brainstorm_guidance.jsonl"
STORY_ARCHITECTURE_MEMORY_PATH = MEMORY_DIR / "story_architecture_guidance.jsonl"
ACCESSIBILITY_MEMORY_PATH = MEMORY_DIR / "accessibility_guidance.jsonl"

DEFAULT_MODEL = os.environ.get("SCENARIO_AGENT_MODEL", "gpt-5")
TRADEOFF_EXEMPT_EVENT_TYPES = {"transition"}
STORY_ENGINE_CONTENT_TRACK = "post_update_text_only"
NARROW_ROOM_ROLES = {
    "ambush",
    "character_encounter",
    "enemy_encounter",
    "mutation_offer",
    "quiet_passage",
    "recovery_beat",
    "rest_beat",
    "simple_passage",
    "symbiote_offer",
}


def commandable_button_count(event: dict[str, Any]) -> int:
    buttons = event.get("buttons", [])
    count = sum(1 for button in buttons if isinstance(button, dict)) if isinstance(buttons, list) else 0
    if str(event.get("type", "")) == "symbiote":
        symbiote_choices = event.get("symbiote_choices", [])
        explicit_choice_count = 0
        if isinstance(symbiote_choices, list):
            explicit_choice_count = sum(1 for choice in symbiote_choices if str(choice).strip())
            count += explicit_choice_count
        if explicit_choice_count == 0 and event.get("symbiote_choice_count") is not None:
            count += max(int(event.get("symbiote_choice_count", 0)), 0)
    return count


def is_tradeoff_exempt_event(event: dict[str, Any]) -> bool:
    if str(event.get("type", "")) in TRADEOFF_EXEMPT_EVENT_TYPES:
        return True
    if str(event.get("ending_id", "")).strip():
        return True
    if bool(event.get("game_over_on_combat", False)):
        return True
    buttons = event.get("buttons", [])
    if isinstance(buttons, list) and buttons:
        actions = {str(button.get("action", "")) for button in buttons if isinstance(button, dict)}
        if actions == {"restart_run"}:
            return True
    return False


def is_narrow_room_role(room_record: dict[str, Any]) -> bool:
    room_role = str(room_record.get("room_role", "")).strip()
    if room_role in NARROW_ROOM_ROLES:
        return True
    tags = room_record.get("tags", [])
    if isinstance(tags, list) and any(str(tag) in NARROW_ROOM_ROLES for tag in tags):
        return True
    return False
ENVIRONMENT_GROUP_KEYS = {
    "environment_id",
    "environment",
    "environment_family",
}
INSTANCE_SITUATION_KEYS = {
    "instance_premise",
    "current_situation",
    "situation",
    "instance_role",
}
ENVIRONMENT_ECHO_KEYS = {
    "environment_echoes",
    "later_instance_echoes",
    "environment_memory_states",
    "memory_states",
}
CORPUS_INFLUENCE_KEYS = {
    "corpus_influences",
    "corpus_anchors",
    "research_influences",
    "source_anchors",
    "source_text_anchors",
}
ROOM_MEMORY_KEYS = {
    "room_state_changes",
    "room_memory_flags",
    "environment_state_changes",
    "environment_memory_flags",
    "memory_key",
    "memory_changes",
    "route_state_changes",
    "actor_state_changes",
    "faction_state_changes",
    "infrastructure_state_change",
    "beast_state_change",
    "character_state_change",
}
ACTION_RESULT_KEYS = {
    "action_results",
    "outcomes",
    "result_lines_by_action",
    "room_result_lines",
    "button_results",
    "action_consequences",
}

EXISTING_ACTION_RE = re.compile(r'^\s*"([^"]+)":\s*$', re.MULTILINE)
VOICE_ALIAS_MAX_WORDS = 4
VOICE_ALIAS_MIN_WORDS = 1
VOICE_ALIAS_MAX_PER_BUTTON = 5
VOICE_ALIAS_STOP_WORDS = {
    "a",
    "an",
    "and",
    "as",
    "at",
    "back",
    "be",
    "away",
    "by",
    "for",
    "from",
    "go",
    "i",
    "in",
    "into",
    "it",
    "my",
    "near",
    "of",
    "on",
    "or",
    "out",
    "the",
    "their",
    "them",
    "then",
    "there",
    "these",
    "this",
    "to",
    "up",
    "with",
}
VOICE_ALIAS_BLOCKLIST = {
    "confirm",
    "help",
    "inventory",
    "options",
    "pause",
    "repeat",
    "repeat choices",
    "continue",
    "resume",
    "status",
}
VOICE_ALIAS_ACTION_SEEDS = {
    "activate_symbiote": ["activate", "wake symbiote", "use symbiote", "trigger symbiote", "bond"],
    "browse_wares": ["approach", "merchant", "trade", "exchange", "barter"],
    "buy_mutation": ["buy", "purchase", "take mutation", "claim mutation", "mutation"],
    "combat": ["fight", "attack", "strike", "engage", "kill"],
    "cut_green_spine": ["cut", "green spine", "spine", "sever", "slice"],
    "drink_pool": ["drink", "sip", "pool", "clean pulse", "take a sip"],
    "leave_merchant": ["walk away", "refuse merchant", "decline merchant", "back off", "leave merchant"],
    "leave_symbiote": ["leave symbiote", "decline symbiote", "refuse symbiote", "no bond", "walk away"],
    "proceed": ["advance", "move on", "carry on", "go forward", "step through"],
    "retreat": ["retreat", "withdraw", "back away", "fall back", "pull back"],
    "study_pool": ["study", "inspect", "sample", "listen", "read"],
    "take_mutation": ["take mutation", "claim mutation", "choose mutation", "mutation", "buy mutation"],
    "take_symbiote": ["bond", "take symbiote", "claim symbiote", "choose symbiote", "accept symbiote"],
    "vent_red_split": ["vent", "cut vent", "cut a vent", "open vent", "vent the wall"],
}
VOICE_ALIAS_FAMILY_SEEDS = {
    "approach": ["approach", "merchant", "trade", "exchange", "barter"],
    "back": ["back away", "back off", "withdraw", "leave", "retreat"],
    "bond": ["bond", "take symbiote", "claim symbiote", "accept symbiote", "choose symbiote"],
    "buy": ["buy", "purchase", "take mutation", "claim mutation", "mutation"],
    "cut": ["cut", "slice", "sever", "open vent", "vent"],
    "drink": ["drink", "sip", "take a sip", "clean pulse", "breathe"],
    "leave": ["leave", "walk away", "withdraw", "back away", "retreat"],
    "mark": ["mark", "trace", "tag", "branch", "select branch"],
    "move": ["move", "continue", "advance", "go on", "step through"],
    "proceed": ["proceed", "advance", "move on", "carry on", "go forward"],
    "retreat": ["retreat", "withdraw", "back away", "fall back", "pull back"],
    "study": ["study", "inspect", "sample", "listen", "read"],
    "take": ["take", "claim", "choose", "accept"],
    "vent": ["vent", "cut vent", "cut a vent", "open vent", "breach"],
}


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


def slugify_id(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "seed"


def _source_seed_filters_are_active(args: argparse.Namespace) -> bool:
    return bool(
        getattr(args, "source_seeds", "")
        or getattr(args, "source_seed", None)
        or getattr(args, "source_work", "")
        or getattr(args, "source_motif", "")
    )


def load_source_seed_context(args: argparse.Namespace) -> list[dict[str, Any]]:
    if not _source_seed_filters_are_active(args):
        return []

    seed_path = Path(args.source_seeds) if getattr(args, "source_seeds", "") else CORPUS_SEEDS_PATH
    if not seed_path.is_absolute():
        seed_path = ROOT / seed_path
    payload = load_json(seed_path)
    seeds = payload.get("seeds", [])
    if not isinstance(seeds, list):
        raise ValueError(f"{seed_path.name} must contain a seeds array")

    requested_ids = set(getattr(args, "source_seed", None) or [])
    source_work = str(getattr(args, "source_work", "") or "")
    source_motif = str(getattr(args, "source_motif", "") or "")
    target_room = str(getattr(args, "room", "") or "")
    selected: list[dict[str, Any]] = []
    for seed in seeds:
        if not isinstance(seed, dict):
            continue
        if requested_ids and str(seed.get("id", "")) not in requested_ids:
            continue
        if source_work and str(seed.get("source_id", "")) != source_work:
            continue
        if source_motif and str(seed.get("motif_id", "")) != source_motif:
            continue
        if target_room:
            suggested_rooms = [str(room) for room in seed.get("suggested_rooms", []) if str(room)]
            if suggested_rooms and target_room not in suggested_rooms:
                continue
        selected.append(_compact_source_seed(seed))

    limit = int(getattr(args, "source_seed_count", 3) or 3)
    return selected[:max(limit, 1)]


def _compact_source_seed(seed: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(seed.get("id", "")),
        "source_id": str(seed.get("source_id", "")),
        "source_title": str(seed.get("source_title", "")),
        "source_author": str(seed.get("source_author", "")),
        "motif_id": str(seed.get("motif_id", "")),
        "motif_group": str(seed.get("motif_group", "")),
        "source_signal": seed.get("source_signal", {}),
        "fleshpunk_seed": str(seed.get("fleshpunk_seed", "")),
        "mechanic_direction": str(seed.get("mechanic_direction", "")),
        "suggested_rooms": seed.get("suggested_rooms", []),
        "suggested_existing_actions": seed.get("suggested_existing_actions", []),
        "generation_guardrails": seed.get("generation_guardrails", []),
    }


def enrich_patch_voice_aliases(patch: dict[str, Any]) -> dict[str, Any]:
    events = patch.get("events", [])
    if not isinstance(events, list):
        return patch
    for item in events:
        if not isinstance(item, dict):
            continue
        event = item.get("event")
        if not isinstance(event, dict):
            continue
        _enrich_event_voice_aliases(event, replace_existing=False)
    return patch


def enrich_events_payload_voice_aliases(payload: dict[str, Any]) -> dict[str, Any]:
    room_events = payload.get("room_events", {})
    if isinstance(room_events, dict):
        for events in room_events.values():
            if not isinstance(events, list):
                continue
            for event in events:
                if isinstance(event, dict):
                    _enrich_event_voice_aliases(event, replace_existing=True)
    special_events = payload.get("special_events", {})
    if isinstance(special_events, dict):
        for event in special_events.values():
            if isinstance(event, dict):
                _enrich_event_voice_aliases(event, replace_existing=True)
    return payload


def _enrich_event_voice_aliases(event: dict[str, Any], replace_existing: bool) -> None:
    buttons = event.get("buttons", [])
    if not isinstance(buttons, list) or not buttons:
        return
    event_text = " ".join([
        str(event.get("line_1", "")),
        str(event.get("line_2", "")),
    ]).strip()
    button_candidates: list[list[dict[str, Any]]] = []
    for index, button in enumerate(buttons):
        if not isinstance(button, dict):
            button_candidates.append([])
            continue
        candidates = _voice_alias_candidates_for_button(button, event_text, index)
        button_candidates.append(candidates)
    resolved = _resolve_voice_alias_candidates(button_candidates)
    for index, button in enumerate(buttons):
        if not isinstance(button, dict):
            continue
        if replace_existing:
            generated = resolved.get(index, [])
            if generated:
                button["voice_aliases"] = generated
        else:
            merged = _merge_voice_aliases(button.get("voice_aliases", []), resolved.get(index, []))
            if merged:
                button["voice_aliases"] = merged


def _resolve_voice_alias_candidates(button_candidates: list[list[dict[str, Any]]]) -> dict[int, list[str]]:
    winner_by_alias: dict[str, dict[str, Any]] = {}
    for candidates in button_candidates:
        for candidate in candidates:
            alias = str(candidate.get("alias", "")).strip()
            if not alias or alias in VOICE_ALIAS_BLOCKLIST:
                continue
            existing = winner_by_alias.get(alias)
            if existing is None or _voice_alias_is_better(candidate, existing):
                winner_by_alias[alias] = candidate

    resolved: dict[int, list[tuple[float, str]]] = {}
    for alias, candidate in winner_by_alias.items():
        index = int(candidate.get("index", -1))
        if index < 0:
            continue
        resolved.setdefault(index, []).append((float(candidate.get("score", 0.0)), alias))

    output: dict[int, list[str]] = {}
    for index, aliases in resolved.items():
        aliases.sort(key=lambda item: (-item[0], item[1]))
        output[index] = [alias for _, alias in aliases[:VOICE_ALIAS_MAX_PER_BUTTON]]
    return output


def _voice_alias_is_better(candidate: dict[str, Any], existing: dict[str, Any]) -> bool:
    candidate_score = float(candidate.get("score", 0.0))
    existing_score = float(existing.get("score", 0.0))
    if candidate_score != existing_score:
        return candidate_score > existing_score
    candidate_words = int(candidate.get("word_count", 0))
    existing_words = int(existing.get("word_count", 0))
    if candidate_words != existing_words:
        return candidate_words < existing_words
    candidate_length = len(str(candidate.get("alias", "")))
    existing_length = len(str(existing.get("alias", "")))
    if candidate_length != existing_length:
        return candidate_length < existing_length
    return int(candidate.get("index", 0)) < int(existing.get("index", 0))


def _merge_voice_aliases(existing_aliases: Any, generated_aliases: list[str]) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for alias in existing_aliases if isinstance(existing_aliases, list) else []:
        normalized = _normalize_voice_alias(str(alias))
        if _is_valid_voice_alias(normalized) and normalized not in seen:
            merged.append(normalized)
            seen.add(normalized)
    for alias in generated_aliases:
        normalized = _normalize_voice_alias(alias)
        if _is_valid_voice_alias(normalized) and normalized not in seen:
            merged.append(normalized)
            seen.add(normalized)
    return merged[:VOICE_ALIAS_MAX_PER_BUTTON]


def _voice_alias_candidates_for_button(button: dict[str, Any], event_text: str, index: int) -> list[dict[str, Any]]:
    label = str(button.get("label", ""))
    action = str(button.get("action", ""))
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add_phrase(phrase: str, score: float, source: str) -> None:
        normalized = _normalize_voice_alias(phrase)
        if not _is_valid_voice_alias(normalized) or normalized in seen:
            return
        seen.add(normalized)
        candidates.append({
            "alias": normalized,
            "score": score,
            "source": source,
            "index": index,
            "word_count": len(normalized.split()),
        })

    for existing in button.get("voice_aliases", []):
        add_phrase(str(existing), 1.0, "existing")
    for phrase in _voice_alias_phrases_from_family(label, action):
        add_phrase(phrase, _voice_alias_score_for_phrase(phrase, 1.0), "family")
    for phrase in _voice_alias_phrases_from_action(action):
        add_phrase(phrase, _voice_alias_score_for_phrase(phrase, 0.98), "action")
    for phrase in _voice_alias_phrases_from_text(label):
        add_phrase(phrase, _voice_alias_score_for_phrase(phrase, 0.84), "label")
    for phrase in _voice_alias_phrases_from_text(event_text):
        add_phrase(phrase, _voice_alias_score_for_phrase(phrase, 0.66), "event_text")

    candidates.sort(key=lambda item: (-float(item.get("score", 0.0)), int(item.get("word_count", 0)), str(item.get("alias", ""))))
    return candidates


def _voice_alias_phrases_from_action(action: str) -> list[str]:
    phrases: list[str] = []
    base = str(action).split(":", 1)[0].replace("_", " ").strip()
    if base:
        phrases.append(base)
    if action in VOICE_ALIAS_ACTION_SEEDS:
        phrases.extend(VOICE_ALIAS_ACTION_SEEDS[action])
    if base in VOICE_ALIAS_ACTION_SEEDS:
        phrases.extend(VOICE_ALIAS_ACTION_SEEDS[base])
    if ":" in action:
        suffix = str(action.split(":", 1)[1]).replace("_", " ").strip()
        if suffix:
            phrases.extend([suffix, f"{base} {suffix}".strip()])
    return _dedupe_alias_phrases(phrases)


def _voice_alias_phrases_from_family(label: str, action: str) -> list[str]:
    phrases: list[str] = []
    for family_key in _voice_alias_family_keys(label, action):
        phrases.extend(VOICE_ALIAS_FAMILY_SEEDS.get(family_key, []))
    return _dedupe_alias_phrases(phrases)


def _voice_alias_family_keys(label: str, action: str) -> list[str]:
    keys: list[str] = []
    normalized_label = _normalize_voice_alias(label)
    normalized_action = _normalize_voice_alias(action).replace("_", " ")
    for phrase, key in (
        ("cut a vent", "cut"),
        ("cut vent", "cut"),
        ("vent the wall", "vent"),
        ("back away", "back"),
        ("back off", "back"),
        ("walk away", "leave"),
        ("leave", "leave"),
        ("approach", "approach"),
        ("trade", "approach"),
        ("exchange", "approach"),
        ("merchant", "approach"),
        ("drink", "drink"),
        ("sip", "drink"),
        ("study", "study"),
        ("inspect", "study"),
        ("sample", "study"),
        ("retreat", "retreat"),
        ("move", "move"),
        ("proceed", "proceed"),
        ("bond", "bond"),
        ("activate", "bond"),
        ("take mutation", "buy"),
        ("purchase", "buy"),
        ("claim mutation", "buy"),
        ("mark", "mark"),
    ):
        if phrase in normalized_label or phrase in normalized_action:
            if key not in keys:
                keys.append(key)

    raw_label_tokens = normalized_label.split()
    if raw_label_tokens:
        first = str(raw_label_tokens[0])
        if first in VOICE_ALIAS_FAMILY_SEEDS and first not in keys:
            keys.append(first)
    raw_action_tokens = normalized_action.split()
    if raw_action_tokens:
        first_action = str(raw_action_tokens[0])
        if first_action in VOICE_ALIAS_FAMILY_SEEDS and first_action not in keys:
            keys.append(first_action)
    if "vent" in normalized_action and "cut" not in keys:
        keys.insert(0, "cut")
    if "merchant" in normalized_action and "approach" not in keys:
        keys.append("approach")
    if "symbiote" in normalized_action and "bond" not in keys:
        keys.append("bond")
    return keys[:3]


def _voice_alias_phrases_from_text(text: str) -> list[str]:
    normalized = _normalize_voice_alias(text)
    if not normalized:
        return []
    phrases: list[str] = []
    for chunk in re.split(r"[.!?;:,/\\-]+", normalized):
        tokens = _voice_alias_tokens(chunk)
        if not tokens:
            continue
        if len(tokens) <= VOICE_ALIAS_MAX_WORDS:
            phrases.append(" ".join(tokens))
        for token in tokens:
            phrases.append(token)
        for size in range(2, min(VOICE_ALIAS_MAX_WORDS, len(tokens)) + 1):
            for start in range(0, len(tokens) - size + 1):
                window = tokens[start:start + size]
                phrases.append(" ".join(window))
    return _dedupe_alias_phrases(phrases)


def _voice_alias_score_for_phrase(phrase: str, base_score: float) -> float:
    tokens = _voice_alias_tokens(phrase)
    if not tokens:
        return 0.0
    score = base_score
    if len(tokens) == 1:
        score += 0.03
    elif len(tokens) == 2:
        score += 0.05
    elif len(tokens) == 3:
        score += 0.02
    else:
        score -= 0.04
    if len(" ".join(tokens)) > 24:
        score -= 0.03
    if any(token in {"merchant", "spine", "pulse", "symbiote", "mutation"} for token in tokens):
        score += 0.03
    return score


def _voice_alias_tokens(text: str) -> list[str]:
    normalized = _normalize_voice_alias(text)
    if not normalized:
        return []
    tokens = [token for token in normalized.split() if token and token not in VOICE_ALIAS_STOP_WORDS]
    compacted: list[str] = []
    for token in tokens:
        if len(token) < 3 and token not in {"cut", "sip", "buy"}:
            continue
        compacted.append(token)
    return compacted[:VOICE_ALIAS_MAX_WORDS]


def _normalize_voice_alias(text: str) -> str:
    normalized = str(text).lower().strip()
    normalized = normalized.replace("/", " ").replace("\\", " ")
    normalized = re.sub(r"[^a-z0-9\s']", " ", normalized)
    normalized = normalized.replace("'", "")
    normalized = " ".join(normalized.split())
    return normalized


def _is_valid_voice_alias(alias: str) -> bool:
    if not alias:
        return False
    if alias in VOICE_ALIAS_BLOCKLIST:
        return False
    if len(alias.split()) > VOICE_ALIAS_MAX_WORDS:
        return False
    if len(alias.split()) < VOICE_ALIAS_MIN_WORDS:
        return False
    if len(alias) > 28:
        return False
    return True


def _dedupe_alias_phrases(phrases: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for phrase in phrases:
        normalized = _normalize_voice_alias(phrase)
        if _is_valid_voice_alias(normalized) and normalized not in seen:
            result.append(normalized)
            seen.add(normalized)
    return result


def load_vibe_guide() -> str:
    return read_text(VIBE_GUIDE_PATH)


def load_lore_guide() -> str:
    return read_text(LORE_GUIDE_PATH)


def load_setting_backbone() -> str:
    return read_text(SETTING_BACKBONE_PATH)


def load_story_room_contract() -> str:
    return read_text(STORY_ROOM_CONTRACT_PATH)


def load_ending_maze_architecture() -> str:
    return read_text(ENDING_MAZE_ARCHITECTURE_PATH)


def load_hymn_corpus_voice() -> str:
    return read_text(HYMN_CORPUS_VOICE_PATH)


def load_research_guides() -> str:
    parts: list[str] = []
    if RESEARCH_STACK_PATH.exists():
        parts.append("# Fleshpunk Corpus Research Stack\n" + read_text(RESEARCH_STACK_PATH))
    for path in RESEARCH_GUIDE_PATHS:
        if path.exists():
            title = path.stem.replace("_", " ").title()
            parts.append("# " + title + "\n" + read_text(path))
    if PULP_RETRIEVAL_INDEX_PATH.exists():
        parts.append("# Pulp Retrieval Index\n" + read_text(PULP_RETRIEVAL_INDEX_PATH))
    return "\n\n".join(parts)


def load_content_authorship_workflow() -> str:
    return read_text(CONTENT_AUTHORSHIP_WORKFLOW_PATH)


def load_accessibility_guide() -> str:
    return read_text(ACCESSIBILITY_GUIDE_PATH)


def load_recent_memory(limit: int = 12, include_core_guides: bool = True) -> str:
    parts = []
    if include_core_guides:
        parts.extend(
            [
                "# Vibe Guide\n" + load_vibe_guide(),
                "# Lore Guide\n" + load_lore_guide(),
                "# Setting Backbone\n" + load_setting_backbone(),
                "# Story Room Contract\n" + load_story_room_contract(),
                "# Ending Maze Architecture\n" + load_ending_maze_architecture(),
                "# Hymn Corpus Voice\n" + load_hymn_corpus_voice(),
                "# Research Guides\n" + load_research_guides(),
                "# Content Authorship Workflow\n" + load_content_authorship_workflow(),
                "# Accessibility Guide\n" + load_accessibility_guide(),
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
    if STORY_ARCHITECTURE_MEMORY_PATH.exists():
        lines = [line for line in STORY_ARCHITECTURE_MEMORY_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
        recent = lines[-limit:]
        if recent:
            parts.append("# Story Architecture Guidance\n" + "\n".join(recent))
    if ACCESSIBILITY_MEMORY_PATH.exists():
        lines = [line for line in ACCESSIBILITY_MEMORY_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
        recent = lines[-limit:]
        if recent:
            parts.append("# Accessibility Guidance\n" + "\n".join(recent))
    return "\n\n".join(parts)


def load_generation_memory_for_model(model: str) -> str:
    if not model.startswith("claude-"):
        return load_recent_memory()
    return "\n\n".join(
        [
            "# Claude Scenario Generation Brief\n"
            "Fleshpunk scenarios are Revelation-scale: compact, playable, story-rich scenes with premise, pressure, choice, result, and future implication. "
            "Every forward scenario starts from one to three tier-0 corpus anchors. Anchors are not flavor; they define the room foundation. "
            "A valid anchor names tier 0, source id/title/author, source file or locator, source moment, story element, and scenario application. "
            "If removing the anchors does not change the premise, choices, pressure, movement/combat problem, and progression vector, the scenario fails.\n\n"
            "Each scenario should enrich Hymn, destabilize Hymn, or both. Enrichment means capability, knowledge, reputation, body discipline, route understanding, or tactical confidence. "
            "Destabilization means injury, enemy attention, appetite, debt, faction suspicion, mutation hunger, route danger, or misrecognition. "
            "Good choices are physical actions the player understands: touch, cut, fight, wait, follow, dirty, brace, study, refuse, swallow, pay, or move. "
            "Do not expose risk labels or branch labels in player-facing text.\n\n"
            "Hymn's voice is empirical field report. Prefer visible structure, pressure, residue, markings, sound, heat, timing, body position, and immediate operational conclusions. "
            "Avoid mystical claims, source-name references, author costume diction, and abstract shorthand unless the term is grounded immediately in visible action. "
            "A normal reader should know what is happening without reading design notes.\n\n"
            "Combat is useful when it changes identity or pressure. Write posture, distance, contact, commitment, recovery, and consequence in plain language. "
            "Use martial research to make the action true, but do not lecture: 'too close for the tail' is better than specialist terminology. "
            "Progression through martial anatomy should change how Hymn moves, fights, reads rooms, or is recognized.\n\n"
            "Mutation and body changes should be multi-use: one in-encounter use, one out-of-encounter use, and one later surprising second use. "
            "Mutations are reliable always-on identity. Symbiotes are stronger but less dependable living partners with needs, cooldowns, wounds, preferences, or refusal pressure. "
            "Every scenario must preserve a playable baseline pure-body route, then use capability tags for any body-option branches instead of listing upgrades in player-facing prose. "
            "Room updates should attach corpus_anchors, corpus_influences, progression_state, environment_echoes, ending_vectors, and mutation_hooks when the scenario changes the room foundation.\n\n"
            "# Body Option Contract\n" + read_text(BODY_OPTION_CONTRACT_PATH),
            "# Glue Layer Contract\n" + read_text(GLUE_LAYER_CONTRACT_PATH),
            "# Pulp Retrieval Index\n" + read_text(PULP_RETRIEVAL_INDEX_PATH),
        ]
    )


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
        (STORY_ARCHITECTURE_MEMORY_PATH, "Story Architecture Guidance"),
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
        "existing_mutations": load_json(MUTATIONS_PATH).get("mutations", []),
        "existing_symbiotes": load_json(SYMBIOTES_PATH).get("symbiotes", []),
        "existing_enemies": enemy_ids(),
        "event_categories": event_categories(),
        "single_choice_room_gaps": room_tradeoff_findings(),
        "room_depth_findings": room_depth_findings(),
        "room_story_findings": room_story_findings(),
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


def room_tradeoff_findings() -> list[dict[str, str]]:
    payload = load_json(EVENTS_PATH)
    findings: list[dict[str, str]] = []

    def add(location: str, severity: str, issue: str, recommendation: str, button_count: int, event_type: str) -> None:
        findings.append({
            "location": location,
            "severity": severity,
            "issue": issue,
            "recommendation": recommendation,
            "button_count": str(button_count),
            "event_type": event_type,
        })

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
            button_count = commandable_button_count(event)
            if button_count < 2:
                event_id = str(event.get("id", "unknown"))
                add(
                    f"room_events.{room_id}.{event_id}",
                    "high",
                    f"single-choice room ({button_count} commandable button{'s' if button_count != 1 else ''})",
                    "Add a second legal choice with a distinct cost, delayed consequence, or alternative pressure axis. Transition events may stay exempt.",
                    button_count,
                    event_type or "unknown",
                )

    for finding in room_depth_findings():
        findings.append({
            "location": finding["location"],
            "severity": finding["severity"],
            "issue": finding["issue"],
            "recommendation": finding["recommendation"],
            "button_count": "n/a",
            "event_type": "room_depth",
        })
    for finding in room_story_findings():
        findings.append({
            "location": finding["location"],
            "severity": finding["severity"],
            "issue": finding["issue"],
            "recommendation": finding["recommendation"],
            "button_count": "n/a",
            "event_type": "room_story",
        })

    return findings


def _has_delayed_consequence(event: dict[str, Any]) -> bool:
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
    text_lower = text.lower()
    delayed_terms = {
        "later",
        "again",
        "return",
        "remembers",
        "remember",
        "learns",
        "learn",
        "claim",
        "debt",
        "mark",
        "scent",
        "tracks",
        "future",
        "next",
        "behind me",
    }
    return any(term in text_lower for term in delayed_terms)


def _has_interactable_actor(event: dict[str, Any]) -> bool:
    actor_keys = {
        "character_id",
        "beast_id",
        "animal_id",
        "infrastructure_actor",
        "organ_actor",
        "system_actor",
        "faction_id",
        "enemy_id",
        "symbiote_id",
        "mutation_id",
    }
    if any(str(event.get(key, "")).strip() for key in actor_keys):
        return True
    symbiote_choices = event.get("symbiote_choices", [])
    if isinstance(symbiote_choices, list) and any(str(choice).strip() for choice in symbiote_choices):
        return True
    if event.get("symbiote_choice_count") is not None:
        return True
    text = "%s %s" % (event.get("line_1", ""), event.get("line_2", ""))
    text_lower = text.lower()
    actor_terms = {
        "mouth",
        "mouths",
        "organ",
        "room",
        "beast",
        "animal",
        "parasite",
        "merchant",
        "chorus",
        "tool",
        "larder",
        "scale",
        "map",
        "lock",
        "rings",
        "ribs",
        "tissue",
        "valve",
        "plate",
        "pressure plate",
        "seam",
        "wall",
        "body",
        "bodies",
        "symbiote",
        "symbiotes",
    }
    return any(term in text_lower for term in actor_terms)


def _has_only_immediate_stat_surface(event: dict[str, Any]) -> bool:
    immediate_keys = {
        "biomass",
        "biomass_cost",
        "damage",
        "break_damage",
        "heal",
        "shield",
        "mutation_id",
        "enemy_id",
    }
    if not any(key in event for key in immediate_keys):
        return False
    return not _has_delayed_consequence(event)


def _is_story_engine_track(rooms_payload: dict[str, Any]) -> bool:
    return str(rooms_payload.get("content_track", "")) == STORY_ENGINE_CONTENT_TRACK


def _has_environment_group(room_record: dict[str, Any]) -> bool:
    return any(room_record.get(key) for key in ENVIRONMENT_GROUP_KEYS)


def _has_instance_situation(record: dict[str, Any]) -> bool:
    if any(record.get(key) for key in INSTANCE_SITUATION_KEYS):
        return True
    text = "%s %s" % (record.get("line_1", ""), record.get("line_2", ""))
    return bool(text.strip())


def _has_environment_echo_plan(room_record: dict[str, Any]) -> bool:
    return any(room_record.get(key) for key in ENVIRONMENT_ECHO_KEYS)


def _environment_id_for_room(room_id: str, room_record: dict[str, Any]) -> str:
    for key in ENVIRONMENT_GROUP_KEYS:
        value = str(room_record.get(key, "")).strip()
        if value:
            return value
    return room_id


def _corpus_influence_records(room_record: dict[str, Any]) -> list[dict[str, Any]]:
    for key in CORPUS_INFLUENCE_KEYS:
        if key not in room_record:
            continue
        records = room_record.get(key, [])
        if isinstance(records, list):
            return [record for record in records if isinstance(record, dict)]
    return []


def _has_specific_corpus_influence(room_record: dict[str, Any]) -> bool:
    for record in _corpus_influence_records(room_record):
        has_source = bool(
            str(record.get("seed_id", "")).strip()
            or str(record.get("source_id", "")).strip()
            or str(record.get("source_title", "")).strip()
            or str(record.get("source_layer", "")).strip()
            or str(record.get("research_layer", "")).strip()
        )
        has_specific_moment = bool(
            str(record.get("source_moment", "")).strip()
            or str(record.get("writing_influence", "")).strip()
            or str(record.get("structural_idea", "")).strip()
            or str(record.get("scene_function", "")).strip()
            or str(record.get("combat_exchange", "")).strip()
            or str(record.get("progression_beat", "")).strip()
            or str(record.get("source_bit", "")).strip()
            or str(record.get("source_excerpt", "")).strip()
            or str(record.get("source_detail", "")).strip()
            or str(record.get("character_function", "")).strip()
        )
        has_application = bool(
            str(record.get("room_application", "")).strip()
            or str(record.get("scenario_application", "")).strip()
            or str(record.get("room_reflection", "")).strip()
            or str(record.get("transform", "")).strip()
            or str(record.get("mechanic_reflection", "")).strip()
        )
        if has_source and has_specific_moment and has_application:
            return True
    return False


def _has_tier0_corpus_anchor(room_record: dict[str, Any]) -> bool:
    anchors = room_record.get("corpus_anchors", [])
    if not isinstance(anchors, list):
        return False
    required = (
        "source_id",
        "source_title",
        "source_author",
        "source_moment",
        "story_element",
        "scenario_application",
    )
    for anchor in anchors:
        if not isinstance(anchor, dict):
            continue
        tier = str(anchor.get("tier", "")).strip()
        has_tier = tier in {"0", "tier0", "tier-0"}
        has_source_location = bool(
            str(anchor.get("source_file", "")).strip()
            or str(anchor.get("source_url", "")).strip()
            or str(anchor.get("source_locator", "")).strip()
            or str(anchor.get("research_source", "")).strip()
        )
        has_required = all(str(anchor.get(key, "")).strip() for key in required)
        if has_tier and has_source_location and has_required:
            return True
    return False


def _has_ending_vector(room_record: dict[str, Any]) -> bool:
    vectors = room_record.get("ending_vectors", [])
    return isinstance(vectors, list) and any(isinstance(vector, dict) and vector.get("id") for vector in vectors)


def _has_mutation_hooks(room_record: dict[str, Any]) -> bool:
    hooks = room_record.get("mutation_hooks", [])
    return isinstance(hooks, list) and any(isinstance(hook, dict) and hook.get("capability") for hook in hooks)


def _has_multiuse_mutation_hooks(room_record: dict[str, Any]) -> bool:
    hooks = room_record.get("mutation_hooks", [])
    if not isinstance(hooks, list):
        return False
    for hook in hooks:
        if not isinstance(hook, dict):
            continue
        in_use = str(hook.get("in_encounter_use", "")).strip() or str(hook.get("combat_use", "")).strip()
        out_use = str(hook.get("out_of_encounter_use", "")).strip() or str(hook.get("exploration_use", "")).strip()
        second_use = str(hook.get("surprising_second_use", "")).strip() or str(hook.get("later_use", "")).strip()
        if in_use and out_use and second_use:
            return True
    return False


def body_option_hook_errors(hooks: Any, location: str) -> list[str]:
    errors: list[str] = []
    if not hooks:
        return errors
    if not isinstance(hooks, list):
        return [f"{location}: mutation_hooks must be a list"]
    for index, hook in enumerate(hooks):
        if not isinstance(hook, dict):
            errors.append(f"{location}[{index}]: mutation hook is not an object")
            continue
        tags = hook.get("capability_tags", [])
        if not isinstance(tags, list) or not any(str(tag).strip() for tag in tags):
            errors.append(f"{location}[{index}]: missing capability_tags")
        if not str(hook.get("baseline_route", "")).strip():
            errors.append(f"{location}[{index}]: missing baseline_route")
        if not str(hook.get("mutation_branch", "")).strip() and not str(hook.get("symbiote_branch", "")).strip():
            errors.append(f"{location}[{index}]: needs mutation_branch or symbiote_branch")
    return errors


def _scenario_character_change(record: dict[str, Any]) -> str:
    for key in ("character_change", "character_change_vector", "scenario_change", "progression_vector"):
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip().lower()
        if isinstance(value, dict):
            for nested_key in ("type", "mode", "vector"):
                nested = value.get(nested_key)
                if isinstance(nested, str) and nested.strip():
                    return nested.strip().lower()
    return ""


def _has_character_change_vector(record: dict[str, Any]) -> bool:
    value = _scenario_character_change(record)
    if any(term in value for term in ("enrich", "destabilize", "both")):
        return True
    return bool(str(record.get("enrichment", "")).strip() or str(record.get("destabilization", "")).strip())


def _has_possibility_tree(record: dict[str, Any]) -> bool:
    for key in ("possibility_tree", "branch_pressures", "future_branches", "branching_consequences"):
        value = record.get(key)
        if isinstance(value, list) and len(value) >= 2:
            return True
        if isinstance(value, dict) and len(value) >= 2:
            return True
    return False


def _has_room_memory_change(event: dict[str, Any]) -> bool:
    return any(event.get(key) for key in ROOM_MEMORY_KEYS)


def _has_action_specific_result(event: dict[str, Any]) -> bool:
    if any(event.get(key) for key in ACTION_RESULT_KEYS):
        return True
    buttons = event.get("buttons", [])
    if not isinstance(buttons, list):
        return False
    button_result_keys = {
        "result_lines",
        "outcome",
        "consequence",
        "room_state_changes",
        "memory_key",
    }
    return any(isinstance(button, dict) and any(button.get(key) for key in button_result_keys) for button in buttons)


def _followups_are_default_only(event: dict[str, Any]) -> bool:
    followups = event.get("story_followups")
    if not isinstance(followups, dict):
        return False
    return bool(followups) and set(str(key) for key in followups.keys()) == {"default"}


def _commandable_button_count(event: dict[str, Any]) -> int:
    return commandable_button_count(event)


def _room_infrastructure_records(room_record: dict[str, Any]) -> list[dict[str, Any]]:
    records = room_record.get("animal_infrastructure", [])
    if not isinstance(records, list):
        return []
    return [record for record in records if isinstance(record, dict)]


def _event_mentions_room_infrastructure(event: dict[str, Any], room_record: dict[str, Any]) -> bool:
    records = _room_infrastructure_records(room_record)
    if not records:
        return False
    parts: list[str] = [
        str(event.get("line_1", "")),
        str(event.get("line_2", "")),
        str(event.get("infrastructure_actor", "")),
        str(event.get("animal_infrastructure", "")),
    ]
    buttons = event.get("buttons", [])
    if isinstance(buttons, list):
        for button in buttons:
            if isinstance(button, dict):
                parts.append(str(button.get("label", "")))
                parts.append(str(button.get("action", "")))
    text = " ".join(parts).lower().replace("_", " ")
    for record in records:
        record_parts = [
            str(record.get("id", "")).replace("_", " "),
            str(record.get("function", "")),
        ]
        possible = record.get("possible_interactions", [])
        if isinstance(possible, list):
            record_parts.extend(str(item).replace("_", " ") for item in possible)
        signature = " ".join(record_parts).lower()
        signature_terms = [
            term
            for term in re.findall(r"[a-z0-9]+", signature)
            if len(term) > 3 and term not in {"with", "that", "they", "from", "into", "after", "before", "room", "work"}
        ]
        if signature_terms and any(term in text for term in signature_terms):
            return True
    return False


def _append_grouped_migration_findings(
    findings: list[dict[str, str]],
    grouped: dict[str, dict[str, Any]],
) -> None:
    for item in grouped.values():
        count = int(item.get("count", 0))
        if count <= 0:
            continue
        examples = item.get("examples", [])
        example_text = ""
        if isinstance(examples, list) and examples:
            example_text = " Examples: " + ", ".join(str(example) for example in examples[:5])
            if count > len(examples[:5]):
                example_text += ", ..."
        findings.append({
            "location": str(item.get("location", "migration")),
            "severity": str(item.get("severity", "medium")),
            "issue": f"{count} {item.get('issue', 'migration finding')}",
            "recommendation": str(item.get("recommendation", "")) + example_text,
        })


def _record_grouped_migration_finding(
    grouped: dict[str, dict[str, Any]],
    key: str,
    *,
    location: str,
    severity: str,
    issue: str,
    recommendation: str,
    example: str,
) -> None:
    item = grouped.setdefault(
        key,
        {
            "location": location,
            "severity": severity,
            "issue": issue,
            "recommendation": recommendation,
            "count": 0,
            "examples": [],
        },
    )
    item["count"] = int(item.get("count", 0)) + 1
    examples = item.setdefault("examples", [])
    if isinstance(examples, list) and len(examples) < 8:
        examples.append(example)


def room_depth_findings(mode: str = "migration") -> list[dict[str, str]]:
    strict_new_contract = mode == "strict"
    payload = load_json(EVENTS_PATH)
    rooms_payload = load_json(ROOMS_PATH)
    findings: list[dict[str, str]] = []
    grouped_migration: dict[str, dict[str, Any]] = {}
    room_events = payload.get("room_events", {})
    if not isinstance(room_events, dict):
        return findings
    rooms_by_id = {
        str(room.get("id", "")): room
        for room in rooms_payload.get("rooms", [])
        if isinstance(room, dict) and room.get("id")
    }
    story_engine_track = _is_story_engine_track(rooms_payload)
    environment_event_counts: dict[str, int] = {}
    if story_engine_track:
        for room_id, events in room_events.items():
            room_record = rooms_by_id.get(str(room_id), {})
            environment_id = _environment_id_for_room(str(room_id), room_record)
            event_count = len(events) if isinstance(events, list) else 0
            environment_event_counts[environment_id] = environment_event_counts.get(environment_id, 0) + event_count

    def add(location: str, severity: str, issue: str, recommendation: str) -> None:
        findings.append({
            "location": location,
            "severity": severity,
            "issue": issue,
            "recommendation": recommendation,
        })

    for room_id, events in room_events.items():
        if not isinstance(events, list):
            add(f"room_events.{room_id}", "high", "room events are not a list", "Room depth cannot be evaluated until events are structured.")
            continue
        room_location = f"room_events.{room_id}"
        room_record = rooms_by_id.get(str(room_id), {})
        narrow_room = is_narrow_room_role(room_record)
        environment_id = _environment_id_for_room(str(room_id), room_record)
        family_event_count = environment_event_counts.get(environment_id, len(events)) if story_engine_track else len(events)
        if family_event_count < 3 and not narrow_room:
            add(
                room_location,
                "high",
                f"thin environment family: only {family_event_count} event{'s' if family_event_count != 1 else ''}",
                "Add enough distinct scenario instances or events inside this environment family to support story pressure, branch possibility, and delayed consequences before calling it complete.",
            )
        if story_engine_track and not _has_environment_group(room_record):
            add(
                room_location,
                "medium",
                "room lacks explicit environment grouping",
                "Add environment_id or environment_family so this room is one instance of a larger environment type, not a literal room the player is expected to revisit.",
            )
        if story_engine_track and not narrow_room and not _has_environment_echo_plan(room_record):
            add(
                room_location,
                "medium",
                "environment has no echo plan",
                "Add environment_echoes, later_instance_echoes, or environment_memory_states describing how choices can surface in later similar rooms.",
            )
        if story_engine_track and not _has_specific_corpus_influence(room_record):
            add(
                room_location,
                "high",
                "scenario lacks a specific corpus/research influence",
                "Add corpus_influences or research_influences with source layer/id, the specific pulp/martial/biological/progression move, and how it changes this scenario.",
            )
        if story_engine_track and not _has_tier0_corpus_anchor(room_record):
            if strict_new_contract:
                add(
                    room_location,
                    "high",
                    "scenario lacks tier-0 corpus anchors",
                    "Add corpus_anchors with tier 0, source id/title/author, source file or locator, source moment, story element, and scenario application. The anchors must be the room foundation, not after-the-fact flavor.",
                )
            else:
                _record_grouped_migration_finding(
                    grouped_migration,
                    "tier0_corpus_anchors",
                    location="migration.corpus_anchors",
                    severity="medium",
                    issue="legacy/current rooms lack tier-0 corpus anchors",
                    recommendation="Add sourced corpus_anchors during migration. Anchors should define pressure, combat/movement, progression, or reversal before drafting.",
                    example=room_location,
                )
        if story_engine_track and not narrow_room and not _has_ending_vector(room_record):
            add(
                room_location,
                "high",
                "environment has no ending vector",
                "Add ending_vectors naming the ending this environment can pull toward, what behavior feeds it, and what diverts it.",
            )
        if story_engine_track and not narrow_room and not _has_mutation_hooks(room_record):
            add(
                room_location,
                "medium",
                "environment has no mutation openings",
                "Add mutation_hooks with concrete multi-use capability tags that alter both encounters and out-of-encounter choices.",
            )
        if story_engine_track and not narrow_room and _has_mutation_hooks(room_record) and not _has_multiuse_mutation_hooks(room_record):
            if strict_new_contract:
                add(
                    room_location,
                    "medium",
                    "mutation hooks are not multi-use",
                    "Mutation hooks should name in_encounter_use, out_of_encounter_use, and surprising_second_use so mutations feel like progression tools instead of stat buttons.",
                )
            else:
                _record_grouped_migration_finding(
                    grouped_migration,
                    "multiuse_mutation_hooks",
                    location="migration.mutation_hooks",
                    severity="low",
                    issue="environment families have legacy mutation hooks without multi-use fields",
                    recommendation="Add in_encounter_use, out_of_encounter_use, and surprising_second_use as each family is migrated.",
                    example=room_location,
                )

        actor_found = False
        delayed_found = False
        memory_found = False
        infrastructure_used = False
        for event in events:
            if not isinstance(event, dict):
                continue
            actor_found = actor_found or _has_interactable_actor(event)
            delayed_found = delayed_found or _has_delayed_consequence(event)
            memory_found = memory_found or _has_room_memory_change(event)
            infrastructure_used = infrastructure_used or _event_mentions_room_infrastructure(event, room_record)
            event_id = str(event.get("id", "unknown"))
            location = f"{room_location}.{event_id}"
            if story_engine_track and not _has_action_specific_result(event):
                add(
                    location,
                    "high",
                    "post-update event relies on generic legacy action results",
                    "Add action_results or per-button result lines/state changes so outcomes show what changed in the story instead of only reporting shared stats.",
                )
            if story_engine_track and not (_has_character_change_vector(event) or _has_character_change_vector(room_record)):
                if strict_new_contract:
                    add(
                        location,
                        "high",
                        "scenario has no character-change vector",
                        "Add character_change as enrich, destabilize, or both, with progression pressure in result data or designer metadata.",
                    )
                else:
                    _record_grouped_migration_finding(
                        grouped_migration,
                        "character_change",
                        location="migration.character_change",
                        severity="medium",
                        issue="legacy/current events lack character_change metadata",
                        recommendation="Add character_change during scenario migration. Do not treat this as a player-facing blocker for old content.",
                        example=location,
                    )
            if story_engine_track and _commandable_button_count(event) > 1 and not (_has_possibility_tree(event) or _has_possibility_tree(room_record)):
                if strict_new_contract:
                    add(
                        location,
                        "medium",
                        "scenario has no possibility tree metadata",
                        "Add possibility_tree or branch_pressures in designer metadata. Keep branches implicit in player-facing prose.",
                    )
                else:
                    _record_grouped_migration_finding(
                        grouped_migration,
                        "possibility_tree",
                        location="migration.possibility_tree",
                        severity="low",
                        issue="legacy/current events lack possibility_tree metadata",
                        recommendation="Add possibility_tree or branch_pressures during migration; keep branches implicit in player-facing text.",
                        example=location,
                    )
            if story_engine_track and _commandable_button_count(event) > 1 and _followups_are_default_only(event):
                add(
                    f"{location}.story_followups",
                    "medium",
                    "all choices enqueue the same default follow-up",
                    "Prefer action-specific follow-ups, or document why every choice awakens the same later character/faction beat.",
                )
            if _has_only_immediate_stat_surface(event):
                add(
                    location,
                    "high",
                    "immediate stat exchange without delayed consequence",
                    "Attach the choice to future room text, route state, deck pressure, character posture, beast behavior, claim, debt, scent, or pursuit.",
                )
            if not _has_interactable_actor(event):
                add(
                    location,
                    "medium",
                    "no clear interactable actor or infrastructure system",
                    "Name what Hymn is interacting with: character, beast, animal, organ, parasite, tool, market, route intelligence, or maintenance process.",
                )
            if str(event.get("enemy_id", "")) and not any(key in event for key in ("beast_state_change", "infrastructure_actor", "reaction_tags", "delayed_consequence")):
                add(
                    location,
                    "high",
                    "combat lacks story consequence",
                    "Give the encounter posture, distance, recovery, scar, respect, fear, hunger, rival attention, learned stance, or mutation appetite.",
                )

        if not delayed_found and not narrow_room:
            add(
                room_location,
                "high",
                "room lacks explicit delayed consequence or memory hook",
                "At least one event should change later instance text, deck pressure, route state, actor state, claim, debt, pursuit, or available choices.",
            )
        if story_engine_track and not memory_found:
            add(
                room_location,
                "high",
                "environment lacks explicit memory/state changes",
                "Add environment_state_changes, environment_memory_flags, actor_state_changes, route_state_changes, or faction_state_changes so choices can alter later room instances or pressure.",
            )
        if story_engine_track and _room_infrastructure_records(room_record) and not infrastructure_used:
            add(
                room_location,
                "medium",
                "declared animal infrastructure is not used by events",
                "Mention and manipulate at least one declared infrastructure actor in room events, choices, or action results.",
            )
        if not actor_found:
            add(
                room_location,
                "medium",
                "room lacks an interactable character, beast, animal, or infrastructure actor",
                "Make the room more than scenery by assigning a behaving system the player can influence.",
            )

    if not strict_new_contract:
        _append_grouped_migration_findings(findings, grouped_migration)
    return findings


def _has_story_anchor(event: dict[str, Any]) -> bool:
    story_keys = {
        "character_id",
        "faction_id",
        "storyline_id",
        "story_stage",
        "source_character_function",
        "animal_infrastructure",
        "recurring_character_id",
        "cross_run_story_hook",
    }
    if any(str(event.get(key, "")).strip() for key in story_keys):
        return True
    text = "%s %s" % (event.get("line_1", ""), event.get("line_2", ""))
    text_lower = text.lower()
    story_terms = {
        "chorus",
        "merchant",
        "operator",
        "operators",
        "survey",
        "rite",
        "ledger",
        "larder",
        "toll",
        "ferry",
        "beetle",
        "larva",
        "larval",
        "mites",
        "hounds",
        "mouths",
        "chapel",
        "map",
    }
    return any(term in text_lower for term in story_terms)


def room_story_findings() -> list[dict[str, str]]:
    payload = load_json(EVENTS_PATH)
    rooms_payload = load_json(ROOMS_PATH)
    special_events = payload.get("special_events", {})
    if not isinstance(special_events, dict):
        special_events = {}
    rooms_by_id = {
        str(room.get("id", "")): room
        for room in rooms_payload.get("rooms", [])
        if isinstance(room, dict) and room.get("id")
    }
    findings: list[dict[str, str]] = []
    room_events = payload.get("room_events", {})
    if not isinstance(room_events, dict):
        return findings

    def add(location: str, severity: str, issue: str, recommendation: str) -> None:
        findings.append({
            "location": location,
            "severity": severity,
            "issue": issue,
            "recommendation": recommendation,
        })

    for room_id, events in room_events.items():
        if not isinstance(events, list):
            continue
        room_location = f"room_events.{room_id}"
        room_record = rooms_by_id.get(str(room_id), {})
        narrow_room = is_narrow_room_role(room_record)
        room_text = " ".join([
            str(room_record.get("first_visit_description", "")),
            str(room_record.get("return_description", "")),
            " ".join(str(tag) for tag in room_record.get("tags", []) if str(tag)),
        ])
        room_story_anchor = _has_story_anchor({"line_1": room_text, "line_2": ""})
        chorus_frame = "chorus" in room_text.lower()
        explicit_story_keys = [
            "faction_ids",
            "storyline_ids",
            "recurring_character_ids",
            "animal_infrastructure",
            "cross_run_story_hooks",
            "progression_state",
        ]
        required_story_keys = explicit_story_keys
        if narrow_room:
            required_story_keys = [
                "faction_ids",
                "storyline_ids",
                "cross_run_story_hooks",
                "progression_state",
            ]
        missing_story_keys = [key for key in required_story_keys if not room_record.get(key)]
        story_events = [event for event in events if isinstance(event, dict) and _has_story_anchor(event)]
        delayed_events = [event for event in events if isinstance(event, dict) and _has_delayed_consequence(event)]
        story_followup_refs: list[str] = []
        for event in events:
            if isinstance(event, dict):
                story_followup_refs.extend(_story_followup_event_ids(event))
                for followup in _story_followup_entries(event):
                    if int(followup.get("delay_rooms", 0)) < 1:
                        add(
                            f"{room_location}.{str(event.get('id', 'unknown'))}.story_followups",
                            "high",
                            "story follow-up fires too soon",
                            "Set delay_rooms to at least 1 so the character/faction beat enters later instead of acting like extra result text.",
                        )
        if missing_story_keys:
            add(
                room_location,
                "high",
                "room lacks complete explicit story backbone",
                "Add non-empty room metadata for: %s." % ", ".join(missing_story_keys),
            )
        if not story_events and not room_story_anchor:
            add(
                room_location,
                "high",
                "room is not anchored to the setting backbone",
                "Tie the room to a faction, recurring character trace, animal infrastructure role, or cross-run storyline.",
            )
        if not delayed_events and not narrow_room:
            add(
                room_location,
                "high",
                "room story has no later-instance or delayed motion",
                "Add a story hook that returns as altered later-instance text, debt, scent, route dependency, faction posture, animal behavior, deck pressure, or ending pressure.",
            )
        if (story_events or room_story_anchor) and not chorus_frame and not any("Chorus" in str(event.get("line_1", "")) or "Chorus" in str(event.get("line_2", "")) for event in story_events):
            add(
                room_location,
                "medium",
                "story anchor lacks Hymn-to-Chorus reporting frame",
                "Keep room story in Hymn's first-person field report frame, with Chorus contacted, checked, or conspicuously absent.",
            )
        if not story_followup_refs and not narrow_room:
            add(
                room_location,
                "high",
                "room story does not enqueue follow-up events",
                "Progress character/faction stories by queueing one-shot special events or later environment echoes from room events, not by relying on literal room revisits.",
            )
        for followup_id in story_followup_refs:
            location = f"{room_location}.story_followups.{followup_id}"
            followup = special_events.get(followup_id, {})
            if not isinstance(followup, dict):
                add(
                    location,
                    "high",
                    "story follow-up references missing special event",
                    "Add the referenced special event or remove the story_followups entry.",
                )
                continue
            if bool(followup.get("reactivate_on_reshuffle", True)):
                add(
                    location,
                    "high",
                    "story follow-up can retrigger in same run",
                    "Set reactivate_on_reshuffle to false and use a trigger_key so character/faction beats are one-shot per run.",
                )

    return findings


def _story_followup_event_ids(event: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    for followup in _story_followup_entries(event):
        event_id = str(followup.get("event_id", ""))
        if event_id:
            ids.append(event_id)
    return sorted(set(ids))


def _story_followup_entries(event: dict[str, Any]) -> list[dict[str, Any]]:
    followups = event.get("story_followups")
    entries: list[dict[str, Any]] = []

    def add_from_value(value: Any) -> None:
        if isinstance(value, str) and value:
            entries.append({"event_id": value})
        elif isinstance(value, dict):
            entries.append(value)

    if isinstance(followups, str):
        add_from_value(followups)
    elif isinstance(followups, dict):
        for value in followups.values():
            add_from_value(value)
    elif isinstance(followups, list):
        for value in followups:
            add_from_value(value)

    return entries


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


def _short_visible_lines(value: Any, limit: int = 3) -> list[str]:
    if not isinstance(value, list):
        return []
    lines: list[str] = []
    for item in value:
        text = str(item).strip()
        if text:
            lines.append(text)
        if len(lines) >= limit:
            break
    return lines


def _blind_choice_read(event: dict[str, Any]) -> list[dict[str, Any]]:
    buttons = event.get("buttons", [])
    action_results = event.get("action_results", {})
    story_followups = event.get("story_followups", {})
    choices: list[dict[str, Any]] = []
    if not isinstance(buttons, list):
        return choices

    for button in buttons:
        if not isinstance(button, dict):
            continue
        label = str(button.get("label", "")).strip()
        if not label:
            continue
        action = str(button.get("action", "")).strip()
        action_result = action_results.get(action, {}) if isinstance(action_results, dict) else {}
        followup = story_followups.get(action, {}) if isinstance(story_followups, dict) else {}
        choice: dict[str, Any] = {"label": label}
        result_lines = _short_visible_lines(action_result.get("lines", [])) if isinstance(action_result, dict) else []
        if result_lines:
            choice["result_lines"] = result_lines
        if isinstance(followup, dict):
            queued_line = str(followup.get("queued_line", "")).strip()
            if queued_line:
                choice["queued_followup_line"] = queued_line
        choices.append(choice)
    return choices


def _blind_event_read(event: dict[str, Any]) -> dict[str, Any]:
    visible_event: dict[str, Any] = {
        "id": str(event.get("id", "")).strip(),
        "type": str(event.get("type", "")).strip(),
    }
    line_1 = str(event.get("line_1", "")).strip()
    line_2 = str(event.get("line_2", "")).strip()
    if line_1:
        visible_event["line_1"] = line_1
    if line_2:
        visible_event["line_2"] = line_2
    choices = _blind_choice_read(event)
    if choices:
        visible_event["choices"] = choices
    return visible_event


def _cold_event_read(event: dict[str, Any]) -> dict[str, Any]:
    visible_event: dict[str, Any] = {
        "id": str(event.get("id", "")).strip(),
        "type": str(event.get("type", "")).strip(),
    }
    line_1 = str(event.get("line_1", "")).strip()
    line_2 = str(event.get("line_2", "")).strip()
    if line_1:
        visible_event["line_1"] = line_1
    if line_2:
        visible_event["line_2"] = line_2
    buttons = event.get("buttons", [])
    if isinstance(buttons, list):
        choices = [
            {"label": str(button.get("label", "")).strip(), "action": str(button.get("action", "")).strip()}
            for button in buttons
            if isinstance(button, dict) and str(button.get("label", "")).strip()
        ]
        if choices:
            visible_event["choices"] = choices
    return visible_event


def blind_player_text_context() -> dict[str, Any]:
    rooms_payload = load_json(ROOMS_PATH)
    events_payload = load_json(EVENTS_PATH)
    decks_payload = load_json(DECKS_PATH)
    rooms_by_id = {
        str(room.get("id", "")): room
        for room in rooms_payload.get("rooms", [])
        if isinstance(room, dict) and str(room.get("id", "")).strip()
    }
    room_events = events_payload.get("room_events", {})
    special_events = events_payload.get("special_events", {})
    visible_rooms: list[dict[str, Any]] = []

    if isinstance(room_events, dict):
        for room_id in sorted(room_events.keys()):
            room = rooms_by_id.get(str(room_id), {})
            room_read: dict[str, Any] = {
                "room_id": str(room_id),
                "name": str(room.get("name", "")).strip(),
                "first_visit_description": str(room.get("first_visit_description", "")).strip(),
                "return_description": str(room.get("return_description", "")).strip(),
                "events": [],
            }
            events = room_events.get(room_id, [])
            if isinstance(events, list):
                room_read["events"] = [_blind_event_read(event) for event in events if isinstance(event, dict)]
            visible_rooms.append(room_read)

    visible_special_events: list[dict[str, Any]] = []
    special_event_values: list[Any] = []
    if isinstance(special_events, dict):
        special_event_values = list(special_events.values())
    elif isinstance(special_events, list):
        special_event_values = special_events
    for event in special_event_values:
        if isinstance(event, dict):
            visible_special_events.append(_blind_event_read(event))

    return {
        "read_rule": "Judge this as a first-time player with no design notes, lore primer, system knowledge, or author intent. Use only these visible room descriptions, event lines, result lines, queued follow-up lines, and choice labels.",
        "opening_room_id": str(decks_payload.get("opening_room_id", "")).strip(),
        "rooms": visible_rooms,
        "special_events": visible_special_events,
    }


def cold_read_text_context() -> dict[str, Any]:
    events_payload = load_json(EVENTS_PATH)
    decks_payload = load_json(DECKS_PATH)
    scope = _playtest_slice_scope()
    room_ids = scope.get("room_ids", set())
    event_ids = scope.get("event_ids", set())
    special_event_ids = scope.get("special_event_ids", set())
    room_events = events_payload.get("room_events", {})
    visible_events: list[dict[str, Any]] = []
    if isinstance(room_events, dict):
        for room_id in sorted(room_ids):
            events = room_events.get(room_id, [])
            if not isinstance(events, list):
                continue
            for event in events:
                if not isinstance(event, dict):
                    continue
                event_id = str(event.get("id", "")).strip()
                if event_ids and event_id not in event_ids:
                    continue
                event_read = _cold_event_read(event)
                event_read["room_id"] = str(room_id)
                visible_events.append(event_read)

    visible_special_events: list[dict[str, Any]] = []
    special_events_payload = events_payload.get("special_events", {})
    if isinstance(special_events_payload, dict):
        for event_id in sorted(special_event_ids):
            event = special_events_payload.get(event_id, {})
            if isinstance(event, dict):
                visible_special_events.append(_cold_event_read(event))

    return {
        "read_rule": "Cold read. Use only the current screen text and choice labels below. Do not use lore, corpus notes, room metadata, hidden consequences, prior drafts, or design intent.",
        "task_standard": [
            "A new player should understand what is physically present.",
            "A new player should understand where Hymn is positioned.",
            "A new player should understand why choosing now matters.",
            "Each choice label should imply a concrete action.",
        ],
        "deck": {
            "opening_event_id": str(decks_payload.get("opening_event_id", "")).strip(),
            "playtest_event_ids": sorted(event_ids),
        },
        "events": visible_events,
        "special_events": visible_special_events,
    }


def playtest_slice_text_context() -> dict[str, Any]:
    rooms_payload = load_json(ROOMS_PATH)
    events_payload = load_json(EVENTS_PATH)
    decks_payload = load_json(DECKS_PATH)
    scope = _playtest_slice_scope()
    room_ids = scope.get("room_ids", set())
    event_ids = scope.get("event_ids", set())
    special_event_ids = scope.get("special_event_ids", set())
    rooms_by_id = {
        str(room.get("id", "")): room
        for room in rooms_payload.get("rooms", [])
        if isinstance(room, dict) and str(room.get("id", "")).strip()
    }
    visible_rooms: list[dict[str, Any]] = []
    room_events = events_payload.get("room_events", {})
    if isinstance(room_events, dict):
        for room_id in sorted(room_ids):
            room = rooms_by_id.get(str(room_id), {})
            events = room_events.get(room_id, [])
            room_read: dict[str, Any] = {
                "room_id": str(room_id),
                "name": str(room.get("name", "")).strip(),
                "first_visit_description": str(room.get("first_visit_description", "")).strip(),
                "return_description": str(room.get("return_description", "")).strip(),
                "events": [],
            }
            if isinstance(events, list):
                room_read["events"] = [
                    _blind_event_read(event)
                    for event in events
                    if isinstance(event, dict)
                    and (not event_ids or str(event.get("id", "")).strip() in event_ids)
                ]
            visible_rooms.append(room_read)

    special_events_payload = events_payload.get("special_events", {})
    visible_special_events: list[dict[str, Any]] = []
    if isinstance(special_events_payload, dict):
        for event_id in sorted(special_event_ids):
            event = special_events_payload.get(event_id, {})
            if isinstance(event, dict):
                visible_special_events.append(_blind_event_read(event))

    return {
        "read_rule": "Minimal playtest-slice context for focused repair/generation. Do not infer from omitted legacy rooms.",
        "deck": {
            "playtest_slice": str(decks_payload.get("playtest_slice", "")).strip(),
            "opening_room_id": str(decks_payload.get("opening_room_id", "")).strip(),
            "opening_event_id": str(decks_payload.get("opening_event_id", "")).strip(),
            "playtest_event_ids": sorted(event_ids),
        },
        "rooms": visible_rooms,
        "special_events": visible_special_events,
        "writing_findings": event_writing_findings(playtest_slice=True),
    }


def _story_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def story_architect_context() -> dict[str, Any]:
    rooms_payload = load_json(ROOMS_PATH)
    events_payload = load_json(EVENTS_PATH)
    decks_payload = load_json(DECKS_PATH)
    room_events = events_payload.get("room_events", {})
    special_events = events_payload.get("special_events", {})
    rooms = rooms_payload.get("rooms", [])
    recurring_characters: dict[str, dict[str, Any]] = {}
    storyline_ids: dict[str, int] = {}
    faction_ids: dict[str, int] = {}
    room_story_inventory: list[dict[str, Any]] = []
    followup_refs: list[dict[str, Any]] = []

    if isinstance(rooms, list):
        for room in rooms:
            if not isinstance(room, dict):
                continue
            room_id = str(room.get("id", "")).strip()
            if not room_id:
                continue
            room_characters = _story_list(room.get("recurring_character_ids", []))
            for character_id in room_characters:
                record = recurring_characters.setdefault(character_id, {"id": character_id, "rooms": []})
                record["rooms"].append(room_id)
            for storyline_id in _story_list(room.get("storyline_ids", [])):
                storyline_ids[storyline_id] = storyline_ids.get(storyline_id, 0) + 1
            for faction_id in _story_list(room.get("faction_ids", [])):
                faction_ids[faction_id] = faction_ids.get(faction_id, 0) + 1
            room_story_inventory.append({
                "room_id": room_id,
                "name": str(room.get("name", "")).strip(),
                "instance_premise": str(room.get("instance_premise", "")).strip(),
                "recurring_character_ids": room_characters,
                "storyline_ids": _story_list(room.get("storyline_ids", [])),
                "faction_ids": _story_list(room.get("faction_ids", [])),
                "progression_state": room.get("progression_state", {}),
                "cross_run_story_hooks": room.get("cross_run_story_hooks", []),
            })

    if isinstance(room_events, dict):
        for room_id, events in room_events.items():
            if not isinstance(events, list):
                continue
            for event in events:
                if not isinstance(event, dict):
                    continue
                event_id = str(event.get("id", "")).strip()
                story_followups = event.get("story_followups", {})
                if not isinstance(story_followups, dict):
                    continue
                for action_id, followup in story_followups.items():
                    if not isinstance(followup, dict):
                        continue
                    followup_refs.append({
                        "source_room_id": str(room_id),
                        "source_event_id": event_id,
                        "source_action": str(action_id),
                        "followup_event_id": str(followup.get("event_id", "")).strip(),
                        "trigger_key": str(followup.get("trigger_key", "")).strip(),
                        "delay_rooms": followup.get("delay_rooms"),
                        "queued_line": str(followup.get("queued_line", "")).strip(),
                    })

    special_event_summaries: list[dict[str, Any]] = []
    special_event_values: list[tuple[str, Any]] = []
    if isinstance(special_events, dict):
        special_event_values = [(str(event_id), event) for event_id, event in special_events.items()]
    elif isinstance(special_events, list):
        special_event_values = [(str(index), event) for index, event in enumerate(special_events)]
    for event_id, event in special_event_values:
        if not isinstance(event, dict):
            continue
        special_event_summaries.append({
            "id": str(event.get("id", event_id)).strip(),
            "type": str(event.get("type", "")).strip(),
            "line_1": str(event.get("line_1", "")).strip(),
            "line_2": str(event.get("line_2", "")).strip(),
            "buttons": [str(button.get("label", "")).strip() for button in event.get("buttons", []) if isinstance(button, dict)],
            "trigger_key": str(event.get("trigger_key", "")).strip(),
            "reactivate_on_reshuffle": event.get("reactivate_on_reshuffle"),
        })

    return {
        "goal": "Find the missing story spine and propose character-driven follow-up encounters grounded in current data.",
        "active_content": {
            "rooms_path": str(ROOMS_PATH.relative_to(ROOT)),
            "events_path": str(EVENTS_PATH.relative_to(ROOT)),
            "decks_path": str(DECKS_PATH.relative_to(ROOT)),
            "opening_room_id": str(decks_payload.get("opening_room_id", "")).strip(),
            "room_count": len(rooms) if isinstance(rooms, list) else 0,
            "room_event_count": sum(len(events) for events in room_events.values() if isinstance(events, list)) if isinstance(room_events, dict) else 0,
            "special_event_count": len(special_event_summaries),
        },
        "blind_player_text_context": blind_player_text_context(),
        "room_story_inventory": room_story_inventory,
        "recurring_character_inventory": sorted(recurring_characters.values(), key=lambda item: item["id"]),
        "storyline_counts": dict(sorted(storyline_ids.items())),
        "faction_counts": dict(sorted(faction_ids.items())),
        "story_followup_refs": followup_refs,
        "special_event_summaries": special_event_summaries,
        "recent_guidance": load_recent_memory(limit=4, include_core_guides=True),
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
        "blind_player_text_context": blind_player_text_context(),
        "deck_config": load_json(DECKS_PATH),
        "event_type_counts": event_type_counts(),
        "room_event_counts": room_event_counts(),
        "events": room_events,
        "special_events": special_events,
        "actions": sorted(existing_actions()),
        "single_choice_room_gaps": room_tradeoff_findings(),
        "room_depth_findings": room_depth_findings(),
        "room_story_findings": room_story_findings(),
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
        "setting_backbone": load_setting_backbone(),
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
        "setting_backbone": load_setting_backbone(),
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
            "story_motion": "How the idea can change across rooms or across runs without Hymn knowing the clone premise.",
            "related_systems": ["danger", "corruption", "merchant", "deck", "enemy", "symbiote", "mutation", "ending", "lore_fragment", "faction", "animal_infrastructure", "environment_memory"],
        },
        "strict_action_notes": events_file_errors(strict_actions=True),
    }


def accessibility_context() -> dict[str, Any]:
    events_payload = load_json(EVENTS_PATH)
    event_samples: list[dict[str, Any]] = []
    for room_id, events in events_payload.get("room_events", {}).items():
        if isinstance(events, list):
            for event in events:
                if isinstance(event, dict):
                    event_samples.append(compact_event(str(room_id), event))
    for event_id, event in events_payload.get("special_events", {}).items():
        if isinstance(event, dict):
            sample = compact_event("special_events", event)
            sample["special_event_id"] = str(event_id)
            event_samples.append(sample)
    return {
        "accessibility_guide": load_accessibility_guide(),
        "vibe_guide": load_vibe_guide(),
        "lore_guide": load_lore_guide(),
        "event_type_counts": event_type_counts(),
        "room_event_counts": room_event_counts(),
        "event_samples": event_samples,
        "actions": sorted(existing_actions()),
        "symbiotes": load_json(SYMBIOTES_PATH).get("symbiotes", []),
        "local_accessibility_findings": event_accessibility_findings(),
        "global_commands": [
            "one",
            "two",
            "three",
            "repeat",
            "repeat choices",
            "status",
            "inventory",
            "help",
            "confirm",
            "cancel",
            "pause",
            "continue",
            "slower",
            "faster",
        ],
        "strict_action_notes": events_file_errors(strict_actions=True),
    }


def compact_event(room_id: str, event: dict[str, Any]) -> dict[str, Any]:
    buttons = event.get("buttons", [])
    actions = []
    if isinstance(buttons, list):
        actions = [button.get("action") for button in buttons if isinstance(button, dict) and button.get("action")]
    compact_buttons = []
    if isinstance(buttons, list):
        for button in buttons:
            if isinstance(button, dict):
                compact_buttons.append({
                    "label": button.get("label"),
                    "action": button.get("action"),
                    "voice_aliases": button.get("voice_aliases", []),
                })
    compact: dict[str, Any] = {
        "room_id": room_id,
        "id": event.get("id"),
        "type": event.get("type"),
        "line_1": event.get("line_1"),
        "line_2": event.get("line_2"),
        "actions": actions,
        "buttons": compact_buttons,
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
            "room_updates": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "room_id": {"type": "string"},
                        "update": {"type": "object"},
                    },
                    "required": ["room_id", "update"],
                    "additionalProperties": False,
                },
            },
            "special_events": {"type": "array", "items": {"type": "object"}},
            "mutations": {"type": "array", "items": {"type": "object"}},
            "symbiotes": {"type": "array", "items": {"type": "object"}},
            "enemies": {"type": "array", "items": {"type": "object"}},
            "scenario_design_notes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "room_id": {"type": "string"},
                        "event_id": {"type": "string"},
                        "scenario_role": {"type": "string"},
                        "primary_pressure": {"type": "string"},
                        "body_path_pressure": {"type": "string"},
                        "avoidance_route": {"type": "string"},
                        "recognition_effect": {"type": "string"},
                        "character_change": {"type": "string"},
                        "possibility_tree": {"type": "array", "items": {"type": "string"}},
                        "progression_vector": {"type": "string"},
                        "corpus_anchors": {"type": "array", "items": {"type": "object"}},
                        "research_influences": {"type": "array", "items": {"type": "object"}},
                    },
                    "required": [
                        "room_id",
                        "event_id",
                        "scenario_role",
                        "primary_pressure",
                        "body_path_pressure",
                        "avoidance_route",
                        "recognition_effect",
                        "character_change",
                        "possibility_tree",
                        "progression_vector",
                        "corpus_anchors",
                        "research_influences",
                    ],
                    "additionalProperties": False,
                },
            },
            "required_engine_changes": {"type": "array", "items": {"type": "string"}},
            "inspiration_notes": {"type": "array", "items": {"type": "string"}},
            "self_critique": {"type": "array", "items": {"type": "string"}},
        },
        "required": [
            "title",
            "design_goal",
            "events",
            "room_updates",
            "special_events",
            "mutations",
            "symbiotes",
            "enemies",
            "scenario_design_notes",
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
            "blind_read_summary": {"type": "string"},
            "fun_score": {"type": "integer", "minimum": 0, "maximum": 10},
            "first_time_player_score": {"type": "integer", "minimum": 0, "maximum": 10},
            "build_score": {"type": "integer", "minimum": 0, "maximum": 10},
            "sequence_cohesion_score": {"type": "integer", "minimum": 0, "maximum": 10},
            "organism_pressure_score": {"type": "integer", "minimum": 0, "maximum": 10},
            "core_loop_diagnosis": {"type": "string"},
            "blind_text_findings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "severity": {"type": "string"},
                        "target": {"type": "string"},
                        "player_facing_evidence": {"type": "string"},
                        "why_it_feels_disconnected": {"type": "string"},
                        "recommendation": {"type": "string"},
                    },
                    "required": [
                        "severity",
                        "target",
                        "player_facing_evidence",
                        "why_it_feels_disconnected",
                        "recommendation",
                    ],
                    "additionalProperties": False,
                },
            },
            "choice_progression_findings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "target": {"type": "string"},
                        "current_choice_read": {"type": "string"},
                        "missing_progression": {"type": "string"},
                        "recommendation": {"type": "string"},
                    },
                    "required": ["target", "current_choice_read", "missing_progression", "recommendation"],
                    "additionalProperties": False,
                },
            },
            "payoff_gaps": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "setup": {"type": "string"},
                        "current_payoff_gap": {"type": "string"},
                        "recommended_payoff": {"type": "string"},
                    },
                    "required": ["setup", "current_payoff_gap", "recommended_payoff"],
                    "additionalProperties": False,
                },
            },
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
            "minimum_game_shape": {"type": "array", "items": {"type": "string"}},
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
            "blind_read_summary",
            "fun_score",
            "first_time_player_score",
            "build_score",
            "sequence_cohesion_score",
            "organism_pressure_score",
            "core_loop_diagnosis",
            "blind_text_findings",
            "choice_progression_findings",
            "payoff_gaps",
            "not_fun_findings",
            "organism_director_findings",
            "decision_loop_rewrites",
            "ending_pressure_plan",
            "content_priorities",
            "system_priorities",
            "minimum_game_shape",
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


def accessibility_critique_schema() -> dict[str, Any]:
    finding_item = {
        "type": "object",
        "properties": {
            "severity": {"type": "string"},
            "target": {"type": "string"},
            "issue": {"type": "string"},
            "recommendation": {"type": "string"},
        },
        "required": ["severity", "target", "issue", "recommendation"],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "eyes_free_score": {"type": "integer", "minimum": 0, "maximum": 10},
            "commandability_score": {"type": "integer", "minimum": 0, "maximum": 10},
            "tts_score": {"type": "integer", "minimum": 0, "maximum": 10},
            "critical_findings": {"type": "array", "items": finding_item},
            "command_parser_findings": {"type": "array", "items": finding_item},
            "tts_findings": {"type": "array", "items": finding_item},
            "schema_recommendations": {"type": "array", "items": {"type": "string"}},
            "command_alias_plan": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string"},
                        "recommended_aliases": {"type": "array", "items": {"type": "string"}},
                        "notes": {"type": "string"},
                    },
                    "required": ["action", "recommended_aliases", "notes"],
                    "additionalProperties": False,
                },
            },
            "state_readout_plan": {"type": "array", "items": {"type": "string"}},
            "testing_plan": {"type": "array", "items": {"type": "string"}},
            "guide_updates": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "section": {"type": "string"},
                        "suggested_text": {"type": "string"},
                    },
                    "required": ["section", "suggested_text"],
                    "additionalProperties": False,
                },
            },
            "next_accessibility_prompt": {"type": "string"},
        },
        "required": [
            "summary",
            "eyes_free_score",
            "commandability_score",
            "tts_score",
            "critical_findings",
            "command_parser_findings",
            "tts_findings",
            "schema_recommendations",
            "command_alias_plan",
            "state_readout_plan",
            "testing_plan",
            "guide_updates",
            "next_accessibility_prompt",
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


def story_architect_schema() -> dict[str, Any]:
    arc_beat_item = {
        "type": "object",
        "properties": {
            "beat_id": {"type": "string"},
            "role": {"type": "string"},
            "trigger": {"type": "string"},
            "encounter_function": {"type": "string"},
            "player_choice": {"type": "string"},
            "visible_change": {"type": "string"},
            "mechanical_consequence": {"type": "string"},
            "implementation_notes": {"type": "array", "items": {"type": "string"}},
        },
        "required": [
            "beat_id",
            "role",
            "trigger",
            "encounter_function",
            "player_choice",
            "visible_change",
            "mechanical_consequence",
            "implementation_notes",
        ],
        "additionalProperties": False,
    }
    character_arc_item = {
        "type": "object",
        "properties": {
            "character_id": {"type": "string"},
            "player_facing_name": {"type": "string"},
            "current_status": {"type": "string"},
            "desire": {"type": "string"},
            "pressure_method": {"type": "string"},
            "relationship_to_hymn": {"type": "string"},
            "first_appearance": {"type": "string"},
            "arc_beats": {"type": "array", "items": arc_beat_item},
            "why_this_is_a_character": {"type": "string"},
            "failure_mode_if_absent": {"type": "string"},
        },
        "required": [
            "character_id",
            "player_facing_name",
            "current_status",
            "desire",
            "pressure_method",
            "relationship_to_hymn",
            "first_appearance",
            "arc_beats",
            "why_this_is_a_character",
            "failure_mode_if_absent",
        ],
        "additionalProperties": False,
    }
    first_spine_item = {
        "type": "object",
        "properties": {
            "sequence_index": {"type": "integer"},
            "target_room_or_event": {"type": "string"},
            "story_function": {"type": "string"},
            "player_question": {"type": "string"},
            "choice_pressure": {"type": "string"},
            "followup_payoff": {"type": "string"},
            "required_data_changes": {"type": "array", "items": {"type": "string"}},
        },
        "required": [
            "sequence_index",
            "target_room_or_event",
            "story_function",
            "player_question",
            "choice_pressure",
            "followup_payoff",
            "required_data_changes",
        ],
        "additionalProperties": False,
    }
    followup_item = {
        "type": "object",
        "properties": {
            "source_event": {"type": "string"},
            "followup_event_id": {"type": "string"},
            "character_id": {"type": "string"},
            "trigger": {"type": "string"},
            "timing": {"type": "string"},
            "scene_function": {"type": "string"},
            "choice_or_route_change": {"type": "string"},
            "mechanical_hook": {"type": "string"},
            "authoring_prompt": {"type": "string"},
        },
        "required": [
            "source_event",
            "followup_event_id",
            "character_id",
            "trigger",
            "timing",
            "scene_function",
            "choice_or_route_change",
            "mechanical_hook",
            "authoring_prompt",
        ],
        "additionalProperties": False,
    }
    pilot_item = {
        "type": "object",
        "properties": {
            "arc_name": {"type": "string"},
            "why_this_first": {"type": "string"},
            "scope_events": {"type": "array", "items": {"type": "string"}},
            "required_system_hooks": {"type": "array", "items": {"type": "string"}},
            "acceptance_tests": {"type": "array", "items": {"type": "string"}},
            "generation_prompt": {"type": "string"},
        },
        "required": [
            "arc_name",
            "why_this_first",
            "scope_events",
            "required_system_hooks",
            "acceptance_tests",
            "generation_prompt",
        ],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "story_diagnosis": {"type": "string"},
            "missing_story_primitives": {"type": "array", "items": {"type": "string"}},
            "character_arcs": {"type": "array", "items": character_arc_item},
            "first_15_minute_spine": {"type": "array", "items": first_spine_item},
            "followup_encounter_plan": {"type": "array", "items": followup_item},
            "pilot_arc_recommendation": pilot_item,
            "story_rules": {"type": "array", "items": {"type": "string"}},
            "patch_strategy": {"type": "array", "items": {"type": "string"}},
            "next_story_prompt": {"type": "string"},
        },
        "required": [
            "summary",
            "story_diagnosis",
            "missing_story_primitives",
            "character_arcs",
            "first_15_minute_spine",
            "followup_encounter_plan",
            "pilot_arc_recommendation",
            "story_rules",
            "patch_strategy",
            "next_story_prompt",
        ],
        "additionalProperties": False,
    }


def story_pilot_schema() -> dict[str, Any]:
    room_event_item = {
        "type": "object",
        "properties": {
            "room_id": {"type": "string"},
            "event": {"type": "object"},
        },
        "required": ["room_id", "event"],
        "additionalProperties": False,
    }
    room_event_update_item = {
        "type": "object",
        "properties": {
            "room_id": {"type": "string"},
            "event_id": {"type": "string"},
            "merge": {"type": "object"},
        },
        "required": ["room_id", "event_id", "merge"],
        "additionalProperties": False,
    }
    deck_pool_update_item = {
        "type": "object",
        "properties": {
            "pool": {"type": "string"},
            "room_id": {"type": "string"},
        },
        "required": ["pool", "room_id"],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "design_goal": {"type": "string"},
            "room_records": {"type": "array", "items": {"type": "object"}},
            "room_events": {"type": "array", "items": room_event_item},
            "special_events": {"type": "array", "items": {"type": "object"}},
            "room_event_updates": {"type": "array", "items": room_event_update_item},
            "deck_pool_updates": {"type": "array", "items": deck_pool_update_item},
            "required_engine_changes": {"type": "array", "items": {"type": "string"}},
            "validation_notes": {"type": "array", "items": {"type": "string"}},
            "self_critique": {"type": "array", "items": {"type": "string"}},
        },
        "required": [
            "title",
            "design_goal",
            "room_records",
            "room_events",
            "special_events",
            "room_event_updates",
            "deck_pool_updates",
            "required_engine_changes",
            "validation_notes",
            "self_critique",
        ],
        "additionalProperties": False,
    }


def build_prompt(args: argparse.Namespace) -> list[dict[str, str]]:
    context = game_context()
    source_seeds = load_source_seed_context(args)
    room = args.room or "any existing room"
    category = args.category or "any defined category"
    category_rules = get_event_category(args.category) if args.category else {}
    system = """
You are a scenario designer for a Godot roguelike called Fleshpunk: Inner Heart.
Generate JSON patches only. Do not write prose outside the JSON object.

Your scenarios should fit the existing data-driven event system:
- Add events under events.json room_events[room_id].
- Add room foundation updates under room_updates when a scenario changes corpus anchors, room premise, progression state, environment echoes, or other room metadata.
- Each event should include id, type, speaker, line_1, line_2, and buttons.
- Event type must be one of the defined category ids.
- Buttons need label and action.
- voice_aliases are auto-enriched by tooling from label, action, and local narration, but you may include short spoken aliases when they are obvious.
- Every room event should offer at least two commandable buttons unless it is explicitly a transition event.
- Do not ship a room that only says Proceed unless the room is truly terminal or transitional.
- Do not ship one-off rooms whose choices resolve only as minor stat changes.
- Target Revelation-scale scenario size: compact, playable, story-rich, and larger than a one-line tradeoff but smaller than a chapter.
- Every scenario needs action/reaction, a memory hook or future pressure, and a character-change vector: enrich, destabilize, or both.
- This is martial progression fantasy. Scenarios should pressure Hymn's current body and record whether she is becoming a mutated weapon, symbiote host, scarred survivor, disciplined baseline fighter, hunted prey, recognized rival, or known route-breaker.
- Forward pressure axes are hunt_pressure, body_drift, baseline_discipline, wound_debt, recognition, and route_memory. Old runtime labels such as danger/corruption may remain for compatibility, but new design should think in these axes.
- Every forward scenario should declare primary_pressure, body_path_pressure, avoidance_route, and recognition_effect in event metadata and scenario_design_notes.
- Combat is foregrounded but often avoidable. Avoidance must be a tactical, social, route, or body-cost choice, not a skip.
- Do not create puzzle rooms. Noncombat rooms should be interpersonal pressure, hostile crossings, rest with teeth, feeding sites, molting thresholds, faction tolls, training echoes, body shrines, or social/ecological recognition beats.
- Every scenario should carry an implicit possibility tree. Keep branch pressure in metadata and result evidence; do not spell out risk labels, branch labels, or future consequences in player-facing text.
- Character/faction progression should use story_followups that enqueue one-shot special_events into the run stack or later environment echoes; do not rely on revisiting the originating room.
- Glue beats should be playable interventions where a prior choice returns with leverage: option mask, price shift, route favor, pattern warning, predator attention, body-path recognition, or ending pressure.
- Glue beats need a visible carrier such as a cord, receipt blister, low feeder, scar mite, lens film, route packet, blood trace, symbiote twitch, or repair animal. Avoid abstract echoes.
- Character events must not retrigger in the same run. Use trigger_key and reactivate_on_reshuffle: false on follow-up special events.
- Treat characters, beasts, animals, parasites, organs, markets, and tools as interactable infrastructure. Beasts should not exist only to attack.
- Every room instance should tell part of the setting story through faction pressure, recurring character traces, animal infrastructure, route memory, or later environment echoes.
- Every environment family should have at least one ending vector. Rooms should be able to pull toward, divert from, or clarify that ending.
- Every generated scenario must pass a cold-reader test. A new player with no lore notes should understand: what kind of place this is, what the place normally does, what visible actor or hazard is present now, why Hymn must decide now, where Hymn is positioned, and what each choice physically changes in the next few seconds.
- Each room event must carry that cold-reader context in its own line_1/line_2, even if the room introduction was skipped, interrupted by audio, or forgotten.
- Start with plain orientation before specialized nouns. Name the place's ordinary function first: repair room, route organ, feeding site, toll crossing, predator den, training floor, bargaining mouth, or recovery pool. Then add the weird biological implementation.
- Do not open a scene with only "something," "it," "the system," or an unexplained proper noun. Introduce the visible body, animal, person, organ, tool, or route feature before pronouns carry the scene.
- If a player-facing line uses a coined term such as operator cellar, survey field, leukocyte hound, marrow lice, route organ, or wall holes, the same line or the previous line must give one concrete job or behavior for it.
- Combat is optional, not forbidden. Use it when it enriches or destabilizes Hymn. Write visible posture, distance, contact, commitment, recovery, and consequence; avoid HEMA lecture jargon.
- If a scenario is requested as action combat, do not turn martial anatomy into a lock, sequence, ritual, diagnostic test, or apparatus puzzle. Start with an active threat in reach or closing range. Choices should be tactics under pressure; outcomes should show opponent reaction, contact, positional shift, recovery cost, injury, and progression consequence.
- Treat mutations as multi-use progression tools, not stat upgrades first. Each major mutation should have an in-encounter use, an out-of-encounter use, and at least one later surprising second use.
- Use the body option contract for pure-body, mutation, and symbiote branches. Rooms should target capability tags first, named options second.
- Baseline Hymn must always have a complete route through the scene. Pure-body discipline means breath, timing, leverage, restraint, pain tolerance, tactical reading, or narrower margins, not absence of content.
- Mutations are reliable always-on body identity. Symbiotes are stronger but less dependable living partners with needs, cooldowns, wounds, preferences, or refusal pressure.
- Keep body-option prose contained. Do not enumerate compatible upgrades in player-facing text; use physical actions in the scene and put tags/qualifying options in metadata.
- Use the setting backbone for factions and cross-run story motion. Corpus inspiration must become original Fleshpunk systems, not copied characters, source scenes, surface mood, or author costume.
- Every room/scenario instance must declare corpus_influences or research_influences that name the source layer/id, the specific pulp/martial/biological/progression move, and the scenario application. source_seed_ids alone are not enough.
- Every forward scenario must start from one to three tier-0 corpus_anchors. Each anchor must include tier 0, source id/title/author, source_file or source_locator, source_moment, story_element, and scenario_application. These anchors are the room foundation: if removing them does not change the premise, choices, pressure, combat/movement problem, and progression vector, the scenario fails.
- Use the Hymn corpus voice guide and research guides for prose. The forward source pressure is the newer pulp/research stack plus martial anatomy: physical immediacy, pursuit, reversal, hostile landscape, mythic compression, body consequence, and advancement pressure. The old Verne/Lovecraft seed set is optional legacy material, not required and not preferred unless explicitly requested or uniquely apt.
- Maintain one house voice across the whole deck. Corpus influence changes what Hymn notices and what a scenario does, not her diction. Do not write one event in Howard mode, one in Sabatini mode, and another in Blackwood mode.
- Do not use author-costume diction in player-facing prose: no eldritch/cyclopean/aeon/nameless/unspeakable/cosmic dread, no expedition lecture voice, no antique asides, no source-name homages, no visible author/source names.
- Use the story scenario contract as an acceptance bar. Valid buttons are necessary but not enough; scenarios need a specific current situation, implicit branch pressure, character change, tier-0 corpus anchors, and action-specific consequence.
- Keep consequences concrete in data and result structure, but keep Hymn's narration bounded by evidence. She can report the cord still pulsing or the record blister sealing; she should not announce the exact future payoff.
- Do not write flat scaffold prose. Each line should carry concrete pressure, place history, bodily stakes, or story motion derived structurally from the corpus.
- Do not write abstract-cool prose. Replace "the room recognizes me" with the visible mechanism: "the floor cut matches my stride," "the mouth lowers to wrist height," or "the hound steps where my boot would land."
- Prefer existing actions unless the user explicitly asks for new mechanics.
- If you invent an action, include it in required_engine_changes and explain what run_manager.gd must do.
- Keep UI text short and playable.
- Follow the vibe guide: first-person internal field report, short clipped phrasing, purpose-built biology, reactive systems, transactional choices.
- Keep Hymn's narration clean and empirical. Report visible structure, motion, markings, pressure, residue, sound, heat, count, timing, and immediate operational choices. Avoid scripture cadence, mystical claims, and unsupported inference about what the organism wants or understands.
- Do not write visible speaker labels such as Her:. Use first-person narration only; if speaker metadata is required, use Hymn.
- Use inspiration structurally, never as copied text.
""".strip()
    if not args.allow_new_actions:
        system += "\n- Do not invent new actions. Use existing actions only."
    if source_seeds:
        system += "\n- If source_seed_context is present, transform those seeds into original Fleshpunk events. Do not copy source names, characters, scenes, or prose."

    user = {
        "request": args.prompt,
        "target_room": room,
        "target_category": category,
        "target_category_rules": category_rules,
        "count": args.count,
        "allow_new_actions": bool(args.allow_new_actions),
        "game_context": context,
        "source_seed_context": source_seeds,
        "memory": load_generation_memory_for_model(args.model),
        "output_contract": {
            "format": "scenario_patch",
            "schema_notes": [
                "events is a list of {room_id, event}",
                "room_updates is a list of {room_id, update}; use it for tier-0 corpus_anchors, corpus_influences, premise, progression_state, environment_echoes, ending_vectors, and mutation_hooks.",
                "mutation_hooks may also carry baseline_route, capability_tags, mutation_branch, and symbiote_branch from the body option contract.",
                "event may include existing keys such as mutation_id, symbiote_id, enemy_id, damage, heal, shield, biomass",
                "voice_aliases may be auto-generated by tooling from label, action, and narration context; keep them short and unique when you do include them.",
                "Every room event should have at least 2 commandable buttons unless the event type is transition.",
                "Every room should include delayed consequence or reaction metadata/prose: future room text, deck pressure, route state, actor state, debt, claim, scent, or pursuit.",
                "Post-update rooms should include action_results or per-button result lines/state changes so shared legacy action handlers do not carry the whole outcome.",
                "Post-update rooms should include environment memory/state keys and later-instance echo text keyed by player behavior.",
                "Rooms/scenarios should include corpus_influences or research_influences: source_id or source_layer, source_title where applicable, source_moment/structural_idea, writing_influence, and scenario_application.",
                "Each event should include character_change: enrich, destabilize, or both.",
                "Each event should include possibility_tree or branch_pressures as designer metadata with at least two future pressures; keep those branches implicit in player-facing text.",
                "Mutation proposals should include in_encounter_use, out_of_encounter_use, and surprising_second_use.",
                "Story progression should use story_followups on room events, referencing one-shot special_events with trigger_key and reactivate_on_reshuffle false.",
                "Events should identify the actor/system being interacted with, not just a cryptic object.",
                "Events should include enough first-read context for a normal player: place function, current actor/hazard, Hymn position, immediate time pressure, and visible action/reaction.",
                "Player-facing prose should define specialized Fleshpunk nouns by behavior before leaning on them as lore terms.",
                "scenario_design_notes should summarize scenario_role, primary_pressure, body_path_pressure, avoidance_route, recognition_effect, character_change, possibility_tree, progression_vector, corpus_anchors, and research_influences for every generated event.",
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
- Does every room event offer at least two commandable buttons unless it is a transition?
- Is the room more than a one-off stat exchange?
- Does it create action/reaction and delayed consequence?
- Is there an interactable character, beast, animal, parasite, organ, market, tool, or infrastructure actor?
- If beasts appear, are they functional infrastructure rather than just attacks?
- Does the room instance tell part of the story of this place through faction behavior, animal infrastructure, recurring character traces, or later environment echoes?
- Does the story continue through one-shot story_followups inserted into the run stack, then across rooms or runs as delayed pressure, altered prices, route memory, animal trust/hostility, Chorus pressure, or ending gravity?
- Do character/faction follow-up special events avoid same-run retriggering?
- Does corpus inspiration become original setting machinery instead of surface mood?
- Is the prose textured enough, or does it read like flat placeholder copy explaining buttons?
- Are buttons instructions to the character rather than spoken dialogue?
- Are proposed additions implementable with current actions, or clearly marked as engine work?
- Suggest new event categories, encounter patterns, mechanics, and vibe-guide updates only when they clarify future generation.
""".strip()

    user = {
        "focus": args.focus,
        "vibe_guide": load_vibe_guide(),
        "setting_backbone": load_setting_backbone(),
        "game_context": game_context(),
        "strict_action_notes": events_file_errors(strict_actions=True),
        "room_depth_findings": room_depth_findings(),
        "room_story_findings": room_story_findings(),
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
- Do room events avoid one-button dead ends unless they are transitions?
- Are rooms avoiding one-off stat exchanges?
- Do choices create delayed pressure, route state, actor state, claim, debt, scent, pursuit, or future text changes?
- Are character/beast/infrastructure interactions creating different future consequences instead of only different immediate numbers?
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
- Start with a blind player read. Pretend you have no lore primer, no vibe guide, no design intent, and no hidden implementation context. Judge only the visible room descriptions, event text, result text, queued follow-up text, and choice labels in blind_player_text_context.
- Do not reward implied plans that are not visible to the player. If a room, choice, pressure, faction, or character only makes sense because of hidden metadata, call that a disconnect.
- The central question is whether the first-time player feels scenes are building into a game: recurring situations, escalating pressures, recognizable actors, changed future choices, and payoff.
- Flag when events feel like isolated vignettes, when choices are just differently flavored interaction verbs, and when consequences do not accumulate into a direction.
- Judge whether the old writing inspiration creates playable specificity or only atmospheric density. Preserve texture, but recommend sharper setups, state changes, and payoffs where clarity is missing.
- The living organism is the director of the run.
- Its job is to notice player patterns, unbalance the player, and push the clone toward an outcome.
- Every repeated decision should create a gravitational pull: corruption, danger/hunter, starvation, injury, debt, or a narrowed route.
- Every room should offer at least one meaningful tradeoff, not just a single Proceed choice.
- Every room needs action/reaction and delayed consequence; immediate stat changes are only the surface.
- Characters, beasts, animals, parasites, organs, markets, and tools should behave as interactable infrastructure.
- Beasts should almost never be "just a fight"; they should carry information, pressure, routes, tolls, immune response, or delayed threat.
- Taking too many mutations raises corruption and pushes the corruption ending.
- Fleeing or dodging too much combat raises danger until the hunter comes.
- Greedy extraction, repeated healing, repeated refusal, repeated bonding, and repeated safety should each have a pressure track or explicit cost.
- The best ending should require balance and neutrality, not maximal power or maximal avoidance.
- Critique whether the game has a repeatable loop of temptation, pressure, feedback, adaptation, and payoff.
- Prefer concrete loop/system/content fixes over broad mood advice.
""".strip()

    user = {
        "focus": args.focus,
        "fun_context": fun_context(),
        "secondary_design_context": {
            "vibe_guide": load_vibe_guide(),
            "memory": load_recent_memory(),
            "use_after_blind_read_only": "Use this only after judging the user-facing text. It can explain intended direction, but it must not excuse player-facing disconnects.",
        },
        "output_contract": {
            "summary": "Blunt judgement of current fun factor.",
            "blind_read_summary": "Blunt first-time player read based only on visible text and choices.",
            "fun_score": "0-10 score for whether the current game loop creates desire to keep playing.",
            "first_time_player_score": "0-10 score for whether an unbiased first-time player understands and wants to continue.",
            "build_score": "0-10 score for whether events build on each other instead of feeling isolated.",
            "sequence_cohesion_score": "0-10 score for whether the first 10-15 minutes feel like one developing run.",
            "organism_pressure_score": "0-10 score for whether the organism behaves like a director that pushes outcomes.",
            "core_loop_diagnosis": "One paragraph naming the current loop and why it fails or works.",
            "blind_text_findings": "Concrete visible-text reasons the game feels clear, compelling, disconnected, or insufficient.",
            "choice_progression_findings": "Where choice labels/results do not escalate, differentiate, or imply future direction.",
            "payoff_gaps": "Setups that are visible but not yet paid off strongly enough for an ordinary player.",
            "not_fun_findings": "Concrete reasons the current game feels like stats instead of a living organism.",
            "organism_director_findings": "How each pressure axis should notice and push repeated decisions.",
            "decision_loop_rewrites": "Specific loops to rewrite, such as mutation shopping, combat avoidance, extraction, healing, symbiote dependence.",
            "ending_pressure_plan": "How player patterns warn, then lock, into endings.",
            "content_priorities": "Content to add first for fun, not just lore.",
            "system_priorities": "Engine/data hooks that create the fun loop.",
            "minimum_game_shape": "Smallest set of additions needed for this to feel like a game with build, payoff, and replay desire.",
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
- The setting must tell ongoing stories through room instances: factions, recurring characters, animal infrastructure, route memory, later environment echoes, and pressure changes.
- Characters can appear through traces, procedures, animals, prices, signals, records, and changed room behavior; they do not need conventional dialogue scenes.
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


def build_accessibility_critique_prompt(args: argparse.Namespace) -> list[dict[str, str]]:
    system = """
You are the accessibility and audio-UX critic for Fleshpunk: Inner Heart.
Your job is to make the game fully playable eyes-free through TTS plus typed or spoken commands.
Return JSON only.

Accessibility doctrine:
- Audio is primary. Visuals are optional support and must never carry required information alone.
- Every encounter must be commandable by number and by short aliases.
- The speech parser must only map to current legal actions, global commands, or legal symbiote activations.
- Each button needs short, distinct voice aliases.
- TTS lines should be short phrase chunks.
- Result text should state mechanical changes clearly.
- Ambiguous commands need confirmation, not guesses.
- Unknown commands should recover with repeat choices, status, or choice number prompts.
- Endings must explain the pressure path that caused them without leaking clone truth.
""".strip()

    user = {
        "focus": args.focus,
        "accessibility_context": accessibility_context(),
        "memory": load_recent_memory(),
        "output_contract": {
            "summary": "Short judgement of eyes-free playability.",
            "eyes_free_score": "0-10 score for full playability without looking.",
            "commandability_score": "0-10 score for command parser readiness.",
            "tts_score": "0-10 score for concise, comprehensible TTS flow.",
            "critical_findings": "Blockers for legally blind / low-vision play.",
            "command_parser_findings": "Problems with aliases, ambiguity, parser schema, and recovery.",
            "tts_findings": "Problems with line length, pacing, state readout, and audio-only clarity.",
            "schema_recommendations": "Data fields or contracts to add before STT.",
            "command_alias_plan": "Recommended aliases for important actions.",
            "state_readout_plan": "What status/repeat/help should speak.",
            "testing_plan": "Concrete eyes-free tests to run.",
            "guide_updates": "Accessibility guide additions.",
            "next_accessibility_prompt": "Compact prompt for the next accessibility pass.",
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
- Each major story idea should have early, mid, and late progression across rooms or runs.
- Create faction conflicts and recurring character story lines that can alter room text, deck pressure, route state, prices, animal behavior, or ending eligibility.
- Animals are insectile, larval, crusted, or oversized-cell infrastructure with jobs; they should rarely be only enemies.
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


def build_story_architect_prompt(args: argparse.Namespace) -> list[dict[str, str]]:
    system = """
You are the story architect for Fleshpunk: Inner Heart.
Your job is to turn the current room/event stack into real playable story architecture.
Return JSON only.

Story doctrine:
- Do not polish prose. Diagnose and plan story structure: characters, desires, relationships, follow-up encounters, escalation, and payoff.
- A character is not a name or a faction tag. A character must recur, want something, pressure Hymn, remember choices, change future options, and create a payoff or rupture.
- The game currently has strong vibe, intricate room apparatuses, and a bestiary/infrastructure layer. Your task is to identify what story spine is missing.
- Follow-up encounters should be scenes, not only atmospheric echoes. Each should change a route, price, option set, pressure, relationship, or ending eligibility.
- The first 10-15 minutes need a visible arc: setup, first character pressure, player response, consequence, changed later encounter, and payoff.
- Use the existing data and active story hints. Prefer a small pilot arc over a massive rewrite.
- Preserve mystery and Hymn's limited knowledge. Do not reveal clone truth or hidden cosmology directly.
- Treat Chorus, the Merchant/Quartermaster, the Soft Captain, the Hunter, and Commandant Signal as candidates only if they can become real recurring agents in play.
- Recommendations must be implementable through room events, story_followups, special_events, environment_state, pressure counters, and small run_manager hooks.
""".strip()

    user = {
        "focus": args.focus,
        "story_architect_context": story_architect_context(),
        "output_contract": {
            "summary": "Short judgement of the current story shape.",
            "story_diagnosis": "Blunt explanation of why the current stack does or does not tell a story.",
            "missing_story_primitives": "The missing primitives: character desire, recurrence, memory, conflict, escalation, payoff, etc.",
            "character_arcs": "Real playable character arcs grounded in current data.",
            "first_15_minute_spine": "A concrete early-run sequence that makes the player feel a story is underway.",
            "followup_encounter_plan": "Follow-up encounter scenes to author next, with triggers and mechanical effect.",
            "pilot_arc_recommendation": "The one arc to build first, with scope, hooks, acceptance tests, and a generation prompt.",
            "story_rules": "Rules future generation must obey so it produces story, not only vibe.",
            "patch_strategy": "Implementation order for Codex/tooling plus OpenAI-authored content.",
            "next_story_prompt": "Compact prompt for the next story-arc generation pass.",
        },
    }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(user, indent=2, ensure_ascii=False)},
    ]


def build_story_pilot_prompt(args: argparse.Namespace) -> list[dict[str, str]]:
    system = """
You are the scenario/writing agent for Fleshpunk: Inner Heart.
Generate JSON only. You are writing the pilot story patch requested by the story architect.

Pilot doctrine:
- Write player-facing prose through Hymn's first-person field-report voice: clipped, concrete, sensory, operational.
- Do not write exposition, lore lectures, visible speaker labels, clone truth, or cosmic explanation.
- This patch must turn echoes into scenes: a recurring agent has leverage, remembers a specific prior choice, and changes the next room's options, price, route, or trap state.
- Use existing actions only unless required_engine_changes names a hook. Available small hooks: action_results.environment_state_changes and room event state_overrides.
- state_overrides format: each room event may include state_overrides: [{state_key, consume_state, consume_state_keys, event:{line_1,line_2,buttons,action_results,story_followups,...}}]. When the state is present, the event override replaces visible text/buttons/results once if consume_state is true.
- Prefer replacing/expanding existing special events that are already queued by current story_followups.
- Return complete special_events. Return room_event_updates as merge patches for existing room events.
- Every special event needs id, type, speaker, line_1, line_2, reactivate_on_reshuffle:false, buttons, and action_results for each meaningful button.
- Every button needs label, action, and voice_aliases.
- Keep required_engine_changes empty if the state_overrides hook is sufficient.
""".strip()

    cold_read_context = bool(getattr(args, "cold_read_context", False))
    minimal_context = bool(getattr(args, "minimal_context", False)) or cold_read_context
    architecture_path = GENERATED_DIR / "story_architect.json"
    architecture = {} if minimal_context else (load_json(architecture_path) if architecture_path.exists() else {})
    previous_pilot_path = GENERATED_DIR / "story_pilot_patch.json"
    previous_pilot = {} if minimal_context else (load_json(previous_pilot_path) if previous_pilot_path.exists() else {})
    user = {
        "focus": args.focus,
        "story_architecture": architecture,
        "previous_story_pilot_patch": previous_pilot,
        "story_architect_context": cold_read_text_context() if cold_read_context else (playtest_slice_text_context() if minimal_context else story_architect_context()),
        "context_mode": "cold_read" if cold_read_context else ("minimal_playtest_slice" if minimal_context else "full_story_architecture"),
        "output_contract": {
            "title": "Patch title.",
            "design_goal": "What story problem this pilot solves.",
            "special_events": "Complete special event objects keyed by their id when applied.",
            "room_records": "Optional complete room records to add or merge into rooms_post_update.json.",
            "room_events": "Optional new room events as {room_id,event} records.",
            "room_event_updates": "Merge patches to existing room events; use state_overrides to make prior choices change later visible encounters.",
            "deck_pool_updates": "Optional {pool, room_id} records to add the room to active deck pools.",
            "required_engine_changes": "Must be empty unless this patch needs hooks beyond action_results.environment_state_changes and state_overrides.",
            "validation_notes": "How to verify the pilot reads as story.",
            "self_critique": "Risks or compromises in the patch.",
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


def extract_json_text(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        return stripped
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start != -1 and end != -1 and end > start:
        return stripped[start:end + 1]
    return stripped


def call_anthropic(
    messages: list[dict[str, str]],
    model: str,
    output_schema: dict[str, Any],
    schema_name: str,
) -> dict[str, Any]:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise SystemExit("ANTHROPIC_API_KEY is not set. Export it or use --mock.")

    system_parts = [message["content"] for message in messages if message.get("role") == "system"]
    user_parts = [message["content"] for message in messages if message.get("role") != "system"]
    max_tokens = int(os.environ.get("SCENARIO_AGENT_MAX_OUTPUT_TOKENS", "12000"))
    request_payload = {
        "model": model,
        "max_tokens": max_tokens,
        "system": "\n\n".join(system_parts),
        "messages": [
            {
                "role": "user",
                "content": "\n\n".join(user_parts),
            }
        ],
        "tools": [
            {
                "name": schema_name,
                "description": f"Return the complete {schema_name} JSON object.",
                "input_schema": output_schema,
            }
        ],
        "tool_choice": {"type": "tool", "name": schema_name},
    }
    data = json.dumps(request_payload).encode("utf-8")
    raw = ""
    errors: list[str] = []
    attempts = int(os.environ.get("SCENARIO_AGENT_API_ATTEMPTS", "3"))
    timeout = int(os.environ.get("SCENARIO_AGENT_API_TIMEOUT", "240"))
    for attempt in range(1, attempts + 1):
        request = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=data,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
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
            raise SystemExit(f"Anthropic API error {exc.code}: {body}") from exc
        except urllib.error.URLError as exc:
            errors.append(f"attempt {attempt}: request failed: {exc}")
        except (http.client.HTTPException, TimeoutError) as exc:
            errors.append(f"attempt {attempt}: connection failed: {exc}")
        if attempt < attempts:
            time.sleep(min(2 ** attempt, 8))
    if not raw:
        detail = "\n".join(errors) if errors else "no response body"
        raise SystemExit(
            "Anthropic API connection failed after "
            f"{attempts} attempts. model={model} schema={schema_name} "
            f"payload_bytes={len(data)} max_output_tokens={max_tokens}\n{detail}"
        )

    try:
        response_payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Anthropic response was not JSON:\n{raw[:2000]}") from exc
    chunks: list[str] = []
    for item in response_payload.get("content", []):
        if isinstance(item, dict) and item.get("type") == "tool_use" and isinstance(item.get("input"), dict):
            return item["input"]
        if isinstance(item, dict) and item.get("type") == "text" and isinstance(item.get("text"), str):
            chunks.append(item["text"])
    text = "\n".join(chunks).strip()
    if not text:
        raise SystemExit(f"Anthropic response did not contain text:\n{raw[:2000]}")
    try:
        return json.loads(extract_json_text(text))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Claude returned non-JSON output:\n{text}") from exc


def call_openai(
    messages: list[dict[str, str]],
    model: str,
    output_schema: dict[str, Any],
    schema_name: str,
) -> dict[str, Any]:
    if model.startswith("claude-"):
        return call_anthropic(messages, model, output_schema, schema_name)

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


def _label_for_action(action: str) -> str:
    labels = {
        "break_amber_cache": "Break the hard mass",
        "break_spike_lane": "Break the pressure line",
        "browse_wares": "Approach the exchange",
        "combat": "Fight through",
        "drink_pool": "Drink the fluid",
        "follow_marked_plates": "Follow the markings",
        "harvest_eggs": "Harvest the sacs",
        "leave_mutation": "Leave the growth",
        "listen_at_green_split": "Listen at the split",
        "listen_red_wall": "Listen to the wall",
        "mark_red_branch": "Mark the safer branch",
        "observe_organ_chamber": "Observe the chamber",
        "pay_resin_toll": "Pay the toll",
        "probe_amber_cache": "Probe the cache",
        "probe_bones": "Probe the bones",
        "proceed": "Move through",
        "retreat": "Back away",
        "rush_red_split": "Rush the split",
        "scavenge_bones": "Scavenge the bones",
        "skip_resin_toll": "Skip the toll",
        "study_pool": "Study the fluid",
        "take_mutation": "Take the change",
        "take_symbiote": "Bond with it",
        "vent_red_split": "Vent the pressure",
    }
    return labels.get(action, action.replace("_", " ").capitalize())


def _mock_patch_from_seed(room: str, category: str, source_seed: dict[str, Any]) -> dict[str, Any]:
    seed_id = str(source_seed.get("id", "corpus_seed"))
    motif_id = str(source_seed.get("motif_id", "source_motif"))
    actions = [
        str(action)
        for action in source_seed.get("suggested_existing_actions", [])
        if str(action).split(":", 1)[0] in existing_actions()
    ]
    if len(actions) < 2:
        actions = ["study_pool", "retreat", "proceed"]

    event_id = "%s_%s" % (room, slugify_id(motif_id))
    buttons = [{"label": _label_for_action(action), "action": action} for action in actions[:3]]
    return {
        "title": "Corpus Seed: %s" % motif_id.replace("_", " ").title(),
        "design_goal": "Transform a public-domain source motif into one playable Fleshpunk room event using existing actions.",
        "events": [
            {
                "room_id": room,
                "event": {
                    "id": event_id,
                    "type": category,
                    "speaker": "Hymn",
                    "primary_pressure": "route_memory",
                    "body_path_pressure": "Hymn can answer with baseline caution or become more legible to living infrastructure.",
                    "avoidance_route": "She can withdraw or choose a low-contact read instead of forcing the room.",
                    "recognition_effect": "The local system records whether Hymn reads, forces, pays, or refuses pressure.",
                    "line_1": "Chorus, contact. The room is running an old procedure through fresh tissue.",
                    "line_2": "It offers a clean path, but the cost is already looking for a place to attach.",
                    "buttons": buttons,
                    "character_change": "both",
                    "possibility_tree": [
                        "Hymn studies the pressure and gains route knowledge while letting the room mark her caution.",
                        "Hymn forces or pays through and becomes more legible to the local system.",
                    ],
                    "progression_vector": "The choice should make a future route or body reading more specific.",
                    "corpus_influences": [
                        {
                            "source_id": seed_id,
                            "structural_idea": motif_id,
                            "scenario_application": "Transform the source seed into original body pressure and future possibility.",
                        }
                    ],
                },
            }
        ],
        "room_updates": [],
        "mutations": [],
        "symbiotes": [],
        "enemies": [],
        "scenario_design_notes": [
            {
                "room_id": room,
                "event_id": event_id,
                "scenario_role": "pulp-sourced pressure choice",
                "primary_pressure": "route_memory",
                "body_path_pressure": "Hymn can answer with baseline caution or become more legible to living infrastructure.",
                "avoidance_route": "She can withdraw or choose a low-contact read instead of forcing the room.",
                "recognition_effect": "The local system records whether Hymn reads, forces, pays, or refuses pressure.",
                "character_change": "both",
                "possibility_tree": [
                    "Hymn studies the pressure and gains route knowledge while letting the room mark her caution.",
                    "Hymn forces or pays through and becomes more legible to the local system.",
                ],
                "progression_vector": "The choice should make a future route or body reading more specific.",
                "corpus_anchors": [
                    {
                        "tier": 0,
                        "source_id": seed_id,
                        "source_title": source_seed.get("source_title", ""),
                        "source_author": source_seed.get("source_author", ""),
                        "source_moment": motif_id,
                        "story_element": "Source motif becomes room pressure.",
                        "scenario_application": "Transform the source seed into original body pressure and future possibility.",
                    }
                ],
                "research_influences": [
                    {
                        "source_id": seed_id,
                        "structural_idea": motif_id,
                        "scenario_application": "Transform the source seed into original body pressure and future possibility.",
                    }
                ],
            }
        ],
        "required_engine_changes": [],
        "inspiration_notes": [
            "Source seed: %s" % seed_id,
            "Source work: %s by %s" % (source_seed.get("source_title", ""), source_seed.get("source_author", "")),
            "Fleshpunk transform: %s" % source_seed.get("fleshpunk_seed", ""),
            "Mechanic direction: %s" % source_seed.get("mechanic_direction", ""),
        ],
        "self_critique": [
            "Uses source motifs structurally only; no source prose, names, or scenes are copied.",
            "Uses existing actions only, so no engine change is required.",
        ],
    }


def mock_patch(room: str, category: str = "choice", source_seeds: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    if source_seeds:
        return _mock_patch_from_seed(room, category, source_seeds[0])

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
                    "primary_pressure": "body_drift",
                    "body_path_pressure": "Drinking pulls Hymn toward biological shortcuts; studying or leaving reinforces baseline discipline.",
                    "avoidance_route": "She can study the rhythm or back away instead of feeding.",
                    "recognition_effect": "The valve records whether Hymn feeds, reads, or refuses living recovery.",
                    "line_1": "A valve in the wall opens when I breathe near it.",
                    "line_2": "It sounds hungry, but the pulse behind it is clean.",
                    "buttons": [
                        {"label": "Drink the clean pulse", "action": "drink_pool"},
                        {"label": "Study the rhythm", "action": "study_pool"},
                        {"label": "Back away", "action": "retreat"},
                    ],
                    "character_change": "both",
                    "possibility_tree": [
                        "Drinking enriches Hymn with clean pulse and teaches the valve her breath.",
                        "Studying preserves restraint and gives route knowledge without feeding the valve.",
                        "Retreat keeps the body unchanged but leaves the clean pulse for something else.",
                    ],
                    "progression_vector": "Hymn either becomes more willing to feed from living infrastructure or more disciplined about reading it first.",
                    "corpus_influences": [
                        {
                            "source_layer": "pulp_pre_1930",
                            "structural_idea": "unsafe refuge and physical temptation",
                            "scenario_application": "Keep branch pressure visible through breath, pulse, and restraint rather than explicit risk labels.",
                        }
                    ],
                },
            }
        ],
        "room_updates": [],
        "mutations": [],
        "symbiotes": [],
        "enemies": [],
        "scenario_design_notes": [
            {
                "room_id": room,
                "event_id": f"{room}_listening_valve",
                "scenario_role": "compact story pressure choice",
                "primary_pressure": "body_drift",
                "body_path_pressure": "Drinking pulls Hymn toward biological shortcuts; studying or leaving reinforces baseline discipline.",
                "avoidance_route": "She can study the rhythm or back away instead of feeding.",
                "recognition_effect": "The valve records whether Hymn feeds, reads, or refuses living recovery.",
                "character_change": "both",
                "possibility_tree": [
                    "Drinking enriches Hymn with clean pulse and teaches the valve her breath.",
                    "Studying preserves restraint and gives route knowledge without feeding the valve.",
                    "Retreat keeps the body unchanged but leaves the clean pulse for something else.",
                ],
                "progression_vector": "Hymn either becomes more willing to feed from living infrastructure or more disciplined about reading it first.",
                "corpus_anchors": [
                    {
                        "tier": 0,
                        "source_id": "mock_unsafe_refuge",
                        "source_title": "Mock unsafe refuge",
                        "source_author": "local",
                        "source_moment": "A safe-looking source of recovery carries attachment pressure.",
                        "story_element": "The room tempts Hymn to feed from living infrastructure.",
                        "scenario_application": "Make recovery, restraint, and refusal produce distinct body readings.",
                    }
                ],
                "research_influences": [
                    {
                        "source_layer": "pulp_pre_1930",
                        "structural_idea": "unsafe refuge and physical temptation",
                        "scenario_application": "Keep the branch pressure visible through breath, pulse, and restraint rather than explicit risk labels.",
                    }
                ],
            }
        ],
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
                "purpose": "A prior choice echoes as a later room-instance consequence.",
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
        "blind_read_summary": "Offline blind-read sample. The visible scenes have strong texture, but the player may not yet see why one chamber matters to the next.",
        "fun_score": 4,
        "first_time_player_score": 5,
        "build_score": 3,
        "sequence_cohesion_score": 4,
        "organism_pressure_score": 3,
        "core_loop_diagnosis": "The loop needs to become temptation, repeated pattern, visible pressure, adaptation, and outcome. Right now many actions reward or punish once, but repeated behavior rarely makes the organism change its strategy.",
        "blind_text_findings": [
            {
                "severity": "high",
                "target": "first-time sequence",
                "player_facing_evidence": "Rooms present specific apparatuses and choices, but the visible follow-through is mostly local.",
                "why_it_feels_disconnected": "A new player sees vivid chambers without enough recurring actors, route changes, or visible payoff to feel a run is building.",
                "recommendation": "Add more explicit later echoes that name what the player did and alter the next available pressure or route.",
            }
        ],
        "choice_progression_findings": [
            {
                "target": "choice labels",
                "current_choice_read": "Many buttons read as interact/extract/avoid variants.",
                "missing_progression": "The label does not always imply what future state or threat the player is accepting.",
                "recommendation": "Make labels and result lines expose distinct upside, cost, and future pressure.",
            }
        ],
        "payoff_gaps": [
            {
                "setup": "The organism records pulse, debt, scent, and damage.",
                "current_payoff_gap": "The player may not see those records changing later scenes quickly enough.",
                "recommended_payoff": "Within two rooms, surface a concrete echo that changes a choice, blocks a route, discounts a toll, or summons pressure.",
            }
        ],
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
        "minimum_game_shape": [
            "A visible early thread that starts in the opening room, changes a later room, and pays off before minute fifteen.",
            "At least one pressure actor that escalates after repeated choices and interrupts the deck.",
            "Choice labels that expose future risk, not only immediate interaction style.",
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


def mock_accessibility_critique() -> dict[str, Any]:
    return {
        "summary": "Offline accessibility sample. The game needs a command schema before STT: every button needs voice aliases, repeat/status/help must be first-class, and all state changes must be spoken.",
        "eyes_free_score": 5,
        "commandability_score": 3,
        "tts_score": 7,
        "critical_findings": [
            {
                "severity": "high",
                "target": "events.json buttons",
                "issue": "Buttons do not yet carry voice_aliases, so STT has no stable command vocabulary.",
                "recommendation": "Add 2-5 short aliases per button and enforce uniqueness within each encounter.",
            }
        ],
        "command_parser_findings": [
            {
                "severity": "high",
                "target": "command parser contract",
                "issue": "Parser behavior is not defined for ambiguity, unknown commands, or confirmation.",
                "recommendation": "Define CommandResult with action, confidence, needs_confirmation, spoken_feedback, and error recovery.",
            }
        ],
        "tts_findings": [
            {
                "severity": "medium",
                "target": "state readout",
                "issue": "Status command needs a stable order for health, shield, biomass, danger, corruption, dependence, and claim.",
                "recommendation": "Implement a status readout that only speaks changed or requested state.",
            }
        ],
        "schema_recommendations": [
            "Add voice_aliases to every button.",
            "Add global command handling for repeat, repeat choices, status, help, confirm, and cancel.",
            "Add command parser tests using current encounter buttons.",
        ],
        "command_alias_plan": [
            {"action": "combat", "recommended_aliases": ["fight", "attack", "kill it"], "notes": "Combat aliases should be available only when combat is a legal button."},
            {"action": "proceed", "recommended_aliases": ["move", "continue", "leave"], "notes": "Use context-specific aliases to avoid making every proceed choice sound identical."},
            {"action": "pay_resin_toll", "recommended_aliases": ["pay", "pay toll", "feed toll"], "notes": "Short toll aliases should not collide with skip toll."},
        ],
        "state_readout_plan": [
            "Status: health, shield, biomass, danger, corruption, dependence, merchant claim.",
            "Repeat choices: number, label, and one short cost phrase.",
            "After action: speak only changed state plus any scheduled warning.",
        ],
        "testing_plan": [
            "Complete a run using typed commands only.",
            "For each encounter, select each button by number.",
            "For each encounter, select each button by at least one alias.",
            "Verify unknown commands recover with repeat/status/help prompt.",
        ],
        "guide_updates": [
            {
                "section": "Command Result Contract",
                "suggested_text": "All parser outputs must be legal current actions, global commands, clarification requests, or cancellations. The parser never invents actions.",
            }
        ],
        "next_accessibility_prompt": "Add voice_aliases to the current event deck and implement a typed command parser that supports numbers, aliases, repeat choices, status, confirm, and cancel.",
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


def mock_story_architect() -> dict[str, Any]:
    return {
        "summary": "Offline story architect sample. The current stack has strong local situations but needs a pilot arc where a recurring figure wants something and changes later encounters.",
        "story_diagnosis": "The rooms imply memory, debt, and pursuit, but many follow-ups behave like echoes instead of scenes. A story spine needs a character who returns with leverage and forces Hymn to answer.",
        "missing_story_primitives": [
            "A recurring character with a visible desire.",
            "Follow-up encounters that change options or prices.",
            "A payoff before the first run feels like disconnected room browsing.",
        ],
        "character_arcs": [
            {
                "character_id": "quartermaster_of_teeth",
                "player_facing_name": "Quartermaster of Teeth",
                "current_status": "Present in metadata and toll imagery, but not yet active enough as a character.",
                "desire": "Convert Hymn's route choices into payable debt.",
                "pressure_method": "Changes prices, closes mouths, and sells route heat to hunters.",
                "relationship_to_hymn": "Predatory accountant who treats her as inventory with legs.",
                "first_appearance": "Opening rib/toll decision or first larder debt.",
                "arc_beats": [
                    {
                        "beat_id": "debt_setup",
                        "role": "setup",
                        "trigger": "First toll refusal or underpayment.",
                        "encounter_function": "Name the debt system as an actor.",
                        "player_choice": "Pay, dispute, or force the mouth.",
                        "visible_change": "A later toll has a marked price or missing safe option.",
                        "mechanical_consequence": "merchant_claim or toll_debt_streak increases.",
                        "implementation_notes": ["Use story_followups and a special_event with trigger_key."],
                    }
                ],
                "why_this_is_a_character": "It wants payment, remembers refusal, and can alter future rooms.",
                "failure_mode_if_absent": "Debt remains flavor and the player does not feel opposed by anyone.",
            }
        ],
        "first_15_minute_spine": [
            {
                "sequence_index": 1,
                "target_room_or_event": "rib_lock_tally_gate_account",
                "story_function": "Open with a pressure-lock bargain.",
                "player_question": "Do I let this place count me, pay it, or injure myself forcing through?",
                "choice_pressure": "Each option creates a different claimant.",
                "followup_payoff": "A named toll actor recognizes the decision within two rooms.",
                "required_data_changes": ["Add a Quartermaster follow-up scene for toll refusal/payment/force."],
            }
        ],
        "followup_encounter_plan": [
            {
                "source_event": "rib_lock_tally_gate_account",
                "followup_event_id": "story_quartermaster_first_claim",
                "character_id": "quartermaster_of_teeth",
                "trigger": "Toll refusal, payment, or forced rib passage.",
                "timing": "1-2 rooms later.",
                "scene_function": "Turn toll accounting into a recurring antagonist scene.",
                "choice_or_route_change": "One option is cheaper, blocked, or dangerous based on the earlier decision.",
                "mechanical_hook": "merchant_claim and environment_state flags.",
                "authoring_prompt": "Write a short follow-up encounter where a toll/accounting actor returns with leverage from the player's first toll decision.",
            }
        ],
        "pilot_arc_recommendation": {
            "arc_name": "Quartermaster Debt Pilot",
            "why_this_first": "It attaches to existing toll/larder/merchant content and can pay off quickly.",
            "scope_events": ["rib_lock_tally_gate_account", "biomass_larder_weighted_pockets", "story_quartermaster_first_claim"],
            "required_system_hooks": ["Track toll stance or reuse merchant_claim", "Allow follow-up event to alter a later toll option"],
            "acceptance_tests": ["A blind player can name who is pressuring them by minute fifteen.", "A prior toll choice visibly changes one later option."],
            "generation_prompt": "Generate the Quartermaster Debt Pilot as setup, escalation, choice, and payoff follow-up encounters using existing actions where possible.",
        },
        "story_rules": [
            "Every named character needs desire, memory, pressure, and payoff.",
            "Every story follow-up must be a scene or option change, not only a mood echo.",
        ],
        "patch_strategy": [
            "Plan one arc first.",
            "Generate OpenAI-authored follow-up encounters for that arc.",
            "Validate that first-run play reveals the character before minute fifteen.",
        ],
        "next_story_prompt": "Generate a small Quartermaster debt arc with 4-6 follow-up encounters, using current rooms and existing actions first.",
    }


def mock_story_pilot() -> dict[str, Any]:
    return {
        "title": "Offline Story Pilot Sample",
        "design_goal": "Show the shape of a story pilot patch without calling OpenAI.",
        "special_events": [
            {
                "id": "story_soft_captain_pulse_mark",
                "type": "story",
                "speaker": "Hymn",
                "line_1": "Chorus, a transit cord drops from an overhead seam and pulses at my wrist interval.",
                "line_2": "The cord holds the count I allowed. A nearby lock opens while the pulse is still running.",
                "reactivate_on_reshuffle": False,
                "buttons": [
                    {"label": "File the rhythm", "action": "proceed", "voice_aliases": ["file rhythm", "report", "rhythm"]},
                    {"label": "Leave it unfiled", "action": "retreat", "voice_aliases": ["leave unfiled", "hide it", "retreat"]},
                ],
                "action_results": {
                    "proceed": {
                        "lines": ["I file the rhythm and keep the cord's interval in my wrist."],
                        "environment_state_changes": ["soft_captain_next_rib_lock"],
                    },
                    "retreat": {
                        "lines": ["I leave the rhythm unfiled. The cord retracts with my count still in it."],
                        "environment_state_changes": ["soft_captain_refused"],
                    },
                },
            }
        ],
        "room_event_updates": [
            {
                "room_id": "rib_lock_tally_gate",
                "event_id": "rib_lock_tally_gate_account",
                "merge": {
                    "state_overrides": [
                        {
                            "state_key": "soft_captain_next_rib_lock",
                            "consume_state": True,
                            "event": {
                                "line_1": "The lock starts at my stored wrist interval before the toll mouth opens.",
                                "line_2": "The held count gives me one quiet slip. Paying or forcing would break it.",
                            },
                        }
                    ]
                },
            }
        ],
        "required_engine_changes": [],
        "validation_notes": ["Mock patch only."],
        "self_critique": ["Insufficient for production; use OpenAI for authored content."],
    }


def validation_errors(
    patch: dict[str, Any],
    allow_new_actions: bool = False,
    expected_category: str = "",
    strict_tradeoffs: bool = False,
    strict_scenario_contract: bool = False,
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
    room_updates = patch.get("room_updates", [])
    if room_updates is None:
        room_updates = []
    if not isinstance(room_updates, list):
        errors.append("patch.room_updates must be a list")
        room_updates = []
    for index, item in enumerate(room_updates):
        if not isinstance(item, dict):
            errors.append(f"room_updates[{index}] is not an object")
            continue
        room_id = str(item.get("room_id", ""))
        if room_id not in rooms:
            errors.append(f"room_updates[{index}].room_id '{room_id}' is not in room_dialogue.json")
        update = item.get("update")
        if not isinstance(update, dict) or not update:
            errors.append(f"room_updates[{index}].update must be a non-empty object")
            continue
        if strict_scenario_contract and update.get("mutation_hooks"):
            errors.extend(body_option_hook_errors(update.get("mutation_hooks"), f"room_updates[{index}].mutation_hooks"))

    seen_ids: set[str] = set()
    design_note_ids: set[str] = set()
    if strict_scenario_contract:
        design_notes = patch.get("scenario_design_notes", [])
        if not isinstance(design_notes, list) or not design_notes:
            errors.append("patch.scenario_design_notes must be a non-empty list in strict scenario mode")
        else:
            for note_index, note in enumerate(design_notes):
                if not isinstance(note, dict):
                    errors.append(f"scenario_design_notes[{note_index}] is not an object")
                    continue
                note_event_id = str(note.get("event_id", "")).strip()
                if note_event_id:
                    design_note_ids.add(note_event_id)
                for key in (
                    "scenario_role",
                    "primary_pressure",
                    "body_path_pressure",
                    "avoidance_route",
                    "recognition_effect",
                    "character_change",
                    "progression_vector",
                ):
                    if not str(note.get(key, "")).strip():
                        errors.append(f"scenario_design_notes[{note_index}]: missing {key}")
                if not _has_possibility_tree(note):
                    errors.append(f"scenario_design_notes[{note_index}]: missing possibility_tree with at least two branches")
                influences = note.get("research_influences", [])
                if not isinstance(influences, list) or not influences:
                    errors.append(f"scenario_design_notes[{note_index}]: missing research_influences")
                anchors = note.get("corpus_anchors", [])
                if not isinstance(anchors, list) or not anchors:
                    errors.append(f"scenario_design_notes[{note_index}]: missing corpus_anchors")
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
        if strict_tradeoffs and not is_tradeoff_exempt_event(event):
            commandable_buttons = commandable_button_count(event)
            if commandable_buttons < 2:
                errors.append(
                    f"{event_id or index}: single-choice room ({commandable_buttons} commandable button{'s' if commandable_buttons != 1 else ''})"
                )
        if strict_scenario_contract:
            if not _has_character_change_vector(event):
                errors.append(f"{event_id or index}: missing character_change (enrich, destabilize, or both)")
            if commandable_button_count(event) > 1 and not _has_possibility_tree(event):
                errors.append(f"{event_id or index}: missing possibility_tree or branch_pressures")
            if not _has_specific_corpus_influence(event):
                errors.append(f"{event_id or index}: missing specific corpus_influences or research_influences")
            if event_id and event_id not in design_note_ids:
                errors.append(f"{event_id}: missing scenario_design_notes entry")
            player_text_parts = [
                str(event.get("line_1", "")),
                str(event.get("line_2", "")),
            ]
            for button in buttons:
                if isinstance(button, dict):
                    player_text_parts.append(str(button.get("label", "")))
            for result_key in ("action_results", "outcomes", "button_results"):
                result_payload = event.get(result_key, {})
                if isinstance(result_payload, dict):
                    for result in result_payload.values():
                        if isinstance(result, dict):
                            lines = result.get("lines", [])
                            if isinstance(lines, list):
                                player_text_parts.extend(str(line) for line in lines)
            player_text = "\n".join(player_text_parts).lower()
            forbidden_patterns = [
                r"\brisk\s*:",
                r"\breward\s*:",
                r"\bcost\s*:",
                r"\bfuture consequence\b",
                r"\bbranch [ab]\b",
                r"\bsafe option\b",
                r"\bcombat option\b",
                r"\bmutation route\b",
                r"\+\d+\s*(corruption|danger|biomass|health|shield)",
            ]
            for pattern in forbidden_patterns:
                if re.search(pattern, player_text):
                    errors.append(f"{event_id or index}: player-facing text exposes risk/branch/stat label matching {pattern!r}")
                    break
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
        if strict_scenario_contract and event.get("mutation_id"):
            hook = event.get("mutation_hook", {})
            if not isinstance(hook, dict):
                errors.append(f"{event_id}: mutation event needs mutation_hook object with multi-use fields")
            else:
                for hook_key in ("in_encounter_use", "out_of_encounter_use", "surprising_second_use"):
                    if not str(hook.get(hook_key, "")).strip():
                        errors.append(f"{event_id}: mutation_hook missing {hook_key}")

    special_events = patch.get("special_events", [])
    if special_events is None:
        special_events = []
    if not isinstance(special_events, list):
        errors.append("patch.special_events must be a list")
        special_events = []
    for index, event in enumerate(special_events):
        if not isinstance(event, dict):
            errors.append(f"special_events[{index}] is not an object")
            continue
        event_id = str(event.get("id", ""))
        if not event_id:
            errors.append(f"special_events[{index}].id is empty")
        if event_id in event_ids:
            errors.append(f"special event id already exists: {event_id}")
        if event_id in seen_ids:
            errors.append(f"duplicate event id in patch: {event_id}")
        seen_ids.add(event_id)
        for key in ("type", "speaker", "line_1", "line_2"):
            if not str(event.get(key, "")).strip():
                errors.append(f"special_events.{event_id or index}: missing {key}")
        buttons = event.get("buttons", [])
        if not isinstance(buttons, list) or not buttons:
            errors.append(f"special_events.{event_id or index}: buttons must be a non-empty list")
            continue
        if strict_tradeoffs and not is_tradeoff_exempt_event(event):
            commandable_buttons = commandable_button_count(event)
            if commandable_buttons < 2:
                errors.append(f"special_events.{event_id or index}: single-choice room ({commandable_buttons} commandable button{'s' if commandable_buttons != 1 else ''})")
        for button_index, button in enumerate(buttons):
            if not isinstance(button, dict):
                errors.append(f"special_events.{event_id}: button {button_index} is not an object")
                continue
            action = str(button.get("action", "")).strip()
            if action and action not in actions and not allow_new_actions:
                errors.append(f"special_events.{event_id}: unknown action '{action}'")

    if not allow_new_actions:
        required_changes = patch.get("required_engine_changes", [])
        if required_changes:
            errors.append("required_engine_changes is not empty, but new actions are not allowed")
    return errors


def events_file_errors(strict_actions: bool = False, strict_tradeoffs: bool = False) -> list[str]:
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
                    if strict_tradeoffs:
                        event_type = str(event.get("type", ""))
                        if not is_tradeoff_exempt_event(event):
                            buttons = event.get("buttons", [])
                            commandable_buttons = commandable_button_count(event)
                            if commandable_buttons < 2:
                                errors.append(f"room_events.{room_id}[{index}]: single-choice room ({commandable_buttons} commandable button{'s' if commandable_buttons != 1 else ''})")
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


def _playtest_slice_scope() -> dict[str, set[str]]:
    decks = load_json(DECKS_PATH)
    room_ids: set[str] = set()
    for key in ("starter_rooms",):
        value = decks.get(key, [])
        if isinstance(value, list):
            room_ids.update(str(room_id) for room_id in value if str(room_id).strip())
    for key in ("opening_room_id", "first_room_after_opening"):
        value = str(decks.get(key, "")).strip()
        if value:
            room_ids.add(value)
    pools = decks.get("room_pools", {})
    if isinstance(pools, dict):
        for pool in pools.values():
            if isinstance(pool, list):
                room_ids.update(str(room_id) for room_id in pool if str(room_id).strip())

    event_ids = {
        str(event_id)
        for event_id in decks.get("playtest_event_ids", [])
        if str(event_id).strip()
    }
    special_event_ids = set()
    opening_event_id = str(decks.get("opening_event_id", "")).strip()
    if opening_event_id:
        special_event_ids.add(opening_event_id)
    return {
        "room_ids": room_ids,
        "event_ids": event_ids,
        "special_event_ids": special_event_ids,
    }


def event_writing_findings(mode: str = "migration", playtest_slice: bool = False) -> list[dict[str, str]]:
    payload = load_json(EVENTS_PATH)
    findings: list[dict[str, str]] = []
    scope = _playtest_slice_scope() if playtest_slice else {}
    scoped_room_ids = scope.get("room_ids", set())
    scoped_event_ids = scope.get("event_ids", set())
    scoped_special_event_ids = scope.get("special_event_ids", set())
    if not playtest_slice:
        findings = room_depth_findings(mode=mode) + room_story_findings()
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
        ("looks safer", "flat safety wording"),
        ("may lower", "flat probability wording"),
        ("may show", "flat probability wording"),
        ("may calm", "flat probability wording"),
        ("buys control", "abstract choice summary"),
        ("buys speed", "abstract choice summary"),
        ("buys uncertainty", "abstract choice summary"),
        ("is useful", "generic utility wording"),
        ("under pressure:", "abstract choice framing"),
        ("three uses", "menu-like choice framing"),
        ("command signal", "abstract command jargon"),
        ("something is", "unintroduced actor"),
        ("something has", "unintroduced actor"),
        ("it wants", "unsupported agency shorthand"),
        ("the system", "abstract system shorthand"),
        ("the room", "abstract room shorthand"),
    ]
    source_style_patterns = [
        (r"\b(verne|lovecraft|howard|sabatini|merritt|dunsany|haggard|burroughs|blackwood|machen|shiel|hodgson|eddison|mundy)\b", "source name leaked into player-facing prose"),
        (r"\b(eldritch|cyclopean|aeon|aeons|nameless|unspeakable|indescribable|blasphemous|cosmic|madness)\b", "Lovecraft costume diction"),
        (r"\b(professor|gentleman|gentlemen|my dear|alas|hurrah)\b", "Verne costume diction"),
        (r"\b(destiny|prophecy|omen|judg(?:e)?ment|invitation|fate)\b", "mystical abstraction in Hymn narration"),
        (r"\b(the organism wants|the room wants|the room remembers|the system knows|the system wants)\b", "unsupported agency claim"),
        (r"\b(later this will|next room will|this queues|this unlocks|ending path|future consequence|branch [ab]|safe option|combat option|mutation route)\b", "future mechanic or branch label stated in narration"),
        (r"(\+[0-9]+\s*(corruption|biomass|danger|health|shield)|risk\s*:|reward\s*:|cost\s*:)", "visible stat/risk label in player-facing prose"),
    ]
    lore_name_terms = {
        "soft captain",
        "pell",
        "mother chancel",
        "commandant signal",
    }
    apparatus_terms = {
        "beetle",
        "bell",
        "blade",
        "bore",
        "body",
        "cord",
        "dock",
        "enemy",
        "ferry",
        "finger",
        "foot",
        "horn",
        "grub",
        "harness",
        "hunter",
        "jaw",
        "joint",
        "larva",
        "lice",
        "mouth",
        "predator",
        "pocket",
        "pore",
        "ring",
        "rival",
        "scale",
        "seam",
        "signal",
        "spur",
        "tail",
        "teeth",
        "tissue",
        "track",
        "valve",
        "wound",
    }
    evidence_terms = {
        "abrasion",
        "bleeding",
        "clean",
        "cold",
        "cut",
        "edge",
        "old",
        "pulse",
        "record",
        "repair",
        "residue",
        "ridge",
        "score",
        "scored",
        "scratch",
        "scent",
        "stain",
        "tally",
        "worn",
    }
    body_stake_terms = {
        "blood",
        "body",
        "boot",
        "breath",
        "cuts",
        "flesh",
        "glove",
        "hand",
        "knees",
        "pulse",
        "shoulder",
        "skin",
        "weight",
        "wound",
        "wrist",
    }
    concrete_terms = {
        "beetle",
        "bell",
        "blood",
        "bone",
        "bore",
        "blister",
        "cord",
        "cut",
        "dock",
        "ferry",
        "floor",
        "fluid",
        "grub",
        "harbor",
        "harness",
        "larva",
        "lice",
        "larder",
        "lens",
        "map",
        "marrow",
        "mouth",
        "pocket",
        "pore",
        "packet",
        "rib",
        "ring",
        "scale",
        "scar",
        "seam",
        "signal",
        "strap",
        "teeth",
        "tissue",
        "token",
        "valve",
        "wall",
        "wound",
    }
    place_function_terms = {
        "bargain",
        "cellar",
        "control",
        "cross",
        "crossing",
        "feed",
        "feeding",
        "floor",
        "gate",
        "harbor",
        "larder",
        "maintenance",
        "map",
        "measure",
        "operator",
        "pool",
        "repair",
        "route",
        "survey",
        "toll",
        "track",
        "training",
    }
    position_pressure_terms = {
        "ahead",
        "angle",
        "behind",
        "close",
        "doorway",
        "low",
        "narrows",
        "near",
        "step",
        "threshold",
        "two steps",
        "under",
    }
    chorus_expected = {"merchant", "danger", "corruption", "symbiote"}

    def add(location: str, severity: str, issue: str, recommendation: str) -> None:
        findings.append({
            "location": location,
            "severity": severity,
            "issue": issue,
            "recommendation": recommendation,
        })

    def check_house_voice_text(text: str, location: str) -> None:
        if not text:
            return
        lower_text = text.lower()
        for pattern, issue in source_style_patterns:
            if re.search(pattern, lower_text):
                add(
                    location,
                    "high",
                    issue,
                    "Rewrite in Hymn's house voice: physical situation, mechanism, evidence, and bodily stakes. Corpus influence should not be visible as author-mode diction.",
                )
        for term in lore_name_terms:
            if term in lower_text:
                add(
                    location,
                    "medium",
                    "proper-name lore in field report",
                    "Use observable traces unless the named figure is physically present or has been introduced in-world.",
                )

    def check_event(event: dict[str, Any], location: str) -> None:
        event_type = str(event.get("type", ""))
        line_1 = str(event.get("line_1", ""))
        line_2 = str(event.get("line_2", ""))
        combined = f"{line_1} {line_2}"
        combined_lower = combined.lower()
        check_house_voice_text(line_1, f"{location}.line_1")
        check_house_voice_text(line_2, f"{location}.line_2")

        for pattern, issue in weak_line_patterns:
            if pattern in combined_lower:
                add(location, "high", issue, "Rewrite as a plain observed situation with one visible actor and one observable pressure. Do not pad with mechanism nouns or future payoff.")

        has_concrete_actor = any(term in combined_lower for term in concrete_terms)
        if event_type in {"choice", "story"} and not has_concrete_actor:
            add(
                location,
                "medium",
                "abstract situation",
                "Name the visible actor, organ, material, or mark involved. One clean concrete detail is enough.",
            )
        if event_type in {"choice", "combat", "boss"}:
            if not any(term in combined_lower for term in place_function_terms):
                add(
                    location,
                    "medium",
                    "missing place function",
                    "Tell a cold reader what kind of place this is or what work it normally performs before the choice begins.",
                )
            if not any(term in combined_lower for term in position_pressure_terms):
                add(
                    location,
                    "medium",
                    "missing immediate position pressure",
                    "Ground the scene in where Hymn stands, what is close, what is narrowing, or what is about to move.",
                )

        if event_type in chorus_expected and "chorus" not in combined_lower:
            add(location, "medium", "missing Chorus field-report cadence", "Add a short Hymn-to-Chorus check without printing a Chorus reply.")

        if str(event.get("enemy_id", "")) and event_type in {"combat", "boss"} and "scene_path" not in event:
            add(location, "low", "combat event relies on enemy scene fallback", "Add scene_path if this encounter needs a specific visible sprite.")

        buttons = event.get("buttons", [])
        if not isinstance(buttons, list):
            return
        commandable_buttons = commandable_button_count(event)
        if not is_tradeoff_exempt_event(event) and commandable_buttons < 2:
            add(
                location,
                "high",
                f"single-choice room ({commandable_buttons} commandable button{'s' if commandable_buttons != 1 else ''})",
                "Add a second legal choice with a distinct cost, delayed consequence, or alternative pressure axis. Transition events may stay exempt.",
            )
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
            check_house_voice_text(label, f"{button_location}.label")

        action_results = event.get("action_results", {})
        if isinstance(action_results, dict):
            for action_id, result in action_results.items():
                if not isinstance(result, dict):
                    continue
                result_lines = result.get("lines", [])
                if isinstance(result_lines, list):
                    for line_index, line in enumerate(result_lines):
                        check_house_voice_text(str(line), f"{location}.action_results.{action_id}.lines[{line_index}]")

        followups = event.get("story_followups", {})
        if isinstance(followups, dict):
            for followup_key, followup in followups.items():
                if isinstance(followup, dict):
                    check_house_voice_text(str(followup.get("queued_line", "")), f"{location}.story_followups.{followup_key}.queued_line")

    def check_room_text(text: str, location: str, require_full_house_style: bool = False) -> None:
        if not text:
            return
        check_house_voice_text(text, location)
        lower_text = text.lower()
        if not require_full_house_style:
            return
        if not any(term in lower_text for term in apparatus_terms):
            add(
                location,
                "medium",
                "room prose lacks concrete pressure point",
                "Name one concrete body, actor, predator, organ, route, wound, material, or pressure point. Do not invent machinery if the scenario is about a person, fight, passage, or mutation.",
            )
        if not any(term in lower_text for term in evidence_terms):
            add(
                location,
                "medium",
                "room prose lacks accumulated evidence",
                "Add wear, repair, residue, old marks, measurement, or prior-use evidence so dread comes from records.",
            )
        if not any(term in lower_text for term in body_stake_terms):
            add(
                location,
                "medium",
                "room prose lacks bodily stakes",
                "Anchor the mechanism to Hymn's body: boot, wrist, pulse, wound, breath, shoulder, weight, or skin.",
            )

    def check_room(room: dict[str, Any], location: str) -> None:
        narrow_room = is_narrow_room_role(room)
        check_room_text(str(room.get("name", "")), f"{location}.name")
        check_room_text(str(room.get("instance_premise", "")), f"{location}.instance_premise")
        check_room_text(str(room.get("first_visit_description", "")), f"{location}.first_visit_description", require_full_house_style=not narrow_room)
        check_room_text(str(room.get("return_description", "")), f"{location}.return_description")
        ui_text = room.get("ui_text", {})
        if isinstance(ui_text, dict):
            check_room_text(str(ui_text.get("line_1", "")), f"{location}.ui_text.line_1", require_full_house_style=not narrow_room)
            check_room_text(str(ui_text.get("line_2", "")), f"{location}.ui_text.line_2", require_full_house_style=not narrow_room)
        progression_state = room.get("progression_state", {})
        if isinstance(progression_state, dict):
            for state_key, state_text in progression_state.items():
                check_room_text(str(state_text), f"{location}.progression_state.{state_key}")
        for array_key in ("cross_run_story_hooks", "environment_echoes"):
            entries = room.get(array_key, [])
            if isinstance(entries, list):
                for index, entry in enumerate(entries):
                    check_room_text(str(entry), f"{location}.{array_key}[{index}]")

    room_events = payload.get("room_events", {})
    if isinstance(room_events, dict):
        for room_id, events in room_events.items():
            if playtest_slice and str(room_id) not in scoped_room_ids:
                continue
            if not isinstance(events, list):
                continue
            for event in events:
                if isinstance(event, dict):
                    event_id = str(event.get("id", "unknown"))
                    if playtest_slice and scoped_event_ids and event_id not in scoped_event_ids:
                        continue
                    check_event(event, f"room_events.{room_id}.{event_id}")

    special_events = payload.get("special_events", {})
    if isinstance(special_events, dict):
        for event_id, event in special_events.items():
            if playtest_slice and scoped_special_event_ids and event_id not in scoped_special_event_ids:
                continue
            if isinstance(event, dict):
                check_event(event, f"special_events.{event_id}")

    rooms_payload = load_json(ROOMS_PATH)
    rooms = rooms_payload.get("rooms", [])
    if isinstance(rooms, list):
        for index, room in enumerate(rooms):
            if isinstance(room, dict):
                room_id = str(room.get("id", index))
                if playtest_slice and room_id not in scoped_room_ids:
                    continue
                check_room(room, f"rooms.{room_id}")

    return findings


def event_accessibility_findings() -> list[dict[str, str]]:
    payload = load_json(EVENTS_PATH)
    findings: list[dict[str, str]] = []
    global_commands = {
        "one",
        "two",
        "three",
        "repeat",
        "repeat choices",
        "status",
        "inventory",
        "help",
        "confirm",
        "cancel",
        "pause",
        "continue",
        "slower",
        "faster",
    }
    visual_only_terms = {
        "visual",
        "see",
        "look",
        "color",
        "red",
        "green",
        "glow",
        "glowing",
    }

    def add(location: str, severity: str, issue: str, recommendation: str) -> None:
        findings.append({
            "location": location,
            "severity": severity,
            "issue": issue,
            "recommendation": recommendation,
        })

    def check_event(event: dict[str, Any], location: str) -> None:
        line_1 = str(event.get("line_1", ""))
        line_2 = str(event.get("line_2", ""))
        for line_key, line in (("line_1", line_1), ("line_2", line_2)):
            word_count = len(line.split())
            if word_count > 22:
                add(f"{location}.{line_key}", "medium", f"TTS line is long ({word_count} words)", "Split into shorter phrase chunks.")
            lower_line = line.lower()
            if any(term in lower_line for term in visual_only_terms) and not any(term in lower_line for term in ("smell", "sound", "hear", "pulse", "heat", "scent", "touch", "breath")):
                add(f"{location}.{line_key}", "low", "possible visual-only cue", "Add nonvisual sensory information or state effect.")

        buttons = event.get("buttons", [])
        if not isinstance(buttons, list) or not buttons:
            add(location, "high", "no commandable buttons", "Every encounter needs at least one legal command target.")
            return

        seen_aliases: dict[str, int] = {}
        for index, button in enumerate(buttons):
            if not isinstance(button, dict):
                continue
            button_location = f"{location}.buttons[{index}]"
            label = str(button.get("label", ""))
            action = str(button.get("action", ""))
            aliases = button.get("voice_aliases", [])
            if not isinstance(aliases, list) or not aliases:
                add(button_location, "high", "missing voice_aliases", "Add 2-5 short spoken aliases for this command.")
                aliases = []
            if len(label.split()) > 5:
                add(button_location, "low", f"long spoken label '{label}'", "Keep command labels short; move nuance into narration.")
            normalized_aliases: list[str] = []
            for alias in aliases:
                alias_text = str(alias).strip().lower()
                if not alias_text:
                    continue
                normalized_aliases.append(alias_text)
                if alias_text in global_commands:
                    add(button_location, "medium", f"alias '{alias_text}' collides with global command", "Use action-specific aliases; numbers remain global.")
                if len(alias_text.split()) > 4:
                    add(button_location, "low", f"alias '{alias_text}' is long", "Prefer short aliases that survive STT.")
                if alias_text in seen_aliases:
                    add(button_location, "high", f"duplicate alias '{alias_text}' in encounter", "Aliases must be unique within the current encounter.")
                else:
                    seen_aliases[alias_text] = index
            if action == "proceed" and not any(alias in normalized_aliases for alias in ("continue", "move", "leave", "proceed")):
                add(button_location, "low", "proceed action lacks simple movement alias", "Add a short movement alias such as move, leave, or continue.")

    room_events = payload.get("room_events", {})
    if isinstance(room_events, dict):
        for room_id, events in room_events.items():
            if isinstance(events, list):
                for event in events:
                    if isinstance(event, dict):
                        check_event(event, f"room_events.{room_id}.{event.get('id', 'unknown')}")

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

    source_seeds = load_source_seed_context(args)
    if args.mock:
        patch = mock_patch(room, args.category or "choice", source_seeds)
    else:
        patch = call_openai(build_prompt(args), args.model, patch_schema(), "scenario_patch")

    enrich_patch_voice_aliases(patch)

    errors = validation_errors(
        patch,
        allow_new_actions=args.allow_new_actions,
        expected_category=args.category or "",
        strict_tradeoffs=args.strict_tradeoffs,
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
    errors = validation_errors(
        patch,
        allow_new_actions=args.allow_new_actions,
        strict_tradeoffs=args.strict_tradeoffs,
        strict_scenario_contract=args.strict_scenario_contract,
    )
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


def cmd_accessibility_critique(args: argparse.Namespace) -> int:
    GENERATED_DIR.mkdir(exist_ok=True)
    if args.mock:
        critique = mock_accessibility_critique()
    else:
        critique = call_openai(
            build_accessibility_critique_prompt(args),
            args.model,
            accessibility_critique_schema(),
            "accessibility_critique",
        )

    out = Path(args.out) if args.out else GENERATED_DIR / "accessibility_critique.json"
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


def cmd_story_architect(args: argparse.Namespace) -> int:
    GENERATED_DIR.mkdir(exist_ok=True)
    if args.mock:
        architecture = mock_story_architect()
    else:
        architecture = call_openai(
            build_story_architect_prompt(args),
            args.model,
            story_architect_schema(),
            "story_architect",
        )

    out = Path(args.out) if args.out else GENERATED_DIR / "story_architect.json"
    if not out.is_absolute():
        out = ROOT / out
    write_json(out, architecture)
    print(out)
    return 0


def cmd_story_pilot(args: argparse.Namespace) -> int:
    GENERATED_DIR.mkdir(exist_ok=True)
    if args.mock:
        patch = mock_story_pilot()
    else:
        patch = call_openai(
            build_story_pilot_prompt(args),
            args.model,
            story_pilot_schema(),
            "story_pilot_patch",
        )

    out = Path(args.out) if args.out else GENERATED_DIR / "story_pilot_patch.json"
    if not out.is_absolute():
        out = ROOT / out
    write_json(out, patch)
    print(out)
    return 0


def _deep_merge_dict(target: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _deep_merge_dict(target[key], value)
        elif key == "state_overrides" and isinstance(value, list) and isinstance(target.get(key), list):
            target[key].extend(value)
        else:
            target[key] = value
    return target


def _normalize_story_pilot_action_results(event: dict[str, Any]) -> None:
    action_results = event.get("action_results")
    if not isinstance(action_results, dict):
        return
    for result in action_results.values():
        if not isinstance(result, dict):
            continue
        if "result_lines" in result and "lines" not in result:
            result["lines"] = result.pop("result_lines")
        environment_changes = result.get("environment_state_changes")
        if isinstance(environment_changes, dict):
            normalized_changes: list[str] = []
            for key, value in environment_changes.items():
                if value in (None, False, 0, "0", "false", "False", "none", "None", "cleared", ""):
                    continue
                normalized_changes.append(str(key))
            result["environment_state_changes"] = normalized_changes


def _normalize_story_pilot_event(event: dict[str, Any]) -> None:
    _normalize_story_pilot_action_results(event)
    overrides = event.get("state_overrides")
    if not isinstance(overrides, list):
        return
    for override in overrides:
        if not isinstance(override, dict):
            continue
        override_event = override.get("event")
        if isinstance(override_event, dict):
            _normalize_story_pilot_event(override_event)


def cmd_apply_story_pilot(args: argparse.Namespace) -> int:
    patch_path = Path(args.patch)
    if not patch_path.is_absolute():
        patch_path = ROOT / patch_path
    patch = load_json(patch_path)
    events_payload = load_json(EVENTS_PATH)
    rooms_payload = load_json(ROOMS_PATH)
    decks_payload = load_json(DECKS_PATH)

    rooms = rooms_payload.setdefault("rooms", [])
    if not isinstance(rooms, list):
        raise SystemExit("rooms must be a list")
    existing_room_ids = {str(room.get("id", "")) for room in rooms if isinstance(room, dict)}
    for room in patch.get("room_records", []):
        if not isinstance(room, dict):
            raise SystemExit("room_records entries must be objects")
        room_id = str(room.get("id", "")).strip()
        if not room_id:
            raise SystemExit("room record missing id")
        if room_id in existing_room_ids:
            for existing_room in rooms:
                if isinstance(existing_room, dict) and str(existing_room.get("id", "")) == room_id:
                    _deep_merge_dict(existing_room, room)
                    break
        else:
            rooms.append(room)
            existing_room_ids.add(room_id)

    special_events = events_payload.setdefault("special_events", {})
    if not isinstance(special_events, dict):
        raise SystemExit("special_events must be an object")

    for event in patch.get("special_events", []):
        if not isinstance(event, dict):
            raise SystemExit("special_events entries must be objects")
        _normalize_story_pilot_event(event)
        event_id = str(event.get("id", "")).strip()
        if not event_id:
            raise SystemExit("special event missing id")
        special_events[event_id] = event

    room_events = events_payload.setdefault("room_events", {})
    if not isinstance(room_events, dict):
        raise SystemExit("room_events must be an object")
    for room_event_record in patch.get("room_events", []):
        if not isinstance(room_event_record, dict):
            raise SystemExit("room_events entries must be objects")
        room_id = str(room_event_record.get("room_id", "")).strip()
        event = room_event_record.get("event", {})
        if not room_id:
            raise SystemExit("room_events entry missing room_id")
        if not isinstance(event, dict):
            raise SystemExit(f"{room_id}: room event must be an object")
        _normalize_story_pilot_event(event)
        room_event_list = room_events.setdefault(room_id, [])
        if not isinstance(room_event_list, list):
            raise SystemExit(f"room_events.{room_id} is not a list")
        event_id = str(event.get("id", "")).strip()
        replaced = False
        for index, existing_event in enumerate(room_event_list):
            if isinstance(existing_event, dict) and str(existing_event.get("id", "")) == event_id:
                room_event_list[index] = event
                replaced = True
                break
        if not replaced:
            room_event_list.append(event)

    for update in patch.get("room_event_updates", []):
        if not isinstance(update, dict):
            raise SystemExit("room_event_updates entries must be objects")
        room_id = str(update.get("room_id", "")).strip()
        event_id = str(update.get("event_id", "")).strip()
        merge_patch = update.get("merge", {})
        if not isinstance(merge_patch, dict):
            raise SystemExit(f"{room_id}.{event_id}: merge must be an object")
        _normalize_story_pilot_event(merge_patch)
        events = room_events.get(room_id, [])
        if not isinstance(events, list):
            raise SystemExit(f"room_events.{room_id} is not a list")
        matched = False
        for event in events:
            if isinstance(event, dict) and str(event.get("id", "")) == event_id:
                _deep_merge_dict(event, merge_patch)
                matched = True
                break
        if not matched:
            raise SystemExit(f"room_events.{room_id}: event '{event_id}' not found")

    enrich_events_payload_voice_aliases(events_payload)

    deck_room_pools = decks_payload.setdefault("room_pools", {})
    if not isinstance(deck_room_pools, dict):
        raise SystemExit("room_pools must be an object")
    for pool_update in patch.get("deck_pool_updates", []):
        if not isinstance(pool_update, dict):
            raise SystemExit("deck_pool_updates entries must be objects")
        pool_name = str(pool_update.get("pool", "")).strip()
        room_id = str(pool_update.get("room_id", "")).strip()
        if not pool_name or not room_id:
            raise SystemExit("deck_pool_updates entries need pool and room_id")
        pool = deck_room_pools.setdefault(pool_name, [])
        if not isinstance(pool, list):
            raise SystemExit(f"room_pools.{pool_name} is not a list")
        if room_id not in [str(value) for value in pool]:
            pool.append(room_id)

    if args.dry_run:
        print("dry-run ok")
        return 0

    write_json(ROOMS_PATH, rooms_payload)
    write_json(EVENTS_PATH, events_payload)
    write_json(DECKS_PATH, decks_payload)
    print("applied story pilot patch")
    return 0


def cmd_validate_events(args: argparse.Namespace) -> int:
    errors = events_file_errors(strict_actions=args.strict_actions)
    if args.strict_tradeoffs:
        for finding in room_tradeoff_findings():
            errors.append(f"{finding['location']}: {finding['issue']}")
    if not errors:
        print("ok")
        return 0
    for error in errors:
        print(error, file=sys.stderr)
    return 1


def cmd_audit_tradeoffs(args: argparse.Namespace) -> int:
    findings = room_tradeoff_findings()
    if args.json:
        print(json.dumps({"findings": findings}, indent=2, ensure_ascii=False))
        return 1 if findings and args.fail_on_findings else 0
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
    return 1 if args.fail_on_findings else 0


def cmd_audit_depth(args: argparse.Namespace) -> int:
    findings = room_depth_findings(mode=args.mode)
    if args.json:
        print(json.dumps({"findings": findings}, indent=2, ensure_ascii=False))
        return 1 if findings and args.fail_on_findings else 0
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
    return 1 if args.fail_on_findings else 0


def cmd_audit_story(args: argparse.Namespace) -> int:
    findings = room_story_findings()
    if args.json:
        print(json.dumps({"findings": findings}, indent=2, ensure_ascii=False))
        return 1 if findings and args.fail_on_findings else 0
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
    return 1 if args.fail_on_findings else 0


def cmd_audit_writing(args: argparse.Namespace) -> int:
    findings = event_writing_findings(mode=args.mode, playtest_slice=args.playtest_slice)
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
    return 1 if args.fail_on_findings else 0


def cmd_audit_accessibility(args: argparse.Namespace) -> int:
    findings = event_accessibility_findings()
    if args.json:
        print(json.dumps({"findings": findings}, indent=2, ensure_ascii=False))
        return 1 if findings and args.fail_on_findings else 0
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
    return 1 if args.fail_on_findings else 0


def cmd_apply(args: argparse.Namespace) -> int:
    patch_path = Path(args.patch)
    patch = load_patch(patch_path)
    enrich_patch_voice_aliases(patch)
    errors = validation_errors(
        patch,
        allow_new_actions=args.allow_new_actions,
        strict_tradeoffs=args.strict_tradeoffs,
        strict_scenario_contract=args.strict_scenario_contract,
    )
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
    special_events_payload = events_payload.setdefault("special_events", {})
    applied_special_events = 0
    for event in patch.get("special_events", []) or []:
        if isinstance(event, dict) and event.get("id"):
            special_events_payload[str(event["id"])] = event
            applied_special_events += 1

    rooms_payload = load_json(ROOMS_PATH)
    room_updates = patch.get("room_updates", [])
    applied_room_updates = 0
    if isinstance(room_updates, list) and room_updates:
        rooms = rooms_payload.get("rooms", [])
        rooms_by_id = {
            str(room.get("id", "")): room
            for room in rooms
            if isinstance(room, dict) and room.get("id")
        }
        for item in room_updates:
            if not isinstance(item, dict):
                continue
            room_id = str(item.get("room_id", ""))
            update = item.get("update", {})
            room = rooms_by_id.get(room_id)
            if isinstance(room, dict) and isinstance(update, dict):
                room.update(update)
                applied_room_updates += 1

    if args.dry_run:
        print("dry-run ok")
        return 0

    write_json(EVENTS_PATH, events_payload)
    if applied_room_updates:
        write_json(ROOMS_PATH, rooms_payload)
    print(f"applied {len(patch['events'])} event(s), {applied_special_events} special event(s), and {applied_room_updates} room update(s)")
    return 0


def cmd_backfill_voice_aliases(args: argparse.Namespace) -> int:
    payload = load_json(EVENTS_PATH)
    before = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    enrich_events_payload_voice_aliases(payload)
    after = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    if before == after:
        print("ok")
        return 0
    if args.dry_run:
        print("voice aliases need backfill")
        return 0
    write_json(EVENTS_PATH, payload)
    print("backfilled voice aliases in events.json")
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
        "blind_read_summary": critique.get("blind_read_summary", ""),
        "fun_score": critique.get("fun_score"),
        "first_time_player_score": critique.get("first_time_player_score"),
        "build_score": critique.get("build_score"),
        "sequence_cohesion_score": critique.get("sequence_cohesion_score"),
        "organism_pressure_score": critique.get("organism_pressure_score"),
        "core_loop_diagnosis": critique.get("core_loop_diagnosis", ""),
        "blind_text_findings": critique.get("blind_text_findings", [])[:6],
        "choice_progression_findings": critique.get("choice_progression_findings", [])[:6],
        "payoff_gaps": critique.get("payoff_gaps", [])[:6],
        "not_fun_findings": critique.get("not_fun_findings", [])[:6],
        "organism_director_findings": critique.get("organism_director_findings", []),
        "decision_loop_rewrites": critique.get("decision_loop_rewrites", []),
        "ending_pressure_plan": critique.get("ending_pressure_plan", []),
        "content_priorities": critique.get("content_priorities", []),
        "system_priorities": critique.get("system_priorities", []),
        "minimum_game_shape": critique.get("minimum_game_shape", []),
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


def cmd_remember_accessibility(args: argparse.Namespace) -> int:
    critique = load_json(Path(args.critique))
    record = {
        "timestamp": dt.datetime.now(dt.UTC).isoformat(),
        "summary": critique.get("summary", ""),
        "eyes_free_score": critique.get("eyes_free_score"),
        "commandability_score": critique.get("commandability_score"),
        "tts_score": critique.get("tts_score"),
        "critical_findings": critique.get("critical_findings", [])[:8],
        "command_parser_findings": critique.get("command_parser_findings", [])[:8],
        "tts_findings": critique.get("tts_findings", [])[:8],
        "schema_recommendations": critique.get("schema_recommendations", []),
        "command_alias_plan": critique.get("command_alias_plan", []),
        "state_readout_plan": critique.get("state_readout_plan", []),
        "testing_plan": critique.get("testing_plan", []),
        "guide_updates": critique.get("guide_updates", []),
        "next_accessibility_prompt": critique.get("next_accessibility_prompt", ""),
        "notes": args.notes or "",
    }
    append_jsonl(ACCESSIBILITY_MEMORY_PATH, record)
    print("remembered accessibility guidance")
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


def cmd_remember_story_architecture(args: argparse.Namespace) -> int:
    architecture = load_json(Path(args.architecture))
    record = {
        "timestamp": dt.datetime.now(dt.UTC).isoformat(),
        "summary": architecture.get("summary", ""),
        "story_diagnosis": architecture.get("story_diagnosis", ""),
        "missing_story_primitives": architecture.get("missing_story_primitives", []),
        "character_arcs": architecture.get("character_arcs", [])[:6],
        "first_15_minute_spine": architecture.get("first_15_minute_spine", []),
        "followup_encounter_plan": architecture.get("followup_encounter_plan", [])[:10],
        "pilot_arc_recommendation": architecture.get("pilot_arc_recommendation", {}),
        "story_rules": architecture.get("story_rules", []),
        "patch_strategy": architecture.get("patch_strategy", []),
        "next_story_prompt": architecture.get("next_story_prompt", ""),
        "notes": args.notes or "",
    }
    append_jsonl(STORY_ARCHITECTURE_MEMORY_PATH, record)
    print("remembered story architecture guidance")
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


def cmd_accessibility_context(_: argparse.Namespace) -> int:
    print(json.dumps(accessibility_context(), indent=2, ensure_ascii=False))
    return 0


def cmd_lore_brainstorm_context(_: argparse.Namespace) -> int:
    print(json.dumps(lore_brainstorm_context(), indent=2, ensure_ascii=False))
    return 0


def cmd_story_architect_context(_: argparse.Namespace) -> int:
    print(json.dumps(story_architect_context(), indent=2, ensure_ascii=False))
    return 0


def cmd_vibe(_: argparse.Namespace) -> int:
    print(load_vibe_guide())
    return 0


def cmd_lore_guide(_: argparse.Namespace) -> int:
    print(load_lore_guide())
    return 0


def cmd_setting_backbone(_: argparse.Namespace) -> int:
    print(load_setting_backbone())
    return 0


def cmd_story_room_contract(_: argparse.Namespace) -> int:
    print(load_story_room_contract())
    return 0


def cmd_ending_maze(_: argparse.Namespace) -> int:
    print(load_ending_maze_architecture())
    return 0


def cmd_hymn_corpus_voice(_: argparse.Namespace) -> int:
    print(load_hymn_corpus_voice())
    return 0


def cmd_content_authorship(_: argparse.Namespace) -> int:
    print(load_content_authorship_workflow())
    return 0


def cmd_accessibility_guide(_: argparse.Namespace) -> int:
    print(load_accessibility_guide())
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
    generate.add_argument("--strict-tradeoffs", action="store_true", help="Require every non-transition room event in the patch to have at least two commandable buttons.")
    generate.add_argument("--source-seeds", help="Optional Fleshpunk seed JSON path. Defaults to generated/corpus/fleshpunk_seeds.json when any source filter is used.")
    generate.add_argument("--source-seed", action="append", help="Specific source seed id to include. Repeatable.")
    generate.add_argument("--source-work", help="Filter source seeds by source_id.")
    generate.add_argument("--source-motif", help="Filter source seeds by motif_id.")
    generate.add_argument("--source-seed-count", type=int, default=3, help="Maximum number of source seeds to include in the generation context.")
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

    fun_critique = sub.add_parser("fun-critique", help="Critique blind first-time fun, build, choice progression, and organism pressure.")
    fun_critique.add_argument("--focus", default="Critique blind first-time user-facing text and choices, whether rooms build into a run, organism pressure, repeated-choice consequences, ending gravity, and stat-only choices.")
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

    accessibility_critique = sub.add_parser("accessibility-critique", help="Critique eyes-free playability, commandability, and TTS/audio UX.")
    accessibility_critique.add_argument("--focus", default="Critique eyes-free playability, command aliases, TTS phrasing, state readouts, and audio-only clarity.")
    accessibility_critique.add_argument("--out", help="Output accessibility critique JSON path.")
    accessibility_critique.add_argument("--model", default=DEFAULT_MODEL)
    accessibility_critique.add_argument("--mock", action="store_true", help="Generate a local sample without calling OpenAI.")
    accessibility_critique.set_defaults(func=cmd_accessibility_critique)

    lore_brainstorm = sub.add_parser("lore-brainstorm", help="Brainstorm lore concepts with reveal boundaries and gameplay hooks.")
    lore_brainstorm.add_argument("--focus", default="Brainstorm factions, recurring characters, relationships, lore fragments, reveal paths, and gameplay hooks.")
    lore_brainstorm.add_argument("--count", type=int, default=6, help="Approximate number of concepts to request per major section.")
    lore_brainstorm.add_argument("--out", help="Output lore brainstorm JSON path.")
    lore_brainstorm.add_argument("--model", default=DEFAULT_MODEL)
    lore_brainstorm.add_argument("--mock", action="store_true", help="Generate a local sample without calling OpenAI.")
    lore_brainstorm.set_defaults(func=cmd_lore_brainstorm)

    story_architect = sub.add_parser("story-architect", help="Plan playable character arcs and follow-up encounter story structure from current repo data.")
    story_architect.add_argument("--focus", default="Plan the smallest character-driven story spine that turns the current room/event stack from strong vibe into a playable story with recurring characters, follow-up scenes, escalation, and payoff.")
    story_architect.add_argument("--out", help="Output story architecture JSON path.")
    story_architect.add_argument("--model", default=DEFAULT_MODEL)
    story_architect.add_argument("--mock", action="store_true", help="Generate a local sample without calling OpenAI.")
    story_architect.set_defaults(func=cmd_story_architect)

    story_pilot = sub.add_parser("story-pilot", help="Generate an OpenAI-authored story pilot patch from story architecture guidance.")
    story_pilot.add_argument("--focus", default="Generate the five-scene pilot story patch recommended by the story architect. Use existing queued special event IDs where possible, add state_overrides to current room events, and keep required_engine_changes empty unless absolutely necessary.")
    story_pilot.add_argument("--out", help="Output story pilot patch JSON path.")
    story_pilot.add_argument("--model", default=DEFAULT_MODEL)
    story_pilot.add_argument("--minimal-context", action="store_true", help="Send only current playtest-slice text and writing findings for small repair passes.")
    story_pilot.add_argument("--cold-read-context", action="store_true", help="Send only current screen text and choice labels for true cold-reader passes.")
    story_pilot.add_argument("--mock", action="store_true", help="Generate a local sample without calling OpenAI.")
    story_pilot.set_defaults(func=cmd_story_pilot)

    validate = sub.add_parser("validate", help="Validate a scenario patch.")
    validate.add_argument("patch")
    validate.add_argument("--allow-new-actions", action="store_true")
    validate.add_argument("--strict-tradeoffs", action="store_true", help="Require every non-transition room event in the patch to have at least two commandable buttons.")
    validate.add_argument("--strict-scenario-contract", action="store_true", help="Require new scenario metadata: character_change, possibility_tree, research influence, scenario_design_notes, and multi-use mutation hooks.")
    validate.set_defaults(func=cmd_validate)

    validate_events = sub.add_parser("validate-events", help="Validate events.json against broad categories.")
    validate_events.add_argument("--strict-actions", action="store_true")
    validate_events.add_argument("--strict-tradeoffs", action="store_true", help="Fail when room events have fewer than two commandable buttons, except transition events.")
    validate_events.set_defaults(func=cmd_validate_events)

    audit_writing = sub.add_parser("audit-writing", help="Audit events.json for weak cause/effect, generic buttons, and voice drift.")
    audit_writing.add_argument("--json", action="store_true", help="Print JSON findings.")
    audit_writing.add_argument("--mode", choices=["migration", "strict"], default="migration", help="Migration groups known legacy metadata debt; strict reports every new-contract gap.")
    audit_writing.add_argument("--playtest-slice", action="store_true", help="Only audit rooms/events visible in the current playtest slice.")
    audit_writing.add_argument("--fail-on-findings", action="store_true", help="Exit nonzero when writing findings are present.")
    audit_writing.set_defaults(func=cmd_audit_writing)

    audit_accessibility = sub.add_parser("audit-accessibility", help="Audit events.json for eyes-free commandability and TTS risks.")
    audit_accessibility.add_argument("--json", action="store_true", help="Print JSON findings.")
    audit_accessibility.add_argument("--fail-on-findings", action="store_true", help="Exit nonzero when accessibility findings are present.")
    audit_accessibility.set_defaults(func=cmd_audit_accessibility)

    audit_tradeoffs = sub.add_parser("audit-tradeoffs", help="Audit room events for one-button dead ends and missing tradeoffs.")
    audit_tradeoffs.add_argument("--json", action="store_true", help="Print JSON findings.")
    audit_tradeoffs.add_argument("--fail-on-findings", action="store_true", help="Exit nonzero when tradeoff findings are present.")
    audit_tradeoffs.set_defaults(func=cmd_audit_tradeoffs)

    audit_depth = sub.add_parser("audit-depth", help="Audit room depth, delayed consequence, memory hooks, and interactable actors.")
    audit_depth.add_argument("--json", action="store_true", help="Print JSON findings.")
    audit_depth.add_argument("--mode", choices=["migration", "strict"], default="migration", help="Migration groups known legacy metadata debt; strict reports every new-contract gap.")
    audit_depth.add_argument("--fail-on-findings", action="store_true", help="Exit nonzero when depth findings are present.")
    audit_depth.set_defaults(func=cmd_audit_depth)

    audit_story = sub.add_parser("audit-story", help="Audit rooms for setting backbone, faction, character, animal infrastructure, and cross-run story motion.")
    audit_story.add_argument("--json", action="store_true", help="Print JSON findings.")
    audit_story.add_argument("--fail-on-findings", action="store_true", help="Exit nonzero when story findings are present.")
    audit_story.set_defaults(func=cmd_audit_story)

    apply = sub.add_parser("apply", help="Apply a valid JSON-only scenario patch.")
    apply.add_argument("patch")
    apply.add_argument("--allow-new-actions", action="store_true")
    apply.add_argument("--strict-tradeoffs", action="store_true", help="Require every non-transition room event in the patch to have at least two commandable buttons.")
    apply.add_argument("--strict-scenario-contract", action="store_true", help="Require new scenario metadata before applying the patch.")
    apply.add_argument("--dry-run", action="store_true")
    apply.set_defaults(func=cmd_apply)

    apply_story_pilot = sub.add_parser("apply-story-pilot", help="Apply a story pilot patch with special_events and room_event_updates.")
    apply_story_pilot.add_argument("patch")
    apply_story_pilot.add_argument("--dry-run", action="store_true")
    apply_story_pilot.set_defaults(func=cmd_apply_story_pilot)

    backfill_aliases = sub.add_parser("backfill-voice-aliases", help="Rebuild voice_aliases across the current events.json deck.")
    backfill_aliases.add_argument("--dry-run", action="store_true", help="Check whether backfill would change events.json without writing.")
    backfill_aliases.set_defaults(func=cmd_backfill_voice_aliases)

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

    remember_accessibility = sub.add_parser("remember-accessibility", help="Store accessibility critique guidance for future generation.")
    remember_accessibility.add_argument("critique")
    remember_accessibility.add_argument("--notes", default="")
    remember_accessibility.set_defaults(func=cmd_remember_accessibility)

    remember_lore_brainstorm = sub.add_parser("remember-lore-brainstorm", help="Store lore brainstorm guidance for future generation.")
    remember_lore_brainstorm.add_argument("brainstorm")
    remember_lore_brainstorm.add_argument("--notes", default="")
    remember_lore_brainstorm.set_defaults(func=cmd_remember_lore_brainstorm)

    remember_story_architecture = sub.add_parser("remember-story-architecture", help="Store story architecture guidance for future generation.")
    remember_story_architecture.add_argument("architecture")
    remember_story_architecture.add_argument("--notes", default="")
    remember_story_architecture.set_defaults(func=cmd_remember_story_architecture)

    context = sub.add_parser("context", help="Print compact game context.")
    context.set_defaults(func=cmd_context)

    balance_context_parser = sub.add_parser("balance-context", help="Print balance levers and run-feel context.")
    balance_context_parser.set_defaults(func=cmd_balance_context)

    fun_context_parser = sub.add_parser("fun-context", help="Print fun-factor and organism pressure context.")
    fun_context_parser.set_defaults(func=cmd_fun_context)

    lore_context_parser = sub.add_parser("lore-context", help="Print lore continuity and voice context.")
    lore_context_parser.set_defaults(func=cmd_lore_context)

    accessibility_context_parser = sub.add_parser("accessibility-context", help="Print eyes-free playability and commandability context.")
    accessibility_context_parser.set_defaults(func=cmd_accessibility_context)

    lore_brainstorm_context_parser = sub.add_parser("lore-brainstorm-context", help="Print lore brainstorm context.")
    lore_brainstorm_context_parser.set_defaults(func=cmd_lore_brainstorm_context)

    story_architect_context_parser = sub.add_parser("story-architect-context", help="Print story architecture packet context.")
    story_architect_context_parser.set_defaults(func=cmd_story_architect_context)

    vibe = sub.add_parser("vibe", help="Print the vibe and design guide.")
    vibe.set_defaults(func=cmd_vibe)

    lore_guide = sub.add_parser("lore-guide", help="Print the lore guide.")
    lore_guide.set_defaults(func=cmd_lore_guide)

    setting_backbone = sub.add_parser("setting-backbone", help="Print the setting backbone.")
    setting_backbone.set_defaults(func=cmd_setting_backbone)

    story_room_contract = sub.add_parser("story-room-contract", help="Print the story room contract.")
    story_room_contract.set_defaults(func=cmd_story_room_contract)

    ending_maze = sub.add_parser("ending-maze", help="Print the ending maze architecture.")
    ending_maze.set_defaults(func=cmd_ending_maze)

    hymn_corpus_voice = sub.add_parser("hymn-corpus-voice", help="Print the Hymn corpus voice guide.")
    hymn_corpus_voice.set_defaults(func=cmd_hymn_corpus_voice)

    content_authorship = sub.add_parser("content-authorship", help="Print the content authorship workflow.")
    content_authorship.set_defaults(func=cmd_content_authorship)

    accessibility_guide = sub.add_parser("accessibility-guide", help="Print the accessibility guide.")
    accessibility_guide.set_defaults(func=cmd_accessibility_guide)

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
