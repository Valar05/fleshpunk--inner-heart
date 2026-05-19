extends Node2D

const HEART_MANAGER_PATH := "/root/HeartManager"
const RUN_MANAGER_PATH := "/root/RunManager"
const HEART_MANAGER_GROUP := "heart_manager"
const MUTATION_SCENE_PATH := "res://mutation.tscn"
const TTS_MANIFEST_PATH := "res://audio/tts_manifest.json"
const CLASH_TRAVEL_DURATION := 0.14
const CLASH_RECOVER_DURATION := 0.18
const DISSOLVE_DURATION := 0.45
const PROGRESS_PARAMETER := "progress"
const PULSE_AMOUNT_PARAMETER := "pulse_amount"
const PULSE_TRANSITION := Tween.TRANS_SINE
const PULSE_EASE := Tween.EASE_IN_OUT
const ROOM_FADE_TRANSITION := Tween.TRANS_SINE
const ROOM_FADE_EASE := Tween.EASE_IN_OUT
const CombatSystemScript := preload("res://combat_system.gd")
const CommandParserScript := preload("res://command_parser.gd")
const CHOICE_NUMBER_WORDS := ["one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]
const PROCEED_BUTTON := {
	"label": "Proceed.",
	"action": "proceed",
	"voice_aliases": ["proceed", "advance", "move on", "go forward", "step through"]
}
const LEAVE_MERCHANT_BUTTON := {
	"label": "Leave",
	"action": "leave_merchant",
	"voice_aliases": ["leave", "leave merchant", "walk away", "back off", "withdraw"]
}

@export_range(0.01, 2.0, 0.01) var base_pulse_duration: float = 0.96
@export_range(0.1, 1.0, 0.01) var pulse_occupancy: float = 0.72
@export_range(0.05, 0.5, 0.01) var pulse_release_ratio: float = 0.22
@export_range(0.05, 2.0, 0.01) var room_fade_duration: float = 0.35
@export var current_room_id := "red_corridor"
@export var tts_bus_name := "Master"
@export_range(-80.0, 12.0, 0.1) var tts_volume_db := 0.0
@export var tts_debug_logs := true

@onready var room_sprite: Sprite2D = $RoomSprite
@onready var merchant_actor: Sprite2D = $Merchant
@onready var dashboard: Sprite2D = $FleshpunkDashboard
@onready var player_actor: Node2D = $Hymn
@onready var enemy_actor: Node2D = $Enemy
@onready var player_home: Marker2D = $PlayerSpot
@onready var enemy_home: Marker2D = $PlacementSpot

var _heart_manager: Node
var _pulse_material: ShaderMaterial
var _pulse_tween: Tween
var _pulse_strength := 1.0
var _room_transition_tween: Tween
var _is_room_transitioning := false
var _combat_tween: Tween
var _is_combat_resolving := false
var _encounter_scene: Node2D
var _pending_advance_after_ack := false
var _rng := RandomNumberGenerator.new()
var _tts_player: AudioStreamPlayer
var _tts_clip_files: Dictionary = {}
var _tts_text_clip_files: Dictionary = {}
var _tts_queue: Array[String] = []
var _tts_sequence_token := 0
var _tts_pitch_scale := 1.0
var _command_parser
var _current_console_lines: Array = []
var _current_console_buttons: Array = []
var _current_console_room_id := ""
var _current_console_encounter: Dictionary = {}
var _pending_confirmation_action: Dictionary = {}
var _last_text_surface_size := Vector2.ZERO


func _ready() -> void:
	RenderingServer.set_default_clear_color(Color.BLACK)
	_rng.randomize()
	_pulse_material = room_sprite.material as ShaderMaterial
	if _pulse_material == null:
		push_warning("RoomSprite is missing a ShaderMaterial. Room pulse is disabled.")
		return

	_pulse_strength = float(_pulse_material.get_shader_parameter(PULSE_AMOUNT_PARAMETER))
	_reset_pulse_state()
	_command_parser = CommandParserScript.new()
	_connect_dashboard()
	_connect_viewport_resize()
	_configure_text_only_surface()
	call_deferred("_configure_text_only_surface")
	_prepare_actors()
	_setup_tts_audio()
	var run_manager := _get_run_manager()
	if run_manager == null:
		push_warning("RunManager not found. Encounter flow is disabled.")
		return

	run_manager.start_new_run()
	_present_encounter(run_manager.get_current_encounter())

	_heart_manager = _resolve_heart_manager()
	if _heart_manager == null:
		push_warning("HeartManager not found. Room pulse is disabled.")
		return

	if not _heart_manager.pulse.is_connected(_on_heart_pulse):
		_heart_manager.pulse.connect(_on_heart_pulse)

	if _heart_manager.has_method("trigger_pulse"):
		_heart_manager.call_deferred("trigger_pulse")
	else:
		call_deferred("_on_heart_pulse", _get_current_bpm())


func _exit_tree() -> void:
	if _heart_manager != null and _heart_manager.pulse.is_connected(_on_heart_pulse):
		_heart_manager.pulse.disconnect(_on_heart_pulse)


func _on_heart_pulse(current_bpm: float) -> void:
	if _pulse_material == null:
		return

	if _pulse_tween != null:
		_pulse_tween.kill()

	var beat_interval = 60.0 / max(current_bpm, 0.1)
	var pulse_duration = min(base_pulse_duration, beat_interval * pulse_occupancy)
	var release_duration = max(pulse_duration * pulse_release_ratio, 0.01)
	var travel_duration = max(pulse_duration - release_duration, 0.01)

	_pulse_material.set_shader_parameter(PULSE_AMOUNT_PARAMETER, _pulse_strength)
	_pulse_material.set_shader_parameter(PROGRESS_PARAMETER, 0.0)

	_pulse_tween = create_tween()
	_pulse_tween.tween_method(_set_pulse_progress, 0.0, 1.0, travel_duration).set_trans(PULSE_TRANSITION).set_ease(PULSE_EASE)
	_pulse_tween.tween_method(_set_pulse_amount, _pulse_strength, 0.0, release_duration).set_trans(PULSE_TRANSITION).set_ease(Tween.EASE_OUT)
	_pulse_tween.tween_callback(_reset_pulse_state)


func _set_pulse_progress(value: float) -> void:
	if _pulse_material != null:
		_pulse_material.set_shader_parameter(PROGRESS_PARAMETER, value)


func _set_pulse_amount(value: float) -> void:
	if _pulse_material != null:
		_pulse_material.set_shader_parameter(PULSE_AMOUNT_PARAMETER, value)


func _reset_pulse_state() -> void:
	if _pulse_material != null:
		_pulse_material.set_shader_parameter(PROGRESS_PARAMETER, 0.0)
		_pulse_material.set_shader_parameter(PULSE_AMOUNT_PARAMETER, 0.0)


func _resolve_heart_manager() -> Node:
	var manager := get_node_or_null(HEART_MANAGER_PATH)
	if manager != null:
		return manager

	var group_members := get_tree().get_nodes_in_group(HEART_MANAGER_GROUP)
	if group_members.is_empty():
		return null

	return group_members[0]


func _get_current_bpm() -> float:
	if _heart_manager != null:
		var current_bpm = _heart_manager.get("bpm")
		if current_bpm != null:
			return float(current_bpm)

	return 10.0


func change_room(room_id: String, room_data: Dictionary = {}) -> void:
	current_room_id = room_id
	if room_data.is_empty():
		var run_manager := _get_run_manager()
		if run_manager != null:
			room_data = run_manager.get_room_data(room_id)

	room_sprite.visible = false
	room_sprite.modulate.a = 1.0


func _configure_text_only_surface() -> void:
	var viewport_size := get_viewport_rect().size
	if viewport_size.x <= 0.0 or viewport_size.y <= 0.0:
		return
	_last_text_surface_size = viewport_size
	room_sprite.visible = false
	merchant_actor.visible = false
	player_actor.visible = false
	enemy_actor.visible = false
	dashboard.visible = true
	dashboard.position = viewport_size * 0.5
	dashboard.scale = Vector2.ONE
	dashboard.z_index = 100
	if dashboard.has_method("set_fullscreen_console_layout"):
		dashboard.call("set_fullscreen_console_layout", viewport_size)


func _connect_viewport_resize() -> void:
	var viewport := get_viewport()
	if viewport == null:
		return
	if not viewport.size_changed.is_connected(_on_viewport_size_changed):
		viewport.size_changed.connect(_on_viewport_size_changed)


func _on_viewport_size_changed() -> void:
	call_deferred("_configure_text_only_surface")


func _connect_dashboard() -> void:
	if dashboard != null and dashboard.has_signal("console_option_selected") and not dashboard.is_connected("console_option_selected", Callable(self, "_on_console_option_selected")):
		dashboard.connect("console_option_selected", Callable(self, "_on_console_option_selected"))
	if dashboard != null and dashboard.has_signal("console_command_submitted") and not dashboard.is_connected("console_command_submitted", Callable(self, "_on_console_command_submitted")):
		dashboard.connect("console_command_submitted", Callable(self, "_on_console_command_submitted"))


func _on_console_command_submitted(command_text: String, room_id: String) -> void:
	if _is_room_transitioning or _is_combat_resolving:
		return
	if _command_parser == null:
		_command_parser = CommandParserScript.new()

	var parse_result: Dictionary = _command_parser.parse_command(command_text, _current_console_buttons, _build_command_context())
	match str(parse_result.get("type", "")):
		"action":
			var action_id := str(parse_result.get("action", ""))
			if action_id != "":
				if bool(parse_result.get("needs_confirmation", false)):
					_pending_confirmation_action = {
						"action_id": action_id,
						"room_id": room_id,
						"label": str(parse_result.get("label", "")),
						"prompt": str(parse_result.get("prompt", "I think you meant that action."))
					}
					_show_confirmation_prompt(str(parse_result.get("prompt", "I think you meant that action.")))
					return
				_on_console_option_selected(action_id, room_id)
		"global":
			_handle_global_command(str(parse_result.get("command", "")))
		"ambiguous":
			_show_transient_console_audio(
				[str(parse_result.get("prompt", "I matched more than one command."))],
				_current_console_buttons,
				_current_console_room_id
			)
		_:
			_show_transient_console_audio(
				[str(parse_result.get("prompt", "I did not match that.")), "Say repeat choices, status, or a choice number."],
				[],
				_current_console_room_id
			)


func _build_command_context() -> Dictionary:
	return {
		"room_id": _current_console_room_id,
		"buttons": _current_console_buttons,
		"lines": _current_console_lines,
		"event_id": str(_current_console_encounter.get("event_id", ""))
	}


func _handle_global_command(command: String) -> void:
	_stop_tts_audio()
	match command:
		"repeat":
			_replay_current_console()
		"repeat_choices":
			_show_transient_console_audio(["Current choices."], _current_console_buttons, _current_console_room_id)
		"status":
			_show_transient_console_audio(_build_status_lines(), _current_console_buttons, _current_console_room_id)
		"inventory":
			_show_transient_console_audio(_build_inventory_lines(), _current_console_buttons, _current_console_room_id)
		"help":
			_show_transient_console_audio(["Say repeat choices, status, or a choice number."], [], _current_console_room_id)
		"confirm":
			if not _pending_confirmation_action.is_empty():
				var pending_action_id := str(_pending_confirmation_action.get("action_id", ""))
				var pending_room_id := str(_pending_confirmation_action.get("room_id", _current_console_room_id))
				_pending_confirmation_action.clear()
				if pending_action_id != "":
					_on_console_option_selected(pending_action_id, pending_room_id)
					return
			_show_transient_console_audio(["Nothing is waiting for confirmation."], _current_console_buttons, _current_console_room_id)
		"slower":
			_adjust_tts_pitch(-0.1)
			_show_transient_console_audio(["Speech slower.", "Current speed: %.2fx." % _tts_pitch_scale], _current_console_buttons, _current_console_room_id)
		"faster":
			_adjust_tts_pitch(0.1)
			_show_transient_console_audio(["Speech faster.", "Current speed: %.2fx." % _tts_pitch_scale], _current_console_buttons, _current_console_room_id)
		"pause":
			_show_transient_console_audio(["Audio paused."], _current_console_buttons, _current_console_room_id)
		"cancel":
			_pending_confirmation_action.clear()
			_show_transient_console_audio(["Action cancelled."], _current_console_buttons, _current_console_room_id)
		"continue_audio":
			_replay_current_console()
		_:
			_show_transient_console_audio(["I did not match that.", "Say repeat choices, status, inventory, confirm, cancel, slower, faster, or a choice number."], _current_console_buttons, _current_console_room_id)


func _on_console_option_selected(action_id: String, room_id: String) -> void:
	if _is_room_transitioning or _is_combat_resolving:
		return

	_stop_tts_audio()
	if action_id != "confirm" and action_id != "cancel":
		_pending_confirmation_action.clear()

	var run_manager := _get_run_manager()
	if run_manager == null:
		return

	if _pending_advance_after_ack and action_id == "proceed":
		_pending_advance_after_ack = false
		_transition_to_encounter(run_manager.advance_to_next_encounter())
		return

	if action_id == "proceed":
		run_manager.consume_current_event("proceed")
		_transition_to_encounter(run_manager.advance_to_next_encounter())
		return

	if action_id == "combat":
		var combat_encounter: Dictionary = run_manager.get_current_encounter()
		run_manager.consume_current_event("combat")
		_begin_room_combat(combat_encounter.get("enemy_data", {}), combat_encounter.get("event_data", {}))
		return

	if action_id == "restart_run":
		_clear_encounter_scene()
		_prepare_actors()
		run_manager.start_new_run()
		_pending_advance_after_ack = false
		_pending_confirmation_action.clear()
		_present_encounter(run_manager.get_current_encounter())
		return

	if action_id == "browse_wares":
		var shop_offer: Dictionary = run_manager.call("get_merchant_shop_offer") if run_manager.has_method("get_merchant_shop_offer") else {}
		_show_console_audio(
			shop_offer.get("lines", ["The merchant's hands move, but I cannot read the scale."]),
			shop_offer.get("buttons", [LEAVE_MERCHANT_BUTTON.duplicate(true)]),
			room_id
		)
		return

	if action_id.begins_with("buy_mutation:"):
		if run_manager.has_method("buy_shop_mutation"):
			var mutation_id := action_id.substr("buy_mutation:".length())
			var purchase_result: Dictionary = run_manager.call("buy_shop_mutation", mutation_id)
			_show_console_audio(
				purchase_result.get("lines", []),
				purchase_result.get("buttons", [LEAVE_MERCHANT_BUTTON.duplicate(true)]),
				room_id
			)
		return

	if action_id.begins_with("take_symbiote:"):
		run_manager.consume_current_event(action_id)
		var symbiote_result := _get_last_action_result(run_manager)
		if not symbiote_result.is_empty():
			_show_action_result(symbiote_result, room_id)
		return

	if action_id.begins_with("activate_symbiote:"):
		if run_manager.has_method("activate_symbiote"):
			var symbiote_id := action_id.substr("activate_symbiote:".length())
			var activation_result: Dictionary = run_manager.call("activate_symbiote", symbiote_id)
			_show_console_audio(
				activation_result.get("lines", []),
				activation_result.get("buttons", [PROCEED_BUTTON.duplicate(true)]),
				room_id
			)
		return

	run_manager.consume_current_event(action_id)
	var action_result := _get_last_action_result(run_manager)
	if not action_result.is_empty():
		_show_action_result(action_result, room_id)
		return

	_show_console_audio(["That interaction is not implemented yet.", "I move on."], [PROCEED_BUTTON.duplicate(true)], room_id)
	_pending_advance_after_ack = true


func _transition_to_encounter(encounter: Dictionary) -> void:
	if _is_room_transitioning:
		return

	if encounter.is_empty():
		return

	_is_room_transitioning = true
	if _room_transition_tween != null:
		_room_transition_tween.kill()

	if dashboard.has_method("clear_console"):
		dashboard.call("clear_console")
	_stop_tts_audio()
	_clear_encounter_scene()

	_room_transition_tween = create_tween()
	_room_transition_tween.tween_property(room_sprite, "modulate:a", 0.0, room_fade_duration).set_trans(ROOM_FADE_TRANSITION).set_ease(ROOM_FADE_EASE)
	_room_transition_tween.tween_callback(_present_encounter.bind(encounter, true))
	_room_transition_tween.tween_property(room_sprite, "modulate:a", 1.0, room_fade_duration).set_trans(ROOM_FADE_TRANSITION).set_ease(ROOM_FADE_EASE)
	_room_transition_tween.tween_callback(_finish_room_transition)


func _finish_room_transition() -> void:
	_is_room_transitioning = false


func _begin_room_combat(enemy_stats: Dictionary, event_data: Dictionary = {}) -> void:
	_is_combat_resolving = true
	_clear_encounter_scene()
	if dashboard.has_method("show_console"):
		dashboard.call("show_console", ["Combat engaged."], [], current_room_id)

	var prepared_enemy_stats := _get_enemy_stats(enemy_stats)
	var combat_result := CombatSystemScript.simulate_combat(_get_player_stats(), prepared_enemy_stats, _rng)
	_play_combat_animation(combat_result, prepared_enemy_stats, event_data)


func _prepare_actors() -> void:
	merchant_actor.visible = false
	if player_actor.has_method("show_world_pose"):
		player_actor.call("show_world_pose", false)
	player_actor.position = player_home.position
	player_actor.visible = false

	if enemy_actor.has_method("reset_visuals"):
		if enemy_actor.has_method("set_visual_scale_multiplier"):
			enemy_actor.call("set_visual_scale_multiplier", 1.0)
		enemy_actor.call("reset_visuals")
	if enemy_actor.has_method("show_world_pose"):
		enemy_actor.call("show_world_pose", true)
	enemy_actor.position = enemy_home.position
	enemy_actor.visible = false
	_clear_encounter_scene()


func _get_player_stats() -> Dictionary:
	var base_stats := {}
	if player_actor.has_method("get_combat_stats"):
		base_stats = player_actor.call("get_combat_stats")
	var run_manager := _get_run_manager()
	if run_manager != null:
		return run_manager.get_player_combat_stats(base_stats)
	return base_stats


func _get_enemy_stats(enemy_stats: Dictionary) -> Dictionary:
	var run_manager := _get_run_manager()
	if run_manager != null and run_manager.has_method("prepare_enemy_combat_stats"):
		return run_manager.call("prepare_enemy_combat_stats", enemy_stats)
	return enemy_stats


func _play_combat_animation(combat_result: Dictionary, enemy_stats: Dictionary, event_data: Dictionary = {}) -> void:
	if _combat_tween != null:
		_combat_tween.kill()

	var enemy_visual: Node2D = merchant_actor if str(enemy_stats.get("id", "")) == "merchant" else enemy_actor
	player_actor.visible = true
	enemy_actor.visible = enemy_visual == enemy_actor
	merchant_actor.visible = enemy_visual == merchant_actor
	if enemy_visual == enemy_actor and enemy_actor.has_method("set_visual_scale_multiplier"):
		enemy_actor.call("set_visual_scale_multiplier", float(enemy_stats.get("visual_scale", 1.0)))
	if player_actor.has_method("show_combat_pose"):
		player_actor.call("show_combat_pose", false)
	if enemy_visual.has_method("show_combat_pose"):
		enemy_visual.call("show_combat_pose", true)

	player_actor.position = player_home.position
	enemy_visual.position = enemy_home.position

	var clash_point := (player_home.position + enemy_home.position) * 0.5
	var player_clash_position := clash_point + Vector2(-90.0, 0.0)
	var enemy_clash_position := clash_point + Vector2(90.0, 0.0)
	var loser: Node2D = enemy_visual if bool(combat_result.get("player_won", false)) else player_actor

	_combat_tween = create_tween()
	_combat_tween.parallel().tween_property(player_actor, "position", player_clash_position, CLASH_TRAVEL_DURATION).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	_combat_tween.parallel().tween_property(enemy_visual, "position", enemy_clash_position, CLASH_TRAVEL_DURATION).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	_combat_tween.parallel().tween_method(_set_actor_dissolve.bind(loser), 0.0, 1.0, DISSOLVE_DURATION).set_delay(CLASH_TRAVEL_DURATION)
	_combat_tween.parallel().tween_property(player_actor, "position", player_home.position, CLASH_RECOVER_DURATION).set_delay(CLASH_TRAVEL_DURATION).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN_OUT)
	_combat_tween.parallel().tween_property(enemy_visual, "position", enemy_home.position, CLASH_RECOVER_DURATION).set_delay(CLASH_TRAVEL_DURATION).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN_OUT)
	_combat_tween.tween_callback(_finalize_combat.bind(combat_result, enemy_stats, event_data))


