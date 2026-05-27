# Fleshpunk Research: Combat Intelligence

## Scope

This note translates martial references into Fleshpunk design constraints. It is not a prose source and should not be used to copy historical terminology into player-facing text.

Core premise: every combat mutation should behave like a body-mounted weapon with range, line, tempo, recovery, leverage, exposure, and tactical debt.

## Source Touchpoints

- Wiktenauer main library: https://wiktenauer.com/wiki/Main_Page
- Fiore de'i Liberi overview: https://wiktenauer.com/wiki/Fiore_de%27i_Liberi
- Fiore spear plays: https://wiktenauer.com/wiki/Fiore_de%27i_Liberi/Spear
- Fiore sword vs. spear: https://wiktenauer.com/wiki/Fiore_de%27i_Liberi/Sword_vs._Spear
- Fiore poleaxe: https://wiktenauer.com/wiki/Fiore_de%27i_Liberi/Poleaxe
- Fiore sword in two hands, narrow play: https://wiktenauer.com/wiki/Fiore_de%27i_Liberi/Sword_in_Two_Hands/Narrow_Play
- Liechtenauer and four guards: https://wiktenauer.com/wiki/Liechtenauer and https://wiktenauer.com/wiki/Vier_Leger
- Jack Slack / fight-analysis layer: use as modern structural reference for stance, feints, counters, pressure, footwork, clinch, and range management.

## Useful Abstractions

### Measure

Measure is whether a body can threaten or be threatened from its current range.

Fleshpunk use:

- tail, proboscis, hooked limb, tongue, spine fan, and throwing organ all define different threat rings
- longer reach should create recovery debt, turning problems, close-range weakness, or anchoring cost
- short weapons should need entry, cover, misdirection, or body commitment
- rooms can ask whether the player fights outside, inside, or under an enemy's preferred measure

Generation rule: never write "attack" without implying range.

### Tempo

Tempo is the timing unit created by commitment, recovery, hesitation, or forced reaction.

Fleshpunk use:

- heavy bone blades should win a committed exchange but lose when baited
- fast tendons should interrupt but create exhaustion or tearing risk
- ambush organs should have one perfect beat, then weakness if they miss
- defensive mutations should buy one tempo, not permanent safety

Generation rule: every combat choice should say what timing advantage it buys or spends.

### Line Control

Line is the path between weapon and target.

Fleshpunk use:

- horn, stinger, spear-tail, and thrusting limb need open lines
- shield plates and folded limbs deny lines
- hooked or chopping limbs alter the line by dragging, pinning, or turning the target
- narrow corridors, grates, rib-lanes, ducts, and hanging organs should matter because they open or close lines

Generation rule: describe obstacles and enemy posture as combat geometry, not decoration.

### Leverage

Leverage is where force is applied against joints, armor, balance, or anchor points.

Fleshpunk use:

- grappling mutations should attach to joints, plates, tendons, throat, spine, weapon limb, or footing
- polearm-like mutations should push, lever, drag, or pin, not only stab
- armor can become a lever target if it catches, locks, or slows rotation
- extra limbs should change leverage networks and make new takedowns or escapes possible

Generation rule: if a mutation has hooks, suckers, clamps, barbs, or tendrils, it needs leverage verbs.

### Commitment And Recovery

Strong attacks should cost stance, breath, skin integrity, attention, or position.

Fleshpunk use:

- the first strike from a heavy mutation should matter; missing should expose the player
- recovery creates the window where enemies punish overuse
- armor can reduce injury but worsen recovery
- flexible tissue can recover faster but may lack stopping power

Generation rule: a strong mutation must have a miss-state, fatigue-state, or counter-state.

### Guard, Stance, And Posture

Guards are readiness states: what the body protects, threatens, and cannot do quickly.

Fleshpunk use:

- low guard: protects belly/legs, prepares thrust or spring, exposes upper line
- high guard: threatens chop or drop, exposes flank and legs
- coiled guard: stores elastic strike, weak to being forced early
- plated guard: absorbs, waits, and narrows choices
- sprawled guard: good for grappling and pinning, poor for retreat

Generation rule: mutations should offer stance identities, not only powers.

## Mutation-To-Weapon Translation

| Anatomy | Weapon Logic | Preferred Range | Strength | Weakness |
| --- | --- | --- | --- | --- |
| Scorpion tail | spear / estoc / rear-line thrust | medium-long | line threat, poison delivery, pursuit check | flank exposure, recovery after miss, poor inside range |
| Blade-arm | sword / axe / hook | close-medium | cut, chop, bind, sever, control limb | needs line and shoulder room |
| Horn / tusk | lance / shield rush | entry range | breaks guard, pins, charges | overcommitment, bad turn radius |
| Raptorial forelimb | trap, grab, puncture | exact striking pocket | explosive capture | whiffs if baited outside pocket |
| Tendril / tongue | whip / rope / grapple | variable | disarm, trip, drag, sense | weak if cut, pinned, or tangled |
| Carapace / shell | armor / shield | close-medium | absorbs and lets player pressure | heat, weight, slow recovery |
| Sucker arm | clinch / distributed grapple | close | controls multiple points | vulnerable to blades, fire, tearing |
| Spine fan | area denial / caltrops | close-medium | punishes entry | poor pursuit, catches environment |
| Acid gland | thrown hazard / gas / softening agent | medium | controls space, weakens armor | friendly contamination, wind/flow risk |
| Wing membrane | footwork / angle change | open space | escape, reposition, dive | cramped rooms, puncture |

## Combat Event Shape

Use this structure for generated combat events:

1. Threat posture: what the enemy body is ready to do.
2. Player body option: what mutation or stance changes the geometry.
3. Commitment: what the player spends or risks.
4. Exchange: what line/tempo/leverage changes.
5. Recovery state: what remains open afterward.
6. Future consequence: scar, exhaustion, respect, fear, mutation appetite, faction attention, route change, or enemy adaptation.

## Anti-Patterns

- "The creature lunges" with no range, posture, or line.
- Damage numbers without positional cause.
- Mutations that are generic spell buttons.
- "Fast" or "strong" with no recovery cost.
- Grapples that do not name what is controlled.
- Armor that only reduces damage and does not change movement.
- Combat choices with no future scar, appetite, or tactical memory.

