# Story Room Contract

This is the forward quality bar for text-only Fleshpunk rooms.

The goal is not a better puzzle prompt. The goal is a story engine where each drawn room instance feels like a specific place inside a larger environment family.

Do not build the dungeon around revisiting one literal room. A room instance can echo prior choices, faction pressure, or learned behavior from similar spaces, but it should stand on its own when first encountered.

## Environment Families

Rooms are grouped by environment, not by literal repetition.

An environment is a reusable kind of space: pressure locks, marrow fields, operator cellars, scar-map junctions, larders, toll harbors, rite chapels, launch bores.

A room is one instance of that environment. It needs a specific local situation, actor, and choice. The next pressure lock is not the same pressure lock. It is another lock in the same living system, possibly changed by what the system learned elsewhere.

## Required Shape

Every forward room needs:

- An `environment_id` or other grouping identity that says what kind of space this belongs to.
- A concrete `corpus_influences` entry naming the specific source passage, authorial move, scene energy, or character function the room is trying to bottle.
- A concrete organism function: what work this environment performs when Hymn is not present.
- A specific instance situation: what is happening in this drawn room right now.
- At least one interactable actor or infrastructure system: animal, organ, parasite, tool, route intelligence, faction remnant, or recurring character trace.
- Three or more room events before the room is considered complete.
- A first-read description that gives enough background to make the current choice intelligible.
- At least one delayed consequence that appears in a later room instance, special event, deck pressure, or environment echo.
- At least one environment memory flag or state change caused by a player choice.
- At least one faction, recurring character, animal infrastructure, or cross-run hook that affects future text, room selection, or pressure.
- At least one ending vector that this environment can lead toward.
- Mutation hooks that describe which future body changes can alter this environment's choices.

## Choice Standard

## Corpus Influence Standard

Every room instance must be written under the influence of a specific piece of the corpus.

This can be:

- a motif such as pressure, sealed compartments, shipwreck rationing, polar survey marks, or ruined architecture
- a structure such as a lock, raft, cabin, pressure suit, captain's command chain, hold, pump, chart, or divided vessel
- a character function such as captain, witness, engineer, merchant, survivor, surveyor, or operator
- a concrete source incident such as a leak entering one compartment, a double hatch opened by screw pressure, or a damaged hull admitting water
- a passage-level writing move such as Verne's procedural exactness, escalating mechanical wonder, measured danger, confident apparatus description, or Lovecraft's accumulated evidence, buried history, architectural dread, or forensic uncertainty

Do not use the corpus as a general vibe bucket, citation list, or idea mine. The point is not "this room uses a pressure suit from Verne." The point is to bottle some of the author's vitality and make the room writing deeper, stranger, and more specific.

Corpus influence must not create separate prose modes. The house style stays Hymn's empirical field report in every room. A Verne-influenced room may foreground sequence, pressure, and apparatus; a Lovecraft-influenced room may foreground residue, prior-use evidence, contamination, and buried history. Neither room should sound like pasted Verne or pasted Lovecraft. The player should feel different operating pressures, not different authors.

A room should include explicit influence notes that can answer:

- Which source work and seed does this room use?
- What exact passage, scene function, object, incident, or character function is shaping the writing?
- What writing energy is being imported: pace, density, syntax, procedural confidence, dread accumulation, observational stance, escalation, cataloguing, or historical pressure?
- How should that influence change Hymn's room description and choice text?
- What choice or ending pressure comes from that influence?

Preferred room metadata shape:

```json
"corpus_influences": [
  {
    "seed_id": "verne_twenty_thousand_leagues_02_sealed_vessel",
    "source_title": "Twenty Thousand Leagues Under the Seas",
    "source_moment": "The narration slows down to explain compartments, pressure, hull resistance, and operational sequence before danger resolves.",
    "writing_influence": "Verne's verve here is procedural wonder: exact parts, sequence, measurement, and danger made legible through engineering detail.",
    "room_application": "The room description should make the rib lock feel like a working apparatus, not a symbol. Choices should read as operations Hymn can test."
  }
]
```

Do not copy source prose, names, characters, or scenes. Do not flatten the source into a citation. Transform the source's writing energy into Fleshpunk material.

## Hymn Narration Standard

Hymn's narration should be clean and empirical.

Prefer:

- observed structure, motion, pressure, residue, markings, damage, sound, heat, count, timing, and body position
- cautious operational conclusions based on visible evidence
- "I can test / pay / force / wait" instead of mythic or moral framing

Avoid:

- scripture cadence
- mystical or devotional language unless Hymn is explicitly describing a built ritual object
- claims that the organism wants, judges, remembers, or understands unless there is visible evidence
- claims that Hymn knows a future consequence before the room has produced evidence for it
- metaphor that hides the practical situation
- abstract labels such as cargo, debtor, invitation, proof, fate, or claim when a physical description will do

