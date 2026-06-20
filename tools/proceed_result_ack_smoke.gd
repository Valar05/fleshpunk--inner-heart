extends SceneTree

const WorldScene := preload("res://world.tscn")


func _init() -> void:
	var world := WorldScene.instantiate()
	root.add_child(world)
	for _index in range(12):
		await process_frame

	world.call("_on_console_option_selected", "proceed", "")
	await process_frame

	var result_lines: Array = world.get("_current_console_lines")
	if not _lines_contain(result_lines, "I descend toward the split armor."):
		push_error("Proceed action_results were not shown before advancing: %s" % str(result_lines))
		quit(1)
		return
	if _lines_contain(result_lines, "One bond is possible."):
		push_error("Proceed advanced straight to the next encounter instead of showing acknowledgement.")
		quit(1)
		return

	world.call("_on_console_option_selected", "proceed", "")
	await create_timer(0.8).timeout

	var next_lines: Array = world.get("_current_console_lines")
	if not _lines_contain(next_lines, "One bond is possible."):
		push_error("Acknowledgement proceed did not advance to the queued encounter: %s" % str(next_lines))
		quit(1)
		return

	print("PROCEED_RESULT_ACK_SMOKE_OK")
	quit(0)


func _lines_contain(lines: Array, needle: String) -> bool:
	for line in lines:
		if str(line).contains(needle):
			return true
	return false
