# Story Scenario Contract

This is the forward quality bar for text-only Fleshpunk room scenarios.

The goal is not a better puzzle prompt or a clearer procedure sheet. The goal is a story engine where each drawn room scenario feels like a compact pulp scene inside a living progression-fantasy dungeon.

Use Revelation-scale scenario size as the target: a scenario should be large enough to feel like a small story beat with a premise, pressure, choice, result, and future implication, but not so large that it becomes a chapter or a rules explanation.

Each scenario should enrich Hymn, destabilize Hymn, or do both.

- `enrich`: adds capability, knowledge, reputation, alliance, body discipline, route understanding, tactical confidence, or mythic identity
- `destabilize`: adds appetite, injury, enemy attention, identity drift, body debt, faction suspicion, mutation hunger, route danger, or social/ecological misrecognition
- `both`: gives power in a way that changes what the world thinks Hymn is becoming

This is advancement progression fantasy through martial anatomy. The player is not just surviving rooms. They are being shaped into a more specialized, more consequential body.

Use `martial_progression_pressure_contract.md` as the forward pressure model. Use `body_option_contract.md` as the forward mutation/symbiote/pure-body model. New scenarios should declare `primary_pressure`, `body_path_pressure`, `avoidance_route`, and `recognition_effect` in designer metadata. Combat may be avoided, but avoidance must still be a meaningful martial or social choice rather than a skip.

The major forward pressure axes are:

- `hunt_pressure`: who or what is tracking Hymn because of noise, blood, broken routes, or unresolved predators
- `body_drift`: how far Hymn solves problems by becoming organism, graft, predator, tool, or symbiote host
- `baseline_discipline`: how far Hymn progresses through clean movement, breath, timing, pain tolerance, and tactical reading without rewriting her body
- `wound_debt`: what injuries, scars, overcommitments, and repair marks later rooms can exploit or recognize
- `recognition`: who learns what kind of fighter/body Hymn is becoming
- `route_memory`: how an environment family adapts to repeated tactics

Old labels such as corruption and danger may remain in runtime compatibility, but forward writing should frame them as body drift and hunt pressure.

Do not build the dungeon around revisiting one literal room. A room instance can echo prior choices, faction pressure, or learned behavior from similar spaces, but it should stand on its own when first encountered.

## Environment Families

Rooms are grouped by environment, not by literal repetition.

An environment is a reusable kind of space: pressure locks, marrow fields, operator cellars, scar-map junctions, larders, toll harbors, rite chapels, launch bores.

A room is one instance of that environment. It needs a specific local situation, actor, and choice. The next pressure lock is not the same pressure lock. It is another lock in the same living system, possibly changed by what the system learned elsewhere.

## Required Shape

Every forward scenario needs:

- An `environment_id` or other grouping identity that says what kind of space this belongs to.
- A concrete `corpus_influences` or `research_influences` entry naming the specific source passage, authorial move, scene energy, combat exchange, progression beat, or character function the scenario is trying to bottle.
- A clear room role: apparatus, enemy encounter, character encounter, symbiote offer, mutation offer, recovery, resource temptation, route choice, ambush, rest beat, story pressure, or simple passage.
- If the room is an apparatus room, name what work the environment performs when Hymn is not present. If it is not an apparatus room, do not invent machinery to satisfy the schema.
- A specific instance situation: what is happening in this drawn room right now.
- At least one interactable pressure point: animal, enemy, character, parasite, organ, tool, route intelligence, faction remnant, symbiote, mutation, wound, resource, or environmental hazard.
- Enough event coverage for the scenario's role. Broad environment-family rooms usually need multiple possible scenario events. A narrow role room, such as a symbiote-host choice, single ambush, recovery temptation, or mutation offer, can be complete with one focused event if the choice is playable, memorable, and consequential.
- A first-read description that gives enough background to make the current choice intelligible.
- A cold-reader context pass: a new player should understand what kind of place this is, what work the place normally performs, what actor or hazard is present now, where Hymn is positioned, why the decision is urgent, and what physical action each choice represents.
- Event text stands alone: `line_1` and `line_2` must still orient a cold reader if the room intro was skipped, interrupted by audio, or forgotten.
- A possibility tree: at least two meaningful branches or future pressures that can diverge from the player's choice.
- A character-change vector: enrichment, destabilization, or both.
- At least one delayed consequence, echo, altered future interpretation, route pressure, faction response, body appetite, or mutation opening.
- At least one environment memory flag or state change caused by a player choice when the scenario's consequences are persistent.
- At least one faction, recurring character, animal infrastructure, predator ecology, mentor/rival trace, or cross-run hook when the scenario touches social or ecological identity.
- At least one ending or progression vector that this environment can contribute to over repeated compatible behavior.
- Mutation hooks that describe which body changes can alter this environment's choices and which body changes this scenario can inspire.
- Body-option hooks that name the baseline discipline route, the relevant capability tags, and whether any mutation or symbiote branch changes the scene's pressure.

