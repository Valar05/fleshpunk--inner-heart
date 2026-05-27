# Glue Layer Contract

This is the forward contract for Fleshpunk connective tissue: opening beats, inter-room insertions, delayed follow-ups, faction pressure scenes, route transitions, threshold warnings, and near-ending pressure.

The glue layer exists to make separate room scenarios feel like one run through a living organism.

It must not become exposition, lore dump, risk ledger, or a second room hidden between rooms. A glue beat is a short scene where a prior choice moves through the organism and comes back with leverage.

## Core Thesis

Rooms ask local questions.

The glue layer asks: who noticed, what did the route learn, what debt moved, what body habit is forming, and what will happen if Hymn repeats it?

A good glue beat has:

- a specific prior action or pressure pattern
- a visible carrier: cord, feeder, receipt blister, scar mite, lens film, ferry larva, route packet, blood trace, symbiote twitch, repair animal, scale mark
- an active agent or system with leverage
- a small choice, not just an echo
- a concrete consequence in the next one to three rooms
- one pressure-axis movement
- one corpus or research anchor used structurally

## What Counts As Glue

### Opening Frame

Sets the run premise before the first room.

It should establish:

- mission entry
- Chorus silence or limited authority
- no clean exit
- first body choice or first body pressure
- one visible sign that the organism is already sorting Hymn

The opening should not explain factions, clone truth, or the full setting.

### Inter-Room Pressure Beat

Fires after a prior room choice with a short delay.

It should do one of these:

- offer a costed favor
- remove or mask one option next room
- alter a price
- schedule a predator, toll, or route counter
- reveal a witness
- deepen a body path
- convert an echo into a playable intervention

### Pattern Warning

Fires on the second repetition of a behavior.

It should make the pattern visible and give the player a chance to break it before the system counters.

Examples:

- two quiet marked lanes make plate teeth pre-align
- two forced passages bring a repair-hunter close enough to hear
- two symbiote activations make the partner anticipate danger before Hymn asks
- two larder debts make the Quartermaster expose a tooth-count

### Pattern Counter

Fires on the third repetition or after refusal of a warning.

It should remove a safe option, raise a price, force a predator, alter a deck weight, or push an ending route.

The counter must feel like the organism learned Hymn's conduct, not like random punishment.

### Character Pressure Beat

Turns a named faction/character into leverage.

It must show desire through action:

- Soft Captain wants quiet transit discipline
- Quartermaster wants balanced intake and paid accounts
- Commandant Signal wants clean mission data and obedience under risk
- Pell wants route grammar completed, even when it becomes predictable
- Dr. Silt Vey wants procedure continued and sampled
- Lumen Brack wants recovery made legible through contamination markers
- Glass Apostle wants to read and be read back
- Merchant wants claim
- Blood Ledger wants unpaid choices made physical

If the character cannot change options, prices, routes, pressure, deck state, or body interpretation, the beat is not ready.

### Body Path Beat

Recognizes the kind of body Hymn is becoming.

It should use `body_option_contract.md`:

- baseline discipline: breath, timing, restraint, clean read, pain tolerance
- mutation path: reliable body identity with visible weakness or recognition
- symbiote path: stronger help with need, cooldown, wound, refusal, or relationship pressure

The beat should not list upgrade names in player-facing text. Use physical tells.

## Corpus Anchor Rules

Glue beats need tier-0 anchors too.

A glue beat may use smaller anchors than a full room, but they must still be load-bearing.

Use the local corpus/research stack by story job:

- Merritt: threshold awe becoming operational danger; strange systems that lure before they strike
- Howard: immediate action, pursuit, chamber pressure, visible bodily consequence
- Sabatini: reversal, social consequence, reputation, duel pressure, bargain under threat
- Haggard: expedition route cost, map uncertainty, survival logistics, taboo thresholds
- Blackwood/Hodgson/Shiel: hostile landscape as actor, distance, silence, weather, dark, or pressure becoming enemy
- Dunsany: short cruel rule that behaves like a fable but resolves as a game mechanic
- Burroughs: body mastery, ecological fitness, hierarchy recognition
- Machen: threshold contamination and body/social recognition breaking
- combat research: posture, range, commitment, recovery, leverage
- biology research: animal infrastructure, sensory organs, adaptation, appetite, symbiosis
- roguelike research: readable danger, item/route uncertainty, attrition, deck memory

Do not cite a source because it matches mood. Cite it because it changes the trigger, carrier, choice, consequence, or pressure axis.

## Glue Beat Shape

Recommended metadata:

```json
{
  "id": "story_soft_captain_second_count",
  "type": "story",
  "thread": "soft_captain",
  "trigger": "pulse_synced twice without forced rib in last 5 rooms",
  "delay_rooms": 2,
  "source_anchors": [
    {
      "tier": 0,
      "source_id": "haggard_king_solomons_mines",
      "source_file": "generated/corpus/pulp_pre_1930/texts/haggard_king_solomons_mines_pg2166.txt",
      "source_moment": "expedition survival depends on route discipline and limited supplies",
      "story_element": "quiet transit becomes a scarce route favor",
      "scenario_application": "the cord offers a clean passage but masks force/payment options next rib lock"
    }
  ],
  "prior_choice_visible": "cord still holds Hymn's wrist interval",
  "agent_desire": "Soft Captain wants quiet compliant transit",
  "player_question": "Accept help that narrows future options, or keep autonomy louder?",
  "pressure_axis": "route_memory",
  "next_room_effect": "next_rib_lock_mask_soft",
  "ending_pull": "ending_soft_captain_transit",
  "line_1": "A transit cord drops and matches my wrist.",
  "line_2": "One nearby lock answers on that beat. If I hold now, it opens quiet and narrow.",
  "choices": ["Match the beat", "Refuse the cord"]
}
```

## Player-Facing Style

Glue text should be short.

Prefer:

- one concrete carrier
- one visible prior mark
- one pressure question
- one action result

Avoid:

- "future consequence"
- "branch"
- "safe option"
- "risk/reward"
- "this queues"
- abstract "something"
- faction names without visible bodies or mechanisms
- lore explanation that does not change play

Use Hymn's field-report voice. Chorus may be addressed, but Chorus does not answer on-screen.

## First Fifteen Minutes

The opening span should produce clear player questions:

1. What is attached to me?
2. Who owns the route?
3. Who prices survival?
4. What happens when I repeat a useful method?
5. Is purity a path or just refusal?
6. Is the organism reacting to my body, my choices, or both?

The first fifteen minutes should include:

- opening descent
- first symbiote/purity choice
- first route/account choice
- first combat or predator pressure
- first delayed follow-up that changes an option or price
- first pattern warning, even if no counter has fired yet

## Acceptance Tests

A glue beat is accepted when:

- a new player can identify what prior action caused it
- the visible carrier is concrete
- the beat gives at least two playable choices unless it is a terminal transition
- it changes next-room behavior, pressure, deck state, price, or recognition
- it has a source/research anchor that is load-bearing
- it does not reveal clone truth
- it does not explain the full lore
- it can be skipped in a run without breaking the story
- repeated behavior escalates through warning before counter

Reject glue that only says "the room remembers" without showing what is carrying the memory.
