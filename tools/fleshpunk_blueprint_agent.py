#!/usr/bin/env python3
"""Generate compact Fleshpunk scenario blueprints with Claude."""

from __future__ import annotations

import argparse
import http.client
import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import fleshpunk_blueprint_compiler as compiler


ROOT = Path(__file__).resolve().parents[1]
MEMORY_DIR = ROOT / ".agent-memory"
GENERATED_DIR = ROOT / "generated"
ROOMS_PATH = ROOT / "rooms_post_update.json"
EVENTS_PATH = ROOT / "events_post_update.json"
PULP_INDEX_PATH = GENERATED_DIR / "corpus" / "pulp_pre_1930" / "retrieval_index.md"
MUTATIONS_PATH = ROOT / "mutations.json"
SYMBIOTES_PATH = ROOT / "symbiotes.json"
BODY_OPTION_CONTRACT_PATH = MEMORY_DIR / "body_option_contract.md"
GLUE_LAYER_CONTRACT_PATH = MEMORY_DIR / "glue_layer_contract.md"
DEFAULT_MODEL = os.environ.get("FLESHPUNK_BLUEPRINT_MODEL", "claude-sonnet-4-6")


def read_text(path: Path, default: str = "") -> str:
    if not path.exists():
        return default
    return path.read_text(encoding="utf-8")


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


def compact_text(text: str, max_chars: int) -> str:
    value = re.sub(r"\s+", " ", text).strip()
    if len(value) <= max_chars:
        return value
    return value[: max_chars - 1].rstrip() + "..."