If Hymn infers, mark it as inference: "It looks like," "I have evidence for," "The marks suggest," or "I cannot confirm."

Hymn's player-facing narration can imply future pressure through an observable tell, but it should not state the future as system knowledge. The data may know that a follow-up is queued; Hymn should only see the cord still pulsing, the grub still chewing, the repair beetles moving, or the record blister sealing.

Every choice should answer:

- What is Hymn physically doing?
- What system is she interacting with?
- What immediate bargain does the player understand?
- What does this environment or actor learn, remember, charge, damage, open, close, or misread later?

Avoid choices that only mean:

- gain biomass
- lose health
- lower danger
- raise corruption
- proceed safely
- fight or skip

Stats can still move, but they are not the point. The story consequence should remain legible if the numbers were hidden.

## Result Standard

Generic legacy action results are not enough for post-update rooms. A post-update event should either provide data-driven per-action result text or use an explicit engine handler that knows the room.

Good result text names the local mechanism:

- the toll mouth accepts underpayment as claim
- scar mites revise the quiet route
- bell polyps leak a Chorus signal
- platelet beetles close the damaged shortcut
- the larder scale distinguishes hunger from taking

Weak result text only reports a stat:

- Danger settles to 1.
- Corruption rises to 2.
- Biomass: 6.
- I should keep moving.

## Follow-Up Standard

Story follow-ups should be one-shot beats with at least one intervening room. They should not act like extra immediate result text.

If an event has multiple choices, prefer action-specific follow-ups. A single `default` follow-up is acceptable only when every choice plausibly awakens the same later beat through a different route.

Follow-ups must be concrete consequences, not only repetition or ambience. The chain should be legible in the data and implied through Hymn's field report. Separate designer knowledge from narrator knowledge:

- what Hymn did
- what system, creature, debt, signal, repair crew, or pursuer was activated
- when it can return
- what new situation appears
- what it offers or costs
- what Hymn can actually observe at the moment of narration

Strong follow-up logic:

- Hymn feeds biomass into a tongue-scale.
- The larder wakes a reserve pocket.
- A ration capsule opens later.
- In the follow-up event, Hymn sees a softened ration pocket and a live scale count.

Weak follow-up logic:

- A later larder recognizes payment.
- The same marks appear again.
- Another room feels changed.
- Hymn says the future pocket will open two rooms later.

Use `queued_line` on story follow-ups when possible so the immediate result gives a diegetic tell: a cord stores pulse, a grub keeps chewing, a repair crew starts moving, a route packet enters the signal. Do not print labels like "cause," "effect," "event deck," or "queued" in player-facing text, and do not let Hymn announce the exact future payoff.

## Environment Echo Standard

Do not rely on returning to the same room. Use environment echoes instead.

An environment echo is a later instance or special event that makes prior behavior legible:

- another pressure lock recognizes unpaid debt
- a marrow field places marks where Hymn tends to step
- a toll mouth uses a previous payment as proof she can owe
- platelet beetles close shortcuts in later damaged corridors
- bell polyps leak a Chorus signal into another environment
- a rite chapel treats prior obedience as operator posture
- a launch bore prepares for her before she arrives

These echoes can be implemented as delayed special events, environment-level state, deck weighting, altered room instance text, or changed action results. They should not depend on literal room revisits.

Echoes should vary the next room instance. A later pressure lock can be friendlier, more hostile, already prepared, partially sealed, or operating with a different organ set. Do not write it as the exact same chamber remembering Hymn. Write it as the same living system applying what has changed across a different local situation.

## Ending Standard

Every environment family should have a possible ending.

The ending does not need to trigger from every event. The ending should become available through repeated or compatible behavior across room instances.

An environment ending should state:

- what behavior pulls Hymn toward it
- what behavior diverts her to another ending
- which mutations can open alternate approaches
- what physical terminal scene shows the accumulated pattern

Combat is legacy pressure, not the forward default. Forward endings should come from route logic, debt, mutation, repair, signal, hunger, measurement, contamination, obedience, refusal, or misdirection.

## Mutation Standard

Mutations are story capabilities.

A mutation should not be designed primarily as damage, armor, or initiative. It should let Hymn interact with future rooms differently:

- hold pressure
- fit through a seam
- breathe fluid
- hide scent
- survive cold
- read signal
- brace against crush
- misdirect tracking

The player should not always know where a mutation will help. The capability should be concrete enough that later use feels earned rather than arbitrary.

## Completion Bar

A room is not complete when it has valid buttons. A room is complete when a player can describe what kind of place this is, what is happening in this instance, why the choices matter, and what future pressure they may have created elsewhere in the dungeon.
