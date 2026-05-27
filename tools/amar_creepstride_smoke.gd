extends SceneTree

const RunManagerScript := preload("res://run_manager.gd")


func _init() -> void:
	var run_manager = _new_run_manager()
	var room_events: Array = run_manager.room_events_by_room.get("amar_creepstride_red_chapel", [])
	if room_events.is_empty():
		push_error("Amar room event was not registered.")
		quit(1)
		return

	run_manager.current_encounter = run_manager.call("_build_room_encounter", "amar_creepstride_red_chapel", room_events[0])
	run_manager.consume_current_event("combat")
	if not run_manager.environment_state.has("amar_creepstride_arc_closed"):
		push_error("Killing Amar did not close the same-run arc.")
		quit(1)
		return
	var next_encounter: Dictionary = _advance_past_rooms_to_special(run_manager, "amar_creepstride_pinch_gate")
	if str(next_encounter.get("event_id", "")) == "amar_creepstride_pinch_gate":
		push_error("Amar pinch gate queued after first-contact kill.")
		quit(1)
		return

	run_manager = _new_run_manager()
	room_events = run_manager.room_events_by_room.get("amar_creepstride_red_chapel", [])
	run_manager.current_encounter = run_manager.call("_build_room_encounter", "amar_creepstride_red_chapel", room_events[0])
	run_manager.consume_current_event("listen_red_wall")
	next_encounter = _advance_past_rooms_to_special(run_manager, "amar_creepstride_pinch_gate")
	if str(next_encounter.get("event_id", "")) != "amar_creepstride_pinch_gate":
		push_error("Amar pinch gate did not follow first cooperation.")
		quit(1)
		return

	run_manager.consume_current_event("mark_red_branch")
	next_encounter = _advance_past_rooms_to_special(run_manager, "amar_creepstride_chapel_lung")
	if str(next_encounter.get("event_id", "")) != "amar_creepstride_chapel_lung":
		push_error("Amar chapel lung did not follow marked tendon branch.")
		quit(1)
		return

	run_manager.consume_current_event("cut_heart_cords")
	next_encounter = _advance_past_rooms_to_special(run_manager, "amar_creepstride_last_stride")
	if str(next_encounter.get("event_id", "")) != "amar_creepstride_last_stride":
		push_error("Amar terminal ending did not follow longest branch.")
		quit(1)
		return
	if str(next_encounter.get("event_data", {}).get("ending_id", "")) != "ending_amar_creepstride_cult_debt":
		push_error("Amar terminal event missing ending id.")
		quit(1)
		return

	print("AMAR_CREEPSTRIDE_SMOKE_OK")
	quit(0)


func _new_run_manager():
	var run_manager := RunManagerScript.new()
	root.add_child(run_manager)
	run_manager.start_new_run()
	return run_manager


func _advance_past_rooms_to_special(run_manager, target_event_id: String) -> Dictionary:
	for _index in range(16):
		var encounter: Dictionary = run_manager.advance_to_next_encounter()
		if str(encounter.get("event_id", "")) == target_event_id:
			return encounter
		if bool(encounter.get("counts_as_room", false)):
			var buttons: Array = encounter.get("buttons", [])
			if buttons.is_empty() or not buttons[0] is Dictionary:
				return encounter
			run_manager.consume_current_event(str(buttons[0].get("action", "proceed")))
			continue
		if str(encounter.get("event_id", "")).begins_with("amar_creepstride_"):
			return encounter
	return {}
