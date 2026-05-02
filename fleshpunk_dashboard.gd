extends Sprite2D

signal console_option_selected(action_id: String, room_id: String)

const DEFAULT_OPTION_LABEL := "Proceed."
const DEFAULT_OPTION_ACTION := "proceed"
const CONSOLE_TEXT_COLOR := Color(0.95, 0.88, 0.8, 1.0)
const CONSOLE_BUTTON_TEXT_COLOR := Color(0.14, 0.07, 0.04, 1.0)
const CONSOLE_BUTTON_COLOR := Color(0.93, 0.74, 0.47, 0.95)

@onready var console_scroll: ScrollContainer = $Console
@onready var console_content: VBoxContainer = $Console/ConsoleContent

var _current_room_id := ""


func _ready() -> void:
	$AnimationPlayer.play("Idle")
	clear_console()


func set_room_data(room_data: Dictionary) -> void:
	_current_room_id = str(room_data.get("id", ""))
	var lines: Array[String] = []
	var ui_text_variant = room_data.get("ui_text", {})
	if ui_text_variant is Dictionary:
		var ui_text: Dictionary = ui_text_variant
		var speaker := str(ui_text.get("speaker", ""))
		var line_1 := str(ui_text.get("line_1", ""))
		var line_2 := str(ui_text.get("line_2", ""))

		if line_1 != "":
			lines.append(line_1)
		if line_2 != "":
			lines.append(line_2)

	show_console(lines, _get_room_options(room_data), _current_room_id)


func clear_console() -> void:
	for child in console_content.get_children():
		child.queue_free()


func append_console_entry(text: String) -> void:
	_append_label(text)
	call_deferred("_scroll_console_to_bottom")


func show_console(lines: Array, options: Array, room_id: String = "") -> void:
	if room_id != "":
		_current_room_id = room_id

	clear_console()
	var narrative_lines := _sanitize_narration_lines(lines)
	for index in narrative_lines.size():
		var line_text := str(narrative_lines[index])
		_append_label(line_text, index == 0 and line_text.ends_with(":"))

	for option in options:
		_append_button(option)

	call_deferred("_reset_console_scroll")


func _sanitize_narration_lines(lines: Array) -> Array[String]:
	var clean_lines: Array[String] = []
	for line in lines:
		var text := str(line).strip_edges()
		if text == "" or text == "Her:":
			continue
		clean_lines.append(text)
	return clean_lines


func _get_room_options(room_data: Dictionary) -> Array:
	var event_data_variant = room_data.get("event_data", {})
	if event_data_variant is Dictionary:
		var event_data: Dictionary = event_data_variant
		var buttons_variant = event_data.get("buttons", event_data.get("options", []))
		if buttons_variant is Array and not buttons_variant.is_empty():
			return buttons_variant

	var top_level_buttons = room_data.get("buttons", [])
	if top_level_buttons is Array and not top_level_buttons.is_empty():
		return top_level_buttons

	return [{"label": DEFAULT_OPTION_LABEL, "action": DEFAULT_OPTION_ACTION}]


func _append_label(text: String, is_heading: bool = false) -> void:
	var label := Label.new()
	label.text = text
	label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_LEFT
	label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	label.add_theme_color_override("font_color", CONSOLE_TEXT_COLOR)
	label.add_theme_font_size_override("font_size", 24 if is_heading else 20)
	console_content.add_child(label)


func _append_button(option_data: Variant) -> void:
	if not option_data is Dictionary:
		return

	var option: Dictionary = option_data
	var button := Button.new()
	button.text = str(option.get("label", DEFAULT_OPTION_LABEL))
	button.custom_minimum_size = Vector2(0, 44)
	button.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	button.focus_mode = Control.FOCUS_ALL
	button.add_theme_font_size_override("font_size", 20)
	button.add_theme_color_override("font_color", CONSOLE_BUTTON_TEXT_COLOR)
	button.add_theme_color_override("font_hover_color", CONSOLE_BUTTON_TEXT_COLOR)
	button.add_theme_color_override("font_pressed_color", CONSOLE_BUTTON_TEXT_COLOR)
	button.add_theme_color_override("font_focus_color", CONSOLE_BUTTON_TEXT_COLOR)
	button.add_theme_stylebox_override("normal", _build_button_style(CONSOLE_BUTTON_COLOR))
	button.add_theme_stylebox_override("hover", _build_button_style(CONSOLE_BUTTON_COLOR.lightened(0.08)))
	button.add_theme_stylebox_override("pressed", _build_button_style(CONSOLE_BUTTON_COLOR.darkened(0.12)))
	button.pressed.connect(_on_console_button_pressed.bind(str(option.get("action", DEFAULT_OPTION_ACTION))))
	console_content.add_child(button)


func _build_button_style(color: Color) -> StyleBoxFlat:
	var style := StyleBoxFlat.new()
	style.bg_color = color
	style.corner_radius_top_left = 10
	style.corner_radius_top_right = 10
	style.corner_radius_bottom_right = 10
	style.corner_radius_bottom_left = 10
	style.content_margin_left = 16
	style.content_margin_right = 16
	style.content_margin_top = 10
	style.content_margin_bottom = 10
	return style


func _on_console_button_pressed(action_id: String) -> void:
	console_option_selected.emit(action_id, _current_room_id)


func _reset_console_scroll() -> void:
	console_scroll.scroll_vertical = 0


func _scroll_console_to_bottom() -> void:
	console_scroll.scroll_vertical = int(console_scroll.get_v_scroll_bar().max_value)