func _set_actor_dissolve(value: float, actor: Node2D) -> void:
	if actor != null and actor.has_method("set_dissolve_progress"):
		actor.call("set_dissolve_progress", value)


func _finalize_combat(combat_result: Dictionary, enemy_stats: Dictionary, event_data: Dictionary = {}) -> void:
	var run_manager := _get_run_manager()
	if run_manager != null:
		combat_result = run_manager.apply_combat_result(combat_result, enemy_stats)
	var enemy_name := str(enemy_stats.get("name", enemy_stats.get("enemy_name", "Enemy")))
	var is_game_over_combat := bool(event_data.get("game_over_on_combat", enemy_stats.get("game_over_on_combat", false)))
	var biomass_total := 0
	if run_manager != null:
		biomass_total = int(run_manager.biomass)
	var lines: Array[String] = [
		"Combat Result:",
		"Enemy tier: %d" % int(enemy_stats.get("tier", 1)),
		"Health lost: %d" % int(combat_result.get("player_damage_taken", 0)),
		"Shield lost: %d" % int(combat_result.get("player_shield_lost", 0)),
		"Biomass: %d" % biomass_total
	]

	if bool(combat_result.get("player_won", false)):
		lines.append("%s dissolved." % enemy_name)
	elif bool(combat_result.get("mitosis_triggered", false)):
		lines.append("The Mitosis Unit takes the death for me.")
		lines.append("It is gone. I wake with one heartbeat left.")
	else:
		lines.append("The player was overwhelmed.")

	if is_game_over_combat:
		if str(enemy_stats.get("id", "")) == "merchant":
			if bool(combat_result.get("player_won", false)):
				lines.append("I beat him. The scale still closes.")
			else:
				lines.append("He takes me apart by weight.")
			lines.append("The last signal I send is noise.")
		elif str(enemy_stats.get("id", "")) == "blood_hunter":
			if bool(combat_result.get("player_won", false)):
				lines.append("I kill the hunter. The route still ends here.")
			else:
				lines.append("The hunter opens me and drinks the run dry.")
			lines.append("The last signal I send is buzzing.")
		else:
			lines.append("This pressure claims the run.")

	var buttons := [PROCEED_BUTTON.duplicate(true)]
	if is_game_over_combat:
		buttons = [{
			"label": "Wake again",
			"action": "restart_run",
			"voice_aliases": ["wake again", "restart", "wake", "again"]
		}]
	_show_console_audio(lines, buttons, current_room_id)

	_prepare_actors()
	_pending_advance_after_ack = not is_game_over_combat
	_is_combat_resolving = false


