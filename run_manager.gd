extends Node

const ROOMS_PATH := "res://room_dialogue.json"
const EVENTS_PATH := "res://events.json"
const DECKS_PATH := "res://encounter_decks.json"
const ENEMIES_PATH := "res://enemies.json"
const MUTATIONS_PATH := "res://mutations.json"
const SYMBIOTES_PATH := "res://symbiotes.json"
const HEART_MANAGER_PATH := "/root/HeartManager"

signal run_started
signal encounter_changed(encounter: Dictionary)

var rooms_by_id: Dictionary = {}
var room_events_by_room: Dictionary = {}
var special_events: Dictionary = {}
var deck_config: Dictionary = {}
var enemies_by_id: Dictionary = {}
var mutations_by_id: Dictionary = {}
var symbiotes_by_id: Dictionary = {}

var current_encounter: Dictionary = {}
var current_room_id := ""
var active_deck_room_ids: Array[String] = []
var base_deck_room_ids: Array[String] = []
var consumed_room_events: Dictionary = {}
var permanently_consumed_events: Dictionary = {}
var rooms_cleared := 0
var biomass := 0
var corruption := 0
var danger := 0
var owned_mutations: Array[String] = []
var owned_symbiotes: Array[String] = []
var player_state: Dictionary = {}

var _merchant_triggered_at_rooms: Dictionary = {}
var _symbiote_triggered_at_rooms: Dictionary = {}
var _corruption_spike_triggers := 0
var _danger_notice_triggers := 0
var _pending_room_id_after_transition := ""
var _pending_encounter_after_overlay: Dictionary = {}
var _last_action_result: Dictionary = {}
var _rng := RandomNumberGenerator.new()


func _ready() -> void:
	_rng.randomize()
	_load_all_data()


func start_new_run() -> void:
	_load_all_data()
	rooms_cleared = 0
	biomass = 0
	corruption = 0
	danger = 0
	owned_mutations.clear()
	owned_symbiotes.clear()
	consumed_room_events.clear()
	permanently_consumed_events.clear()
	_merchant_triggered_at_rooms.clear()
	_symbiote_triggered_at_rooms.clear()
	_corruption_spike_triggers = 0
	_danger_notice_triggers = 0
	_pending_room_id_after_transition = ""
	_pending_encounter_after_overlay.clear()
	_last_action_result.clear()
	player_state = _build_base_player_state()
	base_deck_room_ids = _build_base_deck_room_ids()
	_reset_active_deck()
	current_room_id = str(deck_config.get("opening_room_id", "red_corridor"))
	current_encounter = _build_opening_encounter(current_room_id)
	_sync_heart_rate()
	run_started.emit()
	encounter_changed.emit(get_current_encounter())


func get_current_encounter() -> Dictionary:
	return current_encounter.duplicate(true)


func get_last_action_result() -> Dictionary:
	return _last_action_result.duplicate(true)


func get_room_data(room_id: String) -> Dictionary:
	return rooms_by_id.get(room_id, {}).duplicate(true)


func get_player_combat_stats(fallback_stats: Dictionary = {}) -> Dictionary:
	var stats := fallback_stats.duplicate(true)
	for key in player_state.keys():
		stats[key] = player_state[key]

	var danger_multiplier := 1.0 + float(danger) * 0.5
	stats["damage"] = int(round(float(stats.get("damage", 0)) * danger_multiplier))
	return stats


func consume_current_event(action_id: String = "") -> void:
	if current_encounter.is_empty() or bool(current_encounter.get("consumed", false)):
		return

	var room_id := str(current_encounter.get("room_id", ""))
	var event_id := str(current_encounter.get("event_id", ""))
	var event_data: Dictionary = current_encounter.get("event_data", {})

	if room_id != "" and event_id != "":
		if not consumed_room_events.has(room_id):
			consumed_room_events[room_id] = {}
		consumed_room_events[room_id][event_id] = true

		if not bool(event_data.get("reactivate_on_reshuffle", true)):
			permanently_consumed_events[event_id] = true

	_last_action_result = _apply_action_effects(action_id, event_data)
	current_encounter["consumed"] = true


func advance_to_next_encounter() -> Dictionary:
	if not current_encounter.is_empty() and bool(current_encounter.get("counts_as_room", false)):
		rooms_cleared += 1

	var next_encounter := _build_next_encounter()
	current_encounter = next_encounter
	current_room_id = str(next_encounter.get("room_id", current_room_id))
	encounter_changed.emit(get_current_encounter())
	return get_current_encounter()


