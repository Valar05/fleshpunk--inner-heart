extends SceneTree

const RunManagerScript := preload("res://run_manager.gd")


func _init() -> void:
	var run_manager := RunManagerScript.new()
	root.add_child(run_manager)
	run_manager.start_new_run()

	var opening: Dictionary = run_manager.get_current_encounter()
	if str(opening.get("event_id", "")) != "rib_lock_tally_gate_account":
		push_error("Opening event was not the rib vessel kickoff.")
		quit(1)
		return

	run_manager.consume_current_event("observe_organ_chamber")
	var result: Dictionary = run_manager.get_last_action_result()
	var result_lines: Array = result.get("lines", [])
	if not _lines_contain(result_lines, "The cord keeps my pulse"):
		push_error("Story follow-up did not report its queued consequence.")
		quit(1)
		return

	var first_intervening: Dictionary = run_manager.advance_to_next_encounter()
	if str(first_intervening.get("event_id", "")) == "story_soft_captain_pulse_mark":
		push_error("Story follow-up appeared without enough intervening rooms.")
		quit(1)
		return
	if not bool(first_intervening.get("counts_as_room", false)):
		push_error("Expected a first intervening normal room before the story follow-up.")
		quit(1)
		return

	var buttons: Array = first_intervening.get("buttons", [])
	if buttons.is_empty() or not buttons[0] is Dictionary:
		push_error("First intervening room had no legal first button.")
		quit(1)
		return

	run_manager.consume_current_event(str(buttons[0].get("action", "proceed")))
	var second_intervening: Dictionary = run_manager.advance_to_next_encounter()
	if str(second_intervening.get("event_id", "")) == "story_soft_captain_pulse_mark":
		push_error("Story follow-up appeared after only one intervening room.")
		quit(1)
		return
	if not bool(second_intervening.get("counts_as_room", false)):
		push_error("Expected a second intervening normal room before the story follow-up.")
		quit(1)
		return

	buttons = second_intervening.get("buttons", [])
	if buttons.is_empty() or not buttons[0] is Dictionary:
		push_error("Second intervening room had no legal first button.")
		quit(1)
		return

	run_manager.consume_current_event(str(buttons[0].get("action", "proceed")))
	var followup: Dictionary = run_manager.advance_to_next_encounter()
	if str(followup.get("event_id", "")) != "story_soft_captain_pulse_mark":
		push_error("Expected delayed story_soft_captain_pulse_mark; got %s." % str(followup.get("event_id", "")))
		quit(1)
		return
	if bool(followup.get("counts_as_room", true)):
		push_error("Story follow-up should not count as a normal room clear.")
		quit(1)
		return

	run_manager.consume_current_event("proceed")
	run_manager.advance_to_next_encounter()

	var rib_events: Array = run_manager.room_events_by_room.get("rib_lock_tally_gate", [])
	if rib_events.is_empty():
		push_error("Missing rib_lock_tally_gate events for retrigger check.")
		quit(1)
		return

	run_manager.current_encounter = run_manager.call("_build_room_encounter", "rib_lock_tally_gate", rib_events[0])
	run_manager.consume_current_event("observe_organ_chamber")
	var non_repeat: Dictionary = run_manager.advance_to_next_encounter()
	if str(non_repeat.get("event_id", "")) == "story_soft_captain_pulse_mark":
		push_error("Story follow-up retriggered in the same run.")
		quit(1)
		return

	print("STORY_FOLLOWUP_SMOKE_OK")
	quit(0)


func _lines_contain(lines: Array, needle: String) -> bool:
	for line in lines:
		if str(line).contains(needle):
			return true
	return false
