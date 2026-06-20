---
name: fleshpunk-claude-scenarios
description: "Generate or revise Fleshpunk: Inner Heart scenarios with Claude while preserving Codex as integrator, not prose author. Use when the user asks for Claude-authored scenario content, source packets, 7k input-token constrained prompts, external writing-agent drafts, new room/scenario data, deck wiring, scenario docs visibility, or repeatable content-generation workflow for this repo."
---

# Fleshpunk Claude Scenarios

Use this skill to run the repeatable Claude scenario workflow for `Fleshpunk: Inner Heart`.

Codex owns source-packet construction, tool execution, validation, integration, and repo wiring. Claude or another writing agent owns final player-facing scenario prose unless the user supplies exact text.

## Core Workflow

1. Reorient on active data:
   - Run `python tools/project_bootstrap.py --strict`.
   - Check `git status --short`.
   - Inspect the target room, events, deck, and docs allowlists before assuming generation is missing.

2. Build a narrow source packet:
   - Use `.agent-memory/source_packet_workflow.md` and `.agent-memory/content_authorship_workflow.md`.
   - Include the current style target from `.agent-memory/content_strategy.md`: future scenarios should feel closer to `operator_cellar` and `amar_creepstride_red_chapel` than to the scar-mite/maintenance/procedural rooms.
   - Keep the packet specific to the requested room/character/tension.
   - Include concrete source anchors, target room state, implemented actions, required branch shape, and non-negotiable constraints.
   - Root scenario passes should leave `payoff_hooks` metadata for separately generated follow-ups. Do not require Claude to write the follow-up in the same packet unless the user explicitly asks for a follow-up scenario.
   - When generating a follow-up pass, consume one existing `payoff_hooks` entry and replace/augment it with a concrete `story_followups` target: playable special event, `counts_as_room` when substantial, `room_id`, multiple choices, and concrete branch aftermath.
   - Do not send the whole repo or broad project context to Claude.

3. Generate with Claude through the blueprint agent:
   - Prefer `tools/fleshpunk_blueprint_agent.py` over ad hoc API payloads.
   - Use `--max-input-tokens 7000` unless the user gives a different input budget.
   - Treat the 7k limit as input-token budget, not output-token budget.
   - Use `--dry-run` first to confirm the estimated input budget.
   - Then generate blueprint and compiled candidate JSON.

4. Validate before applying:
   - Run `python tools/scenario_agent.py validate <candidate> --strict-scenario-contract --strict-payoffs`.
   - Run `python tools/scenario_agent.py audit-payoffs --json --include-pending-hooks` when checking unresolved hooks or existing follow-up debt.
   - Run `python tools/scenario_agent.py audit-feedback --json` when checking whether every branch shows immediate acknowledgement before advancing.
   - Run `python tools/scenario_agent.py triage-payoffs --include-pending-hooks --out generated/payoff_triage_report.md` before deciding which hooks become Claude follow-up packets.
   - Run `python tools/scenario_agent.py apply <candidate> --strict-scenario-contract --strict-payoffs --dry-run`.
   - Review branch logic manually for requirements the validator cannot see.
   - If Claude violates a design constraint, revise with Claude rather than hand-authoring final prose.

5. Apply and wire the content:
   - Apply only a validated candidate.
   - If the scenario should be playable or visible, update `encounter_decks_post_update.json`.
   - If the scenario should appear in docs, update `tools/room_doc_browser.py`.
   - If playtest slice tests use hardcoded allowlists, update `tools/playtest_slice_smoke.gd`.

6. Verify:
   - Run `python tools/project_bootstrap.py --strict`.
   - Run `godot --headless --path . --script tools/playtest_slice_smoke.gd` when deck membership changes.
   - Run `godot --headless --path . --script tools/story_followup_smoke.gd` when delayed events change.
   - Run `godot --headless --path . --script tools/post_update_room_smoke.gd` for post-update room safety.
   - Run `git diff --check`.
   - If a doc server is already running, restart stale `tools/room_doc_browser.py` processes and verify with `curl`.

## Reference

Read [references/fleshpunk-claude-workflow.md](references/fleshpunk-claude-workflow.md) for exact command templates, deck/docs wiring rules, and common failure modes.
