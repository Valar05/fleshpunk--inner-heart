extends SceneTree

const RunManagerScript := preload("res://run_manager.gd")


func _init() -> void:
	var run_manager := RunManagerScript.new()
	root.add_child(run_manager)
	run_manager.start_new_run()

	run_manager.current_encounter = {
		"room_id": "red_corridor",
		"event_id": "martial_pressure_test",
		"event_data": {
			"id": "martial_pressure_test",
			"type": "choice",
			"speaker": "Hymn",
			"line_1": "Pressure test.",
			"line_2": "Pressure test.",
			"action_results": {
				"proceed": {
					"lines": ["I test the pressure record."],
					"pressure_axis_changes": ["body_drift", "baseline_discipline"],
					"environment_state_changes": ["hunt_pressure_plus_one"]
				}
			}
		},
		"counts_as_room": false,
		"consumed": false
	}

	run_manager.consume_current_event("proceed")

	if int(run_manager.pressure_counts.get("body_drift", 0)) != 1:
		push_error("body_drift pressure did not increment.")
		quit(1)
		return
	if int(run_manager.pressure_counts.get("baseline_discipline", 0)) != 1:
		push_error("baseline_discipline pressure did not increment.")
		quit(1)
		return
	if int(run_manager.pressure_counts.get("hunt_pressure", 0)) != 1:
		push_error("hunt_pressure environment state alias did not increment.")
		quit(1)
		return
	if int(run_manager.danger) != 1:
		push_error("hunt_pressure_plus_one did not affect legacy danger compatibility.")
		quit(1)
		return

	print("MARTIAL_PRESSURE_SMOKE_OK")
	quit(0)