func _present_encounter(encounter: Dictionary, faded: bool = false) -> void:
	if encounter.is_empty():
		return

	var room_id := str(encounter.get("room_id", current_room_id))
	var room_data: Dictionary = encounter.get("room_data", {})
	var event_data: Dictionary = encounter.get("event_data", {})
	merchant_actor.visible = false
	if room_id != "" and not room_data.is_empty():
		change_room(room_id, room_data)

	if faded:
		room_sprite.modulate.a = 0.0

	_clear_encounter_scene()
	var scene_path := str(encounter.get("scene_path", ""))
	if false and scene_path != "":
		_show_encounter_scene(scene_path, str(event_data.get("spawn_animation", "")))

	var lines: Array = encounter.get("lines", [])
	var buttons: Array = encounter.get("buttons", [PROCEED_BUTTON.duplicate(true)])
	_show_console_audio(lines, buttons, room_id, encounter)


func _show_acknowledgement(lines: Array[String]) -> void:
	_pending_advance_after_ack = true
	_show_console_audio(lines, [PROCEED_BUTTON.duplicate(true)], current_room_id)


func _show_action_result(action_result: Dictionary, room_id: String) -> void:
	var animation_name := str(action_result.get("play_animation", ""))
	if animation_name != "":
		_play_encounter_animation(animation_name)

	var run_manager := _get_run_manager()
	if run_manager != null:
		var encounter: Dictionary = run_manager.get_current_encounter()
		var event_data: Dictionary = encounter.get("event_data", {})
		if _encounter_shows_merchant(encounter, event_data):
			merchant_actor.visible = false

	var lines: Array[String] = []
	var result_lines = action_result.get("lines", [])
	if result_lines is Array:
		for line in result_lines:
			lines.append(str(line))

	if lines.is_empty():
		lines = ["That interaction is not implemented yet.", "I move on."]

	_pending_advance_after_ack = bool(action_result.get("advance_after_ack", true))
	var buttons: Array = action_result.get("buttons", [PROCEED_BUTTON.duplicate(true)])
	_show_console_audio(lines, buttons, room_id if room_id != "" else current_room_id)