def estimate_tokens(text: str) -> int:
    return max(1, (len(text) + 3) // 4)


def env_value(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if value:
        return value
    home = Path.home()
    for path in (home / ".secrets" / "anthropic.env", home / ".bashrc", home / ".profile"):
        text = read_text(path)
        if not text:
            continue
        match = re.search(rf"^\s*(?:export\s+)?{re.escape(name)}=(['\"]?)(.*?)\1\s*$", text, re.MULTILINE)
        if match:
            return match.group(2).strip()
    return ""


def target_room_context(room_id: str) -> dict[str, Any]:
    rooms = load_json(ROOMS_PATH)
    events = load_json(EVENTS_PATH)
    room = next((room for room in rooms.get("rooms", []) if isinstance(room, dict) and room.get("id") == room_id), {})
    if not room:
        raise SystemExit(f"Unknown room_id: {room_id}")
    room_summary_keys = (
        "id",
        "name",
        "room_role",
        "description",
        "first_visit_description",
        "instance_premise",
        "return_description",
    )
    room_summary = {
        key: compact_text(str(room.get(key, "")), 500)
        for key in room_summary_keys
        if room.get(key)
    }
    anchors = room.get("corpus_anchors", [])
    if isinstance(anchors, list):
        room_summary["existing_anchor_ids"] = [
            {
                "source_id": anchor.get("source_id", ""),
                "source_title": anchor.get("source_title", ""),
            }
            for anchor in anchors[:4]
            if isinstance(anchor, dict)
        ]
    compact_events = []
    for event in events.get("room_events", {}).get(room_id, []):
        if not isinstance(event, dict):
            continue
        buttons = event.get("buttons", [])
        compact_events.append({
            "id": event.get("id", ""),
            "type": event.get("type", ""),
            "line_1": compact_text(str(event.get("line_1", "")), 220),
            "line_2": compact_text(str(event.get("line_2", "")), 220),
            "buttons": [
                {"label": button.get("label", ""), "action": button.get("action", "")}
                for button in buttons[:4]
                if isinstance(button, dict)
            ] if isinstance(buttons, list) else [],
        })
    return {
        "room": room_summary,
        "room_events": compact_events,
    }


def compact_project_context() -> dict[str, Any]:
    return {
        "project": "Fleshpunk: Inner Heart",
        "core_thesis": "A martial evolution simulator inside a hostile biomechanical world.",
        "scenario_rules": [
            "Use Revelation-scale scenario size: premise, pressure, choice, result, future implication.",
            "Tier-0 corpus anchors are room foundation, not flavor.",
            "Prefer the newer pre-1930 pulp/research stack for anchors. Do not use the old Verne/Lovecraft seed set unless the user explicitly asks for it or the room truly requires procedure/evidence pressure.",
            "Each scenario enriches Hymn, destabilizes Hymn, or both.",
            "Fleshpunk is martial progression fantasy: rooms pressure Hymn's current body, then remember what kind of fighter/body she becomes.",
            "Declare primary_pressure, body_path_pressure, avoidance_route, and recognition_effect. Use hunt_pressure, body_drift, baseline_discipline, wound_debt, recognition, or route_memory.",
            "Do not overuse passive observation as consequence. Avoid defaulting to the organism reading Hymn's weight, print, scent, heat, gait, profile, or trace; use active conduct, rivalry, debt, injury, bargain, route loss, witness memory, or predator adaptation instead. If a room observes Hymn, name the concrete result: changed price, route, option, hunter tactic, follow-up event, faction leverage, or pressure counter.",
            "Every scenario must preserve a playable baseline pure-body route, then add only one or two capability-tag branches where relevant.",
            "Rooms target body capability tags first, not named upgrade lists. Use tags such as cut, brace, speed, burst, quiet_movement, read_damage, identity_spoof, scent_control, barrier, decoy, anchor, and death_intercept.",
            "Mutations are reliable always-on identity. Symbiotes are stronger but less dependable living partners with needs, cooldowns, wounds, preferences, or refusal pressure.",
            "Combat is foregrounded but often avoidable. Avoidance must be a tactical, social, route, or body-cost choice, not a skip.",
            "No puzzle rooms: do not ask for correct input sequences, ritual locks, diagnostic procedures, or arcane technique tests.",
            "Player-facing text must be concrete: visible materials, pressure, body position, motion, contact, consequence.",
            "No author names, source references, risk labels, branch labels, or stat math in player-facing text.",
            "Combat should be readable physical action: posture, distance, contact, commitment, recovery, consequence.",
            "For action-combat requests, use an active opponent and immediate pressure. Do not convert martial anatomy into a sequence puzzle, ritual lock, diagnostic test, or apparatus procedure.",
            "Progression should change how Hymn moves, fights, reads rooms, mutates, or is recognized.",
            "Root scenarios leave payoff_hook metadata for separately generated follow-ups; do not author the follow-up in the same pass unless the user explicitly asks for a follow-up scenario.",
            "When wiring an already generated follow-up, use story_followups and ensure the target is concrete and playable.",
            "Glue beats are playable interventions where prior choices return with leverage: option masks, price shifts, route favors, pattern warnings, predator attention, body-path recognition, or ending pressure.",
            "Every glue beat needs a visible carrier such as a cord, receipt blister, feeder, scar mite, lens film, route packet, blood trace, symbiote twitch, or repair animal.",
        ],
        "implemented_actions": sorted(compiler.IMPLEMENTED_ACTIONS),
        "event_types": ["choice", "combat", "story", "hazard", "resource", "transition"],
        "pulp_index": compact_text(read_text(PULP_INDEX_PATH), 1000),
        "contract_excerpt": compact_text(read_text(MEMORY_DIR / "story_room_contract.md"), 1200),
        "body_option_contract_excerpt": compact_text(read_text(BODY_OPTION_CONTRACT_PATH), 1200),
        "glue_layer_contract_excerpt": compact_text(read_text(GLUE_LAYER_CONTRACT_PATH), 1200),
        "body_options": {
            "mutations": compact_text(json.dumps(load_json(MUTATIONS_PATH).get("mutations", []), ensure_ascii=False), 1800),
            "symbiotes": compact_text(json.dumps(load_json(SYMBIOTES_PATH).get("symbiotes", []), ensure_ascii=False), 1000),
        },
        "voice_excerpt": compact_text(read_text(MEMORY_DIR / "hymn_corpus_voice.md"), 600),
        "pulp_research_excerpt": compact_text(read_text(MEMORY_DIR / "fleshpunk_research_pulp_before_1930.md"), 600),
        "combat_research_excerpt": compact_text(read_text(MEMORY_DIR / "fleshpunk_research_combat_intelligence.md"), 450),
    }


def blueprint_contract() -> dict[str, Any]:
    return {
        "title": "short scenario title",
        "design_goal": "one sentence",
        "room_id": "existing room id",
        "room_role": "corpus_anchored_*",
        "instance_premise": "room foundation after tier-0 anchors",
        "first_visit_description": "Hymn field report",
        "return_description": "short return text",
        "corpus_anchors": [
            {
                "tier": 0,
                "source_id": "local source id",
                "source_title": "source title",
                "source_author": "source author",
                "source_file": "local path or research source",
                "source_locator": "line range, chapter, or section",
                "source_moment": "source move studied",
                "story_element": "what this becomes in the room foundation",
                "scenario_application": "how it shapes room/choices/results/progression",
            }
        ],
        "environment_echoes": ["later room echo"],
        "progression_state": {"early": "", "mid": "", "late": ""},
        "ending_vectors": [
            {
                "id": "ending_vector_id",
                "label": "ending vector label",
                "pulls_toward": ["visible behavior that feeds this ending"],
                "diverts_to": ["behavior that diverts from it"],
            }
        ],
        "mutation_hooks": [
            {
                "capability": "short capability tag",
                "capability_tags": ["tag_used_by_room"],
                "baseline_route": "how pure-body Hymn can still handle the scene",
                "mutation_branch": "how reliable mutation identity changes the scene, if applicable",
                "symbiote_branch": "how stronger but less dependable symbiote help changes the scene, if applicable",
                "effect": "what changes in Hymn's body",
                "in_encounter_use": "combat or encounter use",
                "out_of_encounter_use": "exploration/social/route use",
                "surprising_second_use": "later unexpected use",
            }
        ],
        "event": {
            "id": "unique event id",
            "type": "choice",
            "scenario_role": "playable pressure scene",
            "primary_pressure": "hunt_pressure | body_drift | baseline_discipline | wound_debt | recognition | route_memory",
            "body_path_pressure": "how this pressures mutation, symbiote, or pure-body discipline",
            "avoidance_route": "how combat can be avoided or converted into another cost",
            "recognition_effect": "who or what actively responds to Hymn's conduct; avoid passive weight/print/scent/heat/profile reads unless essential",
            "environment_id": "room environment id",
            "infrastructure_actor": "actor/system",
            "line_1": "player-facing setup",
            "line_2": "player-facing pressure",
            "choices": [
                {
                    "label": "button label",
                    "action": "implemented action id",
                    "preview": "short design preview, not player text",
                    "result_lines": ["player-facing result line", "player-facing result line"],
                    "environment_state_changes": ["state_key"],
                    "pressure_axis_changes": ["hunt_pressure"],
                    "actor_state_changes": [],
                    "payoff_hook": {
                        "hook_id": "unique_hook_id",
                        "source_action": "same action id",
                        "payoff_type": "playable_escalation | route_change | rival_pressure | price_shift | option_mask | hunter_adaptation",
                        "promise": "what this branch promises the player will matter later",
                        "suggested_room_id": "likely room id or environment family",
                        "followup_pressure": "new pressure the separate follow-up should introduce",
                        "generation_prompt": "compact prompt for the future follow-up scenario pass"
                    },
                }
            ],
            "character_change": "both",
            "possibility_tree": ["designer branch", "designer branch"],
            "progression_vector": "what Hymn gains/risks/becomes",
        },
        "special_events": [],
        "required_engine_changes": [],
        "inspiration_notes": [],
        "self_critique": [],
    }


def build_prompt(args: argparse.Namespace) -> tuple[str, str]:
    system = "\n".join(
        [
            "You are a senior narrative systems writer for Fleshpunk: Inner Heart.",
            "Return exactly one JSON object. No markdown. No commentary.",
            "Write a compact blueprint only; a deterministic compiler will create the final Godot patch.",
            "Start from tier-0 corpus anchors, then room pressure, then playable event.",
            "Default to the newer pulp/research corpus. Avoid the old Verne/Lovecraft seed set unless explicitly requested or uniquely necessary.",
            "If a corpus anchor can be removed without changing the premise, choices, and consequences, the blueprint fails.",
            "Use only implemented actions unless the user explicitly allows new actions.",
            "Do not put source names, author names, risk labels, branch labels, or stat math in player-facing text.",
            "Make the scenario understandable to a first-time player.",
            "If the request asks for action combat, the root event must start with an active threat, readable spacing, and choices that are tactics under pressure.",
            "Avoid passive biometric follow-through: no more default weight/print/scent/heat/profile reads unless the request specifically calls for that mechanism.",
            "Use at least two choices and at least one payoff_hook that can seed a separate follow-up generation pass.",
            "A payoff_hook is not player-facing text. It must name the promised later pressure, the source action, the likely room/family, and a compact generation prompt for the next pass.",
            "Only include special_events/story_followups in this blueprint when the user explicitly requests the follow-up scenario itself or asks to wire an existing generated follow-up.",
            "Keep line_1 and line_2 no more than 32 words each.",
        ]
    )
    user = {
        "request": args.prompt,
        "target_room": args.room,
        "allow_new_actions": False,
        "context": compact_project_context(),
        "target_room_context": target_room_context(args.room),
        "blueprint_contract": blueprint_contract(),
    }
    return system, json.dumps(user, indent=2, ensure_ascii=False)


def extract_json(text: str) -> dict[str, Any]:
	stripped = text.strip()
	if stripped.startswith("```"):
		stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
		stripped = re.sub(r"\s*```$", "", stripped)
	start = stripped.find("{")
	if start == -1:
		raise SystemExit(f"Model did not return JSON:\n{text[:1200]}")
	try:
		payload, end = json.JSONDecoder().raw_decode(stripped[start:])
	except json.JSONDecodeError as exc:
		debug_path = GENERATED_DIR / "last_invalid_fleshpunk_blueprint_response.txt"
		debug_path.write_text(text, encoding="utf-8")
		raise SystemExit(f"Model did not return parseable JSON; response saved to {debug_path}: {exc}") from exc
	trailing = stripped[start + end:].strip()
	if trailing:
		debug_path = GENERATED_DIR / "last_extra_fleshpunk_blueprint_response.txt"
		debug_path.write_text(text, encoding="utf-8")
	if not isinstance(payload, dict):
		raise SystemExit("Blueprint root must be an object")
	return payload


def decode_stream(response: Any) -> dict[str, Any]:
    text_parts: list[str] = []
    stop_reason = ""
    for raw_line in response:
        line = raw_line.decode("utf-8", errors="replace").strip()
        if not line or not line.startswith("data:"):
            continue
        data = line.removeprefix("data:").strip()
        if data == "[DONE]":
            break
        try:
            event = json.loads(data)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "error":
            raise SystemExit(f"Anthropic stream error: {json.dumps(event.get('error', event), ensure_ascii=False)}")
        if event.get("type") == "message_delta":
            delta = event.get("delta", {})
            if isinstance(delta, dict):
                stop_reason = str(delta.get("stop_reason", "") or stop_reason)
        if event.get("type") == "content_block_delta":
            delta = event.get("delta", {})
            if isinstance(delta, dict) and delta.get("type") == "text_delta":
                text_parts.append(str(delta.get("text", "")))
    text = "".join(text_parts)
    if stop_reason == "max_tokens":
        debug_path = GENERATED_DIR / "last_invalid_fleshpunk_blueprint_response.txt"
        debug_path.write_text(text, encoding="utf-8")
        raise SystemExit(f"Anthropic stopped at max_tokens; partial saved to {debug_path}")
    return extract_json(text)


def call_anthropic(system: str, user: str, model: str, max_output_tokens: int) -> dict[str, Any]:
    api_key = env_value("ANTHROPIC_API_KEY")
    if not api_key:
        raise SystemExit("ANTHROPIC_API_KEY is not set.")
    payload = {
        "model": model,
        "max_tokens": max_output_tokens,
        "temperature": 0.2,
        "stream": True,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=data,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "fleshpunk-blueprint-agent/1.0",
            "Connection": "close",
        },
        method="POST",
    )
    attempts = int(os.environ.get("FLESHPUNK_BLUEPRINT_API_ATTEMPTS", "2"))
    timeout = int(os.environ.get("FLESHPUNK_BLUEPRINT_API_TIMEOUT", "180"))
    errors: list[str] = []
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return decode_stream(response)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise SystemExit(f"Anthropic API error {exc.code}: {body}") from exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, http.client.HTTPException) as exc:
            errors.append(f"attempt {attempt}: {exc}")
            if attempt < attempts:
                time.sleep(min(2 ** attempt, 6))
    raise SystemExit("Anthropic API connection failed:\n" + "\n".join(errors))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--room", required=True)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--max-input-tokens", type=int, default=7000)
    parser.add_argument("--max-output-tokens", type=int, default=7000)
    parser.add_argument("--out", default="generated/fleshpunk_blueprint.json")
    parser.add_argument("--compile-out")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--print-prompt", action="store_true")
    args = parser.parse_args()

    system, user = build_prompt(args)
    prompt_text = system + "\n" + user
    budget = {
        "model": args.model,
        "estimated_input_tokens": estimate_tokens(prompt_text),
        "input_bytes": len(prompt_text.encode("utf-8")),
        "max_input_tokens": args.max_input_tokens,
        "max_output_tokens": args.max_output_tokens,
    }
    print(json.dumps(budget, indent=2))
    if args.print_prompt:
        print(user)
    if budget["estimated_input_tokens"] > args.max_input_tokens:
        raise SystemExit(f"prompt budget exceeded: estimated {budget['estimated_input_tokens']} tokens > {args.max_input_tokens}")
    if args.dry_run:
        return 0

    blueprint = call_anthropic(system, user, args.model, args.max_output_tokens)
    errors = compiler.validate_blueprint(blueprint)
    if errors:
        blueprint["_validation_errors"] = errors
    out = Path(args.out)
    if not out.is_absolute():
        out = ROOT / out
    write_json(out, blueprint)
    print(out)
    if errors:
        for error in errors:
            print(error)
        return 2
    if args.compile_out:
        compiled = compiler.compile_patch(blueprint)
        compile_out = Path(args.compile_out)
        if not compile_out.is_absolute():
            compile_out = ROOT / compile_out
        write_json(compile_out, compiled)
        print(compile_out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
