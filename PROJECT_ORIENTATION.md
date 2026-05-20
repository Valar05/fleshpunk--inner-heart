# Fleshpunk: Inner Heart Orientation

## One-Command Bootstrap

Run this first when re-entering the project:

```sh
source ~/.bashrc
python tools/project_bootstrap.py
```

Use strict mode when you want data gaps to fail the check:

```sh
python tools/project_bootstrap.py --strict
```

Smoke test post-update room descriptions:

```sh
godot --headless --path /storage/emulated/0/Documents/GodotProjects/fleshpunk--inner-heart --script /storage/emulated/0/Documents/GodotProjects/fleshpunk--inner-heart/tools/post_update_room_smoke.gd
```

Smoke test delayed story follow-up insertion:

```sh
godot --headless --path /storage/emulated/0/Documents/GodotProjects/fleshpunk--inner-heart --script /storage/emulated/0/Documents/GodotProjects/fleshpunk--inner-heart/tools/story_followup_smoke.gd
```

Smoke test text-only UI layout:

```sh
godot --headless --path /storage/emulated/0/Documents/GodotProjects/fleshpunk--inner-heart --script /storage/emulated/0/Documents/GodotProjects/fleshpunk--inner-heart/tools/text_only_ui_smoke.gd
```

Preview active room/event docs without running Godot:

```sh
python tools/room_doc_browser.py --host 127.0.0.1 --port 3000
```

## Project Shape

- Godot 4.5 mobile project.
- Main scene: `res://world.tscn`.
- Autoloads: `HeartManager` and `RunManager`.
- Viewport target: 1080x1920 portrait.
- Presentation direction is text-only for required play. Room/environment visuals are deprecated as design requirements.
- Rooms are instances grouped by environment family. Do not design the dungeon around revisiting one literal room; later rooms may echo prior choices through shared environment state.
- Rooms should move toward player-facing first-read descriptions, narrated by Hymn, with event narration layered after room text. `return_description` is legacy compatibility, not the forward story structure.
- Character and faction progression uses delayed `story_followups`: room events enqueue one-shot special events into the run stack after at least one intervening room. Do not rely on revisiting the originating room for progression, and do not use follow-ups as instant result text.
- Existing `room_dialogue.json` and `events.json` content is legacy content. Use it for runtime/reference/migration only.
- Forward content starts from generated post-update rooms in `generated/room_mechanics_brainstorm.json`.
- Setting, faction, character, animal-infrastructure, and cross-run story architecture lives in `.agent-memory/setting_backbone.md`.
- Test post-update rooms in text/decision form before refreshing or generating TTS audio.
- Content authorship workflow lives in `.agent-memory/content_authorship_workflow.md`. Codex agents should not be the primary author of player-facing prose; use the scenario/writing agent path for drafting and revision, then let Codex integrate and verify accepted patches.
- The forward story-room quality bar lives in `.agent-memory/story_room_contract.md`; use it before accepting new room/event content.
- Ending-maze structure lives in `.agent-memory/ending_maze_architecture.md`; every environment family should be able to culminate in at least one ending vector.
- Hymn's corpus-blended prose target lives in `.agent-memory/hymn_corpus_voice.md`; use it when rewriting descriptions, events, results, and choice text.
- Every forward room needs a specific `corpus_influences` entry. `source_seed_ids` are not enough; the room must name the concrete source moment, writing energy, and room-writing application.

## Core Runtime Files

- `world.gd`: Presents rooms, handles dashboard button routing, room transitions, encounter scene spawning, and combat animation.
- `run_manager.gd`: Owns run state, deck drawing, resource counters, player stats, encounter construction, and action consequences.
- `fleshpunk_dashboard.gd`: Renders the full-screen text console, command input, and event buttons.
- `combat_system.gd`: Pure combat simulation.
- `heart_manager.gd`: Emits pulse events and exposes BPM.

## Core Data Files

- `room_dialogue.json`: Legacy room ids, images, and fallback room UI text. New rooms should move to text-first room instance descriptions grouped by environment family.
- `events.json`: Legacy room events and special events until post-update rooms are promoted.
- `encounter_decks.json`: Opening room, draw rules, special event cadence, base player stats, and BPM scaling.
- `enemies.json`: Enemy stat records referenced by event `enemy_id`.
- `mutations.json`: Mutation records referenced by event `mutation_id`.
- `symbiotes.json`: Symbiote records referenced by event `symbiote_id`.

## Event Contract