## Choice Standard

Choices should feel like story actions, not visible spreadsheet terms.

The player should understand the immediate fiction: what Hymn can do, touch, fight, swallow, refuse, spare, cut, study, follow, trade, or become. The player should not be handed a fully spelled-out risk ledger.

Prefer implied pressure:

- a tendon still trying to close around her wrist
- a rival watching how she moves
- a wound that drinks the room's warm vapor
- a passage that opens only while the predator feeds
- a symbiote matching her breathing before consent is clear

Avoid explicit labels in player-facing text:

- `+corruption`
- `risk: high`
- `future consequence`
- `ending pressure`
- `branch A / branch B`
- `safe option`
- `combat option`
- `mutation route`

Button text can be clear, but it should still be diegetic:

- `Hold the jaw open`
- `Let the spur grow`
- `Answer with the blade-arm`
- `Leave the rival breathing`
- `Drink only the clear layer`
- `Cut the bell cord before it learns the rhythm`

Every choice should answer:

- What is Hymn physically, socially, or tactically doing?
- What part of her identity does this action strengthen or disturb?
- What future pressure could plausibly remember this?
- What branch becomes more likely without announcing itself as a branch?

## Cold-Reader Context Standard

New scenarios have recently become interesting but too abstract. The generator must now front-load concrete orientation before specialized Fleshpunk terms carry the scene.

Do not rely on the room description to carry basic context. Every playable event should restate enough function, actor, position, and urgency to survive as the current screen by itself.

Before drafting player-facing prose, answer these six questions in the scenario notes:

- What ordinary function does this place perform when Hymn is not here? Examples: repair room, route organ, feeding site, toll crossing, predator den, training floor, bargaining mouth, recovery pool.
- What visible actor, animal, organ, rival, wound, tool, or hazard is present right now?
- Where is Hymn in relation to it? Examples: two steps inside the doorway, low ceiling over her shoulders, hound down-lane, mouth at wrist height.
- What changes if Hymn waits ten seconds?
- What physical action does each button represent in the next few seconds?
- What does a normal person need to know to follow the first read without lore notes?

Player-facing text should then use that context compactly. Do not write an encyclopedia paragraph, but do give a practical noun before an invented noun. "A route organ that records foot placement" is clearer than "a white marrow field." "A maintenance room where old hands steered repair tissue" is clearer than "operator cellar."

Avoid opening lines that lean on unexplained abstraction:

- "Something is using the wall."
- "The system recognizes me."
- "The room remembers."
- "The sequence wants my body."

Prefer visible mechanism and position:

- "A wall-braced predator has its limbs in the old tool holes."
- "The floor cut matches my stride."
- "The toll mouth lowers to wrist height."
- "The hound steps where my boot would land."

## Body Option Standard

Rooms should not be generated as mutation checklists.

Build the playable situation first, then identify one or two body capabilities that could change how Hymn handles it. The baseline pure-body route must remain complete and characterful: breath, timing, leverage, pain tolerance, restraint, reading, or a narrower tactical margin.

Use capability tags from `body_option_contract.md` in designer metadata and room hooks. Examples include `cut`, `brace`, `speed`, `burst`, `quiet_movement`, `read_damage`, `identity_spoof`, `scent_control`, `barrier`, `decoy`, `anchor`, and `death_intercept`.

