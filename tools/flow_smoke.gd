extends SceneTree


func _initialize() -> void:
	var run_manager_script: Script = load("res://run_manager.gd")
	var run_manager: Node = run_manager_script.new()
	root.add_child(run_manager)
	run_manager.start_new_run()

	var opening: Dictionary = run_manager.get_current_encounter()
	print("OPENING_EVENT=%s" % str(opening.get("event_id", "")))
	print("OPENING_BUTTONS=%s" % JSON.stringify(opening.get("buttons", [])))

	var buttons: Array = opening.get("buttons", [])
	for button in buttons:
		if button is Dictionary and str(button.get("action", "")).begins_with("take_symbiote:"):
			run_manager.consume_current_event(str(button.get("action", "")))
			var result: Dictionary = run_manager.get_last_action_result()
			print("BOND_RESULT_BUTTONS=%s" % JSON.stringify(result.get("buttons", [])))
			run_manager.consume_current_event("take_symbiote:pheromones")
			print("OWNED_AFTER_DOUBLE_TAKE=%s" % JSON.stringify(run_manager.owned_symbiotes))
			var activation: Dictionary = run_manager.activate_symbiote("impermeable_barrier")
			print("ACTIVATE_RESULT_BUTTONS=%s" % JSON.stringify(activation.get("buttons", [])))
			run_manager.advance_to_next_encounter()
			print("BARRIER_COOLDOWN_AFTER_ROOM=%d" % int(run_manager.symbiote_cooldowns.get("impermeable_barrier", 0)))
			break

	run_manager.biomass = 100
	run_manager.buy_shop_mutation("lean_muscle")
	run_manager.call("_apply_action_effects", "leave_merchant", {})
	print("MERCHANT_REFUSALS_AFTER_PURCHASE_LEAVE=%d" % int(run_manager.merchant_refusals))

	run_manager.start_new_run()
	for index in range(16):
		var current: Dictionary = run_manager.get_current_encounter()
		if current.is_empty():
			print("EMPTY_ENCOUNTER_AT=%d" % index)
			break
		print("FLOW_%02d=%s/%s scene=%s" % [index, str(current.get("room_id", "")), str(current.get("event_id", "")), str(current.get("scene_path", ""))])
		run_manager.consume_current_event("proceed")
		run_manager.advance_to_next_encounter()

	quit()
