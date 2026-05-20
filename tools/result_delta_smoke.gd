extends SceneTree

const RunManagerScript := preload("res://run_manager.gd")


func _init() -> void:
	var run_manager := RunManagerScript.new()
	root.add_child(run_manager)
	run_manager.start_new_run()

	run_manager.current_encounter = {
		"room_id": "smoke_room",
		"event_id": "smoke_result_delta",
		"event_data": {
			"id": "smoke_result_delta",
			"type": "room",
			"action_results": {
				"harvest_eggs": {
					"lines": ["Agent-authored outcome stays first."]
				}
			}
		}
	}
	run_manager.consume_current_event("harvest_eggs")

	var lines: Array = run_manager.get_last_action_result().get("lines", [])
	if lines.size() < 2 or str(lines[0]) != "Agent-authored outcome stays first.":
		push_error("Action result prose was not preserved before the generated delta.")
		quit(1)
		return
	if not lines.has("Result: Biomass +5. Corruption +1."):
		push_error("Generated result delta was missing or malformed: %s" % str(lines))
		quit(1)
		return

	print("RESULT_DELTA_SMOKE_OK")
	quit(0)
