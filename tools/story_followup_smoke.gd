extends SceneTree

const RunManagerScript := preload("res://run_manager.gd")


func _init() -> void:
	var run_manager := RunManagerScript.new()
	root.add_child(run_manager)
	run_manager.start_new_run()

	var opening: Dictionary = run_manager.get_current_encounter()
	if str(opening.get("event_id", "")) != "game_opening_descent":
		push_error("Opening event was not the scene-setting descent.")
		quit(1)
		return

	run_manager.consume_current_event("proceed")
	opening = run_manager.advance_to_next_encounter()
	if str(opening.get("event_id", "")) != "symbiote_host_offer":
		push_error("Scene-setting descent did not lead to the initial symbiote choice.")
		quit(1)
		return

	run_manager.consume_current_event("leave_symbiote")
	var first_room: Dictionary = run_manager.advance_to_next_encounter()
	if str(first_room.get("room_id", "")) != str(run_manager.deck_config.get("first_room_after_opening", "")):
		push_error("First normal room did not match first_room_after_opening.")
		quit(1)
		return
	if not bool(first_room.get("counts_as_room", false)):
		push_error("First post-opening room should count as a normal room.")
		quit(1)
		return

	var followup_spec: Dictionary = _followup_for_action(first_room, "probe_bones")
	var expected_followup_id := str(followup_spec.get("event_id", ""))
	if expected_followup_id == "":
		push_error("First operator-cellar room did not expose a probe_bones story follow-up.")
		quit(1)
		return

	run_manager.consume_current_event("probe_bones")
	var result: Dictionary = run_manager.get_last_action_result()
	var result_lines: Array = result.get("lines", [])
	var queued_line := str(followup_spec.get("queued_line", ""))
	if queued_line != "" and not _lines_contain(result_lines, queued_line):
		push_error("Story follow-up did not report its queued consequence.")
		quit(1)
		return

	var pending_followup: Dictionary = _pending_story_followup(run_manager, expected_followup_id)
	if pending_followup.is_empty():
		push_error("Story follow-up was not queued: %s." % expected_followup_id)
		quit(1)
		return
	var available_after_rooms := int(pending_followup.get("available_after_rooms", 0))
	if available_after_rooms <= int(run_manager.rooms_cleared):
		push_error("Story follow-up was available immediately instead of delayed: %s." % str(pending_followup))
		quit(1)
		return

	run_manager.current_encounter = {}
	run_manager.set("_pending_room_id_after_transition", "")
	run_manager.set("_pending_encounter_after_overlay", {})
	run_manager.rooms_cleared = available_after_rooms
	var followup: Dictionary = run_manager.advance_to_next_encounter()
	if str(followup.get("event_id", "")) != expected_followup_id:
		push_error("Expected delayed %s; got %s." % [expected_followup_id, str(followup.get("event_id", ""))])
		quit(1)
		return
	if bool(followup.get("counts_as_room", true)):
		push_error("Story follow-up should not count as a normal room clear.")
		quit(1)
		return

	run_manager.consume_current_event("proceed")
	run_manager.advance_to_next_encounter()

	var first_room_id := str(first_room.get("room_id", ""))
	var first_room_events: Array = run_manager.room_events_by_room.get(first_room_id, [])
	if first_room_events.is_empty():
		push_error("Missing first-room events for retrigger check.")
		quit(1)
		return

	run_manager.current_encounter = run_manager.call("_build_room_encounter", first_room_id, first_room.get("event_data", {}))
	run_manager.consume_current_event("probe_bones")
	var non_repeat: Dictionary = run_manager.advance_to_next_encounter()
	if str(non_repeat.get("event_id", "")) == expected_followup_id:
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


func _followup_for_action(encounter: Dictionary, action_id: String) -> Dictionary:
	var event_data: Dictionary = encounter.get("event_data", {})
	var story_followups: Dictionary = event_data.get("story_followups", {})
	var followup = story_followups.get(action_id, {})
	if followup is Dictionary:
		return followup
	return {}


func _pending_story_followup(run_manager, expected_event_id: String) -> Dictionary:
	var pending_events: Array = run_manager.get("_pending_story_events")
	for pending in pending_events:
		if pending is Dictionary and str(pending.get("event_id", "")) == expected_event_id:
			return pending
	return {}
