#!/usr/bin/env python3
"""Apply a reviewed one-room migration candidate to active post-update data."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ROOMS_PATH = ROOT / "rooms_post_update.json"
EVENTS_PATH = ROOT / "events_post_update.json"
DECKS_PATH = ROOT / "encounter_decks_post_update.json"


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


def replace_room(rooms_payload: dict[str, Any], room: dict[str, Any]) -> str:
    room_id = str(room.get("id", ""))
    if not room_id:
        raise ValueError("candidate new_room requires id")
    rooms = rooms_payload.setdefault("rooms", [])
    if not isinstance(rooms, list):
        raise ValueError("rooms_post_update.json rooms must be a list")
    for index, existing in enumerate(rooms):
        if isinstance(existing, dict) and existing.get("id") == room_id:
            rooms[index] = room
            return "replaced"
    rooms.append(room)
    return "added"


def replace_room_events(events_payload: dict[str, Any], room_id: str, events: list[Any]) -> None:
    room_events = events_payload.setdefault("room_events", {})
    if not isinstance(room_events, dict):
        raise ValueError("events_post_update.json room_events must be an object")
    clean_events = [event for event in events if isinstance(event, dict)]
    if len(clean_events) != len(events):
        raise ValueError("candidate events must all be objects")
    room_events[room_id] = clean_events


def merge_special_events(events_payload: dict[str, Any], special_events: dict[str, Any]) -> int:
    if not special_events:
        return 0
    active_special = events_payload.setdefault("special_events", {})
    if not isinstance(active_special, dict):
        raise ValueError("events_post_update.json special_events must be an object")
    for event_id, event in special_events.items():
        if not isinstance(event, dict):
            raise ValueError(f"special event {event_id} must be an object")
        active_special[event_id] = event
    return len(special_events)


def update_deck_pools(decks_payload: dict[str, Any], room_id: str, deck_pools: list[Any]) -> list[str]:
    room_pools = decks_payload.setdefault("room_pools", {})
    if not isinstance(room_pools, dict):
        raise ValueError("encounter_decks_post_update.json room_pools must be an object")
    updated: list[str] = []
    for pool_name_variant in deck_pools:
        pool_name = str(pool_name_variant)
        pool = room_pools.get(pool_name)
        if not isinstance(pool, list):
            raise ValueError(f"candidate references unknown or non-list deck pool '{pool_name}'")
        if room_id not in pool:
            pool.append(room_id)
            updated.append(pool_name)
    return updated


def cmd_apply(args: argparse.Namespace) -> int:
    candidate_path = Path(args.candidate)
    if not candidate_path.is_absolute():
        candidate_path = ROOT / candidate_path
    candidate = load_json(candidate_path)
    room = candidate.get("new_room")
    if not isinstance(room, dict):
        raise ValueError("candidate requires new_room object")
    room_id = str(room.get("id", ""))
    events = candidate.get("events", [])
    if not isinstance(events, list):
        raise ValueError("candidate requires events array")
    deck_pools = candidate.get("deck_pools", [])
    if not isinstance(deck_pools, list):
        raise ValueError("candidate deck_pools must be an array")
    special_events = candidate.get("special_events", {})
    if not isinstance(special_events, dict):
        raise ValueError("candidate special_events must be an object")

    rooms_payload = load_json(ROOMS_PATH)
    events_payload = load_json(EVENTS_PATH)
    decks_payload = load_json(DECKS_PATH)

    room_action = replace_room(rooms_payload, room)
    replace_room_events(events_payload, room_id, events)
    special_count = merge_special_events(events_payload, special_events)
    updated_pools = update_deck_pools(decks_payload, room_id, deck_pools)

    if args.dry_run:
        print(
            f"dry-run ok: {room_action} room {room_id}, "
            f"{len(events)} event(s), {special_count} special event(s), "
            f"updated pools: {', '.join(updated_pools) or 'none'}"
        )
        return 0

    write_json(ROOMS_PATH, rooms_payload)
    write_json(EVENTS_PATH, events_payload)
    write_json(DECKS_PATH, decks_payload)
    print(
        f"applied: {room_action} room {room_id}, "
        f"{len(events)} event(s), {special_count} special event(s), "
        f"updated pools: {', '.join(updated_pools) or 'none'}"
    )
    return 0


def cmd_remove(args: argparse.Namespace) -> int:
    room_id = args.room_id
    rooms_payload = load_json(ROOMS_PATH)
    events_payload = load_json(EVENTS_PATH)
    decks_payload = load_json(DECKS_PATH)

    rooms = rooms_payload.get("rooms", [])
    if not isinstance(rooms, list):
        raise ValueError("rooms_post_update.json rooms must be a list")
    before_rooms = len(rooms)
    rooms_payload["rooms"] = [
        room for room in rooms if not (isinstance(room, dict) and room.get("id") == room_id)
    ]

    room_events = events_payload.get("room_events", {})
    removed_events = 0
    if isinstance(room_events, dict):
        events = room_events.pop(room_id, [])
        removed_events = len(events) if isinstance(events, list) else 0

    removed_pools: list[str] = []
    room_pools = decks_payload.get("room_pools", {})
    if isinstance(room_pools, dict):
        for pool_name, pool in room_pools.items():
            if isinstance(pool, list) and room_id in pool:
                room_pools[pool_name] = [candidate for candidate in pool if candidate != room_id]
                removed_pools.append(str(pool_name))

    removed_room = before_rooms - len(rooms_payload["rooms"])
    if args.dry_run:
        print(
            f"dry-run ok: removed {removed_room} room(s), {removed_events} event(s), "
            f"pools: {', '.join(removed_pools) or 'none'}"
        )
        return 0

    write_json(ROOMS_PATH, rooms_payload)
    write_json(EVENTS_PATH, events_payload)
    write_json(DECKS_PATH, decks_payload)
    print(
        f"removed: {removed_room} room(s), {removed_events} event(s), "
        f"pools: {', '.join(removed_pools) or 'none'}"
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command")

    apply_parser = sub.add_parser("apply")
    apply_parser.add_argument("candidate")
    apply_parser.add_argument("--dry-run", action="store_true")
    apply_parser.set_defaults(func=cmd_apply)

    remove_parser = sub.add_parser("remove")
    remove_parser.add_argument("room_id")
    remove_parser.add_argument("--dry-run", action="store_true")
    remove_parser.set_defaults(func=cmd_remove)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.command is None:
        if hasattr(args, "candidate"):
            return args.func(args)
        parser.print_help()
        return 2
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
