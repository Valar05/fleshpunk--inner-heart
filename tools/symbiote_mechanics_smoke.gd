extends SceneTree


func _initialize() -> void:
	call_deferred("_run")


func _run() -> void:
	var run_manager := preload("res://run_manager.gd").new()
	root.add_child(run_manager)
	await process_frame
	run_manager.start_new_run()

	var failed := false

	run_manager.owned_symbiotes = ["mitosis_unit"]
	run_manager.symbiote_health = {"mitosis_unit": 1}
	run_manager.active_symbiotes.clear()
	run_manager.player_state = {"health": 5, "shield": 0, "armor": 0}
	if bool(run_manager.call("_can_activate_symbiote", "mitosis_unit")):
		failed = true
		push_error("Mitosis Unit should not be manually activatable.")

	var damage_result: Dictionary = run_manager.call("_apply_player_damage", 99)
	if not bool(damage_result.get("mitosis_triggered", false)):
		failed = true
		push_error("Mitosis Unit did not passively trigger on lethal damage.")
	if int(run_manager.player_state.get("health", 0)) != 1:
		failed = true
		push_error("Mitosis Unit should leave the player at 1 health.")
	if run_manager.owned_symbiotes.has("mitosis_unit"):
		failed = true
		push_error("Mitosis Unit should die after triggering.")

	run_manager.owned_symbiotes = ["impermeable_barrier"]
	run_manager.symbiote_health = {"impermeable_barrier": 3}
	run_manager.symbiote_cooldowns.clear()
	run_manager.active_symbiotes.clear()
	var first_activation: Dictionary = run_manager.activate_symbiote("impermeable_barrier")
	if not run_manager.active_symbiotes.has("impermeable_barrier"):
		failed = true
		push_error("Impermeable Barrier did not activate.")
	if not str(first_activation.get("lines", [])).contains("Impermeable Barrier plates over me"):
		failed = true
		push_error("Impermeable Barrier activation did not return its readout.")

	run_manager.call("_advance_symbiote_room_state")
	for _index in range(4):
		run_manager.call("_tick_symbiote_cooldowns")
	if not bool(run_manager.call("_can_activate_symbiote", "impermeable_barrier")):
		failed = true
		push_error("Impermeable Barrier should be activatable again after cooldown.")
	var second_activation: Dictionary = run_manager.activate_symbiote("impermeable_barrier")
	if not str(second_activation.get("lines", [])).contains("Impermeable Barrier plates over me"):
		failed = true
		push_error("Impermeable Barrier repeat activation did not return its readout.")

	root.remove_child(run_manager)
	run_manager.queue_free()
	quit(1 if failed else 0)
