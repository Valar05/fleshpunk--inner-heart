#!/usr/bin/env python3
"""Validate Fleshpunk mutation and symbiote body-option metadata."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MUTATIONS_PATH = ROOT / "mutations.json"
SYMBIOTES_PATH = ROOT / "symbiotes.json"

MUTATION_REQUIRED = (
    "id",
    "name",
    "body_option_type",
    "reliability_model",
    "capability_tags",
    "tradeoff_axes",
    "branch_role",
    "weakness",
    "in_encounter_use",
    "out_of_encounter_use",
    "surprising_second_use",
    "progression_identity",
)

SYMBIOTE_REQUIRED = (
    "id",
    "name",
    "body_option_type",
    "reliability_model",
    "capability_tags",
    "tradeoff_axes",
    "in_encounter_use",
    "out_of_encounter_use",
    "sapience_hint",
    "need",
    "relationship_pressure",
    "failure_modes",
)

KNOWN_TAGS = {
    "anchor",
    "bargain_hunger",
    "barrier",
    "baseline_discipline",
    "brace",
    "burst",
    "calm_weak_life",
    "contact_punish",
    "contamination",
    "cut",
    "death_intercept",
    "decoy",
    "digest_unsafe",
    "identity_spoof",
    "quiet_movement",
    "read_damage",
    "scent_control",
    "seal_wound",
    "speed",
}

KNOWN_AXES = {
    "baseline_discipline",
    "body_drift",
    "hunt_pressure",
    "recognition",
    "route_memory",
    "wound_debt",
}


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected JSON object")
    return payload


def non_empty(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return bool(value)
    return value is not None


def audit_record(record: dict[str, Any], required: tuple[str, ...], expected_type: str, location: str) -> list[str]:
    errors: list[str] = []
    for key in required:
        if not non_empty(record.get(key)):
            errors.append(f"{location}: missing {key}")
    if record.get("body_option_type") != expected_type:
        errors.append(f"{location}: body_option_type must be {expected_type}")

    tags = record.get("capability_tags", [])
    if not isinstance(tags, list) or not all(isinstance(tag, str) and tag for tag in tags):
        errors.append(f"{location}: capability_tags must be a non-empty string list")
    else:
        unknown = sorted(set(tags) - KNOWN_TAGS)
        if unknown:
            errors.append(f"{location}: unknown capability tags: {', '.join(unknown)}")

    axes = record.get("tradeoff_axes", [])
    if not isinstance(axes, list) or not all(isinstance(axis, str) and axis for axis in axes):
        errors.append(f"{location}: tradeoff_axes must be a non-empty string list")
    else:
        unknown = sorted(set(axes) - KNOWN_AXES)
        if unknown:
            errors.append(f"{location}: unknown tradeoff axes: {', '.join(unknown)}")

    if expected_type == "symbiote":
        failure_modes = record.get("failure_modes", [])
        if not isinstance(failure_modes, list) or len(failure_modes) < 2:
            errors.append(f"{location}: failure_modes should name at least two limits")
    return errors


def main() -> int:
    errors: list[str] = []
    mutations = load_json(MUTATIONS_PATH).get("mutations", [])
    symbiotes = load_json(SYMBIOTES_PATH).get("symbiotes", [])
    if not isinstance(mutations, list) or not mutations:
        errors.append("mutations.json: mutations must be a non-empty list")
    else:
        for index, mutation in enumerate(mutations):
            if not isinstance(mutation, dict):
                errors.append(f"mutations[{index}]: expected object")
                continue
            errors.extend(audit_record(mutation, MUTATION_REQUIRED, "mutation", f"mutations.{mutation.get('id', index)}"))

    if not isinstance(symbiotes, list) or not symbiotes:
        errors.append("symbiotes.json: symbiotes must be a non-empty list")
    else:
        for index, symbiote in enumerate(symbiotes):
            if not isinstance(symbiote, dict):
                errors.append(f"symbiotes[{index}]: expected object")
                continue
            errors.extend(audit_record(symbiote, SYMBIOTE_REQUIRED, "symbiote", f"symbiotes.{symbiote.get('id', index)}"))

    if errors:
        for error in errors:
            print(error)
        return 1
    print(f"body option audit passed: {len(mutations)} mutations, {len(symbiotes)} symbiotes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
