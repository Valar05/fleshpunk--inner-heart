# Fleshpunk Scenario Agent Style Memory

Use first-person, immediate, bodily narration from Hymn.
Do not render a speaker label such as `Her:`.

Preferred texture:
- Bio-industrial rooms that behave like organs, machines, and traps.
- Choices with tradeoffs: biomass, danger, corruption, health, shield, mutations, symbiotes, or combat exposure.
- Short lines. The UI usually presents two spoken lines and two or three buttons.
- Consequences should be legible before they are chosen, but not fully safe.
- Hymn reports to Chorus frequently for instruction or confirmation.
- Chorus is never heard directly.
- Hymn does not know she is a clone. Never reveal that knowledge in her narration.
- The organism should feel like it notices patterns and answers them.
- Repeated decisions should push the run toward corruption, danger/hunter, debt, starvation, injury, narrowed access, or another ending pressure.
- The best ending requires balance and neutrality, not maximal power or maximal avoidance.

Fun-factor critique lens:
- Does this create desire to take one more room?
- Does the choice tempt the player into a pattern?
- Does the organism react if the player repeats that pattern?
- Is there feedback before the run locks into an ending?
- Is this more than a stat trade?

Avoid:
- Modern jokes, lore exposition dumps, and generic fantasy magic.
- Long paragraphs.
- Copying exact phrasing from external sources.
- Adding new actions unless the patch also calls out required engine changes.
- Clean rewards with no pressure response.
- Choices that only move numbers without changing future rooms, pressure, warnings, or ending gravity.
- Meta run-language in narrated text: clone, next clone, build, card, ending, stat, or system.

Existing useful actions:
- `proceed`
- `combat`
- `take_mutation`
- `leave_mutation`
- `take_symbiote`
- `leave_symbiote`
- `drink_pool`
- `study_pool`
- `retreat`
- `harvest_eggs`
- `cauterize_eggs`
- `slip_between_eggs`
- `siphon_amber`
- `overdraw_amber`
- `seal_amber_wound`
- `leave_amber`
- `take_green_tunnel`
- `cut_green_spine`
- `listen_at_green_split`
- `open_red_artery`
- `brace_through_red_split`
- `mark_red_branch`
- `push_through_spikes`
- `leave_merchant`
- `run`
