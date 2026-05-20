# Fleshpunk: Inner Heart - Vibe & Design Guide

## Core Identity

**Fleshpunk** is a world where biology has replaced industry.

- Flesh is infrastructure
- Bone is architecture
- Organs are machinery
- Growth replaces construction

Nothing is "alive" in the traditional sense - everything is **functional, reactive, and repurposed**.

This is not chaos.
This is **systems made of meat**.

## Player Fantasy

You are not a hero.

You are:
- A survivor
- A scavenger
- A trespasser inside something larger than yourself

You are:
> **inside a system that does not need you - but will use you if allowed**

## Tone & Voice

### Communication Style

All narration is:
- First person
- Internal monologue
- Delivered like a **field report over a degraded radio channel**
- Hymn reporting to Chorus

### Voice Rules

- Short, clipped phrasing
- Observational first, emotional second
- No rhetorical questions
- No exposition dumps
- No visible speaker labels. Do not print "Her:" or equivalent name tags.
- Hymn may ask Chorus for instruction, confirmation, or signal checks.
- Chorus is never heard directly.

### Knowledge Boundaries

Hymn does not know she is a clone.

The story may imply repeated instances, memory leakage, and prior run residue, but Hymn's narration cannot state or understand the clone premise.

Allowed:
- "I have been here before. Maybe."
- "This memory does not belong cleanly to me."
- "Chorus, confirm route."
- "The last signal breaks up."

Not allowed:
- "I am a clone."
- "Another clone wakes."
- "The next Hymn will remember."
- Any narrator text that explains the run structure from outside Hymn's point of view.

#### Example

Bad:
> "There's a strange organism here. I wonder what it does."

Good:
> "Contact. Unknown organism. Not passive."
> "Could be useful. Could be a mistake."

## Emotional Tone

- Controlled tension
- Quiet dread
- Clinical curiosity
- Occasional flashes of instinct or unease

Never:
- Overly dramatic
- Whimsical
- Comedic, unless extremely dry and situational

## World Logic

Everything in the world should feel:

### 1. Purpose-Built

Nothing exists randomly.
If it's there, it *does something*.

### 2. Reactive

The environment:
- notices the player
- adapts
- escalates

### 3. Transactional

Everything has a cost:
- health
- danger
- mutation
- future consequences

Recovery is still a transaction.
Healing may cost contamination, attention, future access, or delayed pressure.
A restored body should usually leave residue.

### Room Role Variety

Purpose-built does not mean every room is an elaborate device.

Only some rooms should feel like apparatus rooms. Others can be direct encounters, character beats, symbiote choices, mutation offers, nests, pools, ambushes, quiet passages, or moments of pressure around a single body or object. Do not add extra biological machinery just to prove the world is functional.

The player should understand the room's role quickly:

- this is a fight
- this is a choice of symbiotes
- this is a wounded body with a cost
- this is a tempting pool
- this is a narrow passage
- this is a toll or machine
- this is a character making an offer

Use set dressing only until the role is clear. More moving parts can make the room weaker.

## Core Fun Loop

The game is not about optimal stat conversion.

It is about a living organism noticing player patterns, unbalancing the run, and pushing Hymn toward an outcome.

The repeatable loop should be:

1. Temptation: the room offers power, safety, yield, access, or relief.
2. Repetition: the player leans on a pattern because it works.
3. Organism reaction: the system notices and changes pressure.
4. Warning: the run shows what the pattern is turning into.
5. Adaptation or lock: the player corrects course, or the run slides toward an ending.

Fun comes from feeling the organism answer back.
Stats are only useful when they make that answer legible.

Design rule:
- No stat-only choices.
- Every decision must shift a pressure axis, preserve balance at a cost, reveal a warning, alter future deck/content, or move the run closer to an ending.
- Safe choices still create pressure somewhere.
- Refusing, fleeing, healing, extracting, mutating, bonding, and waiting must all have run-shaping consequences when repeated.

## Text-Only Presentation

The project no longer treats room art, enemy art, or environmental visuals as design requirements.

The only required visual interface is:
- room text
- decision text
- status/inventory text
- command feedback

Everything else is deprecated mood support. New design work must assume a player can understand the entire game from text and audio alone.

Room identity comes from Hymn's narration, not from images.

Each room should have:
- a first-visit description: relatively longer, establishing function, threat, and what the room seems to want
- a return description: shorter, immediately recognizable, and focused on changed pressure or route state
- event narration layered after the room description

Room descriptions are always Hymn reporting to Chorus. They must not use detached narrator voice.

## Legacy Content Boundary

The original room and event set is legacy content.

Use legacy content as implementation reference, action-handler reference, and migration material. Do not treat it as the forward creative baseline.

Forward room work should begin from generated post-update rooms and corpus-derived mechanics, then promote those rooms into the data model with first-visit and return descriptions.

