extends SceneTree

const RunManagerScript := preload("res://run_manager.gd")


func _init() -> void:
	var run_manager = _new_run_manager()

	var opening: Dictionary = run_manager.get_current_encounter()
	if str(opening.get("event_id", "")) != "game_opening_descent":
		push_error("Expected initial game_opening_descent; got %s." % str(opening.get("event_id", "")))
		quit(1)
		return
	if bool(opening.get("counts_as_room", true)):
		push_error("Initial scene-setting descent should not count as a normal room.")
		quit(1)
		return

	run_manager.consume_current_event("proceed")
	opening = run_manager.advance_to_next_encounter()
	if str(opening.get("event_id", "")) != "symbiote_host_offer":
		push_error("Expected initial symbiote_host_offer after descent; got %s." % str(opening.get("event_id", "")))
		quit(1)
		return
	if bool(opening.get("counts_as_room", true)):
		push_error("Initial symbiote choice should not count as a normal room.")
		quit(1)
		return

	run_manager.consume_current_event("leave_symbiote")
	var next_encounter: Dictionary = run_manager.advance_to_next_encounter()
	if str(next_encounter.get("event_id", "")) != "rib_lock_tally_gate_account":
		push_error("Expected rib lock as first normal room; got %s." % str(next_encounter.get("event_id", "")))
		quit(1)
		return
	if not bool(next_encounter.get("counts_as_room", false)):
		push_error("Rib lock should count as a normal room.")
		quit(1)
		return
	run_manager.consume_current_event("observe_organ_chamber")
	next_encounter = run_manager.advance_to_next_encounter()
	if str(next_encounter.get("event_id", "")) == "symbiote_host_offer":
		push_error("Symbiote offer repeated after the initial opening choice.")
		quit(1)
		return

	run_manager = _new_run_manager()
	run_manager.rooms_cleared = 4
	run_manager._pending_room_id_after_transition = ""
	run_manager._symbiote_triggered_at_rooms[1] = true
	next_encounter = run_manager.call("_build_next_encounter")
	if str(next_encounter.get("event_id", "")) != "merchant_arrival":
		push_error("Expected merchant_arrival at cadence room 4; got %s." % str(next_encounter.get("event_id", "")))
		quit(1)
		return

	run_manager = _new_run_manager()
	run_manager.current_encounter = run_manager.call("_build_special_encounter", "story_quartermaster_teeth_count")
	run_manager.consume_current_event("proceed")
	if run_manager.merchant_claim != 1:
		push_error("merchant_claim_up did not alter merchant_claim.")
		quit(1)
		return

	run_manager = _new_run_manager()
	run_manager.rooms_cleared = 12
	run_manager._pending_room_id_after_transition = ""
	run_manager.merchant_claim = 3
	run_manager._symbiote_triggered_at_rooms[12] = true
	run_manager._merchant_triggered_at_rooms[12] = true
	next_encounter = run_manager.call("_build_next_encounter")
	if str(next_encounter.get("event_id", "")) != "ending_merchant_debt":
		push_error("Expected ending_merchant_debt from merchant claim; got %s." % str(next_encounter.get("event_id", "")))
		quit(1)
		return

	run_manager = _new_run_manager()
	run_manager.rooms_cleared = 8
	run_manager._pending_room_id_after_transition = ""
	run_manager._ending_locks["corruption"] = true
	next_encounter = run_manager.call("_build_next_encounter")
	if str(next_encounter.get("event_id", "")) != "corruption_claim":
		push_error("Expected corruption_claim after terminal corruption lock; got %s." % str(next_encounter.get("event_id", "")))
		quit(1)
		return

	print("CADENCE_AND_ENDINGS_SMOKE_OK")
	quit(0)


func _new_run_manager():
	var run_manager := RunManagerScript.new()
	root.add_child(run_manager)
	run_manager.start_new_run()
	return run_manager