func _get_last_action_result(run_manager: Node) -> Dictionary:
	if run_manager != null and run_manager.has_method("get_last_action_result"):
		return run_manager.call("get_last_action_result")
	return {}


func _encounter_shows_merchant(encounter: Dictionary, event_data: Dictionary) -> bool:
	if str(event_data.get("type", "")) == "merchant":
		return true
	return str(encounter.get("event_id", "")) == "merchant_arrival"


func _show_console_audio(lines: Array, buttons: Array, room_id: String, encounter: Dictionary = {}) -> void:
	_current_console_lines = lines.duplicate(true)
	_current_console_buttons = buttons.duplicate(true)
	_current_console_room_id = room_id
	_current_console_encounter = encounter.duplicate(true)
	if dashboard.has_method("show_console"):
		dashboard.call("show_console", lines, buttons, room_id)
	_focus_command_input()

	_tts_sequence_token += 1
	if encounter.is_empty():
		call_deferred("_play_generated_console_audio", lines, buttons, _tts_sequence_token)
	else:
		call_deferred("_play_encounter_audio", encounter, lines, buttons, _tts_sequence_token)


func _show_transient_console_audio(lines: Array, buttons: Array, room_id: String) -> void:
	if dashboard.has_method("show_console"):
		dashboard.call("show_console", lines, buttons, room_id)
	_focus_command_input()

	_tts_sequence_token += 1
	call_deferred("_play_generated_console_audio", lines, buttons, _tts_sequence_token)


