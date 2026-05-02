extends Node2D

const HEART_MANAGER_PATH := "/root/HeartManager"
const RUN_MANAGER_PATH := "/root/RunManager"
const HEART_MANAGER_GROUP := "heart_manager"
const MUTATION_SCENE_PATH := "res://mutation.tscn"
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

@export_range(0.01, 2.0, 0.01) var base_pulse_duration: float = 0.96
@export_range(0.1, 1.0, 0.01) var pulse_occupancy: float = 0.72
@export_range(0.05, 0.5, 0.01) var pulse_release_ratio: float = 0.22
@export_range(0.05, 2.0, 0.01) var room_fade_duration: float = 0.35
@export var current_room_id := "red_corridor"

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


func _ready() -> void:
	_rng.randomize()
	_pulse_material = room_sprite.material as ShaderMaterial
	if _pulse_material == null:
		push_warning("RoomSprite is missing a ShaderMaterial. Room pulse is disabled.")
		return

	_pulse_strength = float(_pulse_material.get_shader_parameter(PULSE_AMOUNT_PARAMETER))
	_reset_pulse_state()
	_connect_dashboard()
	_prepare_actors()
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

	var image_path := str(room_data.get("image", ""))
	if image_path != "":
		var room_texture = load(image_path)
		if room_texture is Texture2D:
			room_sprite.texture = room_texture

	room_sprite.modulate.a = 1.0


func _connect_dashboard() -> void:
	if dashboard != null and dashboard.has_signal("console_option_selected") and not dashboard.is_connected("console_option_selected", Callable(self, "_on_console_option_selected")):
		dashboard.connect("console_option_selected", Callable(self, "_on_console_option_selected"))


func _on_console_option_selected(action_id: String, room_id: String) -> void:
	if _is_room_transitioning or _is_combat_resolving:
		return

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
		_present_encounter(run_manager.get_current_encounter())
		return

	if action_id == "browse_wares":
		if dashboard.has_method("show_console"):
			var shop_offer: Dictionary = run_manager.call("get_merchant_shop_offer") if run_manager.has_method("get_merchant_shop_offer") else {}
			dashboard.call("show_console", shop_offer.get("lines", ["The merchant's hands move, but I cannot read the scale."]), shop_offer.get("buttons", [{"label": "Leave", "action": "leave_merchant"}]), room_id)
		return

	if action_id.begins_with("buy_mutation:"):
		if dashboard.has_method("show_console") and run_manager.has_method("buy_shop_mutation"):
			var mutation_id := action_id.substr("buy_mutation:".length())
			var purchase_result: Dictionary = run_manager.call("buy_shop_mutation", mutation_id)
			dashboard.call("show_console", purchase_result.get("lines", []), purchase_result.get("buttons", [{"label": "Leave", "action": "leave_merchant"}]), room_id)
		return

	if action_id.begins_with("take_symbiote:"):
		run_manager.consume_current_event(action_id)
		var symbiote_result := _get_last_action_result(run_manager)
		if not symbiote_result.is_empty():
			_show_action_result(symbiote_result, room_id)
		return

	if action_id.begins_with("activate_symbiote:"):
		if dashboard.has_method("show_console") and run_manager.has_method("activate_symbiote"):
			var symbiote_id := action_id.substr("activate_symbiote:".length())
			var activation_result: Dictionary = run_manager.call("activate_symbiote", symbiote_id)
			dashboard.call("show_console", activation_result.get("lines", []), activation_result.get("buttons", [{"label": "Proceed.", "action": "proceed"}]), room_id)
		return

	run_manager.consume_current_event(action_id)
	var action_result := _get_last_action_result(run_manager)
	if not action_result.is_empty():
		_show_action_result(action_result, room_id)
		return

	if dashboard.has_method("show_console"):
		dashboard.call("show_console", ["That interaction is not implemented yet.", "I move on."], [{"label": "Proceed.", "action": "proceed"}], room_id)
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

	if dashboard.has_method("show_console"):
		var buttons := [{"label": "Proceed.", "action": "proceed"}]
		if is_game_over_combat:
			buttons = [{"label": "Wake again", "action": "restart_run"}]
		dashboard.call("show_console", lines, buttons, current_room_id)

	_prepare_actors()
	_pending_advance_after_ack = not is_game_over_combat
	_is_combat_resolving = false


func _present_encounter(encounter: Dictionary, faded: bool = false) -> void:
	if encounter.is_empty():
		return

	var room_id := str(encounter.get("room_id", current_room_id))
	var room_data: Dictionary = encounter.get("room_data", {})
	var event_data: Dictionary = encounter.get("event_data", {})
	merchant_actor.visible = _encounter_shows_merchant(encounter, event_data)
	if room_id != "" and not room_data.is_empty():
		change_room(room_id, room_data)

	if faded:
		room_sprite.modulate.a = 0.0

	_clear_encounter_scene()
	var scene_path := str(encounter.get("scene_path", ""))
	if scene_path != "":
		_show_encounter_scene(scene_path, str(event_data.get("spawn_animation", "")))

	var lines: Array = encounter.get("lines", [])
	var buttons: Array = encounter.get("buttons", [{"label": "Proceed.", "action": "proceed"}])
	if dashboard.has_method("show_console"):
		dashboard.call("show_console", lines, buttons, room_id)


func _show_acknowledgement(lines: Array[String]) -> void:
	_pending_advance_after_ack = true
	if dashboard.has_method("show_console"):
		dashboard.call("show_console", lines, [{"label": "Proceed.", "action": "proceed"}], current_room_id)


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
	if dashboard.has_method("show_console"):
		var buttons: Array = action_result.get("buttons", [{"label": "Proceed.", "action": "proceed"}])
		dashboard.call("show_console", lines, buttons, room_id if room_id != "" else current_room_id)


func _get_last_action_result(run_manager: Node) -> Dictionary:
	if run_manager != null and run_manager.has_method("get_last_action_result"):
		return run_manager.call("get_last_action_result")
	return {}


func _encounter_shows_merchant(encounter: Dictionary, event_data: Dictionary) -> bool:
	if str(event_data.get("type", "")) == "merchant":
		return true
	return str(encounter.get("event_id", "")) == "merchant_arrival"


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