## Depth Standard

Rooms are not one-off stat kiosks.

A room is only good enough when it has:
- an identifiable actor or system with behavior: character, beast, organ, colony, route intelligence, tool, parasite, market, or maintenance process
- action and reaction: the room responds to what Hymn does, not only with an immediate number
- delayed consequence: at least one choice changes future room text, deck pressure, route state, character posture, beast behavior, claim, debt, pursuit, or available choices
- legible uncertainty: the player understands the category of risk without seeing the entire consequence table
- memory: repeat use should change the room, the organism, or the way later rooms treat Hymn

Minor stat changes are allowed only as the visible surface of a larger consequence.

Bad pattern:
- cryptic object
- three vague choices
- +biomass / -health / +corruption
- no later reaction
- no actor remembers it

Good pattern:
- the room has a clear role and pressure
- a character, beast, or infrastructure system can be interacted with
- each choice teaches the organism something different
- consequences return later as warning, pursuit, debt, altered route text, changed offers, or a new constraint

Animals and beasts are also infrastructure. They should not exist only as attacks. A beast can be a valve, courier, immune sensor, toll collector, route cleaner, womb guard, memory carrier, or living tool. Combat is one possible interaction, not the default meaning of a beast.

Rooms should also tell the story of the place. A room is weak if it has no faction pressure, no recurring character trace, no animal or infrastructure behavior, and no cross-run story motion. The primary progression mechanic is event insertion: when Hymn kicks off a character or faction thread, a one-shot special event is pushed into the run stack. The player should feel that stories continue when Hymn leaves: ledgers tighten, survey marks become traps, rites wait for a hand, Chorus narrows the mission, animal systems remember treatment, and healing changes identity.

Character and faction follow-up events do not retrigger in the same run. A room can start a thread, but it should not farm the same character beat by repeated draws.

## Prose Texture Standard

The current post-update prose is scaffold prose. It is functional, but too flat to be final.

Forward writing should draw more heavily from the corpus texture:
- Verne gives procedure, route logic, pressure, instruments, expedition accounting, and the feeling that survival depends on understanding a mechanism.
- Lovecraft gives deep-time architecture, bad records, contamination, inheritance dread, biological wrongness, and the slow realization that an environment has a history older than the observer.

Use `.agent-memory/hymn_corpus_voice.md` for the dedicated blended voice target. It defines how to compress Verne's procedural verve and Lovecraft's evidence-based dread into Hymn's clean field-report narration.

Do not copy source prose or imitate antique diction. Transform the depth:
- name concrete mechanisms instead of generic weird objects
- give rooms history through wear, repair, measurement, residue, marks, and failed prior use
- make sentences carry two jobs: sensory texture plus operational consequence
- replace vague hedges like "may help" or "looks safer" with field judgement under uncertainty
- avoid flat option-list prose where line two merely explains three buttons
- avoid overexplaining biological machinery when the room is really about an enemy, character, symbiote, mutation, wound, or simple choice

Bad pattern:
- "The room wants payment. Paying is safer. Breaking it is noisy."

Better pattern:
- "The toll mouth opens along an old bite seam. Its inner teeth are polished by many hands, or many copies of the same hand. Feeding it should quiet the lock; forcing it will teach the ribs my weight in damage."

## Audio-First Accessibility

The game must be fully playable without looking at the screen.

Audio, text, and commands carry the required information:
- current room state
- legal choices
- likely costs
- pressure changes
- combat results
- ending causes

Every playable choice needs a short command path: number input, typed text, and eventually speech recognition through the same parser.

Accessibility is not a separate mode. It is the primary interface discipline.

## Organism As Director

The organism is the run director.

It should:
- notice repeated player behavior
- answer with pressure
- narrow routes when a pattern is abused
- offer more tempting versions of the same mistake
- reveal warnings before locking the player into an ending

It does not punish randomly.
It builds a case.

Repeated strategies should create gravitational pull:
- too much mutation, symbiote dependence, invasive healing, or body gain pulls toward corruption
- too much fleeing, combat avoidance, noisy extraction, or merchant refusal pulls toward danger and the hunter
- too much greed can create hunger, debt, pursuit, or unstable rooms
- too much safety can cost access, yield, information, or timing

## Ending Pressure

Endings are not just final scenes.
They are the destination of repeated behavior.

### Corruption Ending

Driven by:
- too many mutations
- too much symbiote dependence
- invasive healing
- body-rewrite choices
- repeated acceptance of the organism's gifts

Warnings before lock:
- Hymn's narration drifts
- rooms recognize altered tissue
- merchant offers become more intimate
- powerful choices become easier to justify

The corruption ending should be clear without meta explanation:
- Hymn loses bodily boundary and agency
- the organism starts answering through her body
- Chorus receives degraded reports, not exposition
- never say she is a clone or that another clone will replace her

