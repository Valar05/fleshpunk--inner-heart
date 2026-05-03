# Fleshpunk: Inner Heart Orientation

## One-Command Bootstrap

Run this first when re-entering the project:

```sh
python tools/project_bootstrap.py
```

Use strict mode when you want data gaps to fail the check:

```sh
python tools/project_bootstrap.py --strict
```

## Project Shape

- Godot 4.5 mobile project.
- Main scene: `res://world.tscn`.
- Autoloads: `HeartManager` and `RunManager`.
- Viewport target: 1080x1920 portrait.

## Core Runtime Files

- `world.gd`: Presents rooms, handles dashboard button routing, room transitions, encounter scene spawning, and combat animation.
- `run_manager.gd`: Owns run state, deck drawing, resource counters, player stats, encounter construction, and action consequences.
- `fleshpunk_dashboard.gd`: Renders console text and event buttons on the dashboard sprite.
- `combat_system.gd`: Pure combat simulation.
- `heart_manager.gd`: Emits pulse events and exposes BPM.

## Core Data Files

- `room_dialogue.json`: Room ids, images, and fallback room UI text.
- `events.json`: Room events and special events.
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

Useful commands:

```sh
python tools/scenario_agent.py context
python tools/scenario_agent.py generate --room bone_corridor --mock
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

Memory and style guidance live in `.agent-memory/`.

## Current Engineering Rule

For event and mechanic work:

1. Add explicit action handlers in `run_manager.gd` when a choice needs gameplay consequences.
2. Keep event patches limited to existing action ids unless engine work is planned.
3. Use `tools/project_bootstrap.py --strict` to catch unhandled actions and dangling ids before accepting data patches.
4. Use `tools/mechanics_agent.py` to brainstorm deeper systems before expanding placeholder handlers.