func apply_combat_result(combat_result: Dictionary, enemy_data: Dictionary) -> void:
	player_state["health"] = int(max(int(combat_result.get("player_remaining_health", player_state.get("health", 0))), 0))
	player_state["shield"] = int(max(int(combat_result.get("player_remaining_shield", player_state.get("shield", 0))), 0))
	if bool(combat_result.get("player_won", false)):
		biomass += int(enemy_data.get("biomass_reward", 0))


func get_danger_bpm() -> float:
	return float(deck_config.get("base_bpm", 20.0)) + float(danger) * float(deck_config.get("danger_bpm_step", 5.0))


func _load_all_data() -> void:
	rooms_by_id = _index_rooms(_load_json(ROOMS_PATH))
	var events_payload: Dictionary = _load_json(EVENTS_PATH)
	room_events_by_room = _index_room_events(events_payload.get("room_events", {}))
	special_events = _index_special_events(events_payload.get("special_events", {}))
	deck_config = _load_json(DECKS_PATH)
	enemies_by_id = _index_simple_map(_load_json(ENEMIES_PATH).get("enemies", []))
	mutations_by_id = _index_simple_map(_load_json(MUTATIONS_PATH).get("mutations", []))
	symbiotes_by_id = _index_simple_map(_load_json(SYMBIOTES_PATH).get("symbiotes", []))


func _build_base_player_state() -> Dictionary:
	var stats: Dictionary = deck_config.get("base_player_stats", {}).duplicate(true)
	if stats.is_empty():
		stats = {
			"damage": 8,
			"armor": 2,
			"shield": 6,
			"health": 30,
			"ambush_chance": 0.15,
			"initiative": 0.6
		}
	return stats


func _build_base_deck_room_ids() -> Array[String]:
	var chosen_rooms: Array[String] = []
	for starter_room in deck_config.get("starter_rooms", []):
		var room_id := str(starter_room)
		if room_id != "" and not chosen_rooms.has(room_id):
			chosen_rooms.append(room_id)

	for rule_variant in deck_config.get("draw_rules", []):
		if not rule_variant is Dictionary:
			continue

		var rule: Dictionary = rule_variant
		var pool_name := str(rule.get("pool", ""))
		var count := int(rule.get("count", 0))
		var pool_variant = deck_config.get("room_pools", {}).get(pool_name, [])
		if not pool_variant is Array:
			continue

		var pool_ids: Array[String] = []
		for value in pool_variant:
			pool_ids.append(str(value))

		for _index in count:
			var room_choice := _draw_room_from_pool(pool_ids, chosen_rooms)
			if room_choice != "":
				chosen_rooms.append(room_choice)

	_ensure_room_type_in_deck(chosen_rooms, "combat")
	return chosen_rooms


func _ensure_room_type_in_deck(chosen_rooms: Array[String], event_type: String) -> void:
	for room_id in chosen_rooms:
		if _room_has_event_type(room_id, event_type):
			return

	var eligible_rooms := _get_rooms_with_event_type(event_type)
	if eligible_rooms.is_empty():
		return

	var replacement_room := eligible_rooms[_rng.randi_range(0, eligible_rooms.size() - 1)]
	if chosen_rooms.has(replacement_room):
		return

	for index in range(chosen_rooms.size() - 1, -1, -1):
		var room_id := chosen_rooms[index]
		if room_id == str(deck_config.get("opening_room_id", "")):
			continue
		if not _room_has_event_type(room_id, event_type):
			chosen_rooms[index] = replacement_room
			return

	chosen_rooms.append(replacement_room)


func _get_rooms_with_event_type(event_type: String) -> Array[String]:
	var room_ids: Array[String] = []
	for room_id_variant in room_events_by_room.keys():
		var room_id := str(room_id_variant)
		if room_id != "" and _room_has_event_type(room_id, event_type):
			room_ids.append(room_id)
	return room_ids


func _room_has_event_type(room_id: String, event_type: String) -> bool:
	var room_events: Array = room_events_by_room.get(room_id, [])
	for event_variant in room_events:
		if not event_variant is Dictionary:
			continue
		if str(event_variant.get("type", "")) == event_type:
			return true
	return false


func _reset_active_deck() -> void:
	active_deck_room_ids = base_deck_room_ids.duplicate(true)
	consumed_room_events.clear()


