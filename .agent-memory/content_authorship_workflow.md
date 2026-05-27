# Content Authorship Workflow

This project separates prose authorship from code integration.

## Rule

Codex agents should not be the primary author of player-facing game prose.

For room descriptions, event narration, result lines, ending text, button labels, lore fragments, and other visible story content:

1. Use the scenario/writing agent path to draft or revise the prose.
2. Use critic/audit passes to reject weak voice, author-mode drift, technobabble, unsupported inference, and flat cause/effect.
3. Let Codex apply the accepted patch, wire data, adjust tests, and run validation.

Codex may write or edit:

- schemas, tooling, tests, smoke checks, and docs
- mechanical glue in `run_manager.gd`, `world.gd`, and data handlers
- exact text supplied by the user
- tiny non-literary labels needed for tests or command wiring
- emergency repair of malformed JSON without changing creative intent

If a requested task requires new or substantially revised player-facing prose and the writing agent path is unavailable, Codex should stop and say that prose generation is blocked rather than silently hand-authoring final content.

## Required Content Pipeline

For new content, legacy migration, or substantial prose revision:

1. Gather context:

```sh
python tools/project_bootstrap.py --strict
python tools/scenario_agent.py context
python tools/scenario_agent.py hymn-corpus-voice
python tools/scenario_agent.py story-room-contract
```

2. For from-scratch scenarios, recurring-character arcs, endings, delayed follow-ups, or substantial rewrites, build a source packet before generation. Use `.agent-memory/source_packet_workflow.md`. Do not send the whole repo or a broad freeform prompt to an external writing agent.

3. Generate candidate prose/data through `tools/scenario_agent.py generate` or an equivalent dedicated writing agent using the approved source packet and the same memory docs.

4. Critique the candidate before applying:

```sh
python tools/scenario_agent.py critique --patch generated/scenario_patch.json
python tools/scenario_agent.py lore-critique
```

5. Validate and apply only accepted patches:

```sh
python tools/scenario_agent.py validate generated/scenario_patch.json --strict-tradeoffs
python tools/scenario_agent.py apply generated/scenario_patch.json --strict-tradeoffs
```

6. Run active content gates:

```sh
python tools/scenario_agent.py audit-writing
python tools/scenario_agent.py audit-story --json
python tools/scenario_agent.py validate-events --strict-actions
python tools/project_bootstrap.py --strict
```

7. Run Godot smoke tests when room/event behavior changes:

```sh
godot --headless --path /storage/emulated/0/Documents/GodotProjects/fleshpunk--inner-heart --script /storage/emulated/0/Documents/GodotProjects/fleshpunk--inner-heart/tools/post_update_room_smoke.gd
godot --headless --path /storage/emulated/0/Documents/GodotProjects/fleshpunk--inner-heart --script /storage/emulated/0/Documents/GodotProjects/fleshpunk--inner-heart/tools/story_followup_smoke.gd
```

## Voice Gate

All generated prose must obey `.agent-memory/hymn_corpus_voice.md`.

The house voice is not "Verne room" versus "Lovecraft room." Corpus influence changes what Hymn notices:

- Verne pressure becomes sequence, measurement, apparatus logic, and practical curiosity.
- Lovecraft pressure becomes residue, prior-use evidence, contamination, buried history, and dread built from records.
- Hymn's visible prose stays clipped, empirical, bodily, and operational.

## Codex Role

Codex owns:

- preserving data shape
- avoiding broken actions and dangling refs
- integrating accepted patches
- keeping tests and smoke checks current
- surfacing when generated prose fails the house voice

Codex does not own:

- final literary voice
- primary room/event prose invention
- ad hoc rewriting of large content surfaces
