#!/usr/bin/env python3
"""Extract source motifs and transform them into Fleshpunk design seeds."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import textwrap
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
GENERATED_DIR = ROOT / "generated"
CORPUS_DIR = GENERATED_DIR / "corpus"
TEXTS_DIR = CORPUS_DIR / "texts"
SOURCES_PATH = CORPUS_DIR / "public_domain_sources.json"
MOTIFS_PATH = CORPUS_DIR / "motifs.json"
SEEDS_PATH = CORPUS_DIR / "fleshpunk_seeds.json"
ROOMS_PATH = ROOT / "room_dialogue.json"
RUN_MANAGER_PATH = ROOT / "run_manager.gd"

GUTENBERG_START_RE = re.compile(r"\*\*\*\s*START OF (?:THE|THIS) PROJECT GUTENBERG EBOOK[^\n]*\*\*\*", re.IGNORECASE)
GUTENBERG_END_RE = re.compile(r"\*\*\*\s*END OF (?:THE|THIS) PROJECT GUTENBERG EBOOK[^\n]*\*\*\*", re.IGNORECASE)
WORD_RE = re.compile(r"[a-z][a-z'-]+", re.IGNORECASE)
ACTION_CASE_RE_TEMPLATE = r'^{indent}"([^"]+)":\s*$'
WORLD_ACTIONS = {"proceed", "combat", "browse_wares", "restart_run"}

MOTIF_GROUPS: dict[str, dict[str, list[str]]] = {
    "locations": {
        "subterranean_route": ["cave", "cavern", "tunnel", "shaft", "gallery", "abyss", "underground", "subterranean", "crater"],
        "ocean_pressure": ["sea", "ocean", "submarine", "nautilus", "reef", "depth", "pressure", "current", "diving"],
        "polar_expedition": ["ice", "antarctic", "snow", "glacier", "polar", "frost", "white", "cold", "latitude"],
        "island_system": ["island", "shore", "beach", "colony", "settlement", "harbor", "coast", "reef"],
        "sealed_house_or_lab": ["house", "cellar", "laboratory", "room", "vault", "study", "library", "attic", "basement"],
        "ancient_ruin": ["ruin", "city", "cyclopean", "monolith", "stone", "temple", "wall", "arch", "masonry"],
    },
    "character_functions": {
        "mission_commander": ["captain", "commander", "leader", "chief", "authority", "orders", "command"],
        "scientist_witness": ["professor", "doctor", "naturalist", "geologist", "chemist", "student", "observer"],
        "engineer_operator": ["engineer", "mechanic", "machine", "engine", "apparatus", "instrument", "valve"],
        "hidden_patron": ["unknown", "invisible", "mysterious", "secret", "concealed", "anonymous", "unseen"],
        "crew_or_party": ["crew", "party", "companion", "sailor", "men", "expedition", "survivors"],
        "tainted_family_or_cult": ["family", "ancestor", "blood", "heir", "cult", "rite", "worship", "lineage"],
    },
    "machines_or_systems": {
        "sealed_vessel": ["vessel", "ship", "submarine", "boat", "nautilus", "hull", "cabin", "compartment"],
        "pressure_system": ["pressure", "valve", "pump", "current", "flow", "tide", "compression", "gauge"],
        "excavation_system": ["drill", "pickaxe", "shaft", "mine", "boring", "descent", "rope", "ladder"],
        "signal_or_record": ["signal", "message", "manuscript", "letter", "journal", "record", "document", "cipher"],
        "biological_process": ["growth", "organism", "creature", "tissue", "blood", "disease", "decay", "fungus", "cell"],
        "navigation_system": ["map", "compass", "latitude", "longitude", "route", "chart", "bearing", "course"],
    },
    "survival_pressures": {
        "hunger_and_ration": ["hunger", "thirst", "ration", "provisions", "food", "water", "starvation", "famine"],
        "isolation": ["alone", "silence", "solitude", "lost", "deserted", "abandoned", "remote"],
        "panic_or_mutiny": ["panic", "madness", "fear", "mutiny", "terror", "riot", "despair", "frenzy"],
        "injury_and_exhaustion": ["wound", "injury", "blood", "fatigue", "fever", "weakness", "pain", "sick"],
        "contamination": ["poison", "taint", "contamination", "infection", "disease", "corruption", "decay"],
        "pursuit_or_hunt": ["pursuit", "hunt", "chase", "attack", "enemy", "monster", "beast", "track"],
        "knowledge_cost": ["secret", "forbidden", "terrible", "truth", "revelation", "discovery", "horror", "unknown"],
    },
}

ROOM_AFFINITY: dict[str, list[str]] = {
    "subterranean_route": ["bone_corridor", "organ_chamber_red"],
    "ocean_pressure": ["healing_pool", "organ_chamber_red"],
    "polar_expedition": ["bone_corridor", "split_green_corridor"],
    "island_system": ["egg_corridor", "healing_pool"],
    "sealed_house_or_lab": ["red_corridor", "organ_chamber_red"],
    "ancient_ruin": ["bone_corridor", "spiked_red_corridor"],
    "mission_commander": ["red_corridor", "organ_chamber_red"],
    "scientist_witness": ["organ_chamber_red", "healing_pool"],
    "engineer_operator": ["amber_corridor", "split_red_corridor"],
    "hidden_patron": ["red_corridor", "split_green_corridor"],
    "crew_or_party": ["egg_corridor", "bone_corridor"],
    "tainted_family_or_cult": ["organ_chamber_red", "healing_pool"],
    "sealed_vessel": ["organ_chamber_red", "red_corridor"],
    "pressure_system": ["spiked_red_corridor", "split_red_corridor"],
    "excavation_system": ["bone_corridor", "amber_corridor"],
    "signal_or_record": ["red_corridor", "split_green_corridor"],
    "biological_process": ["healing_pool", "egg_corridor"],
    "navigation_system": ["split_green_corridor", "split_red_corridor"],
    "hunger_and_ration": ["amber_corridor", "egg_corridor"],
    "isolation": ["red_corridor", "bone_corridor"],
    "panic_or_mutiny": ["split_red_corridor", "spiked_red_corridor"],
    "injury_and_exhaustion": ["healing_pool", "red_corridor"],
    "contamination": ["healing_pool", "organ_chamber_red"],
    "pursuit_or_hunt": ["spiked_red_corridor", "bone_corridor"],
    "knowledge_cost": ["organ_chamber_red", "red_corridor"],
}

ACTION_AFFINITY: dict[str, list[str]] = {
    "subterranean_route": ["listen_at_green_split", "probe_bones", "mark_red_branch"],
    "ocean_pressure": ["study_pool", "drink_pool", "observe_organ_chamber"],
    "polar_expedition": ["retreat", "probe_bones", "listen_at_green_split"],
    "island_system": ["harvest_eggs", "study_pool", "proceed"],
    "sealed_house_or_lab": ["observe_organ_chamber", "study_pool", "proceed"],
    "ancient_ruin": ["probe_bones", "follow_marked_plates", "scavenge_bones"],
    "mission_commander": ["mark_red_branch", "proceed", "retreat"],
    "scientist_witness": ["study_pool", "observe_organ_chamber", "probe_bones"],
    "engineer_operator": ["probe_amber_cache", "vent_red_split", "break_amber_cache"],
    "hidden_patron": ["pay_resin_toll", "skip_resin_toll", "browse_wares"],
    "crew_or_party": ["retreat", "combat", "proceed"],
    "tainted_family_or_cult": ["take_mutation", "study_pool", "leave_mutation"],
    "sealed_vessel": ["observe_organ_chamber", "pay_resin_toll", "proceed"],
    "pressure_system": ["vent_red_split", "push_through_spikes", "break_spike_lane"],
    "excavation_system": ["break_amber_cache", "scavenge_bones", "cut_heart_cords"],
    "signal_or_record": ["mark_red_branch", "study_pool", "listen_red_wall"],
    "biological_process": ["disturb_pool", "drink_pool", "take_mutation"],
    "navigation_system": ["mark_red_branch", "listen_at_green_split", "proceed"],
    "hunger_and_ration": ["pay_resin_toll", "skip_resin_toll", "harvest_eggs"],
    "isolation": ["proceed", "retreat", "listen_red_wall"],
    "panic_or_mutiny": ["retreat", "rush_red_split", "combat"],
    "injury_and_exhaustion": ["drink_pool", "study_pool", "disturb_pool"],
    "contamination": ["take_mutation", "study_pool", "disturb_green_spores"],
    "pursuit_or_hunt": ["combat", "retreat", "push_through_spikes"],
    "knowledge_cost": ["study_pool", "observe_organ_chamber", "take_symbiote"],
}

TRANSFORM_LINES: dict[str, dict[str, str]] = {
    "subterranean_route": {
        "seed": "A descent route becomes a warm bore through layered tissue; each safer landmark is also a place the organism can remember Hymn.",
        "mechanic": "Repeated mapping lowers danger now but creates marked-route pressure that can later spring a snare.",
    },
    "ocean_pressure": {
        "seed": "An undersea pressure journey becomes a sealed fluid corridor that equalizes through valves grown from living membrane.",
        "mechanic": "Opening pressure buys passage or healing, but raises corruption when the fluid enters Hymn's body.",
    },
    "polar_expedition": {
        "seed": "A polar rescue route becomes a sterile white marrow field where warmth, signal, and memory drain together.",
        "mechanic": "Waiting and listening reduce immediate danger but increase isolation pressure and delayed hunter attention.",
    },
    "island_system": {
        "seed": "A survival island becomes a self-contained organ colony that supplies tools only when fed useful losses.",
        "mechanic": "Scavenging builds biomass, while repeated dependence teaches the room to price basic access.",
    },
    "sealed_house_or_lab": {
        "seed": "A haunted house or laboratory becomes a sealed operator chamber whose walls preserve failed procedures as tissue reflexes.",
        "mechanic": "Studying records unlocks safer choices but adds knowledge pressure and signal degradation.",
    },
    "ancient_ruin": {
        "seed": "An ancient ruin becomes old bio-infrastructure: bone masonry, maintenance rites, and organs mistaken for monuments.",
        "mechanic": "Respecting markings lowers danger; stripping relic tissue gives biomass and pushes greed or hunter pressure.",
    },
    "mission_commander": {
        "seed": "A commander figure becomes Chorus pressure: remote authority, incomplete orders, and mission logic that prices hesitation.",
        "mechanic": "Following orders should clarify the route while increasing a pressure the player can hear in later warnings.",
    },
    "scientist_witness": {
        "seed": "A scientist-witness becomes Hymn's field report discipline: observe first, name the mechanism, then admit the cost.",
        "mechanic": "Study actions should reveal a safer line or pressure forecast while trading time, danger, or corruption.",
    },
    "engineer_operator": {
        "seed": "An engineer-operator becomes a maintenance intelligence: valves, tolls, and repair reflexes that treat Hymn as a tool.",
        "mechanic": "Technical interactions should offer a clean manipulation and a forceful shortcut with different pressure costs.",
    },
    "hidden_patron": {
        "seed": "A hidden patron becomes unseen intervention by Chorus, the merchant, or the organism, helpful only because it creates leverage.",
        "mechanic": "Aid should solve the immediate room and leave a visible claim, debt, or dependency marker.",
    },
    "crew_or_party": {
        "seed": "An expedition party becomes internal company: symbiotes, old signals, and body systems arguing without becoming separate narrators.",
        "mechanic": "Group-pressure events should make retreat, combat, and waiting each teach the director a different habit.",
    },
    "tainted_family_or_cult": {
        "seed": "A tainted bloodline or cult becomes facility operator residue: maintenance rites remembered by tissue, not people.",
        "mechanic": "Ritual or inheritance choices should grant access while raising corruption or knowledge pressure without exposing clone truth.",
    },
    "sealed_vessel": {
        "seed": "A vessel becomes a ribbed transit organ with compartments that open only when Hymn matches its pulse economy.",
        "mechanic": "Paying or synchronizing advances safely; forcing bulkheads creates damage, noise, and future pursuit.",
    },
    "pressure_system": {
        "seed": "Mechanical pressure becomes vascular pressure: valves, clots, vents, and arterial doors that punish repeated shortcuts.",
        "mechanic": "Venting reduces danger and gives biomass, but overuse makes later rooms overpressurized.",
    },
    "excavation_system": {
        "seed": "Excavation becomes surgical trespass through marrow and amber, with every tool doubling as a wound.",
        "mechanic": "Breaking hard tissue yields resources at health cost; probing finds quiet routes with lower reward.",
    },
    "signal_or_record": {
        "seed": "Journals and signals become Chorus packets with missing checksum, old operator notes, and memory that may not belong to Hymn.",
        "mechanic": "Reading clarifies choices but can raise corruption, dependence, or knowledge pressure.",
    },
    "biological_process": {
        "seed": "Alien process becomes tissue logic: growth, rot, repair, and appetite operate as infrastructure, not scenery.",
        "mechanic": "Healing and growth choices are explicit transactions that restore stats while leaving residue.",
    },
    "navigation_system": {
        "seed": "Charts and bearings become pulse maps, scar routes, and branch markings that the organism can counter-map.",
        "mechanic": "Route skill reduces immediate danger, but repeated use schedules route-specific retaliation.",
    },
    "hunger_and_ration": {
        "seed": "Ration pressure becomes biomass economics: the body, merchant, and corridor all account for stored meat.",
        "mechanic": "Paying biomass avoids harm; skipping tolls accrues claim that can become a reckoning encounter.",
    },
    "isolation": {
        "seed": "Isolation becomes signal loss between Hymn and Chorus; quiet rooms are safer but less accountable.",
        "mechanic": "Silence can reduce danger while increasing dependence on internal voices, symbiotes, or memory residue.",
    },
    "panic_or_mutiny": {
        "seed": "Crew panic becomes internal system disagreement: organs, symbiotes, and mission orders pulling against each other.",
        "mechanic": "Fast choices avoid one cost and add another, making repeated panic legible to the director.",
    },
    "injury_and_exhaustion": {
        "seed": "Exhaustion becomes body debt: every forced route spends tissue that the facility can recognize later.",
        "mechanic": "Damage choices should state the wound, the resource gained, and which pressure axis noticed it.",
    },
    "contamination": {
        "seed": "Contamination becomes useful corruption: the facility repairs Hymn by making her more legible to itself.",
        "mechanic": "Healing, mutation, and study can all restore control while moving corruption toward a lock.",
    },
    "pursuit_or_hunt": {
        "seed": "Hunt logic becomes immune response: the organism dispatches specialized hunters to answer repeated avoidance or noise.",
        "mechanic": "Avoiding combat is valid but must increment a visible pressure that eventually sends a named response.",
    },
    "knowledge_cost": {
        "seed": "Forbidden knowledge becomes operational truth that helps Hymn survive while crossing her knowledge boundaries.",
        "mechanic": "Lore choices should grant route clarity or safer actions, never clone truth, and should carry pressure.",
    },
}


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


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig") if path.exists() else ""


def strip_gutenberg_boilerplate(text: str) -> str:
    start = GUTENBERG_START_RE.search(text)
    if start is not None:
        text = text[start.end():]
    end = GUTENBERG_END_RE.search(text)
    if end is not None:
        text = text[:end.start()]
    return text


def count_terms(text: str, terms: list[str]) -> tuple[int, list[dict[str, int]]]:
    lower = text.lower()
    matches: list[dict[str, int]] = []
    total = 0
    for term in terms:
        pattern = r"(?<![a-z])%s(?![a-z])" % re.escape(term.lower())
        count = len(re.findall(pattern, lower))
        if count > 0:
            matches.append({"term": term, "count": count})
            total += count
    matches.sort(key=lambda item: (-int(item["count"]), str(item["term"])))
    return total, matches[:8]


def word_count(text: str) -> int:
    return len(WORD_RE.findall(text))


def get_sources() -> list[dict[str, Any]]:
    payload = load_json(SOURCES_PATH)
    works = payload.get("works", [])
    if not isinstance(works, list):
        raise ValueError("public_domain_sources.json must contain a works array")
    return [work for work in works if isinstance(work, dict)]


def get_room_ids() -> list[str]:
    if not ROOMS_PATH.exists():
        return []
    payload = load_json(ROOMS_PATH)
    rooms = payload.get("rooms", [])
    if not isinstance(rooms, list):
        return []
    return [str(room.get("id", "")) for room in rooms if isinstance(room, dict) and room.get("id")]


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


def summarize_source(work: dict[str, Any]) -> dict[str, Any]:
    local_path = ROOT / str(work.get("local_path", ""))
    raw_text = read_text(local_path)
    body = strip_gutenberg_boilerplate(raw_text)
    groups: dict[str, Any] = {}
    all_ranked: list[dict[str, Any]] = []
    body_word_count = word_count(body)

    for group_name, motifs in MOTIF_GROUPS.items():
        group_results: list[dict[str, Any]] = []
        for motif_id, terms in motifs.items():
            count, evidence_terms = count_terms(body, terms)
            if count <= 0:
                continue
            density = round(count / max(body_word_count, 1) * 10000, 2)
            result = {
                "motif_id": motif_id,
                "score": count,
                "density_per_10k_words": density,
                "evidence_terms": evidence_terms,
            }
            group_results.append(result)
            all_ranked.append({"group": group_name, **result})
        group_results.sort(key=lambda item: (-int(item["score"]), str(item["motif_id"])))
        groups[group_name] = group_results[:5]

    all_ranked.sort(key=lambda item: (-int(item["score"]), str(item["motif_id"])))
    return {
        "source_id": str(work.get("id", "")),
        "author": str(work.get("author", "")),
        "title": str(work.get("title", "")),
        "ebook_number": int(work.get("ebook_number", 0)),
        "source_page": str(work.get("source_page", "")),
        "local_path": str(work.get("local_path", "")),
        "word_count_without_gutenberg_boilerplate": body_word_count,
        "top_motifs": all_ranked[:10],
        "motif_groups": groups,
    }


def build_motifs_payload(limit: int = 0) -> dict[str, Any]:
    sources = get_sources()
    if limit > 0:
        sources = sources[:limit]
    works = [summarize_source(work) for work in sources]
    return {
        "generated_at": dt.datetime.now(dt.UTC).isoformat(),
        "source_manifest": str(SOURCES_PATH.relative_to(ROOT)),
        "notes": [
            "Scores are deterministic keyword counts against Gutenberg text with boilerplate stripped.",
            "Evidence terms are terms and counts, not source quotations.",
        ],
        "works": works,
    }


def flatten_top_motifs(work: dict[str, Any], max_count: int) -> list[dict[str, Any]]:
    seen: set[str] = set()
    flattened: list[dict[str, Any]] = []
    for item in work.get("top_motifs", []):
        if not isinstance(item, dict):
            continue
        motif_id = str(item.get("motif_id", ""))
        if motif_id == "" or motif_id in seen:
            continue
        seen.add(motif_id)
        flattened.append(item)
        if len(flattened) >= max_count:
            break
    return flattened


def affinity_values(motif_id: str, table: dict[str, list[str]], fallback: list[str]) -> list[str]:
    return table.get(motif_id, fallback)[:3]


def build_seed(work: dict[str, Any], motif: dict[str, Any], index: int, available_rooms: list[str]) -> dict[str, Any]:
    motif_id = str(motif.get("motif_id", ""))
    transform = TRANSFORM_LINES.get(motif_id, {
        "seed": "A public-domain expedition motif becomes a body-system encounter that offers safety with a visible cost.",
        "mechanic": "Make the choice affect at least one pressure axis, then let repeated use teach the organism.",
    })
    room_fallback = available_rooms[:3] if available_rooms else ["red_corridor"]
    return {
        "id": "%s_%02d_%s" % (str(work.get("source_id", "source")), index + 1, motif_id),
        "source_id": str(work.get("source_id", "")),
        "source_title": str(work.get("title", "")),
        "source_author": str(work.get("author", "")),
        "motif_id": motif_id,
        "motif_group": str(motif.get("group", "")),
        "source_signal": {
            "score": int(motif.get("score", 0)),
            "density_per_10k_words": float(motif.get("density_per_10k_words", 0.0)),
            "evidence_terms": motif.get("evidence_terms", []),
        },
        "fleshpunk_seed": transform["seed"],
        "mechanic_direction": transform["mechanic"],
        "suggested_rooms": affinity_values(motif_id, ROOM_AFFINITY, room_fallback),
        "suggested_existing_actions": affinity_values(motif_id, ACTION_AFFINITY, ["proceed", "retreat", "study_pool"]),
        "generation_guardrails": [
            "Transform structure and pressure, not names or prose.",
            "Keep Hymn's narration first-person and clipped.",
            "Do not reveal clone truth.",
            "State mechanical pressure changes in result text.",
        ],
    }


def build_seeds_payload(motifs_payload: dict[str, Any], max_per_work: int) -> dict[str, Any]:
    available_rooms = get_room_ids()
    seeds: list[dict[str, Any]] = []
    for work in motifs_payload.get("works", []):
        if not isinstance(work, dict):
            continue
        for index, motif in enumerate(flatten_top_motifs(work, max_per_work)):
            seeds.append(build_seed(work, motif, index, available_rooms))
    return {
        "generated_at": dt.datetime.now(dt.UTC).isoformat(),
        "motifs_source": str(MOTIFS_PATH.relative_to(ROOT)),
        "notes": [
            "Seeds are original Fleshpunk transformations derived from motif counts.",
            "Use suggested_existing_actions unless planning engine work.",
        ],
        "seeds": seeds,
    }


def validate_motifs(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    works = payload.get("works", [])
    if not isinstance(works, list) or not works:
        errors.append("motifs payload must contain a non-empty works array")
        return errors
    for index, work in enumerate(works):
        if not isinstance(work, dict):
            errors.append("works[%d] must be an object" % index)
            continue
        for key in ("source_id", "title", "author", "local_path", "top_motifs", "motif_groups"):
            if key not in work:
                errors.append("works[%d] missing %s" % (index, key))
        if int(work.get("word_count_without_gutenberg_boilerplate", 0)) <= 0:
            errors.append("works[%d] has no body words" % index)
    return errors


def validate_seeds(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    known_rooms = set(get_room_ids())
    known_actions = existing_actions()
    seeds = payload.get("seeds", [])
    if not isinstance(seeds, list) or not seeds:
        errors.append("seeds payload must contain a non-empty seeds array")
        return errors
    for index, seed in enumerate(seeds):
        if not isinstance(seed, dict):
            errors.append("seeds[%d] must be an object" % index)
            continue
        for key in ("id", "source_id", "motif_id", "fleshpunk_seed", "mechanic_direction", "suggested_rooms", "suggested_existing_actions"):
            if key not in seed:
                errors.append("seeds[%d] missing %s" % (index, key))
        if not isinstance(seed.get("suggested_rooms", []), list) or not seed.get("suggested_rooms", []):
            errors.append("seeds[%d] needs at least one suggested room" % index)
        else:
            for room_id in seed.get("suggested_rooms", []):
                if str(room_id) not in known_rooms:
                    errors.append("seeds[%d] suggests unknown room %s" % (index, room_id))
        if not isinstance(seed.get("suggested_existing_actions", []), list) or not seed.get("suggested_existing_actions", []):
            errors.append("seeds[%d] needs at least one suggested action" % index)
        else:
            for action_id in seed.get("suggested_existing_actions", []):
                action_family = str(action_id).split(":", 1)[0]
                if action_family not in known_actions:
                    errors.append("seeds[%d] suggests unhandled action %s" % (index, action_id))
    return errors


def cmd_context(_: argparse.Namespace) -> int:
    sources = get_sources()
    existing_texts = 0
    total_bytes = 0
    for work in sources:
        path = ROOT / str(work.get("local_path", ""))
        if path.exists():
            existing_texts += 1
            total_bytes += path.stat().st_size
    print("Corpus context")
    print("--------------")
    print(f"Sources: {len(sources)}")
    print(f"Local texts: {existing_texts}")
    print(f"Bytes: {total_bytes}")
    print(f"Manifest: {SOURCES_PATH.relative_to(ROOT)}")
    print(f"Motifs output: {MOTIFS_PATH.relative_to(ROOT)}")
    print(f"Seeds output: {SEEDS_PATH.relative_to(ROOT)}")
    print("\nWorks")
    for work in sources:
        print("- %s, %s (#%s)" % (work.get("author", ""), work.get("title", ""), work.get("ebook_number", "")))
    return 0


def cmd_extract(args: argparse.Namespace) -> int:
    payload = build_motifs_payload(args.limit)
    errors = validate_motifs(payload)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    out_path = Path(args.out) if args.out else MOTIFS_PATH
    if not out_path.is_absolute():
        out_path = ROOT / out_path
    write_json(out_path, payload)
    print("wrote %s" % out_path.relative_to(ROOT))
    print("works=%d" % len(payload.get("works", [])))
    return 0


def cmd_transform(args: argparse.Namespace) -> int:
    motifs_path = Path(args.motifs) if args.motifs else MOTIFS_PATH
    if not motifs_path.is_absolute():
        motifs_path = ROOT / motifs_path
    if not motifs_path.exists():
        payload = build_motifs_payload(0)
        write_json(motifs_path, payload)
    motifs_payload = load_json(motifs_path)
    motif_errors = validate_motifs(motifs_payload)
    if motif_errors:
        for error in motif_errors:
            print(error, file=sys.stderr)
        return 1
    seeds_payload = build_seeds_payload(motifs_payload, max(args.max_per_work, 1))
    seed_errors = validate_seeds(seeds_payload)
    if seed_errors:
        for error in seed_errors:
            print(error, file=sys.stderr)
        return 1
    out_path = Path(args.out) if args.out else SEEDS_PATH
    if not out_path.is_absolute():
        out_path = ROOT / out_path
    write_json(out_path, seeds_payload)
    print("wrote %s" % out_path.relative_to(ROOT))
    print("seeds=%d" % len(seeds_payload.get("seeds", [])))
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    target = Path(args.path)
    if not target.is_absolute():
        target = ROOT / target
    payload = load_json(target)
    errors = validate_seeds(payload) if "seeds" in payload else validate_motifs(payload)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("ok: %s" % target.relative_to(ROOT))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    context = sub.add_parser("context", help="Print corpus source context.")
    context.set_defaults(func=cmd_context)

    extract = sub.add_parser("extract", help="Extract deterministic motif counts from source texts.")
    extract.add_argument("--limit", type=int, default=0, help="Limit number of works processed.")
    extract.add_argument("--out", help="Output motifs JSON path.")
    extract.set_defaults(func=cmd_extract)

    transform = sub.add_parser("transform", help="Transform motifs into Fleshpunk design seeds.")
    transform.add_argument("--motifs", help="Input motifs JSON path. Defaults to generated/corpus/motifs.json.")
    transform.add_argument("--max-per-work", type=int, default=4, help="Maximum seeds to produce per source work.")
    transform.add_argument("--out", help="Output seeds JSON path.")
    transform.set_defaults(func=cmd_transform)

    validate = sub.add_parser("validate", help="Validate motifs or seeds JSON.")
    validate.add_argument("path")
    validate.set_defaults(func=cmd_validate)
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
    except OSError as exc:
        print(textwrap.fill(f"file error: {exc}", width=88), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