### Hunter / Danger Ending

Driven by:
- too much fleeing
- repeated combat avoidance
- noisy extraction
- merchant refusal
- leaving unresolved threats behind

Warnings before lock:
- distant pursuit signs
- routes closing behind Hymn
- enemy cards becoming more frequent
- rooms behaving like ambush organs

### Balanced / Neutral Ending

The best ending requires balance and restraint.

Driven by:
- taking only enough power to survive
- fighting when necessary
- refusing clean dependence
- keeping danger and corruption below lock thresholds
- alternating risk instead of abusing one answer

The neutral route should feel tense, not empty.
Restraint should earn access, lore, and ending eligibility.

## Core Systems (Narrative Integration)

### Danger

Danger is not just difficulty.

It represents:
- how much attention the environment is paying to you
- how aggressively it responds

Higher danger:
- faster encounters
- more volatile outcomes
- more extreme rewards

Balance rule:
- Danger should change how rooms behave, not just how hard numbers hit.
- Higher danger can tighten seals, accelerate response, increase ambush probability, or make extraction less stable.
- The player should feel watched.

### Mutations

Mutations are:
- power
- corruption
- identity drift

They should feel:
> useful first, questionable later

Balance rule:
- Mutations should be easiest to justify when the body is already under pressure.
- Their value should be immediate.
- Their cost should become clearer over time.

### Symbiotes

Symbiotes are:
- partnerships
- dependencies
- risks

They are never purely beneficial.

Balance rule:
- Symbiotes should feel like temptation, dependency, and timing pressure.
- Avoid turning symbiotes into routine scheduled rewards.
- Some offers may be damaged, partial, deferred, or conditional.

### Rooms

Each room is a **scenario**, not just a location.

Rooms should communicate:
- function: what it does
- risk: what it costs
- opportunity: what it offers

Room description rule:
- `line_1` should be concrete before it is poetic.
- Describe visible structure, position, texture, smell, sound, movement, and what blocks or tempts Hymn.
- Avoid pure metaphor as the first read. The player should be able to picture the room from audio alone.
- `line_2` should translate that situation into plain stakes and likely consequences.
- Flavor can ride on top of clarity, but it cannot replace physical detail.

## Event Design Philosophy

Every event should present:

### 1. A Clear Situation

> "What is happening right now?"

### 2. A Tradeoff

> "What do I gain vs what do I risk?"

### 3. Uncertainty

> "I don't fully know the outcome."

### 4. Delayed Consequence

Some choices should pay off now and cost later.
Delayed consequences are valid when they preserve hesitation:
- a mark
- a future danger increase
- a narrowed route
- a changed merchant offer

## Player Interaction Model

- Player does **not speak**
- Player chooses actions
- The character **interprets and executes**

Buttons are:
> instructions to the character, not dialogue

### Button Rules

- Each button should be a bodily or procedural command.
- Repeated verbs are allowed only when the stakes clearly differ.
- Refusal is still an action. It should cost access, yield, position, time, or safety.
- Neutral exits are rare. If the player leaves, they should feel what was lost.

## Resource & Extraction Rules

Resource events should read like compressed telemetry:
- short sentences
- concrete material
- immediate consequence
- no generic loot phrasing

Extraction should usually show the system reacting:
- seams tighten
- glands spasm
- pressure drops or rises
- residue marks the body
- access narrows

Useful resource tradeoff shapes:
- controlled extraction: lower yield, lower bodily cost, less attention
- greedy extraction: higher yield, higher damage, danger, corruption, or future pressure
- stabilization: seal or suppress the source, gaining safety while losing material

## Visual Language

- Chunky, readable silhouettes
- Organic but structured forms
- Limited color coding:
  - Red -> baseline / flesh / pressure
  - Green -> growth / mutation / sustain
  - Blue -> swarm / alien / hostile system
  - Bone -> aftermath / death / structure

Everything should look:
> tactile, invasive, and functional

## The Merchant

The merchant is not a person.

They are:
> **a system that learned exchange**

Traits:
- Controlled
- Patient
- Never urgent
- Never surprised

They do not move like a human.
They do not touch directly.

All interaction is mediated.

Cadence rule:
- Merchant appearances should feel patient, rare, and slightly intrusive.
- The exchange is not a rest stop.
- It is another system pressure with its own hidden cost or deferred obligation.

## Design Goal

The game should feel like:

- You are **navigating a living machine**
- Every decision **echoes forward**
- There is no clean win state - only outcomes

## What This Is NOT

- Not survival horror: no helplessness
- Not power fantasy: no dominance
- Not pure roguelike repetition

It is:
> **a system-driven descent shaped by your decisions**

## Guiding Principle

> If the player hesitates for even a second before choosing, the design is working.