Mutations should read as reliable always-on body identity. They can make a path cleaner, stranger, more forceful, more recognizable, or more vulnerable, but they should not become puzzle keys.

Symbiotes should read as stronger but less dependable partners. They can dominate a moment, but the room should acknowledge dormancy, cooldown, hunger, wound risk, preference, refusal, or relationship pressure in metadata and later consequences.

Player-facing prose should stay contained. Do not enumerate all compatible upgrades. Write the action in physical terms and let metadata name the qualifying tags.

## Corpus Influence Standard

Every scenario must be written under the influence of a specific piece of the corpus or research stack.

The forward corpus emphasis is pulp, martial anatomy, biological adaptation, roguelike pressure, and progression cadence. The old Verne/Lovecraft seed set is optional legacy material, not required and not preferred. Use it only when the user asks for it or when a room specifically needs sealed-vessel procedure, measurement, evidence accumulation, contamination records, or buried-history pressure. Otherwise choose from the newer pre-1930 pulp/research stack.

### Tier-0 Corpus Anchors

Corpus anchors are tier-0 story elements. They are not optional flavor, citations after the fact, or loose mood references.

Every forward scenario starts from one to three `corpus_anchors`. Each anchor must be sourced from a local whole-text corpus file or a named research source, and each anchor must define a concrete story job before drafting begins.

A valid tier-0 anchor names:

- `tier`: `0`
- `source_id`, `source_title`, and `source_author`
- `source_file` or stable research source
- `source_locator`: chapter, line span, section, or search handle
- `source_moment`: the source move being studied
- `story_element`: what this becomes in the room foundation
- `scenario_application`: how it changes the room description, choices, result text, pressure, progression, or combat

If the source anchor can be removed without changing the scenario's premise, choices, and consequences, the scenario has failed corpus discipline.

Tier-0 anchors should normally supply at least two of these foundations:

- a pressure engine: pursuit, shrinking ground, hunger, weather, debt, enemy attention, route collapse
- a combat or movement problem: range, line, timing, leverage, recovery, posture, forced commitment
- a progression prize or wound: learned stance, body discipline, mutation appetite, rank recognition, social debt, predator identity
- a story reversal: hunter/prey flip, guide turns rival, refuge becomes trap, victory creates debt, escape becomes recognition

This can be:

- a pulp scene function such as pursuit, duel, ambush, oath, betrayal, threshold crossing, lost-world descent, unsafe refuge, expedition exhaustion, or sudden reversal
- a character function such as rival, witness, guide, predator, oath-bound enemy, failed predecessor, captive, surgeon, scout, or claimant
- a martial structure such as measure, tempo, line, guard, clinch, recovery, overcommitment, leverage, wound opening, or pressure
- a biological adaptation such as armor segmentation, raptorial strike pocket, camouflage failure, sucker leverage, pressure tolerance, lure behavior, molt vulnerability, or distributed limb control
- a progression beat such as humiliation, breakthrough, training cost, rank challenge, new stance, social recognition, or identity narrowing
- a roguelike pressure such as hunger, trap readability, item uncertainty, route pressure, attrition, deck memory, or terrain interaction
- a passage-level writing move from the pulp corpus: compressed danger, hard physical stakes, hostile landscape acting before a monster appears, mythic rule stated through action, or reputation changing because of visible conduct

Do not use the corpus as a general vibe bucket, citation list, or idea mine. The point is not "this room uses a pressure suit from Verne." The point is to bottle some of the author's vitality and make the room writing deeper, stranger, and more specific.

Corpus influence must not create separate prose modes. The house style stays Hymn's empirical field report in every room. A Howard-influenced scenario may foreground decisive physical danger. A Sabatini-influenced scenario may foreground reversal, duel, reputation, or social consequence. A Blackwood-influenced scenario may foreground a landscape becoming hostile through evidence. A Merritt-influenced scenario may foreground awe turning into survival math. None of these should sound like pasted source prose. The player should feel different operating pressures, not different authors.

A scenario should include influence notes that can answer:

