# Fleshpunk Claude Scenario Workflow

## Command Templates

Dry-run input budget:

```bash
python tools/fleshpunk_blueprint_agent.py \
  --room <room_id> \
  --prompt "<specific scenario request and constraints>" \
  --model claude-sonnet-4-6 \
  --max-input-tokens 7000 \
  --max-output-tokens 12000 \
  --out generated/<slug>_blueprint.json \
  --compile-out generated/<slug>_claude_candidate.json \
  --dry-run
```

Generate:

```bash
python tools/fleshpunk_blueprint_agent.py \
  --room <room_id> \
  --prompt "<same tightened prompt>" \
  --model claude-sonnet-4-6 \
  --max-input-tokens 7000 \
  --max-output-tokens 12000 \
  --out generated/<slug>_blueprint.json \
  --compile-out generated/<slug>_claude_candidate.json
```

Validate and apply:

```bash
python tools/scenario_agent.py validate generated/<slug>_claude_candidate.json --strict-scenario-contract --strict-payoffs
python tools/scenario_agent.py audit-payoffs --json --include-pending-hooks
python tools/scenario_agent.py triage-payoffs --include-pending-hooks --out generated/payoff_triage_report.md
python tools/scenario_agent.py apply generated/<slug>_claude_candidate.json --strict-scenario-contract --strict-payoffs --dry-run
python tools/scenario_agent.py apply generated/<slug>_claude_candidate.json --strict-scenario-contract --strict-payoffs
```

Post-apply checks:

```bash
python tools/project_bootstrap.py --strict
godot --headless --path . --script tools/story_followup_smoke.gd
godot --headless --path . --script tools/post_update_room_smoke.gd
godot --headless --path . --script tools/playtest_slice_smoke.gd
git diff --check
```

## Prompt Shape

Use a compact prompt with:

- Target room id and scenario role.
- Style target: closer to Operator Cellar and Amar/Red Chapel than to mite-room procedure.
- Required branch shape.
- Explicit forbidden drift.
- Required `payoff_hooks` behavior for separately generated follow-ups.
- Required pure-body baseline.
- Concrete body/action prose requirement.
- "No markdown, no labels in player-facing lines."

Example pattern:

```text
Rewrite <character/room> from scratch as a compact playable scenario.
Keep estimated input under 7000 tokens.
Style target: closer to Operator Cellar and Amar/Red Chapel: immediate, confrontational, bodily, readable, and character-pressured.
Avoid mite-room drift: no apparatus-first ritual/procedure/ecology puzzle unless it becomes a live scene with an actor, threat, rival, witness, debt-holder, predator, or bodily commitment.
Root choices must be: <choice A>; <choice B>; <choice C>.
IMPORTANT: <non-negotiable branch rule>.
Root scenario pass: leave payoff_hooks for the branches that need follow-up; do not author the follow-up in this same packet.
Only generate Claude packets for `inserted_scenario` and `delayed_scenario` triage rows; resolve `concrete_response` and `closed_pruned` rows with small integration patches.
Follow-up pass: consume one named payoff_hook and wire the generated special event through story_followups.
Preserve a pure-body baseline route.
Use concrete body/action prose. No markdown, no labels in player-facing lines.
Keep output compact enough to finish.
```

## Manual Review Checklist

Before applying, check:

- The estimated input tokens are under the requested cap.
- Root event starts from active pressure, not exposition.
- Player-facing text omits author/source names, branch labels, risk labels, and stat math.
- Kill/mercy/debt/follow-up branches match the user's stated design.
- Root scenario generations leave `payoff_hooks` instead of same-pass follow-ups unless asked otherwise.
- Follow-up generations consume a specific `payoff_hooks` entry and then add `story_followups` only when the target special event exists.
- `story_followups` only exist for branches intended to schedule delayed pressure.
- Special-event IDs are unique before apply.
- Source anchors use local repo paths when the room's existing anchors do.
- The candidate uses implemented actions only.

## Deck And Docs Wiring

Scenario data can exist but still be invisible.

For active playtest visibility:

- Add the new root event id to `encounter_decks_post_update.json` `playtest_event_ids`.
- Add the room id to relevant `room_pools`, usually `route`, `branch`, and `random_non_special` if it should appear naturally.
- Update `tools/playtest_slice_smoke.gd` hardcoded `PLAYTEST_ROOMS` and `PLAYTEST_EVENTS` if the constrained slice should include it.

For docs visibility:

- Add the room id to `FEATURED_SCENARIO_ROOMS` in `tools/room_doc_browser.py`.
- Add the root event id to `ACTIVE_EVENT_IDS` if the docs are filtering events.
- Restart a stale server process if `curl http://127.0.0.1:3000/scenarios` does not reflect file changes.

Useful restart flow:

```bash
ps -ef | rg "room_doc_browser|nodemon|127.0.0.1:3000"
kill <old_room_doc_browser_pid>
python tools/room_doc_browser.py --host 127.0.0.1 --port 3000
curl -s http://127.0.0.1:3000/scenarios | rg "<expected room title>|scenarios/"
```

## Common Failure Modes

- Non-streaming direct Anthropic calls may close the connection on large structured outputs. Prefer the streaming blueprint agent.
- A candidate can validate structurally while violating a design rule, such as writing a same-pass follow-up when the request was only for a root hook. Inspect branch logic manually.
- Valid room/event JSON does not guarantee playtest visibility. Check decks and docs allowlists.
- After applying a patch, validating the same patch file may report "event id already exists"; use pre-apply validation/dry-run and post-apply bootstrap checks instead.
- Generated files under `generated/` are scratch artifacts and are usually ignored by git.