func _build_opening_encounter(room_id: String) -> Dictionary:
	var opening_event_id := str(deck_config.get("opening_event_id", ""))
	var room_events: Array = room_events_by_room.get(room_id, [])
	for event_variant in room_events:
		if event_variant is Dictionary and str(event_variant.get("id", "")) == opening_event_id:
			return _build_room_encounter(room_id, event_variant)

	return _build_next_encounter()


func _build_next_encounter() -> Dictionary:
	if not _pending_encounter_after_overlay.is_empty():
		var pending_encounter := _pending_encounter_after_overlay.duplicate(true)
		_pending_encounter_after_overlay.clear()
		return pending_encounter

	if _pending_room_id_after_transition != "":
		return _build_pending_room_encounter()

	if _should_offer_corruption_spike_room():
		_corruption_spike_triggers += 1
		return _build_corruption_spike_encounter()

	if _should_offer_danger_notice():
		_danger_notice_triggers += 1
		return _build_special_encounter("danger_spike_notice")

	if _should_offer_symbiote_host():
		var symbiote_rooms_key := rooms_cleared
		_symbiote_triggered_at_rooms[symbiote_rooms_key] = true
		return _build_symbiote_encounter()

	if _should_offer_merchant():
		var room_encounter := _draw_room_encounter()
		if str(room_encounter.get("kind", "")) == "room_event":
			var merchant_rooms_key := rooms_cleared
			_merchant_triggered_at_rooms[merchant_rooms_key] = true
			_pending_encounter_after_overlay = room_encounter.duplicate(true)
			return _build_special_encounter(
				"merchant_arrival",
				str(room_encounter.get("room_id", current_room_id)),
				room_encounter.get("room_data", {})
			)
		return room_encounter

	return _draw_room_encounter()


func _should_offer_merchant() -> bool:
	var merchant_every := int(deck_config.get("merchant_every", 5))
	if merchant_every <= 0 or rooms_cleared <= 0:
		return false
	if rooms_cleared % merchant_every != 0:
		return false
	return not _merchant_triggered_at_rooms.has(rooms_cleared)


func _should_offer_danger_notice() -> bool:
	var threshold := int(deck_config.get("danger_notice_threshold", 2))
	if threshold <= 0:
		return false
	if not special_events.has("danger_spike_notice"):
		return false
	return danger >= threshold * (_danger_notice_triggers + 1)


func _should_offer_corruption_spike_room() -> bool:
	var threshold := int(deck_config.get("corruption_spike_threshold", 3))
	if threshold <= 0:
		return false
	if not special_events.has("corruption_spike_room"):
		return false
	return corruption >= threshold * (_corruption_spike_triggers + 1)


func _should_offer_symbiote_host() -> bool:
	var symbiote_every := int(deck_config.get("symbiote_every", 3))
	if symbiote_every <= 0 or rooms_cleared <= 0:
		return false
	if rooms_cleared % symbiote_every != 0:
		return false
	if _symbiote_triggered_at_rooms.has(rooms_cleared):
		return false
	if not special_events.has("symbiote_host_offer"):
		return false
	return not _get_available_symbiote_ids().is_empty()


func _build_symbiote_encounter() -> Dictionary:
	var available_symbiote_ids := _get_available_symbiote_ids()
	if available_symbiote_ids.is_empty():
		return _draw_room_encounter()

	var symbiote_id := available_symbiote_ids[_rng.randi_range(0, available_symbiote_ids.size() - 1)]
	var symbiote_data: Dictionary = symbiotes_by_id.get(symbiote_id, {}).duplicate(true)
	var event_data: Dictionary = special_events.get("symbiote_host_offer", {}).duplicate(true)
	if event_data.is_empty():
		return _draw_room_encounter()

	event_data["symbiote_id"] = symbiote_id
	event_data["symbiote_name"] = str(symbiote_data.get("name", symbiote_id))
	event_data["line_1"] = "A %s is fused into the room's flesh." % event_data["symbiote_name"]
	event_data["line_2"] = "Do I let it bond with me?"

	return {
		"kind": "special_event",
		"room_id": current_room_id,
		"room_data": get_room_data(current_room_id),
		"event_id": str(event_data.get("id", "symbiote_host_offer")),
		"event_data": event_data,
		"scene_path": str(event_data.get("scene_path", "")),
		"lines": _build_lines({}, event_data),
		"buttons": _build_buttons(event_data),
		"enemy_data": _resolve_enemy_data(event_data),
		"counts_as_room": false,
		"consumed": false
	}


