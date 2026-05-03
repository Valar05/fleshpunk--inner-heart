extends SceneTree


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	var world_scene = load("res://world.tscn") as PackedScene
	if world_scene == null:
		push_error("Could not load world scene.")
		quit(1)
		return

	var world = world_scene.instantiate()
	root.add_child(world)
	await create_timer(1.0).timeout

	if not world.has_method("_on_console_option_selected"):
		push_error("World cannot receive console selections.")
		quit(1)
		return

	world.call("_on_console_option_selected", "take_symbiote:impermeable_barrier", "red_corridor")
	await create_timer(1.0).timeout
	quit(0)
