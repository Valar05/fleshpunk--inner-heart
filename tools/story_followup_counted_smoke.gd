extends SceneTree

const RunManagerScript := preload("res://run_manager.gd")


func _init() -> void:
	var run_manager := RunManagerScript.new()
	root.add_child(run_manager)
	run_manager.start_new_run()

	var target_event := _find_room_event(run_manager, "amber_corridor", "amber_corridor_silt_confrontation")
	if target_event.is_empty():
		push_error("Missing amber corridor escalation root event.")
		quit(1)
		return

	run_manager.current_encounter = run_manager.call("_build_room_encounter", "amber_corridor", target_event)
	run_manager.current_room_id = "amber_corridor"
	run_manager.consume_current_event("break_marked_pattern")

	# The selected branch queues amber_corridor_silt_return_spoiled after two room clears.
	run_manager.rooms_cleared = 3
	var next_encounter: Dictionary = run_manager.call("_build_next_encounter")
	if str(next_encounter.get("event_id", "")) != "amber_corridor_silt_return_spoiled":
		push_error("Expected counted escalation follow-up, got %s." % str(next_encounter.get("event_id", "")))
		quit(1)
		return
	if not bool(next_encounter.get("counts_as_room", false)):
		push_error("Escalation follow-up did not count as a room.")
		quit(1)
		return
	if str(next_encounter.get("room_id", "")) != "amber_corridor":
		push_error("Escalation follow-up has wrong room id: %s." % str(next_encounter.get("room_id", "")))
		quit(1)
		return

	run_manager.current_encounter = next_encounter
	run_manager.advance_to_next_encounter()
	if int(run_manager.rooms_cleared) != 4:
		push_error("Counted follow-up did not advance rooms_cleared; got %d." % int(run_manager.rooms_cleared))
		quit(1)
		return

	print("STORY_FOLLOWUP_COUNTED_SMOKE_OK")
	quit(0)


func _find_room_event(run_manager: Node, room_id: String, event_id: String) -> Dictionary:
	var room_events: Array = run_manager.room_events_by_room.get(room_id, [])
	for event_variant in room_events:
		if event_variant is Dictionary and str(event_variant.get("id", "")) == event_id:
			return event_variant
	return {}
