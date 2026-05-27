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
	if str(opening.get("event_id", "")) != "game_opening_descent":
		push_error("Opening encounter was not the scene-setting descent.")
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
	var first_room_lines: Array = first_room.get("lines", [])
	if first_room_lines.is_empty() or not str(first_room_lines[0]).contains("operator cellar"):
		push_error("First normal operator-cellar room did not include the first-visit room description.")
		quit(1)
		return

	var room_id := "white_marrow_field"
	var room_events: Array = run_manager.room_events_by_room.get(room_id, [])
	if room_events.is_empty():
		push_error("white_marrow_field has no post-update events.")
		quit(1)
		return

	var first_encounter: Dictionary = run_manager.call("_build_room_encounter", room_id, room_events[0])
	var first_lines: Array = first_encounter.get("lines", [])
	if first_lines.is_empty() or not str(first_lines[0]).contains("corridor opens into white marrow"):
		push_error("First white_marrow_field encounter did not use first_visit_description.")
		quit(1)
		return

	var return_encounter: Dictionary = run_manager.call("_build_room_encounter", room_id, room_events[0])
	var return_lines: Array = return_encounter.get("lines", [])
	if return_lines.is_empty() or not str(return_lines[0]).contains("white marrow field opens ahead"):
		push_error("Second white_marrow_field encounter did not use return_description.")
		quit(1)
		return

	print("POST_UPDATE_ROOM_SMOKE_OK")
	quit(0)