func _show_confirmation_prompt(prompt_text: String) -> void:
	_stop_tts_audio()
	_tts_sequence_token += 1
	if dashboard.has_method("show_console"):
		dashboard.call("show_console", [prompt_text, "Say confirm or cancel."], _current_console_buttons, _current_console_room_id)
	_focus_command_input()
	_play_tts_clip_sequence(["system_confirm"])


func _replay_current_console() -> void:
	if _current_console_lines.is_empty() and _current_console_buttons.is_empty():
		_show_transient_console_audio(["Say repeat choices, status, or a choice number."], _current_console_buttons, _current_console_room_id)
		return
	if dashboard.has_method("show_console"):
		dashboard.call("show_console", _current_console_lines, _current_console_buttons, _current_console_room_id)
	_focus_command_input()

	_tts_sequence_token += 1
	if _current_console_encounter.is_empty():
		call_deferred("_play_generated_console_audio", _current_console_lines, _current_console_buttons, _tts_sequence_token)
	else:
		call_deferred("_play_encounter_audio", _current_console_encounter, _current_console_lines, _current_console_buttons, _tts_sequence_token)


func _build_status_lines() -> Array[String]:
	var run_manager := _get_run_manager()
	if run_manager == null:
		return ["Status report.", "Run manager unavailable."]

	var player_state: Dictionary = run_manager.get("player_state")
	var director_state: Dictionary = run_manager.call("get_director_state") if run_manager.has_method("get_director_state") else {}
	var lines: Array[String] = [
		"Status report.",
		"Health: %d." % int(player_state.get("health", 0)),
		"Shield: %d." % int(player_state.get("shield", 0)),
		"Biomass: %d." % int(run_manager.get("biomass")),
		"Danger: %d." % int(run_manager.get("danger")),
		"Corruption: %d." % int(run_manager.get("corruption"))
	]
	var ending_pressure := str(director_state.get("ending_pressure", ""))
	if ending_pressure != "":
		lines.append("Ending pressure: %s." % ending_pressure)
	return lines