func _build_corruption_spike_encounter() -> Dictionary:
	var room_id := "spiked_red_corridor"
	var event_data: Dictionary = special_events.get("corruption_spike_room", {}).duplicate(true)
	if event_data.is_empty():
		return _draw_room_encounter()

	return {
		"kind": "special_event",
		"room_id": room_id,
		"room_data": get_room_data(room_id),
		"event_id": str(event_data.get("id", "corruption_spike_room")),
		"event_data": event_data,
		"scene_path": str(event_data.get("scene_path", "")),
		"lines": _build_lines(get_room_data(room_id), event_data),
		"buttons": _build_buttons(event_data),
		"enemy_data": _resolve_enemy_data(event_data),
		"counts_as_room": true,
		"consumed": false
	}


func _draw_room_encounter() -> Dictionary:
	var fail_safe := 0
	while fail_safe < 128:
		fail_safe += 1
		if active_deck_room_ids.is_empty():
			if rooms_cleared > 0 and special_events.has("floor_transition"):
				_reset_active_deck()
				var preview_room_id := _pick_preview_room_id()
				if preview_room_id != "":
					_pending_room_id_after_transition = preview_room_id
					return _build_special_encounter("floor_transition", preview_room_id, get_room_data(preview_room_id))
				return _build_special_encounter("floor_transition")
			_reset_active_deck()

		if active_deck_room_ids.is_empty():
			return {}

		var room_id := active_deck_room_ids[_rng.randi_range(0, active_deck_room_ids.size() - 1)]
		var eligible_events := _get_eligible_events_for_room(room_id)
		if eligible_events.is_empty():
			active_deck_room_ids.erase(room_id)
			continue

		var event_data: Dictionary = eligible_events[_rng.randi_range(0, eligible_events.size() - 1)]
		return _build_room_encounter(room_id, event_data)

	return {}


func _build_pending_room_encounter() -> Dictionary:
	var room_id := _pending_room_id_after_transition
	_pending_room_id_after_transition = ""
	if room_id == "":
		return _draw_room_encounter()

	var eligible_events := _get_eligible_events_for_room(room_id)
	if eligible_events.is_empty():
		active_deck_room_ids.erase(room_id)
		return _draw_room_encounter()

	var event_data: Dictionary = eligible_events[_rng.randi_range(0, eligible_events.size() - 1)]
	return _build_room_encounter(room_id, event_data)


func _pick_preview_room_id() -> String:
	var candidate_room_ids: Array[String] = []
	for room_id in active_deck_room_ids:
		if not _get_eligible_events_for_room(room_id).is_empty():
			candidate_room_ids.append(room_id)

	if candidate_room_ids.is_empty():
		return ""

	return candidate_room_ids[_rng.randi_range(0, candidate_room_ids.size() - 1)]


func _get_eligible_events_for_room(room_id: String) -> Array[Dictionary]:
	var eligible_events: Array[Dictionary] = []
	var room_events: Array = room_events_by_room.get(room_id, [])
	var consumed_for_room: Dictionary = consumed_room_events.get(room_id, {})

	for event_variant in room_events:
		if not event_variant is Dictionary:
			continue

		var event_data: Dictionary = event_variant
		var event_id := str(event_data.get("id", ""))
		if event_id == "":
			continue

		if consumed_for_room.has(event_id):
			continue

		if permanently_consumed_events.has(event_id):
			continue

		eligible_events.append(event_data)

	return eligible_events


func _build_room_encounter(room_id: String, event_data: Dictionary) -> Dictionary:
	var room_data := get_room_data(room_id)
	return {
		"kind": "room_event",
		"room_id": room_id,
		"room_data": room_data,
		"event_id": str(event_data.get("id", "")),
		"event_data": event_data.duplicate(true),
		"scene_path": str(event_data.get("scene_path", "")),
		"lines": _build_lines(room_data, event_data),
		"buttons": _build_buttons(event_data),
		"enemy_data": _resolve_enemy_data(event_data),
		"counts_as_room": true,
		"consumed": false
	}