Events are data-driven. A room event usually needs:

- `id`
- `type`
- `speaker`
- `line_1`
- `line_2`
- `buttons`

Each button needs:

- `label`
- `action`

Button actions only produce specific gameplay if `run_manager.gd` handles the action in `_apply_action_effects`, or if `world.gd` handles the action before passing it to the run manager. Unknown actions fall back to the generic acknowledgement path.

## Scenario Agent

Existing scenario tooling lives in `tools/scenario_agent.py`.

Default forward generation should target post-update room ids, not legacy room ids, once those rooms are promoted into data.

Codex workflow rule: scenario/writing agents author player-facing prose. Codex applies accepted patches, wires mechanics, adjusts tests, and runs validation. Do not hand-author room descriptions, event narration, result lines, endings, or large button-label rewrites as final content unless the user supplies exact text.

Useful commands:

```sh
python tools/scenario_agent.py context
python tools/scenario_agent.py content-authorship
python tools/scenario_agent.py setting-backbone
python tools/scenario_agent.py hymn-corpus-voice
python tools/scenario_agent.py audit-story --json
python tools/scenario_agent.py generate --room rib_lock_tally_gate --category choice --strict-tradeoffs --mock
python tools/scenario_agent.py generate --mock --room rib_lock_tally_gate --category choice --source-work verne_twenty_thousand_leagues --source-motif sealed_vessel --strict-tradeoffs --out generated/corpus_seed_scenario_patch.json
python tools/scenario_agent.py validate generated/scenario_patch.json
python tools/scenario_agent.py apply generated/scenario_patch.json
```

## Mechanics Agent

Mechanics brainstorming lives in `tools/mechanics_agent.py`.

Use it when an action technically has a handler but still feels like a placeholder, or when a proposed mechanic should spawn new symbiote/mutation ideas.

Useful commands:

```sh
python tools/mechanics_agent.py context
python tools/mechanics_agent.py brainstorm --mock --action break_spike_lane
python tools/mechanics_agent.py brainstorm --action break_spike_lane --action probe_amber_cache --count 3
python tools/mechanics_agent.py validate generated/mechanics_brainstorm.json
```

The mechanics agent writes proposal JSON only. It does not apply data or engine changes.

## Corpus Agent

Public-domain source extraction lives in `tools/corpus_agent.py`.

Raw acquired texts and source metadata live under `generated/corpus/` and are ignored by git. Tracked source notes live in `.agent-memory/inspiration_sources.md`.

Useful commands:

```sh
python tools/corpus_agent.py context
python tools/corpus_agent.py extract
python tools/corpus_agent.py transform
python tools/corpus_agent.py validate generated/corpus/fleshpunk_seeds.json
```

The corpus agent does not write game events. It extracts motif counts and produces transformed Fleshpunk design seeds that can inform scenario or mechanics work.

Memory and style guidance live in `.agent-memory/`. Current content strategy lives in `.agent-memory/content_strategy.md`.

## Content Authorship Rule

Future Codex agents should treat player-facing writing as agent-authored content, not local hand prose. Use `.agent-memory/content_authorship_workflow.md` as the operating contract.

Required acceptance gate for generated or migrated content:

```sh
python tools/scenario_agent.py audit-writing
python tools/scenario_agent.py audit-story --json
python tools/scenario_agent.py validate-events --strict-actions
python tools/project_bootstrap.py --strict
```

When room/event behavior changes, also run:

```sh
godot --headless --path /storage/emulated/0/Documents/GodotProjects/fleshpunk--inner-heart --script /storage/emulated/0/Documents/GodotProjects/fleshpunk--inner-heart/tools/post_update_room_smoke.gd
godot --headless --path /storage/emulated/0/Documents/GodotProjects/fleshpunk--inner-heart --script /storage/emulated/0/Documents/GodotProjects/fleshpunk--inner-heart/tools/story_followup_smoke.gd
```

## Current Engineering Rule

For event and mechanic work:

1. Add explicit action handlers in `run_manager.gd` when a choice needs gameplay consequences.
2. Keep event patches limited to existing action ids unless engine work is planned.
3. Use `tools/project_bootstrap.py --strict` to catch unhandled actions and dangling ids before accepting data patches.
4. Use `tools/mechanics_agent.py` to brainstorm deeper systems before expanding placeholder handlers.
5. Design and promote post-update generated rooms before adding more events.
6. Do not patch legacy rooms unless the task is explicitly migration or compatibility.