func _build_inventory_lines() -> Array[String]:
	var run_manager := _get_run_manager()
	if run_manager == null:
		return ["Inventory report.", "Run manager unavailable."]

	var lines: Array[String] = [
		"Inventory report.",
		"Biomass: %d." % int(run_manager.get("biomass"))
	]
	var mutation_names := _named_items_from_run_manager(run_manager, "owned_mutations", "mutations_by_id")
	var symbiote_names := _named_items_from_run_manager(run_manager, "owned_symbiotes", "symbiotes_by_id")
	lines.append("Mutations: %s." % ("none" if mutation_names.is_empty() else ", ".join(mutation_names)))
	lines.append("Symbiotes: %s." % ("none" if symbiote_names.is_empty() else ", ".join(symbiote_names)))
	return lines


func _named_items_from_run_manager(run_manager: Node, owned_key: String, data_key: String) -> Array[String]:
	var names: Array[String] = []
	var owned = run_manager.get(owned_key)
	var data = run_manager.get(data_key)
	if not owned is Array or not data is Dictionary:
		return names
	for item_id_variant in owned:
		var item_id := str(item_id_variant)
		var item_data: Dictionary = data.get(item_id, {})
		names.append(str(item_data.get("name", item_id)))
	return names


func _setup_tts_audio() -> void:
	_tts_player = get_node_or_null("TTSPlayer") as AudioStreamPlayer
	if _tts_player == null:
		_tts_player = AudioStreamPlayer.new()
		_tts_player.name = "TTSPlayer"
		add_child(_tts_player)
	_apply_tts_audio_settings()
	if not _tts_player.finished.is_connected(_on_tts_finished):
		_tts_player.finished.connect(_on_tts_finished)
	_ensure_tts_bus_audible()
	_load_tts_manifest()


func _apply_tts_audio_settings() -> void:
	if _tts_player == null:
		return
	_tts_player.bus = _resolve_tts_bus_name()
	_tts_player.volume_db = tts_volume_db
	_tts_player.pitch_scale = _tts_pitch_scale


func _load_tts_manifest() -> void:
	_tts_clip_files.clear()
	_tts_text_clip_files.clear()
	if not FileAccess.file_exists(TTS_MANIFEST_PATH):
		return

	var file := FileAccess.open(TTS_MANIFEST_PATH, FileAccess.READ)
	if file == null:
		push_warning("Unable to open TTS manifest: %s" % TTS_MANIFEST_PATH)
		return

	var parsed = JSON.parse_string(file.get_as_text())
	if not parsed is Dictionary:
		push_warning("TTS manifest is not valid JSON.")
		return

	var clips = parsed.get("clips", [])
	if not clips is Array:
		return

	for clip in clips:
		if not clip is Dictionary:
			continue
		var clip_id := str(clip.get("id", ""))
		var clip_file := str(clip.get("file", ""))
		if clip_id != "" and clip_file != "":
			_tts_clip_files[clip_id] = clip_file
		var text_key := str(clip.get("text_key", ""))
		if text_key != "" and clip_file != "" and not _tts_text_clip_files.has(text_key):
			_tts_text_clip_files[text_key] = clip_file


func _play_encounter_audio(encounter: Dictionary, lines: Array, buttons: Array, sequence_token: int) -> void:
	await get_tree().create_timer(0.15).timeout
	if sequence_token != _tts_sequence_token:
		return

	var event_id := str(encounter.get("event_id", ""))
	if event_id == "" or _tts_clip_files.is_empty():
		_log_tts("No TTS clips queued. event=%s manifest_clips=%d" % [event_id, _tts_clip_files.size()])
		_play_generated_console_audio(lines, buttons, sequence_token)
		return

	var clip_ids: Array[String] = []
	for line_index in range(lines.size()):
		var line_clip_id := "%s_line_%d" % [event_id, line_index + 1]
		if _tts_clip_files.has(line_clip_id):
			clip_ids.append(line_clip_id)

	for button_index in range(buttons.size()):
		var choice_clip_id := "%s_choice_%d" % [event_id, button_index + 1]
		if _tts_clip_files.has(choice_clip_id):
			clip_ids.append(choice_clip_id)

	_log_tts("Encounter %s queued %d TTS clips." % [event_id, clip_ids.size()])
	if clip_ids.is_empty():
		_play_generated_console_audio(lines, buttons, sequence_token)
	else:
		_play_tts_clip_sequence(clip_ids)


func _play_generated_console_audio(lines: Array, buttons: Array, sequence_token: int) -> void:
	await get_tree().create_timer(0.15).timeout
	if sequence_token != _tts_sequence_token:
		return
	_play_generated_console_audio_now(lines, buttons)


func _play_tts_clip_sequence(clip_ids: Array[String]) -> void:
	_stop_tts_playback_only()

	for clip_id in clip_ids:
		var clip_file := str(_tts_clip_files.get(clip_id, ""))
		if _tts_clip_available(clip_file):
			_tts_queue.append(clip_id)
		else:
			_log_tts("Missing TTS file for %s: %s" % [clip_id, clip_file])

	_play_next_tts_clip()


func _play_tts_file_sequence(clip_files: Array[String]) -> void:
	_stop_tts_playback_only()
	for clip_file in clip_files:
		if _tts_clip_available(clip_file):
			_tts_queue.append(clip_file)
		else:
			_log_tts("Missing TTS file: %s" % clip_file)
	_play_next_tts_clip()