func _build_special_encounter(event_id: String, room_id_override: String = "", room_data_override: Dictionary = {}) -> Dictionary:
	var event_data: Dictionary = special_events.get(event_id, {}).duplicate(true)
	var room_id := room_id_override if room_id_override != "" else current_room_id
	var room_data := room_data_override if not room_data_override.is_empty() else get_room_data(room_id)
	return {
		"kind": "special_event",
		"room_id": room_id,
		"room_data": room_data,
		"event_id": event_id,
		"event_data": event_data,
		"scene_path": str(event_data.get("scene_path", "")),
		"lines": _build_lines({}, event_data),
		"buttons": _build_buttons(event_data),
		"enemy_data": _resolve_enemy_data(event_data),
		"counts_as_room": false,
		"consumed": false
	}


func _build_lines(room_data: Dictionary, event_data: Dictionary) -> Array[String]:
	var lines: Array[String] = []
	var speaker := str(event_data.get("speaker", room_data.get("ui_text", {}).get("speaker", "")))
	var line_1 := str(event_data.get("line_1", room_data.get("ui_text", {}).get("line_1", "")))
	var line_2 := str(event_data.get("line_2", room_data.get("ui_text", {}).get("line_2", "")))

	if speaker != "":
		lines.append("%s:" % speaker)
	if line_1 != "":
		lines.append(line_1)
	if line_2 != "":
		lines.append(line_2)

	return lines


func _build_buttons(event_data: Dictionary) -> Array:
	var buttons_variant = event_data.get("buttons", [])
	if buttons_variant is Array and not buttons_variant.is_empty():
		return buttons_variant.duplicate(true)
	return [{"label": "Proceed.", "action": "proceed"}]


func _resolve_enemy_data(event_data: Dictionary) -> Dictionary:
	var enemy_id := str(event_data.get("enemy_id", ""))
	if enemy_id == "":
		return {}
	return enemies_by_id.get(enemy_id, {}).duplicate(true)


