extends SceneTree

const RunManagerScript := preload("res://run_manager.gd")


func _init() -> void:
	var run_manager := RunManagerScript.new()
	root.add_child(run_manager)
	run_manager.start_new_run()

	if str(run_manager.content_track) != "post_update_text_only":
		push_error("RunManager did not load post-update content track.")
		quit(1)
		return

	var opening: Dictionary = run_manager.get_current_encounter()
	var opening_lines: Array = opening.get("lines", [])
	if opening_lines.is_empty() or not str(opening_lines[0]).contains("wet toll mouth"):
		push_error("Opening encounter did not include the first-visit room description.")
		quit(1)
		return

	var room_id := "rib_lock_larval_cradle"
	var room_events: Array = run_manager.room_events_by_room.get(room_id, [])
	if room_events.is_empty():
		push_error("rib_lock_larval_cradle has no post-update events.")
		quit(1)
		return

	var first_encounter: Dictionary = run_manager.call("_build_room_encounter", room_id, room_events[0])
	var first_lines: Array = first_encounter.get("lines", [])
	if first_lines.is_empty() or not str(first_lines[0]).contains("Black fluid fills the drop"):
		push_error("First rib_lock_larval_cradle encounter did not use first_visit_description.")
		quit(1)
		return

	var return_encounter: Dictionary = run_manager.call("_build_room_encounter", room_id, room_events[0])
	var return_lines: Array = return_encounter.get("lines", [])
	if return_lines.is_empty() or not str(return_lines[0]).contains("black fluid, hanging harness"):
		push_error("Second rib_lock_larval_cradle encounter did not use return_description.")
		quit(1)
		return

	print("POST_UPDATE_ROOM_SMOKE_OK")
	quit(0)
