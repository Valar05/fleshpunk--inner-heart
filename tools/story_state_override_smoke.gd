extends SceneTree

const RunManagerScript := preload("res://run_manager.gd")


func _init() -> void:
	var run_manager := RunManagerScript.new()
	root.add_child(run_manager)
	run_manager.start_new_run()

	run_manager.current_encounter = run_manager.call("_build_special_encounter", "story_soft_captain_pulse_mark")
	run_manager.consume_current_event("proceed")
	if not run_manager.environment_state.has("next_rib_lock_mask_soft"):
		push_error("Soft Captain follow-up did not set next_rib_lock_mask_soft.")
		quit(1)
		return

	var room_events: Array = run_manager.room_events_by_room.get("rib_lock_tally_gate", [])
	if room_events.is_empty():
		push_error("rib_lock_tally_gate has no events.")
		quit(1)
		return

	var encounter: Dictionary = run_manager.call("_build_room_encounter", "rib_lock_tally_gate", room_events[0])
	var buttons: Array = encounter.get("buttons", [])
	if buttons.size() != 2:
		push_error("Soft Captain override did not mask rib-lock buttons.")
		quit(1)
		return
	if str(buttons[0].get("label", "")) != "Hold the count and slip":
		push_error("Soft Captain override did not expose the authored slip option.")
		quit(1)
		return
	if run_manager.environment_state.has("next_rib_lock_mask_soft"):
		push_error("Soft Captain override did not consume next_rib_lock_mask_soft.")
		quit(1)
		return

	print("STORY_STATE_OVERRIDE_SMOKE_OK")
	quit(0)
