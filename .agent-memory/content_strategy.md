# Content Strategy

## Current Direction

The original shipped room/event content is now **legacy content**.

Use it for:
- runtime reference
- action handler reference
- migration examples
- regression checks

Do not use it as the forward creative target.

New content work should proceed from the generated post-update rooms, the public-domain corpus seed pipeline where still useful, and the current martial-anatomy research stack in `fleshpunk_corpus_research_stack.md`.

Use `martial_progression_pressure_contract.md` for the forward pressure model. Use `body_option_contract.md` for mutations, symbiotes, pure-body discipline, capability tags, and room branch discipline. New generation should treat Fleshpunk as martial progression fantasy: Hymn either hones a baseline body, rewrites herself through mutation/symbiote choices, or survives through scars, reputation, route memory, and social/ecological recognition.

Use `glue_layer_contract.md` for opening beats, inter-room special events, delayed follow-ups, pattern warnings, faction pressure scenes, and route transitions. The glue layer is where prior room choices come back as leverage: altered prices, masked options, predator attention, route favors, body-path recognition, or ending pressure.

Before forward generation, consult the research notes:

- `fleshpunk_research_combat_intelligence.md`
- `fleshpunk_research_biology_mutation.md`
- `fleshpunk_research_roguelike_systems.md`
- `fleshpunk_research_atmosphere_progression.md`
- `fleshpunk_research_pulp_before_1930.md`

Use `story_room_contract.md` as the acceptance standard for forward room scenarios. Valid button wiring is necessary but not sufficient; a scenario must expose a specific current situation, action-specific consequence, implicit branch pressure, and a character-change vector: enrichment, destabilization, or both.

The target scenario size is closer to Revelation than to a procedural room spec: compact, playable, and story-rich. Prefer one vivid pulp-fed situation with a meaningful possibility tree over a large apparatus diagram.

Use `ending_maze_architecture.md` for run structure. Every environment family should have at least one possible ending vector. Not every path reaches that ending, but every room family should be able to culminate somewhere.

Use `hymn_corpus_voice.md` for prose, but do not treat the old Verne/Lovecraft seed set as required. It is optional legacy material for procedure, evidence, contamination, and buried-history pressure only. The target is not generic weird fiction, citation metadata, HEMA lecture, biology textbook, or direct source homage. Hymn's voice should compress concrete procedural observation, hostile-world pressure, and tactical body consequence into clean field-report narration.

Every scenario must also declare a concrete research influence. The influence must name the transformed pressure pattern: source layer, source category, specific structural idea, writing or mechanic influence, and scenario application. `source_seed_ids` alone are not enough because they do not say what energy the scenario actually inherited.

For forward work, the strongest influence records should usually come from martial anatomy: anatomy as weapon geometry, armor, movement engine, stance, spacing, commitment, recovery, adaptation, and social/ecological escalation.

Forward generation must pass a cold-reader context test. The writing has been interesting but sometimes too abstract. Every generated room/event should make a normal player understand the place function, visible actor or hazard, Hymn's position, urgency, and the physical meaning of each choice before relying on coined terms or lore names.

When the user asks for action combat, do not convert martial anatomy into a biological puzzle, rite, procedure, sequence, or apparatus test. Use martial research to shape a fight that is already happening: opponent, range, pressure, contact, commitment, recovery, injury, and consequence.

When the user asks for mechanics or room generation, require each scenario to identify:

- `primary_pressure`
- `body_path_pressure`
- `avoidance_route`
- `recognition_effect`
- baseline pure-body route
- relevant capability tags
- mutation-favored branch, if any
- symbiote-favored branch, if any

Do not create puzzle rooms. Noncombat rooms should still involve pressure, conduct, witness, route cost, appetite, rest vulnerability, bargaining, or body-path progression.

Use the pulp corpus to add story pressure, physical immediacy, pursuit, reversal, rival recognition, lost-world danger, hostile landscape behavior, and mythic compression. Do not use it to clone prose.

When generating glue beats, require:

- a specific prior action or pressure pattern
- a concrete visible carrier such as a cord, receipt blister, feeder, scar mite, lens film, route packet, blood trace, symbiote twitch, or repair animal
- an active faction, character, animal, or system with leverage
- at least one choice unless terminal
- a next-room, deck, pressure, price, route, or recognition effect
- a tier-0 corpus/research anchor that changes the trigger, carrier, choice, consequence, or pressure axis

## Post-Update Room Track

Forward room work starts from `generated/room_mechanics_brainstorm.json`.

Current generated room ids:

- `rib_vessel_lock`
- `white_marrow_field`
- `operator_cellar`
- `scar_map_junction`
- `biomass_larder`
- `drowned_toll_harbor`
- `maintenance_rite_chapel`
- `launch_bore`

These ids currently behave like environment seeds. Forward work should split that concept cleanly: environment family first, then multiple concrete room instances/events inside that family.

## Room Contract

New rooms are text-only required content.

Each room needs:
- `id`
- `environment_id` or equivalent family grouping
- `corpus_influences` with source title, seed id, specific source moment, writing influence, and room application
- `first_visit_description`
- a specific instance premise/current situation
- pressure/mechanic notes
- valid event hooks

`return_description`, `image`, old `ui_text`, and sprite-based identity are legacy fields. They may remain temporarily for compatibility, but forward room identity must come from Hymn's first-read text and the current event situation, not from literal revisits.

## Generation Rule

When generating scenarios, mechanics, or lore:

