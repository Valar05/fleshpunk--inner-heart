# Fleshpunk Research: Roguelike Systems

## Scope

This note extracts procedural structure from open-source and reference roguelikes without copying content, names, layouts, enemies, or prose.

Core premise: Fleshpunk rooms should become pressure systems where anatomy, resource scarcity, terrain, danger memory, and route choices interact.

## Source Touchpoints

- Brogue CE repository: https://github.com/tmewett/BrogueCE
- Brogue CE wiki: https://brogue.wiki/
- Brogue fundamentals: https://brogue.wiki/mw/index.php/Brogue_fundamentals
- Brogue traps: https://brogue.wiki/mw/index.php/Trap
- Shattered Pixel Dungeon repository: https://github.com/00-Evan/shattered-pixel-dungeon
- Shattered Pixel Dungeon item/code organization: https://github.com/00-Evan/shattered-pixel-dungeon/tree/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/items
- Shattered Pixel Dungeon hero/code organization: https://github.com/00-Evan/shattered-pixel-dungeon/tree/master/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/actors/hero
- Caves of Qud official site: https://www.cavesofqud.com/
- Caves of Qud official mutation reference: https://wiki.cavesofqud.com/wiki/Mutations
- Darkest Dungeon stress reference: https://darkestdungeon.wiki.gg/wiki/Stress_(Darkest_Dungeon)

## Brogue Lessons

Brogue's useful lesson is not "make the same dungeon." It is clarity plus systemic terrain pressure.

Fleshpunk transformations:

- room hazards should be legible before they are fatal
- gas, fire, fluids, traps, foliage, pits, and machines should interact with movement
- depth should change density, not only numbers
- resources should be gifts with danger attached
- terrain should turn one tactical choice into several consequences

Room design rule:

Every hazard should answer what the player can infer, trigger, avoid, redirect, consume, or mutate through.

## Shattered Pixel Dungeon Lessons

Shattered Pixel Dungeon's useful lesson is layered identity: hero class, equipment, items, talents, status effects, and level pressure all create different runs from the same dungeon grammar.

Fleshpunk transformations:

- mutations should function like class identity plus equipment plus terrain verb
- consumables should be risky diagnosis tools: useful now, clearer later, dangerous when unknown
- upgrade pressure should force commitment rather than let the player keep every path open
- class-like mutation branches should have preferred tactics, room verbs, and social consequences
- status effects should be readable and tactical, not hidden math

System design rule:

Every progression choice should close or complicate another route.

## Caves Of Qud Lessons

Use Caves of Qud as a structural reference for breadth, world texture, and mutations that can be character abilities, anatomy, senses, social liabilities, or ecological identity.

Fleshpunk transformations:

- mutations can alter faction response, not only combat
- natural traits and acquired mutations can share the same system
- body changes can unlock environmental interaction
- defects can fund power, but they should be playable liabilities, not bookkeeping
- generated history should give rooms social and ecological context

System design rule:

Mutation is identity. It should alter how the world reads the player.

## Darkest Dungeon Lessons

Use Darkest Dungeon as a structural reference for attrition and psychological pressure, not for its setting or prose.

Fleshpunk transformations:

- corruption, hunger, pain, breath debt, heat, and scent can be parallel attrition tracks
- stress thresholds should create behavior changes, not only penalties
- expedition pressure should persist between rooms
- rest should be a tactical decision with risk, cost, and possible interruption
- breaking points can be opportunities for strange adaptation, not only punishment

System design rule:

Long-term pressure should create route stories: why this body made this desperate choice.

## Procedural Room Pressure Types

Use these as generation categories:

- `terrain_pressure`: movement geometry changes risk
- `resource_pressure`: a useful thing costs body, time, or attention
- `predator_pressure`: enemy controls range, route, or timing
- `diagnosis_pressure`: unknown object/item/symptom can be tested
- `mutation_pressure`: body can solve problem but deepens identity drift
- `faction_pressure`: choice changes who recognizes or hates the player
- `attrition_pressure`: hunger, pain, heat, breath, infection, stress, scent
- `route_pressure`: forward path, safer detour, ending vector, shortcut, trap
- `memory_pressure`: previous choices alter text, enemies, or room state

## Room Generation Template

- `room_function`: what does this place do in the organism/world?
- `visible_hazard`: what can the player infer immediately?
- `hidden_coupling`: what interaction can be discovered?
- `body_solution`: which anatomy changes the problem?
- `non_body_solution`: what can a cautious player do?
- `cost`: what is spent now?
- `debt`: what follows later?
- `route_effect`: what opens, closes, or gets marked?
- `readability_note`: what makes the danger fair?

## Encounter Variety Rules

- A combat room is not always a fight; it can be a posture contest, escape, bait, feeding decision, or surgical trade.
- A reward room should still alter hunger, scent, faction memory, route pressure, or mutation appetite.
- A trap should become interesting when redirected, fed, jammed, worn, sensed, or used against an enemy.
- A mutation offer should have at least one room where it is specifically useful and one where it is specifically awkward.
- The deck should mix high-intensity rooms with quiet, readable rooms that build dread or resource pressure.

## Anti-Patterns

- Procedural rooms that only produce stat deltas.
- Hazards with no visible clue.
- Mutations that do not change room verbs.
- Items that are only currency.
- Enemies with no terrain relationship.
- Runs whose events can be shuffled without changing meaning.
- No persistent consequence from repeated behavior.