func _play_next_tts_clip() -> void:
	if _tts_player == null:
		return
	if _tts_queue.is_empty():
		return

	var clip_id := str(_tts_queue.pop_front())
	var clip_file := str(_tts_clip_files.get(clip_id, clip_id))
	if clip_file == "":
		_play_next_tts_clip()
		return

	var stream = _load_tts_audio_stream(clip_file)
	if not stream is AudioStream:
		_log_tts("Failed to load TTS stream: %s" % clip_file)
		_play_next_tts_clip()
		return

	_tts_player.stream = stream
	_apply_tts_audio_settings()
	_tts_player.play()
	_log_tts("Playing %s on bus %s at %.1f dB with pitch %.2f." % [clip_id, _tts_player.bus, _tts_player.volume_db, _tts_player.pitch_scale])


func _load_tts_audio_stream(clip_file: String) -> AudioStream:
	if ResourceLoader.exists(clip_file):
		var imported_stream = load(clip_file)
		if imported_stream is AudioStream:
			return imported_stream
	match clip_file.get_extension().to_lower():
		"wav":
			return AudioStreamWAV.load_from_file(clip_file)
		"mp3":
			return AudioStreamMP3.load_from_file(clip_file)
		"ogg":
			return AudioStreamOggVorbis.load_from_file(clip_file)
	return load(clip_file) as AudioStream


func _tts_clip_available(clip_file: String) -> bool:
	if clip_file == "":
		return false
	return ResourceLoader.exists(clip_file) or FileAccess.file_exists(clip_file)


func _play_generated_console_audio_now(lines: Array, buttons: Array) -> void:
	var phrases := _build_console_speech_phrases(lines, buttons)
	var clip_files: Array[String] = []
	for phrase in phrases:
		var key := _tts_text_key(phrase)
		if not _tts_text_clip_files.has(key):
			_log_tts("No generated follow-up clip for phrase: %s" % phrase)
			continue
		clip_files.append(str(_tts_text_clip_files[key]))

	if clip_files.is_empty():
		_log_tts("No generated clips matched this console update.")
		return
	_log_tts("Generated follow-up TTS matched %d clips." % clip_files.size())
	_play_tts_file_sequence(clip_files)


func _build_console_speech_text(lines: Array, buttons: Array) -> String:
	return " ".join(_build_console_speech_phrases(lines, buttons))


func _build_console_speech_phrases(lines: Array, buttons: Array) -> Array[String]:
	var speech_parts: Array[String] = []
	for line in lines:
		for phrase in _expand_spoken_line(str(line)):
			if phrase != "":
				speech_parts.append(phrase)

	for index in range(buttons.size()):
		var button = buttons[index]
		if not button is Dictionary:
			continue
		var label := str(button.get("label", "")).strip_edges()
		if label == "":
			continue
		var number_word := str(index + 1)
		if index < CHOICE_NUMBER_WORDS.size():
			number_word = str(CHOICE_NUMBER_WORDS[index])
		speech_parts.append(_normalize_spoken_phrase("Choice %s. %s." % [number_word, label.trim_suffix(".")]))

	return speech_parts


func _adjust_tts_pitch(delta: float) -> void:
	_tts_pitch_scale = clamp(_tts_pitch_scale + delta, 0.75, 1.35)
	_apply_tts_audio_settings()


func _expand_spoken_line(line: String) -> Array[String]:
	var normalized := _normalize_spoken_phrase(line)
	if normalized == "":
		return []
	if _is_zero_value_tts_phrase(normalized):
		return []
	if normalized.find(":") == -1 and _tts_has_generated_phrase(normalized):
		return [normalized]

	var damage_pattern := RegEx.new()
	damage_pattern.compile("^(\\d+) damage hit\\. Barrier blocked (\\d+), armor blocked (\\d+), shield lost (\\d+), health lost (\\d+)\\.(.*)$")
	var damage_match := damage_pattern.search(normalized)
	if damage_match != null:
		var phrases: Array[String] = []
		_append_nonzero_stat_phrase(phrases, "Damage hit %s." % damage_match.get_string(1), int(damage_match.get_string(1)))
		_append_nonzero_stat_phrase(phrases, "Barrier blocked %s." % damage_match.get_string(2), int(damage_match.get_string(2)))
		_append_nonzero_stat_phrase(phrases, "Armor blocked %s." % damage_match.get_string(3), int(damage_match.get_string(3)))
		_append_nonzero_stat_phrase(phrases, "Shield lost %s." % damage_match.get_string(4), int(damage_match.get_string(4)))
		_append_nonzero_stat_phrase(phrases, "Health lost %s." % damage_match.get_string(5), int(damage_match.get_string(5)))
		var tail := str(damage_match.get_string(6)).strip_edges()
		if tail != "":
			for phrase in _split_sentence_phrases(tail):
				phrases.append(phrase)
		return phrases

	return _split_sentence_phrases(normalized)


func _split_sentence_phrases(text: String) -> Array[String]:
	var phrases: Array[String] = []
	for part in text.split(". ", false):
		var phrase := _canonical_tts_phrase(_normalize_spoken_phrase(part))
		if phrase != "":
			phrases.append(phrase)
	return phrases


func _canonical_tts_phrase(phrase: String) -> String:
	var normalized := _normalize_spoken_phrase(phrase)
	if normalized == "":
		return ""
	if _is_zero_value_tts_phrase(normalized):
		return ""

	var combat_result_pattern := RegEx.new()
	combat_result_pattern.compile("^Combat Result:\\.$")
	if combat_result_pattern.search(normalized) != null:
		return "Combat result."

	var label_patterns := [
		{"pattern": "^(\\d+) damage hit\\.$", "template": "Damage hit %s."},
		{"pattern": "^Biomass: (\\d+)\\.$", "template": "Biomass now %s."},
		{"pattern": "^Corruption: (\\d+)\\.$", "template": "Corruption now %s."},
		{"pattern": "^Danger: (\\d+)\\.$", "template": "Danger now %s."},
		{"pattern": "^Claim: (\\d+)\\.$", "template": "Claim now %s."},
		{"pattern": "^Marked route streak: (\\d+)\\.$", "template": "Marked route streak %s."},
		{"pattern": "^Health restored: (\\d+)\\.$", "template": "Health restored %s."},
		{"pattern": "^Shield restored: (\\d+)\\.$", "template": "Shield restored %s."},
		{"pattern": "^Health lost: (\\d+)\\.$", "template": "Health lost %s."},
		{"pattern": "^Shield lost: (\\d+)\\.$", "template": "Shield lost %s."},
		{"pattern": "^Enemy tier: (\\d+)\\.$", "template": "Enemy tier %s."},
	]
	for rule in label_patterns:
		var label_pattern := RegEx.new()
		label_pattern.compile(str(rule["pattern"]))
		var label_match := label_pattern.search(normalized)
		if label_match != null:
			if int(label_match.get_string(1)) == 0:
				return ""
			return str(rule["template"]) % label_match.get_string(1)

	return normalized