- Which source work and seed does this room use?
- What exact passage, scene function, exchange, object, incident, or character function is shaping the writing?
- What energy is being imported: pursuit, duel pressure, lost-world awe, threshold dread, reversal, physical confidence, ritual law, environmental hostility, breakthrough hunger, or social recognition?
- How should that influence change Hymn's room description, choice text, and result text?
- What enrichment, destabilization, branch, or progression pressure comes from that influence?

Preferred room metadata shape:

```json
"corpus_influences": [
  {
    "source_id": "howard_red_shadows",
    "source_title": "Red Shadows",
    "source_moment": "A pursuit scene turns moral purpose into immediate physical motion and consequence.",
    "writing_influence": "Compressed pulp momentum: the body acts before the world has finished explaining itself.",
    "scenario_application": "The predator encounter should begin with posture, distance, and intent. Hymn's choices should reveal whether she becomes hunter, escaped prey, or marked rival."
  }
]
```

Do not copy source prose, names, characters, or scenes. Do not flatten the source into a citation. Transform the source's writing energy into Fleshpunk material.

Use `generated/corpus/pulp_pre_1930/retrieval_index.md` when choosing local whole-text sources.

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
- HEMA lecture language in player-facing text unless the term is natural and obvious from context
- prose that explains the design intent before the player feels the situation

If Hymn infers, mark it as inference: "It looks like," "I have evidence for," "The marks suggest," or "I cannot confirm."

Hymn's player-facing narration can imply future pressure through an observable tell, but it should not state the future as system knowledge. The data may know that a follow-up is queued; Hymn should only see the cord still pulsing, the grub still chewing, the repair beetles moving, or the record blister sealing.

Avoid choices that only mean:

- gain biomass
- lose health
- lower danger
- raise corruption
- proceed safely
- fight or skip

Stats can still move, but they are not the point. The story consequence should remain legible if the numbers were hidden.

## Combat Standard

Combat is allowed, useful, and sometimes necessary. It is not mandatory.

When a scenario is meant to be action combat, it must not translate fighting concepts into an arcane procedure, sequence puzzle, lock/key test, or ritual apparatus. Martial anatomy is not a puzzle language. It is bodies under pressure.

An action-combat scenario must include:

- an active opponent, predator, rival, parasite, guard animal, or hostile body that can hurt Hymn now
- immediate contact or imminent contact in the root event
- readable spacing: who can reach whom, what blocks movement, and what range favors each body
- tactics as actions under pressure, not abstract technique names
- an enemy reaction, recovery problem, injury risk, positional shift, or opening after each choice
- enrichment or destabilization through the fight: learned stance, scar, appetite, rival attention, body debt, respect, fear, route access, mutation pressure, or new weakness

Avoid:

- grip sequences, ordered pores, pressure locks, ritual inputs, diagnostic tests, or machinery standing in for combat
- choices that mean "solve the martial puzzle" rather than "commit to a tactic while something is trying to hurt Hymn"
- HEMA lecture language, technique jargon, or anatomical cleverness without motion
- enemies that wait politely while Hymn reads the room

A combat scenario should be readable to a player who has never heard of HEMA. Use the research stack to make the fight physically true, then write the visible action.

Good combat writing gives:

- posture: what each body is ready to do
- distance: who can reach whom and what the room permits
- intent: kill, pin, test, feed, escape, display, punish, train, or claim
- commitment: what Hymn risks when she acts
- contact: what limb, blade, tail, tooth, horn, plate, or surface matters
- recovery: what is left open afterward
- consequence: scar, respect, fear, hunger, rival attention, learned stance, mutation appetite, or route change

Use simple words before specialist words:

- `too close for the tail` instead of `inside measure`
- `the blade-arm cannot turn in the duct` instead of `line denial`
- `it waits for her weight to settle` instead of `tempo trap`
- `the hook catches behind the knee` instead of `leverage exchange`

Combat should not be filler. If fighting does not enrich or destabilize Hymn, use a different pressure: bargain, passage, lure, injury, restraint, hunger, rival recognition, or mutation offer.

## Result Standard

