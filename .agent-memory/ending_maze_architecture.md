# Ending Maze Architecture

The game should behave more like a maze of endings than a puzzle box with a single win route.

Every environment family should have at least one ending it can lead toward. Not every path through that environment reaches the ending, but repeated choices, compatible mutations, refusals, payments, shortcuts, and delayed echoes can make that ending available.

## Core Rule

Each room instance asks a local question.

Each environment family asks a larger question.

Each ending answers that larger question.

Examples:

- Rib locks ask: does Hymn pass as measured cargo, paid account, damaged transit, or protected passenger?
- Larders ask: does Hymn become fed, indebted, rationed, or inventoried?
- Rite chapels ask: does Hymn become operator, tool, repaired subject, or refused procedure?
- Launch bores ask: does Hymn remain a field agent, become payload, or break the launch system?

## Ending Shape

An ending is not only failure. It is a terminal interpretation of Hymn's route.

Good endings:

- follow from repeated observable choices
- can be approached from several room instances in an environment family
- can be diverted by mutations, refusal, or contradictory behavior
- do not require combat
- are readable before they close
- have a clean terminal scene with `restart_run`

Legacy ending ideas to preserve:

- Merchant ending: too much exchange/debt/refusal puts Hymn fully on the scale.
- Overmutation ending: useful body changes accumulate until the boundary fails.

Forward ending ideas:

- Environment endings: each family has one terminal route.
- Mutation endings: mutations are not combat upgrades first; they are story capabilities that open, alter, or close room paths.
- Cross-family endings: a mutation gained in one family may solve, corrupt, or redirect another family's ending route.

## Mutation Role

Mutations are story keys and alternate verbs.

A mutation should answer:

- What room mechanism does this let Hymn interact with differently?
- What future room might this unexpectedly help with?
- What ending pressure does this mutation increase or reduce?
- What does the mutation make easier at the cost of making another interpretation more likely?

Do not design mutations primarily as combat math. Combat may be deprecated. Existing combat stat fields can remain as legacy compatibility, but forward mutation design should use capability tags.

Example capability tags:

- `brace_pressure`: hold or wedge pressure locks.
- `thin_body`: pass narrow seams without forcing damage.
- `heat_null`: cross cold marrow or avoid thermal tracking.
- `scent_mask`: misdirect pursuit and toll identification.
- `hard_shell`: survive crush, pressure, or tool contact.
- `wet_breath`: use fluid routes without contamination.
- `signal_sense`: detect Chorus or organism signal routing.

## Rib Vessel Lock Ending Seed

Environment: `rib_vessel_lock`

Ending id: `ending_soft_captain_transit`

Working title: The Soft Captain Route

Question: Can Hymn become a handled transit object without becoming debt, damage, or command payload?

Pressure sources:

- pulse measured by pressure plates
- biomass paid into tally valves
- rib seams forced open
- ferry-larvae protected or overloaded
- bell polyps muted or left transmitting
- platelet beetle repairs preserved, exploited, or misdirected

Ending approach:

- repeated careful passage, protected ferry use, and readable repairs make the transit system lower itself before Hymn acts
- too much payment diverts toward Merchant/Ledger endings
- too much forced opening diverts toward hunt/damage endings
- too much signal obedience diverts toward Chorus/launch endings
- compatible mutations can open alternate transit methods

Terminal scene:

Hymn enters a pressure lock that no longer asks for a choice. Ribs lower in sequence. Ferry larvae and valves move on pre-set timing. Chorus signal is delayed. The route carries her somewhere Chorus did not authorize.

This can be rescue, containment, or misrouting depending on surrounding pressure, but it should feel earned by earlier transit behavior.
