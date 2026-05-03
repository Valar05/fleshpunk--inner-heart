extends SceneTree


func _initialize() -> void:
	call_deferred("_run")


func _run() -> void:
	var world_scene := load("res://world.tscn") as PackedScene
	if world_scene == null:
		push_error("Unable to load world.tscn.")
		quit(1)
		return

	var world := world_scene.instantiate()
	root.add_child(world)
	await process_frame
	await process_frame

	var cases := [
		{
			"name": "pressure lock",
			"lines": ["The run tilts. Corruption has the stronger claim."],
			"buttons": [],
		},
		{
			"name": "biomass and danger",
			"lines": ["Biomass: 6. Danger rises to 1."],
			"buttons": [],
		},
		{
			"name": "pheromones activation",
			"lines": [
				"Pheromones bleeds scent into the air.",
				"It lasts this room. Then it needs two rooms quiet.",
			],
			"buttons": [{"label": "Proceed.", "action": "proceed"}],
		},
		{
			"name": "damage summary",
			"lines": ["3 damage hit. Barrier blocked 0, armor blocked 0, shield lost 3, health lost 0."],
			"buttons": [],
			"forbidden": ["Barrier blocked 0.", "Armor blocked 0.", "Health lost 0."],
		},
		{
			"name": "four damage summary",
			"lines": ["4 damage hit. Barrier blocked 0, armor blocked 0, shield lost 4, health lost 0."],
			"buttons": [],
			"forbidden": ["Barrier blocked 0.", "Armor blocked 0.", "Health lost 0."],
		},
		{
			"name": "zero restore skipped",
			"lines": ["Health restored: 0. Danger rises to 1."],
			"buttons": [],
			"forbidden": ["Health restored 0."],
		},
		{
			"name": "combat result",
			"lines": [
				"Combat Result:",
				"Enemy tier: 1",
				"Health lost: 3",
				"Shield lost: 0",
				"Biomass: 6",
				"Blood Hunter dissolved.",
			],
			"buttons": [{"label": "Proceed.", "action": "proceed"}],
			"forbidden": ["Shield lost 0."],
		},
		{
			"name": "merchant showdown",
			"lines": [
				"Combat Result:",
				"Enemy tier: 3",
				"Health lost: 4",
				"Shield lost: 0",
				"Biomass: 0",
				"He takes me apart by weight.",
				"The last signal I send is noise.",
			],
			"buttons": [{"label": "Wake again", "action": "restart_run"}],
			"forbidden": ["Shield lost 0.", "Biomass now 0."],
		},
		{
			"name": "barrier activation",
			"lines": [
				"Impermeable Barrier plates over me. 8 armor waiting for the next hit.",
				"If the full layer breaks, it gets hurt.",
			],
			"buttons": [
				{"label": "Proceed.", "action": "proceed"},
				{"label": "Activate: Impermeable Barrier", "action": "activate_symbiote:impermeable_barrier"},
			],
		},
		{
			"name": "merchant refusal",
			"lines": ["Danger rises to 1. He remembers the refusal."],
			"buttons": [{"label": "Proceed.", "action": "proceed"}],
		},
		{
			"name": "late pheromones button",
			"lines": ["I keep moving."],
			"buttons": [
				{"label": "Proceed.", "action": "proceed"},
				{"label": "Activate: Pheromones", "action": "activate_symbiote:pheromones"},
			],
		},
	]

	var failed := false
	var text_clips: Dictionary = world.get("_tts_text_clip_files")
	for test_case in cases:
		var phrases: Array = world.call("_build_console_speech_phrases", test_case["lines"], test_case["buttons"])
		for forbidden_phrase in test_case.get("forbidden", []):
			if phrases.has(forbidden_phrase):
				failed = true
				push_error("Forbidden zero-value TTS phrase for %s: %s" % [test_case["name"], forbidden_phrase])
		for phrase in phrases:
			var key: String = world.call("_tts_text_key", phrase)
			if not text_clips.has(key):
				failed = true
				push_error("Missing TTS phrase for %s: %s" % [test_case["name"], phrase])

	root.remove_child(world)
	world.queue_free()
	quit(1 if failed else 0)