Generic legacy action results are not enough for post-update rooms. A post-update event should either provide data-driven per-action result text or use an explicit engine handler that knows the room.

Good result text names what changed in the story:

- the toll mouth accepts underpayment as claim
- scar mites revise the quiet route
- bell polyps leak a Chorus signal
- platelet beetles close the damaged shortcut
- the larder scale distinguishes hunger from taking
- the rival lowers its horns because Hymn did not flinch
- the new spur changes how her foot finds the floor
- the wound learns to open when warm air passes over it
- the predator leaves because she smelled less like prey than kin

Weak result text only reports a stat:

- Danger settles to 1.
- Corruption rises to 2.
- Biomass: 6.
- I should keep moving.

Result text should keep branch pressure implicit. It can show a sign, scar, appetite, route change, or witness. It should not explain the possibility tree.

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

Forward endings should come from repeated character shaping: what Hymn keeps accepting, refusing, feeding, sparing, hunting, imitating, severing, or becoming.

Combat can feed an ending if it changes identity: predator, champion, oath-breaker, feared specimen, living weapon, escaped prey, or rival claimant. It should not feed an ending only because fights incremented a counter.

## Mutation Standard

Mutations are story capabilities, combat identities, and progression thresholds.

A mutation should not be designed primarily as damage, armor, or initiative. Each major mutation should be multi-use: it needs at least one in-encounter use and at least one out-of-encounter use.

In-encounter uses can include:

- combat posture
- reach
- grip
- defense
- pursuit
- escape
- intimidation
- restraint
- wound control
- predator misdirection

Out-of-encounter uses can include:

- hold pressure
- fit through a seam
- breathe fluid
- hide scent
- survive cold
- read signal
- brace against crush
- misdirect tracking
- negotiate status
- recognize a route
- endure an environment
- unlock a ritual or threshold
- communicate with altered organisms
- change how factions classify Hymn

Additional mutation uses can bridge both modes:

- threaten from a new range
- hold a new stance
- survive a specific predator tactic
- signal membership in a feared or desired body lineage
- unlock a breakthrough, molt, duel, challenge, or body discipline

The player should not always know where a mutation will help. The capability should be concrete enough that later use feels earned rather than arbitrary.

Legacy mutations can inspire mechanics, but forward mutation design should ask:

- What martial problem does this body solve?
- What story identity does it create?
- What older option does it make awkward or impossible?
- What new room verbs does it unlock?
- What appetite, witness, rival, faction, predator, or ending pressure does it invite?
- What is its in-encounter use?
- What is its out-of-encounter use?
- What surprising second use can the player discover later?

## Progression Standard

Fleshpunk progression is not a shop list of upgrades. It is a chain of bodily commitments.

Every scenario should be able to answer at least one progression question:

- What did Hymn learn about her body?
- What did the world learn about Hymn?
- What can she now attempt that she could not attempt before?
- What did she make harder for her future self?
- Who or what would recognize this change?
- What appetite or discipline did she strengthen?

Progression beats can be quiet. A scenario can advance the character by teaching a route, earning a witness, preserving restraint, refusing a body, or seeing a future rival, not only by granting mutation.

## Completion Bar

A scenario is not complete when it has valid buttons. A scenario is complete when a player can describe what kind of place this is, what is happening right now, what Hymn chose to become or resist, and what future pressure may have been created elsewhere in the dungeon.

## Variety Standard

Do not make every room an apparatus room.

The organism has infrastructure, but the game also needs enemies, characters, offers, quiet corridors, wounds, nests, pools, ambushes, and direct choices. A symbiote-host room can be about the body on the floor and the cost of bonding. A hunter room can be about whether Hymn fights, slips past, or misdirects it. A rest or recovery room can be about need, risk, and contamination. These rooms do not need extra valves, tally organs, beetles, route records, or pressure logic unless those elements are already the point.

Strong migration preserves the legacy room's core role first, then raises the writing level. If a legacy room is mostly "choose one symbiote," the forward version should make that choice vivid and consequential, not wrap it in unnecessary machinery.

Use enough setting texture to ground the room, then stop. One clear image and one playable pressure often beat a dense explanation of how the whole space works.