1. Prefer post-update room ids.
2. Use legacy actions only when they still fit the new mechanic.
3. Do not patch legacy rooms unless the task is explicitly migration or compatibility.
4. Transform corpus/research seeds structurally; do not copy source names, scenes, characters, terminology, or prose.
5. Keep room descriptions distinct from event text: room text establishes place/function, event text describes the current situation.
6. Reject one-off rooms whose choices resolve as isolated stat changes.
7. Require action/reaction and future possibility, but keep risk and branch structure implicit in player-facing text.
8. Treat beasts, animals, parasites, and characters as interactable infrastructure, not just attackers.
9. Use `setting_backbone.md` before room generation; every room should carry faction pressure, recurring character traces, animal infrastructure, or cross-run story motion.
10. Progress character/faction stories with one-shot special event insertions or later environment echoes from room events. Do not rely on revisiting the same room for progression, and do not allow the same character beat to retrigger within one run.
11. Reject flat scaffold prose. Room and event writing must carry corpus-derived texture, procedural specificity, and history of the place.
12. Use combat when it enriches or destabilizes Hymn. Rebuild combat around readable martial anatomy: posture, distance, pressure, recovery, injury, anatomy-specific strengths, and anatomy-specific weaknesses. Do not require combat in every scenario.
13. Treat mutations as story capabilities, combat identities, movement changes, progression thresholds, and future room verbs, not stat upgrades first. Each major mutation should have both an in-encounter use and an out-of-encounter use, plus at least one later surprising second use. A mutation should help with some later room mechanisms while increasing or reducing specific ending pressure.
14. Treat symbiotes as stronger but less dependable living partners, not equipment. Each symbiote should have capability tags, in-encounter use, out-of-encounter use, a need, a sapience hint, relationship pressure, and failure modes. They may overpower a room branch, but they can be dormant, wounded, hungry, on cooldown, possessive, afraid, or unwilling.
15. Require a specific corpus influence for every room instance. Reject rooms that only use corpus as mood, provenance, citation, genre, or broad inspiration.
16. Treat glue beats as playable interventions, not narration between rooms. A glue beat must change options, prices, pressure, route state, deck state, body-path recognition, or ending pull.

## Check Modes

Use strict checks for new generation patches:

```sh
python tools/scenario_agent.py validate generated/prototype_pulp_scenario_patch.json --strict-scenario-contract
```

Use migration-mode audits for the current applied deck while old content is being converted:

```sh
python tools/scenario_agent.py audit-depth --json
python tools/scenario_agent.py audit-writing --json
```

Use strict audit mode only after a room family has been migrated to the new scenario contract:

```sh
python tools/scenario_agent.py audit-depth --json --mode strict
python tools/scenario_agent.py audit-writing --json --mode strict
```

## Anti-Overmechanization Rule

The post-update contract is a guardrail, not the desired surface texture.

Do not make every room read like a pressure-machine diagram, procedural puzzle, or Rube Goldberg device. The game is not a parade of clever biological mechanisms. A room can be simple, immediate, quiet, predatory, wounded, empty, or uncanny. It still needs consequence, but consequence can come from mood, scarcity, pursuit, debt, injury, lost information, or character pressure rather than a new bespoke apparatus.

Forward migration should preserve the broad feel and pacing of legacy rooms while raising the writing level:

- one strong room identity is better than six interacting parts
- one memorable image plus one playable pressure is enough for many rooms
- avoid stacking valves, beetles, tally organs, stride records, scent marks, and follow-up systems into the same room unless the legacy room already demands that density
- do not make the text sound derivative of the existing post-update rooms
- keep descriptions readable in play; the player should feel danger and option pressure before they feel schema compliance
- do not spell out risk trees, branch labels, or future consequences in player-facing text
- let some rooms be corridors, pools, nests, shrines, ambushes, or rests, not all infrastructure puzzles
- event text should not merely explain button economics or future scheduler hooks

Critiques should reject content that satisfies metadata while feeling overdesigned, too mechanical, too derivative, or unlike the game being made.

## Critique Standard

A critique that says the current post-update rooms are broadly good is too soft.

The current post-update room track is a scaffold, not finished content. It proves text-only room loading and seed-based direction. It does not yet satisfy the desired room depth.

Critiques must flag:
- broad environment-family rooms with only one event, unless the room has a narrow role such as symbiote offer, ambush, recovery beat, mutation offer, or character encounter
- rooms with no specific corpus influence, or a source seed id without the actual passage-level writing move being transformed
- rooms or environment families with no ending vector
- mutations that only change combat stats and do not create room capabilities
- mutations without both in-encounter and out-of-encounter uses
- choices that only imply immediate stat changes
- missing delayed consequences
- missing environment memory or later-instance echoes
- missing interactable characters, beasts, animals, or infrastructure actors
- beasts used only as combat starts
- cryptic objects whose function does not become mechanical behavior
- room instances that do not change future text, deck state, pressure state, environment state, or route state
- rooms that tell no story about the place and cannot be tied to the faction web, animal infrastructure, or recurring character arcs
- story kickoff events that do not enqueue a valid one-shot follow-up special event
- lines that read like generic option summaries instead of textured field narration
- vague safety language such as "looks safer" or "may help" without concrete mechanism, cost, or history

## Audio Timing

Test post-update rooms in text/decision form before making audio.

Do not refresh or generate TTS for post-update rooms until the room loop, descriptions, and choices are accepted.
