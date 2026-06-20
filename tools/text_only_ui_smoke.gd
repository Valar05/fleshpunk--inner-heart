extends SceneTree

const WorldScene := preload("res://world.tscn")


func _init() -> void:
	var world := WorldScene.instantiate()
	root.add_child(world)
	for index in range(12):
		await process_frame

	var dashboard := world.get_node_or_null("FleshpunkDashboard")
	var backdrop := world.get_node_or_null("FleshpunkDashboard/FullscreenBackdrop")
	var console := world.get_node_or_null("FleshpunkDashboard/Console")
	var console_content := world.get_node_or_null("FleshpunkDashboard/Console/ConsoleContent")
	var command_input := world.get_node_or_null("FleshpunkDashboard/CommandInput")
	var room_sprite := world.get_node_or_null("RoomSprite")
	var hymn := world.get_node_or_null("Hymn")

	if dashboard == null or console == null or command_input == null:
		push_error("Text-only UI nodes are missing.")
		quit(1)
		return

	var dashboard_sprite := dashboard as Sprite2D
	if dashboard_sprite == null or dashboard_sprite.texture == null:
		push_error("Fleshpunk dashboard sprite background is missing.")
		quit(1)
		return

	if backdrop != null and backdrop.visible:
		push_error("TextureRect backdrop should not replace the dashboard sprite background.")
		quit(1)
		return

	if float(dashboard_sprite.self_modulate.a) < 0.99:
		push_error("Dashboard sprite should be visible as the background.")
		quit(1)
		return

	var texture_size := dashboard_sprite.texture.get_size()
	if texture_size.x < 900.0 or texture_size.y < 1600.0:
		push_error("Dashboard did not load the portrait texture: %s." % str(texture_size))
		quit(1)
		return
	var sprite_width := texture_size.x * absf(dashboard_sprite.scale.x)
	var sprite_height := texture_size.y * absf(dashboard_sprite.scale.y)
	var sprite_left := dashboard_sprite.global_position.x - sprite_width * 0.5
	var sprite_top := dashboard_sprite.global_position.y - sprite_height * 0.5
	var sprite_right := dashboard_sprite.global_position.x + sprite_width * 0.5
	var sprite_bottom := dashboard_sprite.global_position.y + sprite_height * 0.5
	if sprite_left > 1.0 or sprite_top > 1.0 or sprite_right < 1079.0 or sprite_bottom < 1919.0:
		push_error("Dashboard sprite does not cover the viewport: left %.1f top %.1f right %.1f bottom %.1f." % [sprite_left, sprite_top, sprite_right, sprite_bottom])
		quit(1)
		return

	if sprite_top > 4.0 or sprite_bottom < 1916.0:
		push_error("Portrait dashboard sprite does not cover the viewport vertically: top %.1f bottom %.1f." % [sprite_top, sprite_bottom])
		quit(1)
		return
	if dashboard_sprite.global_position.y > 1300.0 and dashboard_sprite.scale.y < 2.0:
		push_error("Dashboard transform still matches the old bottom-half animation: position %s scale %s." % [str(dashboard_sprite.global_position), str(dashboard_sprite.scale)])
		quit(1)
		return

	if room_sprite != null and room_sprite.visible:
		push_error("Room sprite should be hidden for text-only presentation.")
		quit(1)
		return
	if hymn != null and hymn.visible:
		push_error("Hymn sprite should be hidden for text-only presentation.")
		quit(1)
		return

	var console_rect: Rect2 = console.get_global_rect()
	var console_width := console_rect.size.x
	var console_height := console_rect.size.y
	if console_width < 900.0 or console_height < 1500.0:
		push_error("Console does not cover enough of the viewport: %.1fx%.1f." % [console_width, console_height])
		quit(1)
		return
	if console_rect.position.y > 100.0 or console_rect.end.y < 1700.0:
		push_error("Console should fill the dark terminal area higher on screen: %s." % str(console_rect))
		quit(1)
		return

	var input_rect: Rect2 = command_input.get_global_rect()
	var input_height := input_rect.size.y
	if input_height < 70.0:
		push_error("Command input is too small for the text-only layout.")
		quit(1)
		return
	var command_line := command_input as LineEdit
	if command_line != null and command_line.placeholder_text.length() > 36:
		push_error("Command input placeholder is too long for portrait: %s." % command_line.placeholder_text)
		quit(1)
		return

	var first_button: Button = null
	if console_content != null:
		for child in console_content.get_children():
			if child is Button:
				first_button = child
				break

	if first_button == null:
		push_error("No command button was rendered.")
		quit(1)
		return

	var normal_style := first_button.get_theme_stylebox("normal") as StyleBoxFlat
	if normal_style == null:
		push_error("Command button is missing its normal stylebox.")
		quit(1)
		return

	if normal_style.bg_color.v < 0.45:
		push_error("Command button normal style is too dark: %s." % normal_style.bg_color)
		quit(1)
		return

	print("TEXT_ONLY_UI_SMOKE_OK")
	quit(0)