func _append_nonzero_stat_phrase(phrases: Array[String], phrase: String, value: int) -> void:
	if value != 0:
		phrases.append(phrase)


func _is_zero_value_tts_phrase(phrase: String) -> bool:
	var zero_patterns := [
		"^Damage hit 0\\.$",
		"^Barrier blocked 0\\.$",
		"^Armor blocked 0\\.$",
		"^Shield lost 0\\.$",
		"^Health lost 0\\.$",
		"^Health restored 0\\.$",
		"^Shield restored 0\\.$",
		"^Health lost: 0\\.$",
		"^Shield lost: 0\\.$",
		"^Health restored: 0\\.$",
		"^Shield restored: 0\\.$",
		"^Biomass: 0\\.$",
		"^Biomass now 0\\.$",
		"^Corruption: 0\\.$",
		"^Corruption now 0\\.$",
		"^Corruption rises to 0\\.$",
		"^Corruption settles to 0\\.$",
		"^Danger: 0\\.$",
		"^Danger now 0\\.$",
		"^Danger rises to 0\\.$",
		"^Danger settles to 0\\.$",
		"^Claim: 0\\.$",
		"^Claim now 0\\.$",
		"^Marked route streak: 0\\.$",
		"^Marked route streak 0\\.$",
		"^I only have 0\\.$",
		"^It wants 0 biomass\\.$",
		"^The pool knits 0 health back into place\\.$",
		"^The amber hardens over me and restores 0 shield\\.$",
		"^The soft tunnel carries me forward and mends 0 health\\.$",
	]
	for pattern in zero_patterns:
		var zero_pattern := RegEx.new()
		zero_pattern.compile(pattern)
		if zero_pattern.search(phrase) != null:
			return true
	return false


func _normalize_spoken_phrase(text: String) -> String:
	var normalized := " ".join(text.strip_edges().split(" ", false))
	while normalized.ends_with("..") or normalized.ends_with("!!") or normalized.ends_with("??"):
		normalized = normalized.substr(0, normalized.length() - 1)
	if normalized != "" and not [".", "!", "?"].has(normalized.right(1)):
		normalized += "."
	return normalized


func _tts_text_key(text: String) -> String:
	return _normalize_spoken_phrase(text).to_lower().sha256_text()


func _tts_has_generated_phrase(text: String) -> bool:
	return _tts_text_clip_files.has(_tts_text_key(text))


func _resolve_tts_bus_name() -> String:
	for bus_index in range(AudioServer.bus_count):
		var bus_name := AudioServer.get_bus_name(bus_index)
		if bus_name == tts_bus_name:
			return tts_bus_name
	push_warning("TTS bus '%s' was not found. Falling back to Master." % tts_bus_name)
	return "Master"


func _ensure_tts_bus_audible() -> void:
	var bus_name := _resolve_tts_bus_name()
	var bus_index := AudioServer.get_bus_index(bus_name)
	if bus_index < 0:
		return
	AudioServer.set_bus_mute(bus_index, false)
	AudioServer.set_bus_volume_db(bus_index, 0.0)
	_log_tts("Audio bus ready: %s index=%d muted=%s volume=%.1f dB" % [
		bus_name,
		bus_index,
		str(AudioServer.is_bus_mute(bus_index)),
		AudioServer.get_bus_volume_db(bus_index)
	])


func _stop_tts_audio() -> void:
	_tts_sequence_token += 1
	_stop_tts_playback_only()


func _stop_tts_playback_only() -> void:
	_tts_queue.clear()
	if _tts_player != null:
		_tts_player.stop()


func _on_tts_finished() -> void:
	_play_next_tts_clip()


func _log_tts(message: String) -> void:
	if tts_debug_logs:
		print("[TTS] %s" % message)


func _show_encounter_scene(scene_path: String, spawn_animation: String = "") -> void:
	var packed_scene = load(scene_path) as PackedScene
	if packed_scene == null:
		return

	var scene_instance = packed_scene.instantiate()
	if not scene_instance is Node2D:
		scene_instance.queue_free()
		return

	_encounter_scene = scene_instance
	add_child(_encounter_scene)
	_encounter_scene.position = enemy_home.position
	_encounter_scene.z_index = 10
	if spawn_animation != "":
		_play_encounter_animation(spawn_animation)


func _clear_encounter_scene() -> void:
	if _encounter_scene != null:
		_encounter_scene.queue_free()
		_encounter_scene = null


func _play_encounter_animation(animation_name: String) -> void:
	if _encounter_scene == null:
		return

	var animation_player := _encounter_scene.get_node_or_null("AnimationPlayer") as AnimationPlayer
	if animation_player != null and animation_player.has_animation(animation_name):
		animation_player.play(animation_name)


func _get_run_manager() -> Node:
	return get_node_or_null(RUN_MANAGER_PATH)


func _focus_command_input() -> void:
	if dashboard != null and dashboard.has_method("focus_command_input"):
		dashboard.call_deferred("focus_command_input")