func _apply_action_effects(action_id: String, event_data: Dictionary) -> Dictionary:
	match action_id:
		"take_mutation":
			var mutation_id := str(event_data.get("mutation_id", ""))
			if mutation_id != "" and not owned_mutations.has(mutation_id):
				owned_mutations.append(mutation_id)
			_add_corruption(1)
			return {
				"play_animation": "open",
				"lines": [
					"Her:",
					"The egg splits and the mutation takes hold.",
					"Corruption rises to %d." % corruption
				]
			}
		"take_symbiote":
			var symbiote_id := str(event_data.get("symbiote_id", ""))
			if symbiote_id != "" and not owned_symbiotes.has(symbiote_id):
				owned_symbiotes.append(symbiote_id)
			_add_corruption(1)
			var symbiote_name := str(event_data.get("symbiote_name", "symbiote"))
			return {
				"lines": [
					"Her:",
					"The %s latches on and sinks into her flesh." % symbiote_name,
					"Corruption rises to %d." % corruption
				]
			}
		"leave_symbiote":
			return {
				"lines": [
					"Her:",
					"I left the %s writhing in the wall." % str(event_data.get("symbiote_name", "symbiote")),
					"I should keep moving."
				]
			}
		"leave_mutation":
			return {
				"lines": [
					"Her:",
					"I left the mutation where it twitched.",
					"I should keep moving."
				]
			}
		"drink_pool":
			var restored_health := _restore_player_health(int(event_data.get("heal", 8)))
			_add_corruption(1)
			return {
				"lines": [
					"Her:",
					"The pool knits %d health back into place." % restored_health,
					"Something of it lingers. Corruption rises to %d." % corruption
				]
			}
		"study_pool":
			var reduced_corruption := _add_corruption(-1)
			return {
				"lines": [
					"Her:",
					"I study the current instead of stepping into it.",
					"Corruption settles to %d." % reduced_corruption
				]
			}
		"retreat":
			return {
				"lines": [
					"Her:",
					"I back away from the pool before it can learn my shape.",
					"Better to keep moving."
				]
			}
		"harvest_eggs":
			_add_biomass(int(event_data.get("biomass", 5)))
			_add_corruption(1)
			return {
				"lines": [
					"Her:",
					"I split the sacs and strip out fresh biomass.",
					"Biomass: %d. Corruption: %d." % [biomass, corruption]
				]
			}
		"cauterize_eggs":
			return _build_damage_result(int(event_data.get("damage", 6)), [
				"Her:",
				"I burn a lane through the nest and the sacs burst against me."
			], "I make it through, singed but breathing.")
		"slip_between_eggs":
			return {
				"lines": [
					"Her:",
					"I thread between the sacs and leave them unbroken.",
					"Nothing gained. Nothing owed."
				]
			}
		"siphon_amber":
			var amber_damage := _apply_player_damage(int(event_data.get("damage", 2)))
			_add_biomass(int(event_data.get("biomass", 7)))
			return {
				"lines": [
					"Her:",
					"I carve amber clot from the wall and pocket the mass.",
					_build_damage_summary(int(event_data.get("damage", 2)), amber_damage),
					"Biomass: %d." % biomass
				]
			}
		"seal_amber_wound":
			var restored_shield := _restore_player_shield(int(event_data.get("shield", 5)))
			_add_corruption(1)
			return {
				"lines": [
					"Her:",
					"The amber hardens over me and restores %d shield." % restored_shield,
					"Corruption rises to %d." % corruption
				]
			}
		"leave_amber":
			return {
				"lines": [
					"Her:",
					"I leave the amber sealed in the wall.",
					"It watches me go."
				]
			}
		"take_green_tunnel":
			var green_heal := _restore_player_health(int(event_data.get("heal", 4)))
			_add_corruption(1)
			return {
				"lines": [
					"Her:",
					"The soft tunnel carries me forward and mends %d health." % green_heal,
					"It leaves residue behind. Corruption: %d." % corruption
				]
			}
		"cut_green_spine":
			var green_damage := _apply_player_damage(int(event_data.get("damage", 4)))
			_add_biomass(int(event_data.get("biomass", 5)))
			return {
				"lines": [
					"Her:",
					"I cut through the rigid spine and tear biomass free.",
					_build_damage_summary(int(event_data.get("damage", 4)), green_damage),
					"Biomass: %d." % biomass
				]
			}
		"listen_at_green_split":
			_add_danger(-1)
			return {
				"lines": [
					"Her:",
					"I wait, listen, and pick the calmer pulse.",
					"Danger settles to %d." % danger
				]
			}
		"open_red_artery":
			_add_biomass(int(event_data.get("biomass", 6)))
			_add_corruption(1)
			return {
				"lines": [
					"Her:",
					"I open the swollen artery and collect what spills out.",
					"Biomass: %d. Corruption: %d." % [biomass, corruption]
				]
			}
		"brace_through_red_split":
			return _build_damage_result(int(event_data.get("damage", 4)), [
				"Her:",
				"I force the dry lane open with my body."
			], "The junction yields, but it costs me flesh.")
		"mark_red_branch":
			_add_danger(-1)
			return {
				"lines": [
					"Her:",
					"I trace the pulse pattern and choose the safer branch.",
					"Danger settles to %d." % danger
				]
			}
		"push_through_spikes":
			return _build_damage_result(int(event_data.get("damage", 8)), [
				"Her:",
				"The corridor closes until I force myself through the spikes."
			], "The passage opens only after it has taken its cut.")
		"leave_merchant":
			_add_danger(1)
			return {
				"lines": [
					"Her:",
					"I leave the merchant to its clicking teeth.",
					"Danger rises to %d." % danger
				]
			}
		"run":
			_add_danger(1)
			return {
				"lines": [
					"Her:",
					"I run for the next chamber without looking back.",
					"Danger rises to %d." % danger
				]
			}
		_:
			return {}

	return {}


func _get_available_symbiote_ids() -> Array[String]:
	var available_ids: Array[String] = []
	for symbiote_id_variant in symbiotes_by_id.keys():
		var symbiote_id := str(symbiote_id_variant)
		if symbiote_id != "" and not owned_symbiotes.has(symbiote_id):
			available_ids.append(symbiote_id)
	return available_ids


func _add_biomass(amount: int) -> int:
	biomass = int(max(biomass + amount, 0))
	return biomass


func _add_corruption(amount: int) -> int:
	corruption = int(max(corruption + amount, 0))
	return corruption


func _apply_player_damage(raw_damage: int) -> Dictionary:
	var armor_value := int(player_state.get("armor", 0))
	var non_negative_damage: int = int(max(raw_damage, 0))
	var mitigated_by_armor: int = int(min(armor_value, non_negative_damage))
	var post_armor_damage: int = int(max(raw_damage - mitigated_by_armor, 0))
	var current_shield := int(player_state.get("shield", 0))
	var shield_lost: int = int(min(current_shield, post_armor_damage))
	player_state["shield"] = current_shield - shield_lost
	var remaining_damage: int = int(max(post_armor_damage - shield_lost, 0))
	var current_health := int(player_state.get("health", 0))
	var health_lost: int = int(min(current_health, remaining_damage))
	player_state["health"] = current_health - health_lost
	return {
		"mitigated_by_armor": mitigated_by_armor,
		"shield_lost": shield_lost,
		"health_lost": health_lost,
		"remaining_shield": int(player_state.get("shield", 0)),
		"remaining_health": int(player_state.get("health", 0))
	}


