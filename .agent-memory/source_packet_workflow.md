# Source Packet Workflow

Use this workflow before asking Claude, OpenAI, or another writing agent to draft player-facing Fleshpunk scenario prose.

## Rule

Do not send the whole repo, broad project context, or a freeform "write this scenario" prompt to an external writing agent.

Build a small source packet first. The packet is the writing contract. The generated patch should answer the packet, not rediscover the project.

## When Required

Use a source packet for:

- from-scratch room/scenario drafting
- substantial room/event rewrites
- recurring character arcs
- ending vectors
- delayed story follow-ups
- payoff triage rows classified as `inserted_scenario` or `delayed_scenario`
- prose refreshes after mechanics change

Do not use this workflow for tiny non-literary glue, malformed JSON repair, tests, or engine-only changes.

## Packet Contents

A source packet should include:

- Target scope: room ids, event ids, data files, whether this is replacement or additive.
- Current live context: relevant room record, current event/special event JSON, current deck placement if relevant.
- Design decision: the intended dilemma, branches, ending vector, and non-goals.
- Player-facing constraints: Hymn voice, cold-reader requirements, commandability, no revealed branch labels.
- Mechanics constraints: existing actions to prefer, allowed new handlers, required state flags, follow-up cadence.
- Source anchors: one to three tier-0 corpus/research anchors with structural moves and scenario application.
- Output contract: exact JSON shape or document shape, validation commands, and what must remain unapplied.

Keep the packet narrow. Include excerpts and summaries, not entire memory docs, unless the whole file is directly necessary.

## Workflow

1. Create or update a packet under `generated/`, for example:

```text
generated/amar_creepstride_source_packet.md
```

2. Review the packet before generation. The packet should make the requested draft possible without reading the whole repo.

3. Send only the packet plus the required output schema to the writing agent.

4. Save the response under `generated/` as an unapplied candidate.

5. For existing dangling follow-ups, triage before generating:

```sh
python tools/scenario_agent.py audit-feedback --json
python tools/scenario_agent.py triage-payoffs --include-pending-hooks --out generated/payoff_triage_report.md
```

Only build Claude source packets for rows classified as `inserted_scenario` or `delayed_scenario`. Use `audit-feedback` to catch branches that advance without an acknowledgement screen even when the delayed payoff audit is clean. Rows classified as `concrete_response` or `closed_pruned` should become small integration patches with concrete result/state closure, not new scenario prose.

6. Critique and validate the candidate before applying:

```sh
python tools/scenario_agent.py validate generated/SCENARIO_PATCH.json --strict-scenario-contract --strict-payoffs
python tools/scenario_agent.py critique --patch generated/SCENARIO_PATCH.json --out generated/SCENARIO_CRITIQUE.json
python tools/project_bootstrap.py --strict
```

6. Apply only after the candidate passes review, or manually integrate only the accepted structural pieces.

## Drift Checks

Before calling an external writer, stop if any of these are true:

- The prompt says "from scratch" but does not include current live data.
- The prompt names corpus sources but does not say what structural job each source performs.
- The prompt asks for final prose without an output schema.
- The model would need to infer existing actions, state flags, or follow-up mechanics from memory.
- The result would be hard to distinguish from an applied patch.

Fix the packet first.
