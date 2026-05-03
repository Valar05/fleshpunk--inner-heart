# Fleshpunk: Inner Heart - Accessibility Guide

This game is audio-first.
Visuals may support mood, but no required information may exist only in art, color, animation, or layout.

## North Star

The game must be fully playable without looking at the screen.

Every turn must make clear:
- where Hymn is
- what changed
- what choices are legal
- what each choice is likely to cost
- what state pressures are rising or falling
- what the player can say next

## Command Model

The speech system should feed text into the same command parser used for typed commands.

Core commands:
- one
- two
- three
- repeat
- repeat choices
- status
- inventory
- help
- confirm
- cancel
- pause
- continue
- slower
- faster

Context commands:
- fight
- run
- leave
- withdraw
- pay
- skip
- study
- harvest
- listen
- probe
- drink
- cut
- break
- activate barrier
- activate pheromones
- activate mitosis

## Event Requirements

Every button must have:
- label
- action
- voice_aliases

Voice aliases should be short, distinct, and natural to say.

Example:

```json
{
  "label": "Pay 5 biomass",
  "action": "pay_resin_toll",
  "voice_aliases": ["pay", "pay toll", "feed toll", "give biomass"]
}
```

## TTS Rules

Narration should be phrase-based.

Avoid:
- long paragraphs
- nested clauses
- visual-only descriptions
- choices hidden inside prose
- multiple mechanical changes in one unbroken sentence

Prefer:
- short room narration
- short pressure line
- numbered choices
- explicit result lines
- status summaries on request

## Result Rules

After every action, audio must state the important mechanical change.

Examples:
- "Danger rises to 3."
- "Biomass: 8."
- "Dependence mark added."
- "Merchant Claim rises."
- "Barrier blocked 4 damage."

## Ambiguity Rules

If a spoken command maps to more than one legal action, ask for confirmation.

If a command is unknown, say:
- "I did not match that."
- "Say repeat choices, status, or a choice number."

The parser should never invent actions.
It may only choose from current legal buttons, global commands, and legal symbiote activations.

## Ending Rules

Every ending must explain cause.

The player should be able to ask why:
- "why"
- "explain"
- "what happened"

The answer should summarize the pressure path without exposing clone truth.

## Audit Rules

Flag:
- buttons without voice aliases
- duplicate aliases within one encounter
- aliases that collide with global commands
- visible-only information
- missing state-change result text
- overly long TTS lines
- generic or ambiguous button labels
- ending text without cause
- any required information carried only by sprite, color, or animation