func _restore_player_health(amount: int) -> int:
	var current_health := int(player_state.get("health", 0))
	var max_health := int(deck_config.get("base_player_stats", {}).get("health", current_health))
	var missing_health: int = int(max(max_health - current_health, 0))
	var restored: int = int(clamp(amount, 0, missing_health))
	player_state["health"] = current_health + restored
	return restored


func _restore_player_shield(amount: int) -> int:
	var current_shield := int(player_state.get("shield", 0))
	var max_shield := int(deck_config.get("base_player_stats", {}).get("shield", current_shield))
	var missing_shield: int = int(max(max_shield - current_shield, 0))
	var restored: int = int(clamp(amount, 0, missing_shield))
	player_state["shield"] = current_shield + restored
	return restored


func _build_damage_result(raw_damage: int, intro_lines: Array[String], closing_line: String) -> Dictionary:
	var damage_result := _apply_player_damage(raw_damage)
	var lines := intro_lines.duplicate()
	lines.append(_build_damage_summary(raw_damage, damage_result))
	lines.append(closing_line)
	return {"lines": lines}


func _build_damage_summary(raw_damage: int, damage_result: Dictionary) -> String:
	return "%d damage hit. Armor blocked %d, shield lost %d, health lost %d." % [
		raw_damage,
		int(damage_result.get("mitigated_by_armor", 0)),
		int(damage_result.get("shield_lost", 0)),
		int(damage_result.get("health_lost", 0))
	]


func _add_danger(amount: int) -> void:
	danger = int(max(danger + amount, 0))
	_sync_heart_rate()


func _sync_heart_rate() -> void:
	var heart_manager := get_node_or_null(HEART_MANAGER_PATH)
	if heart_manager != null:
		heart_manager.set("bpm", get_danger_bpm())


func _index_rooms(payload: Dictionary) -> Dictionary:
	var indexed: Dictionary = {}
	var rooms_variant = payload.get("rooms", [])
	if not rooms_variant is Array:
		return indexed

	for room_variant in rooms_variant:
		if not room_variant is Dictionary:
			continue
		var room_data: Dictionary = room_variant
		var room_id := str(room_data.get("id", ""))
		if room_id != "":
			indexed[room_id] = room_data.duplicate(true)

	return indexed


func _index_room_events(payload: Variant) -> Dictionary:
	var indexed: Dictionary = {}
	if not payload is Dictionary:
		return indexed

	for room_id in payload.keys():
		var events_variant = payload[room_id]
		if not events_variant is Array:
			continue
		indexed[str(room_id)] = events_variant.duplicate(true)

	return indexed


func _index_special_events(payload: Variant) -> Dictionary:
	var indexed: Dictionary = {}
	if not payload is Dictionary:
		return indexed

	for event_id in payload.keys():
		var event_variant = payload[event_id]
		if event_variant is Dictionary:
			indexed[str(event_id)] = event_variant.duplicate(true)

	return indexed


func _index_simple_map(payload: Variant) -> Dictionary:
	var indexed: Dictionary = {}
	if not payload is Array:
		return indexed

	for item_variant in payload:
		if not item_variant is Dictionary:
			continue
		var item_data: Dictionary = item_variant
		var item_id := str(item_data.get("id", ""))
		if item_id != "":
			indexed[item_id] = item_data.duplicate(true)

	return indexed


func _draw_room_from_pool(pool_ids: Array[String], already_chosen: Array[String]) -> String:
	var available: Array[String] = []
	for room_id in pool_ids:
		if not already_chosen.has(room_id):
			available.append(room_id)

	if available.is_empty():
		available = pool_ids.duplicate(true)

	if available.is_empty():
		return ""

	return available[_rng.randi_range(0, available.size() - 1)]


func _load_json(path: String) -> Dictionary:
	if not FileAccess.file_exists(path):
		return {}

	var raw_json := FileAccess.get_file_as_string(path)
	var parsed = JSON.parse_string(raw_json)
	if parsed is Dictionary:
		return parsed

	return {}
