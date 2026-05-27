extends SceneTree

const RunManagerScript := preload("res://run_manager.gd")

const PLAYTEST_ROOMS := {
	"operator_cellar": true,
	"white_marrow_field": true,
}

const PLAYTEST_EVENTS := {
	"operator_cellar_grip_predator": true,
	"operator_cellar_wall_reader": true,
	"white_marrow_field_hound_lanes": true,
}


func _init() -> void:
	var run_manager := RunManagerScript.new()
	root.add_child(run_manager)
	run_manager.start_new_run()

	if str(run_manager.deck_config.get("playtest_slice", "")) != "corpus_anchored_martial_progression":
		push_error("Post-update deck is not marked as the corpus-anchored playtest slice.")
		quit(1)
		return

	var pools: Dictionary = run_manager.deck_config.get("room_pools", {})
	for pool_name in pools.keys():
		var pool = pools.get(pool_name, [])
		if not pool is Array:
			continue
		for room_id_variant in pool:
			var room_id := str(room_id_variant)
			if not PLAYTEST_ROOMS.has(room_id):
				push_error("Playtest pool '%s' contains unapproved room '%s'." % [str(pool_name), room_id])
				quit(1)
				return
			var room_data := run_manager.get_room_data(room_id)
			if not _has_tier_zero_anchor(room_data):
				push_error("Playtest room '%s' lacks a tier-0 corpus anchor." % room_id)
				quit(1)
				return

	var seen_rooms := {}
	for index in range(18):
		var encounter: Dictionary = run_manager.get_current_encounter()
		if encounter.is_empty():
			push_error("Encounter stream went empty at index %d." % index)
			quit(1)
			return

		var room_id := str(encounter.get("room_id", ""))
		var event_id := str(encounter.get("event_id", ""))
		if bool(encounter.get("counts_as_room", false)):
			seen_rooms[room_id] = true
			if not PLAYTEST_ROOMS.has(room_id):
				push_error("Playable room '%s/%s' is outside the anchored playtest slice." % [room_id, event_id])
				quit(1)
				return
			if not PLAYTEST_EVENTS.has(event_id):
				push_error("Playable event '%s/%s' is outside the new Claude event slice." % [room_id, event_id])
				quit(1)
				return

		run_manager.consume_current_event(_first_button_action(encounter))
		run_manager.advance_to_next_encounter()

	for required_room in PLAYTEST_ROOMS.keys():
		if not seen_rooms.has(required_room):
			push_error("Required playtest room '%s' did not appear in the opening stream." % required_room)
			quit(1)
			return

	print("PLAYTEST_SLICE_SMOKE_OK")
	quit(0)


func _has_tier_zero_anchor(room_data: Dictionary) -> bool:
	var anchors = room_data.get("corpus_anchors", [])
	if not anchors is Array:
		return false
	for anchor in anchors:
		if anchor is Dictionary and int(anchor.get("tier", -1)) == 0:
			return true
	return false


func _first_button_action(encounter: Dictionary) -> String:
	var buttons = encounter.get("buttons", [])
	if buttons is Array:
		for button in buttons:
			if button is Dictionary:
				var action := str(button.get("action", ""))
				if action != "":
					return action
	return "proceed"
