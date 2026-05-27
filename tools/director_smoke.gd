extends SceneTree

const RunManagerScript := preload("res://run_manager.gd")


func _init() -> void:
	var run_manager := RunManagerScript.new()
	root.add_child(run_manager)
	run_manager.start_new_run()

	run_manager.consume_current_event("take_symbiote:impermeable_barrier")
	var after_bond: Dictionary = run_manager.get_director_state()
	if int(after_bond.get("pressure_counts", {}).get("dependence", 0)) < 1:
		push_error("Director did not count symbiote bonding as dependence pressure.")
		quit(1)
		return
	if int(after_bond.get("pressure_counts", {}).get("corruption", 0)) > 0:
		push_error("Director counted basic symbiote bonding as corruption pressure.")
		quit(1)
		return

	run_manager.activate_symbiote("impermeable_barrier")
	var after_activation: Dictionary = run_manager.get_director_state()
	if int(after_activation.get("pressure_counts", {}).get("dependence", 0)) < 1:
		push_error("Director did not count symbiote activation as dependence pressure.")
		quit(1)
		return

	for index in range(4):
		run_manager.current_encounter = {
			"room_id": "red_corridor",
			"event_id": "smoke_avoid_%d" % index,
			"event_data": {
				"id": "smoke_avoid_%d" % index,
				"type": "combat",
				"speaker": "Her",
				"line_1": "Smoke contact.",
				"line_2": "Smoke avoidance.",
				"enemy_id": "blood_hunter",
				"buttons": [{"label": "Slip past", "action": "proceed"}]
			},
			"counts_as_room": true,
			"consumed": false
		}
		run_manager.consume_current_event("proceed")

	var after_avoidance: Dictionary = run_manager.get_director_state()
	if not bool(after_avoidance.get("ending_locks", {}).get("hunter", false)):
		push_error("Director did not lock hunter pressure after repeated combat avoidance.")
		quit(1)
		return

	if bool(run_manager.call("_should_offer_hunter_reckoning")):
		push_error("Hunter reckoning fired before the minimum room count.")
		quit(1)
		return

	run_manager.rooms_cleared = int(run_manager.deck_config.get("ending_reckoning_min_rooms", 12))
	if not bool(run_manager.call("_should_offer_hunter_reckoning")):
		push_error("Hunter reckoning did not become available after the minimum room count.")
		quit(1)
		return

	var lore_manager := RunManagerScript.new()
	root.add_child(lore_manager)
	lore_manager.start_new_run()

	for toll_index in range(3):
		lore_manager.current_encounter = {
			"room_id": "amber_corridor",
			"event_id": "smoke_toll_%d" % toll_index,
			"event_data": {
				"id": "smoke_toll_%d" % toll_index,
				"type": "amber",
				"biomass_cost": 5,
				"buttons": [{"label": "Skip the toll", "action": "skip_resin_toll"}]
			},
			"counts_as_room": false,
			"consumed": false
		}
		lore_manager.consume_current_event("skip_resin_toll")

	var after_tolls: Dictionary = lore_manager.get_director_state()
	if int(after_tolls.get("merchant_claim", 0)) < 3:
		push_error("Resin toll skips did not raise Merchant Claim.")
		quit(1)
		return
	if not bool(lore_manager.call("_should_offer_merchant_reckoning")):
		push_error("Merchant Claim did not make Merchant Reckoning available.")
		quit(1)
		return

	var baffle_manager := RunManagerScript.new()
	root.add_child(baffle_manager)
	baffle_manager.start_new_run()
	for baffle_index in range(2):
		baffle_manager.current_encounter = {
			"room_id": "split_green_corridor",
			"event_id": "smoke_baffle_%d" % baffle_index,
			"event_data": {
				"id": "smoke_baffle_%d" % baffle_index,
				"type": "choice",
				"buttons": [{"label": "Mute the lane", "action": "turn_baffle"}]
			},
			"counts_as_room": false,
			"consumed": false
		}
		baffle_manager.consume_current_event("turn_baffle")

	var baffle_next := baffle_manager.advance_to_next_encounter()
	if str(baffle_next.get("event_id", "")) != "story_smother_flat_air_warning":
		push_error("Repeated baffle use did not schedule the flat-air warning.")
		quit(1)
		return

	var plate_manager := RunManagerScript.new()
	root.add_child(plate_manager)
	plate_manager.start_new_run()
	for plate_index in range(3):
		plate_manager.current_encounter = {
			"room_id": "bone_corridor",
			"event_id": "smoke_plate_%d" % plate_index,
			"event_data": {
				"id": "smoke_plate_%d" % plate_index,
				"type": "choice",
				"buttons": [{"label": "Follow the marks", "action": "follow_marked_plates"}]
			},
			"counts_as_room": false,
			"consumed": false
		}
		plate_manager.consume_current_event("follow_marked_plates")

	var plate_next := plate_manager.advance_to_next_encounter()
	if str(plate_next.get("event_id", "")) != "plate_snare_warning_v1":
		push_error("Repeated marked plate use did not schedule Plate Snare warning.")
		quit(1)
		return

	quit(0)
