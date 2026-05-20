# Content Strategy

## Current Direction

The original shipped room/event content is now **legacy content**.

Use it for:
- runtime reference
- action handler reference
- migration examples
- regression checks

Do not use it as the forward creative target.

New content work should proceed from the generated post-update rooms and the public-domain corpus seed pipeline.

Use `story_room_contract.md` as the acceptance standard for forward rooms. Valid button wiring is necessary but not sufficient; a room instance must expose organism function, a specific current situation, action-specific consequence, and future pressure that can echo through later rooms in the same environment family.

Use `ending_maze_architecture.md` for run structure. Every environment family should have at least one possible ending vector. Not every path reaches that ending, but every room family should be able to culminate somewhere.

Use `hymn_corpus_voice.md` for prose. The target is not generic weird fiction or citation metadata. Hymn's voice should absorb Verne's procedural verve and Lovecraft's evidence-based dread, then compress both into clean field-report narration.

Every room must also declare a concrete corpus influence. The influence must name the specific passage, authorial move, scene function, object, incident, or character function shaping the writing. `source_seed_ids` alone are not enough because they do not say what energy the room actually inherited.

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
4. Transform corpus seeds structurally; do not copy source names, scenes, characters, or prose.
5. Keep room descriptions distinct from event text: room text establishes place/function, event text describes the current situation.
6. Reject one-off rooms whose choices resolve as isolated stat changes.
7. Require action/reaction and delayed consequence in room mechanics.
8. Treat beasts, animals, parasites, and characters as interactable infrastructure, not just attackers.
9. Use `setting_backbone.md` before room generation; every room should carry faction pressure, recurring character traces, animal infrastructure, or cross-run story motion.
10. Progress character/faction stories with one-shot special event insertions or later environment echoes from room events. Do not rely on revisiting the same room for progression, and do not allow the same character beat to retrigger within one run.
11. Reject flat scaffold prose. Room and event writing must carry corpus-derived texture, procedural specificity, and history of the place.
12. Treat combat as legacy unless explicitly retained. Forward obstacles should be bypassed, paid, altered, endured, misdirected, mutated through, or allowed to become endings.
13. Treat mutations as story capabilities and future room verbs, not combat upgrades first. A mutation should help with some later room mechanisms while increasing or reducing specific ending pressure.
14. Require a specific corpus influence for every room instance. Reject rooms that only use corpus as mood, provenance, citation, genre, or broad inspiration.

## Anti-Overmechanization Rule

The post-update contract is a guardrail, not the desired surface texture.

Do not make every room read like a pressure-machine diagram, procedural puzzle, or Rube Goldberg device. The game is not a parade of clever biological mechanisms. A room can be simple, immediate, quiet, predatory, wounded, empty, or uncanny. It still needs consequence, but consequence can come from mood, scarcity, pursuit, debt, injury, lost information, or character pressure rather than a new bespoke apparatus.

Forward migration should preserve the broad feel and pacing of legacy rooms while raising the writing level:

- one strong room identity is better than six interacting parts
- one memorable image plus one playable pressure is enough for many rooms
- avoid stacking valves, beetles, tally organs, stride records, scent marks, and follow-up systems into the same room unless the legacy room already demands that density
- do not make the text sound derivative of the existing post-update rooms
- keep descriptions readable in play; the player should feel danger and option pressure before they feel schema compliance
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
