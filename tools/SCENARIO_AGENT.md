# Fleshpunk Scenario Agent

Generate scenario patches:

```sh
OPENAI_API_KEY=... python tools/scenario_agent.py generate --room bone_corridor --count 3
```

Generate within a broad category:

```sh
python tools/scenario_agent.py categories
OPENAI_API_KEY=... python tools/scenario_agent.py generate --room amber_corridor --category resource --count 2
```

Review the project voice guide:

```sh
python tools/scenario_agent.py vibe
python tools/scenario_agent.py lore-guide
```

Generate a local sample without OpenAI:

```sh
python tools/scenario_agent.py generate --room healing_pool --mock
```

Validate a patch:

```sh
python tools/scenario_agent.py validate generated/scenario_patch.json
```

Validate the current event data:

```sh
python tools/scenario_agent.py validate-events
python tools/scenario_agent.py validate-events --strict-actions
```

Critique a patch or the current event file against the vibe guide:

```sh
python tools/scenario_agent.py critique --patch generated/scenario_patch.json --out generated/patch_critique.json
python tools/scenario_agent.py critique --focus "Suggest new event types, encounters, and vibe guide updates."
```

Critique balance and run feel against the vibe guide:

```sh
python tools/scenario_agent.py balance-context
python tools/scenario_agent.py balance-critique --out generated/balance_critique.json
python tools/scenario_agent.py remember-balance generated/balance_critique.json --notes "Use this as current run-feel direction."
```

Critique fun factor and whether the organism is directing the run toward outcomes:

```sh
python tools/scenario_agent.py fun-context
python tools/scenario_agent.py fun-critique --out generated/fun_critique.json
python tools/scenario_agent.py remember-fun generated/fun_critique.json --notes "Use this as current fun-loop direction."
```

Critique lore continuity, Chorus usage, and Hymn's knowledge boundaries:

```sh
python tools/scenario_agent.py lore-context
python tools/scenario_agent.py lore-critique --out generated/lore_critique.json
python tools/scenario_agent.py remember-lore generated/lore_critique.json --notes "Use this as current lore direction."
```

Brainstorm new lore with gameplay hooks:

```sh
python tools/scenario_agent.py lore-brainstorm-context
python tools/scenario_agent.py lore-brainstorm --out generated/lore_brainstorm.json
python tools/scenario_agent.py remember-lore-brainstorm generated/lore_brainstorm.json --notes "Promote these lore hooks."
```

During play, `run_manager.gd` writes lightweight balance telemetry to `user://fleshpunk_run_balance_log.jsonl`.

Store critique guidance so future generation sees it:

```sh
python tools/scenario_agent.py remember-critique generated/content_critique.json --notes "Use this as the current creative direction."
```

Apply a JSON-only patch to `events.json`:

```sh
python tools/scenario_agent.py apply generated/scenario_patch.json
```

Record feedback so future generations adapt:

```sh
python tools/scenario_agent.py remember generated/scenario_patch.json --accepted --notes "Good tone; make risk clearer next time."
python tools/scenario_agent.py remember generated/scenario_patch.json --rejected --notes "Too generic; avoid fantasy language."
```

Notes:

- By default, the agent must use existing action ids from `run_manager.gd`.
- Event `type` values must match one of the category ids in `.agent-memory/event_categories.json`.
- Use `--allow-new-actions` only when you want it to propose engine work.
- The model can suggest mutations, symbiotes, or enemies, but this first tool only applies event patches automatically.
- Memory lives in `.agent-memory/`.
