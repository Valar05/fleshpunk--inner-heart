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
var active_deck_cards: Array[Dictionary] = []
var active_deck_room_ids: Array[String] = []
var base_deck_room_ids: Array[String] = []
var consumed_room_events: Dictionary = {}
var permanently_consumed_events: Dictionary = {}
var rooms_cleared := 0
var biomass := 0
var corruption := 0
var danger := 0
var merchant_refusals := 0
var merchant_claim := 0
var baffle_mutes := 0
var marked_route_streak := 0
var pressure_counts: Dictionary = {}
var ending_pressure := ""
var owned_mutations: Array[String] = []
var owned_symbiotes: Array[String] = []
var symbiote_health: Dictionary = {}
var symbiote_cooldowns: Dictionary = {}
var active_symbiotes: Dictionary = {}
var player_state: Dictionary = {}

var _merchant_triggered_at_rooms: Dictionary = {}
var _symbiote_triggered_at_rooms: Dictionary = {}
var _merchant_reckoning_triggered := false
var _corruption_spike_triggers := 0
var _danger_notice_triggers := 0
var _director_triggered_warnings: Dictionary = {}
var _pending_director_events: Array[String] = []
var _ending_locks: Dictionary = {}
var _hunter_reckoning_triggered := false
var _corruption_claim_triggered := false
var _pending_room_id_after_transition := ""
var _pending_encounter_after_overlay: Dictionary = {}
var _last_action_result: Dictionary = {}
var _merchant_purchase_made := false
var _merchant_due_before_redraw := false
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
	merchant_refusals = 0
	merchant_claim = 0
	baffle_mutes = 0
	marked_route_streak = 0
	pressure_counts.clear()
	ending_pressure = ""
	owned_mutations.clear()
	owned_symbiotes.clear()
	symbiote_health.clear()
	symbiote_cooldowns.clear()
	active_symbiotes.clear()
	active_deck_cards.clear()
	consumed_room_events.clear()
	permanently_consumed_events.clear()
	_merchant_triggered_at_rooms.clear()
	_symbiote_triggered_at_rooms.clear()
	_merchant_reckoning_triggered = false
	_corruption_spike_triggers = 0
	_danger_notice_triggers = 0
	_director_triggered_warnings.clear()
	_pending_director_events.clear()
	_ending_locks.clear()
	_hunter_reckoning_triggered = false
	_corruption_claim_triggered = false
	_pending_room_id_after_transition = ""
	_pending_encounter_after_overlay.clear()
	_last_action_result.clear()
	_merchant_purchase_made = false
	_merchant_due_before_redraw = false
	player_state = _build_base_player_state()
	base_deck_room_ids = _build_base_deck_room_ids()
	_reset_active_deck()
	current_room_id = str(deck_config.get("opening_room_id", "red_corridor"))
	current_encounter = _build_opening_encounter(current_room_id)
	var opening_event_data: Dictionary = current_encounter.get("event_data", {})
	if str(opening_event_data.get("type", "")) == "symbiote":
		_remove_symbiote_cards_from_active_deck()
	_sync_heart_rate()
	run_started.emit()
	encounter_changed.emit(get_current_encounter())


func get_current_encounter() -> Dictionary:
	return current_encounter.duplicate(true)


func get_last_action_result() -> Dictionary:
	return _last_action_result.duplicate(true)


func get_director_state() -> Dictionary:
	return {
		"pressure_counts": pressure_counts.duplicate(true),
		"ending_pressure": ending_pressure,
		"ending_locks": _ending_locks.duplicate(true),
		"balanced_eligible": _is_balanced_eligible(),
		"merchant_claim": merchant_claim,
		"baffle_mutes": baffle_mutes,
		"marked_route_streak": marked_route_streak
	}


func get_room_data(room_id: String) -> Dictionary:
	return rooms_by_id.get(room_id, {}).duplicate(true)


func get_player_combat_stats(fallback_stats: Dictionary = {}) -> Dictionary:
	var stats := fallback_stats.duplicate(true)
	for key in player_state.keys():
		stats[key] = player_state[key]

	var danger_multiplier := 1.0 + float(danger) * 0.5
	stats["damage"] = int(round(float(stats.get("damage", 0)) * danger_multiplier))
	_apply_owned_mutation_combat_effects(stats)
	return stats


func prepare_enemy_combat_stats(enemy_stats: Dictionary) -> Dictionary:
	var stats := enemy_stats.duplicate(true)
	if active_symbiotes.has("pheromones"):
		var symbiote_data: Dictionary = symbiotes_by_id.get("pheromones", {})
		var initiative_delta := float(symbiote_data.get("enemy_initiative_delta", -1.0))
		stats["initiative"] = clamp(float(stats.get("initiative", 0.5)) + initiative_delta, 0.0, 1.0)
		stats["speed"] = max(float(stats.get("speed", 1.0)) + initiative_delta, 0.01)
		active_symbiotes.erase("pheromones")
		_start_symbiote_cooldown("pheromones", 3)
	return stats


func activate_symbiote(symbiote_id: String) -> Dictionary:
	if symbiote_id == "" or not owned_symbiotes.has(symbiote_id) or not symbiotes_by_id.has(symbiote_id):
		return _build_symbiote_activation_result([
			"Nothing under my skin answers that shape.",
			"I keep moving."
		])
	if int(symbiote_health.get(symbiote_id, 0)) <= 0:
		return _build_symbiote_activation_result([
			"The symbiote is dead tissue now.",
			"I get no use from it."
		])
	if active_symbiotes.has(symbiote_id):
		return _build_symbiote_activation_result([
			"It's already awake.",
			"I feel it waiting under the skin."
		])

	var symbiote_data: Dictionary = symbiotes_by_id.get(symbiote_id, {})
	var symbiote_name := str(symbiote_data.get("name", symbiote_id))
	match symbiote_id:
		"impermeable_barrier":
			var armor_pool := int(symbiote_data.get("armor", 8))
			active_symbiotes[symbiote_id] = {"armor": armor_pool}
			return _with_director_lines(_build_symbiote_activation_result([
				"%s plates over me. %d armor waiting for the next hit." % [symbiote_name, armor_pool],
				"If the full layer breaks, it gets hurt."
			]), _record_action_pattern("activate_symbiote", {}))
		"pheromones":
			active_symbiotes[symbiote_id] = true
			return _with_director_lines(_build_symbiote_activation_result([
				"%s bleeds scent into the air." % symbiote_name,
				"It lasts this room. Then it needs two rooms quiet."
			]), _record_action_pattern("activate_symbiote", {}))
		"mitosis_unit":
			active_symbiotes[symbiote_id] = true
			return _with_director_lines(_build_symbiote_activation_result([
				"%s wakes and starts counting my organs." % symbiote_name,
				"If I die before it sleeps, it dies instead."
			]), _record_action_pattern("activate_symbiote", {}))

	return _with_director_lines(_build_symbiote_activation_result([
		"%s twitches, but I don't know how to use it yet." % symbiote_name,
		"I leave it dormant."
	]), _record_action_pattern("activate_symbiote", {}))


func get_merchant_shop_offer() -> Dictionary:
	var lines: Array[String] = [
		"The merchant sets out eggs like weights on a scale.",
		"Biomass: %d. One placed mass buys one change. Withdrawal leaves him counting." % biomass
	]
	var buttons: Array[Dictionary] = []
	for mutation_id_variant in mutations_by_id.keys():
		var mutation_id := str(mutation_id_variant)
		if owned_mutations.has(mutation_id):
			continue
		var mutation_data: Dictionary = mutations_by_id.get(mutation_id, {})
		var mutation_name := str(mutation_data.get("name", mutation_id))
		var mutation_cost := _get_mutation_cost(mutation_data)
		buttons.append({
			"label": "%s - %d biomass" % [mutation_name, mutation_cost],
			"action": "buy_mutation:%s" % mutation_id
		})

	if buttons.is_empty():
		lines.append("Nothing here wants me twice.")
	buttons.append({"label": "Withdraw", "action": "leave_merchant"})
	return {
		"lines": lines,
		"buttons": buttons
	}


func buy_shop_mutation(mutation_id: String) -> Dictionary:
	if mutation_id == "" or not mutations_by_id.has(mutation_id):
		return {
			"lines": [
				"The scale has no place for that shape.",
				"I keep my biomass close."
			],
			"buttons": [{"label": "Back to scales", "action": "browse_wares"}, {"label": "Withdraw", "action": "leave_merchant"}]
		}

	var mutation_data: Dictionary = mutations_by_id.get(mutation_id, {})
	var mutation_name := str(mutation_data.get("name", mutation_id))
	if owned_mutations.has(mutation_id):
		return {
			"lines": [
				"%s is already written into me." % mutation_name,
				"The merchant's scale stays still."
			],
			"buttons": [{"label": "Back to scales", "action": "browse_wares"}, {"label": "Withdraw", "action": "leave_merchant"}]
		}

	var mutation_cost := _get_mutation_cost(mutation_data)
	if biomass < mutation_cost:
		return {
			"lines": [
				"The scale wants %d biomass for %s." % [mutation_cost, mutation_name],
				"I only have %d." % biomass
			],
			"buttons": [{"label": "Back to scales", "action": "browse_wares"}, {"label": "Withdraw", "action": "leave_merchant"}]
		}

	biomass -= mutation_cost
	owned_mutations.append(mutation_id)
	_merchant_purchase_made = true
	_add_corruption(1)
	_apply_owned_mutation_state_bounds()
	return _with_director_lines({
		"lines": [
			"I feed the scale. The egg lunges before I finish stepping back.",
			"It bursts across my legs and crawls inward.",
			"%s settles into me. Biomass: %d. Corruption: %d." % [mutation_name, biomass, corruption]
		],
		"buttons": [{"label": "Back to scales", "action": "browse_wares"}, {"label": "Withdraw", "action": "leave_merchant"}]
	}, _record_action_pattern("buy_mutation", {}))


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
	_last_action_result = _with_director_lines(_last_action_result, _record_action_pattern(action_id, event_data))
	current_encounter["consumed"] = true


func advance_to_next_encounter() -> Dictionary:
	if not current_encounter.is_empty() and bool(current_encounter.get("counts_as_room", false)):
		rooms_cleared += 1
		_advance_symbiote_room_state()

	var next_encounter := _build_next_encounter()
	current_encounter = next_encounter
	current_room_id = str(next_encounter.get("room_id", current_room_id))
	encounter_changed.emit(get_current_encounter())
	return get_current_encounter()


func apply_combat_result(combat_result: Dictionary, enemy_data: Dictionary) -> Dictionary:
	var adjusted_result := combat_result.duplicate(true)
	if int(adjusted_result.get("player_remaining_health", player_state.get("health", 0))) <= 0 and active_symbiotes.has("mitosis_unit"):
		_kill_symbiote("mitosis_unit")
		adjusted_result["player_remaining_health"] = 1
		adjusted_result["enemy_won"] = false
		adjusted_result["mitosis_triggered"] = true

	player_state["health"] = int(max(int(adjusted_result.get("player_remaining_health", player_state.get("health", 0))), 0))
	player_state["shield"] = int(max(int(adjusted_result.get("player_remaining_shield", player_state.get("shield", 0))), 0))
	if bool(adjusted_result.get("player_won", false)):
		biomass += int(enemy_data.get("biomass_reward", 0))
	return adjusted_result


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


func _build_active_deck_cards() -> Array[Dictionary]:
	var cards: Array[Dictionary] = []

	var enemy_count := int(max(1 + danger, 1))
	enemy_count += int(_get_pressure_count("avoid_combat") / 2)
	if _is_ending_locked("hunter"):
		enemy_count += 2
	var max_enemy_cards := int(deck_config.get("max_enemy_cards_per_deck", 4))
	if max_enemy_cards > 0:
		enemy_count = min(enemy_count, max_enemy_cards)
	_append_room_cards(cards, _get_room_pool_ids("enemy"), enemy_count, "combat", [])

	var branch_count := _rng.randi_range(
		int(deck_config.get("branch_cards_min", 1)),
		int(deck_config.get("branch_cards_max", 2))
	)
	_append_room_cards(cards, _get_room_pool_ids("branch"), branch_count, "", ["combat", "boss", "symbiote"])

	var straight_count := _rng.randi_range(
		int(deck_config.get("straight_cards_min", 2)),
		int(deck_config.get("straight_cards_max", 4))
	)
	_append_room_cards(cards, _get_room_pool_ids("straight_noncombat"), straight_count, "", ["combat", "boss", "symbiote"])

	if bool(deck_config.get("symbiote_card_per_deck", true)) and not _get_available_symbiote_ids().is_empty():
		cards.append({"kind": "symbiote"})

	_shuffle_deck_cards(cards)
	return cards


func _get_room_pool_ids(pool_name: String) -> Array[String]:
	var pool_variant = deck_config.get("room_pools", {}).get(pool_name, [])
	var pool_ids: Array[String] = []
	if not pool_variant is Array:
		return pool_ids
	for value in pool_variant:
		var room_id := str(value)
		if room_id != "":
			pool_ids.append(room_id)
	return pool_ids


func _append_room_cards(cards: Array[Dictionary], pool_ids: Array[String], count: int, preferred_type: String = "", excluded_types: Array[String] = []) -> void:
	var available_ids := pool_ids.duplicate()
	var chosen_ids: Array[String] = []
	for _index in range(max(count, 0)):
		var room_id := _draw_room_from_pool(available_ids, chosen_ids)
		if room_id == "":
			return
		if _get_eligible_events_for_room(room_id, preferred_type, excluded_types).is_empty():
			available_ids.erase(room_id)
			continue
		chosen_ids.append(room_id)
		cards.append({
			"kind": "room",
			"room_id": room_id,
			"event_type": preferred_type,
			"excluded_types": excluded_types.duplicate()
		})


func _shuffle_deck_cards(cards: Array[Dictionary]) -> void:
	for index in range(cards.size() - 1, 0, -1):
		var swap_index := _rng.randi_range(0, index)
		var temp := cards[index]
		cards[index] = cards[swap_index]
		cards[swap_index] = temp


func _remove_symbiote_cards_from_active_deck() -> void:
	for index in range(active_deck_cards.size() - 1, -1, -1):
		if str(active_deck_cards[index].get("kind", "")) == "symbiote":
			active_deck_cards.remove_at(index)


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
	active_deck_cards = _build_active_deck_cards()
	active_deck_room_ids = base_deck_room_ids.duplicate(true)
	consumed_room_events.clear()
	_merchant_due_before_redraw = false


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

	if not _pending_director_events.is_empty():
		var director_event_id := str(_pending_director_events.pop_front())
		if special_events.has(director_event_id):
			return _build_special_encounter(director_event_id)

	if _should_offer_corruption_claim():
		_corruption_claim_triggered = true
		return _build_special_encounter("corruption_claim")

	if _should_offer_hunter_reckoning():
		_hunter_reckoning_triggered = true
		return _build_special_encounter("hunter_reckoning")

	if _should_offer_merchant_reckoning():
		_merchant_reckoning_triggered = true
		return _build_special_encounter("merchant_reckoning")

	if _should_offer_corruption_spike_room():
		_corruption_spike_triggers += 1
		return _build_corruption_spike_encounter()

	if _should_offer_danger_notice():
		_danger_notice_triggers += 1
		return _build_special_encounter("danger_spike_notice")

	return _draw_room_encounter()


func _should_offer_merchant() -> bool:
	var merchant_every := int(deck_config.get("merchant_every", 5))
	if merchant_every <= 0 or rooms_cleared <= 0:
		return false
	if rooms_cleared % merchant_every != 0:
		return false
	return not _merchant_triggered_at_rooms.has(rooms_cleared)


func _should_offer_merchant_reckoning() -> bool:
	if _merchant_reckoning_triggered:
		return false
	if not special_events.has("merchant_reckoning"):
		return false
	var refusal_limit := int(deck_config.get("merchant_refusal_limit", 0))
	var claim_limit := int(deck_config.get("merchant_claim_limit", 3))
	var refusal_due := refusal_limit > 0 and merchant_refusals >= refusal_limit
	var claim_due := claim_limit > 0 and merchant_claim >= claim_limit
	return refusal_due or claim_due


func _should_offer_hunter_reckoning() -> bool:
	if _hunter_reckoning_triggered:
		return false
	if not special_events.has("hunter_reckoning"):
		return false
	if not _can_offer_terminal_pressure_event():
		return false
	return _is_ending_locked("hunter")


func _should_offer_corruption_claim() -> bool:
	if _corruption_claim_triggered:
		return false
	if not special_events.has("corruption_claim"):
		return false
	if not _can_offer_terminal_pressure_event():
		return false
	return _is_ending_locked("corruption")


func _can_offer_terminal_pressure_event() -> bool:
	var minimum_rooms := int(deck_config.get("ending_reckoning_min_rooms", 12))
	return rooms_cleared >= max(minimum_rooms, 0)


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

	var event_data: Dictionary = special_events.get("symbiote_host_offer", {}).duplicate(true)
	if event_data.is_empty():
		return _draw_room_encounter()

	var choice_count := int(event_data.get("symbiote_choice_count", 3))
	event_data["symbiote_choices"] = _draw_symbiote_choices(available_symbiote_ids, choice_count)
	event_data["line_1"] = "Chorus, dying host ahead. Several symbiotes still clinging to it."
	event_data["line_2"] = "One bond makes one dependency. The shock kills the rest."

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
		if active_deck_cards.is_empty():
			if _merchant_due_before_redraw:
				_reset_active_deck()
			elif rooms_cleared > 0 and special_events.has("merchant_arrival"):
				_merchant_due_before_redraw = true
				_merchant_triggered_at_rooms[rooms_cleared] = true
				return _build_special_encounter("merchant_arrival", current_room_id, get_room_data(current_room_id))
			else:
				_reset_active_deck()

		if active_deck_cards.is_empty():
			return _build_fallback_encounter("active deck empty after reset")

		var card: Dictionary = active_deck_cards.pop_front()
		if str(card.get("kind", "")) == "symbiote":
			return _build_symbiote_encounter()

		var room_id := str(card.get("room_id", ""))
		var preferred_type := str(card.get("event_type", ""))
		var excluded_types: Array[String] = _normalize_string_array(card.get("excluded_types", []))
		var eligible_events := _get_eligible_events_for_room(room_id, preferred_type, excluded_types)
		if eligible_events.is_empty():
			continue

		var event_data: Dictionary = eligible_events[_rng.randi_range(0, eligible_events.size() - 1)]
		return _build_room_encounter(room_id, event_data)

	return _build_fallback_encounter("no eligible event after 128 draw attempts")


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


func _get_eligible_events_for_room(room_id: String, preferred_type: String = "", excluded_types: Array[String] = []) -> Array[Dictionary]:
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

		var event_type := str(event_data.get("type", ""))
		if preferred_type != "" and event_type != preferred_type:
			continue
		if excluded_types.has(event_type):
			continue

		eligible_events.append(event_data)

	return eligible_events


func _build_room_encounter(room_id: String, event_data: Dictionary) -> Dictionary:
	var room_data := get_room_data(room_id)
	var enemy_data := _resolve_enemy_data(event_data)
	var scene_path := str(event_data.get("scene_path", ""))
	if scene_path == "" and str(event_data.get("type", "")) == "combat":
		scene_path = str(enemy_data.get("scene_path", ""))
	return {
		"kind": "room_event",
		"room_id": room_id,
		"room_data": room_data,
		"event_id": str(event_data.get("id", "")),
		"event_data": event_data.duplicate(true),
		"scene_path": scene_path,
		"lines": _build_lines(room_data, event_data),
		"buttons": _build_buttons(event_data),
		"enemy_data": enemy_data,
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


func _build_fallback_encounter(reason: String) -> Dictionary:
	var room_id := current_room_id if current_room_id != "" else str(deck_config.get("opening_room_id", "red_corridor"))
	var event_data := {
		"id": "fallback_empty_draw",
		"type": "narrative",
		"speaker": "Her",
		"line_1": "Chorus, route draw failed. The corridor holds open but gives me nothing clean.",
		"line_2": "Debug: %s. I force a reset and keep moving." % reason,
		"buttons": [{"label": "Force the route open", "action": "proceed"}]
	}
	_reset_active_deck()
	return {
		"kind": "fallback_event",
		"room_id": room_id,
		"room_data": get_room_data(room_id),
		"event_id": "fallback_empty_draw",
		"event_data": event_data,
		"scene_path": "",
		"lines": _build_lines({}, event_data),
		"buttons": _build_buttons(event_data),
		"enemy_data": {},
		"counts_as_room": false,
		"consumed": false
	}


func _build_lines(room_data: Dictionary, event_data: Dictionary) -> Array[String]:
	var lines: Array[String] = []
	var line_1 := str(event_data.get("line_1", room_data.get("ui_text", {}).get("line_1", "")))
	var line_2 := str(event_data.get("line_2", room_data.get("ui_text", {}).get("line_2", "")))

	if line_1 != "":
		lines.append(line_1)
	if line_2 != "":
		lines.append(line_2)

	return lines


func _build_buttons(event_data: Dictionary) -> Array:
	if event_data.has("symbiote_choices"):
		return _build_symbiote_choice_buttons(event_data)

	var buttons_variant = event_data.get("buttons", [])
	var buttons: Array = []
	if buttons_variant is Array and not buttons_variant.is_empty():
		buttons = buttons_variant.duplicate(true)
	else:
		buttons = [{"label": "Proceed.", "action": "proceed"}]
	return _append_symbiote_activation_buttons(buttons, event_data)


func _build_symbiote_choice_buttons(event_data: Dictionary) -> Array:
	var buttons: Array = []
	var choices: Array[String] = _normalize_symbiote_choices(event_data.get("symbiote_choices", []))
	for symbiote_id in choices:
		if not symbiotes_by_id.has(symbiote_id):
			continue
		if owned_symbiotes.has(symbiote_id):
			continue
		var symbiote_data: Dictionary = symbiotes_by_id.get(symbiote_id, {})
		buttons.append({
			"label": "Bond: %s" % str(symbiote_data.get("name", symbiote_id)),
			"action": "take_symbiote:%s" % symbiote_id
		})

	var fallback_buttons = event_data.get("buttons", [])
	if fallback_buttons is Array:
		for button in fallback_buttons:
			if button is Dictionary:
				buttons.append(button.duplicate(true))

	if buttons.is_empty():
		buttons.append({"label": "Leave them", "action": "leave_symbiote"})
	return buttons


func _append_symbiote_activation_buttons(buttons: Array, event_data: Dictionary) -> Array:
	var event_type := str(event_data.get("type", ""))
	if event_type == "merchant" or event_type == "symbiote":
		return buttons
	for symbiote_id in owned_symbiotes:
		if not _can_activate_symbiote(symbiote_id):
			continue
		var symbiote_data: Dictionary = symbiotes_by_id.get(symbiote_id, {})
		buttons.append({
			"label": "Activate: %s" % str(symbiote_data.get("name", symbiote_id)),
			"action": "activate_symbiote:%s" % symbiote_id
		})
	return buttons


func _can_activate_symbiote(symbiote_id: String) -> bool:
	if not symbiotes_by_id.has(symbiote_id):
		return false
	if int(symbiote_health.get(symbiote_id, 0)) <= 0:
		return false
	if int(symbiote_cooldowns.get(symbiote_id, 0)) > 0:
		return false
	if active_symbiotes.has(symbiote_id):
		return false
	return true


func _build_symbiote_activation_result(lines: Array[String]) -> Dictionary:
	var buttons: Array = [{"label": "Proceed.", "action": "proceed"}]
	var event_data: Dictionary = current_encounter.get("event_data", {})
	if not event_data.is_empty() and not bool(current_encounter.get("consumed", false)) and not event_data.has("symbiote_choices"):
		buttons = _build_buttons(event_data)
	return {"lines": lines, "buttons": buttons}


func _get_enemy_tier() -> int:
	var pressure_tier_bonus := int(_get_pressure_count("avoid_combat") / 3)
	if _is_ending_locked("hunter"):
		pressure_tier_bonus += 1
	return int(max(1 + _merchant_triggered_at_rooms.size() + danger + pressure_tier_bonus, 1))


func _apply_enemy_tier(enemy_data: Dictionary) -> Dictionary:
	var tier := _get_enemy_tier()
	var tier_steps := tier - 1
	enemy_data["tier"] = tier
	enemy_data["armor"] = int(enemy_data.get("armor", 0))
	enemy_data["shield"] = int(enemy_data.get("shield", 0)) + tier_steps * 2
	enemy_data["damage"] = int(enemy_data.get("damage", 1)) + tier_steps
	enemy_data["health"] = int(enemy_data.get("health", 5)) + tier_steps * 5
	enemy_data["speed"] = float(enemy_data.get("speed", 1.0))
	enemy_data["visual_scale"] = 1.0 + float(tier_steps) * 0.12
	return enemy_data


func _resolve_enemy_data(event_data: Dictionary) -> Dictionary:
	var enemy_id := str(event_data.get("enemy_id", ""))
	if enemy_id == "":
		return {}
	var enemy_data: Dictionary = enemies_by_id.get(enemy_id, {}).duplicate(true)
	if enemy_data.is_empty():
		return {}
	return _apply_enemy_tier(enemy_data)


func _apply_action_effects(action_id: String, event_data: Dictionary) -> Dictionary:
	if action_id.begins_with("take_symbiote:"):
		return _take_symbiote_from_event(action_id.substr("take_symbiote:".length()), event_data)

	match action_id:
		"take_mutation":
			var mutation_id := str(event_data.get("mutation_id", ""))
			if mutation_id != "" and owned_mutations.has(mutation_id):
				return {
					"lines": [
						"The mutation is already in me.",
						"I leave the growth twitching behind."
					]
				}
			if mutation_id != "" and not owned_mutations.has(mutation_id):
				owned_mutations.append(mutation_id)
			_add_corruption(1)
			return {
				"play_animation": "open",
				"lines": [
					"The flesh opens and the mutation takes hold.",
					"Corruption rises to %d." % corruption
				]
			}
		"take_symbiote":
			return _take_symbiote_from_event(str(event_data.get("symbiote_id", "")), event_data)
		"leave_symbiote":
			var remaining_symbiotes := _describe_symbiote_choices(_normalize_symbiote_choices(event_data.get("symbiote_choices", [])))
			return {
				"lines": [
					"I leave the host and its symbiotes behind.",
					"%s do not follow." % (remaining_symbiotes if remaining_symbiotes != "" else "They")
				]
			}
		"leave_mutation":
			return {
				"lines": [
					"I left the mutation where it twitched.",
					"I should keep moving."
				]
			}
		"drink_pool":
			var restored_health := _restore_player_health(int(event_data.get("heal", 8)))
			_add_corruption(1)
			return {
				"lines": [
					"The pool knits %d health back into place." % restored_health,
					"Something of it lingers. Corruption rises to %d." % corruption
				]
			}
		"study_pool":
			var reduced_corruption := _add_corruption(-1)
			return {
				"lines": [
					"I study the current instead of stepping into it.",
					"Corruption settles to %d." % reduced_corruption
				]
			}
		"retreat":
			return {
				"lines": [
					"I back away before the room can learn my shape.",
					"Better to keep moving."
				]
			}
		"harvest_eggs":
			_add_biomass(int(event_data.get("biomass", 5)))
			_add_corruption(1)
			return {
				"lines": [
					"I split the sacs and strip out fresh biomass.",
					"Biomass: %d. Corruption: %d." % [biomass, corruption]
				]
			}
		"cauterize_eggs":
			return _build_damage_result(int(event_data.get("damage", 6)), [
				"I burn a lane through the nest and the sacs burst against me."
			], "I make it through, singed but breathing.")
		"slip_between_eggs":
			return {
				"lines": [
					"I thread between the sacs and leave them unbroken.",
					"Nothing gained. Nothing owed."
				]
			}
		"inspect_cracked_egg":
			_add_biomass(int(event_data.get("biomass", 3)))
			return {
				"lines": [
					"I check the cracked shell and scrape warm residue from the split.",
					"Biomass: %d." % biomass
				]
			}
		"track_hatchling":
			var hatchling_damage := _apply_player_damage(int(event_data.get("damage", 3)))
			_add_biomass(int(event_data.get("biomass", 6)))
			_add_danger(1)
			return {
				"lines": [
					"I follow the drag marks until the hatchling doubles back.",
					_build_damage_summary(int(event_data.get("damage", 3)), hatchling_damage),
					"Biomass: %d. Danger rises to %d." % [biomass, danger]
				]
			}
		"siphon_amber":
			var amber_damage := _apply_player_damage(int(event_data.get("damage", 2)))
			_add_biomass(int(event_data.get("biomass", 7)))
			return {
				"lines": [
					"I carve amber clot from the wall and pocket the mass.",
					_build_damage_summary(int(event_data.get("damage", 2)), amber_damage),
					"Biomass: %d." % biomass
				]
			}
		"break_amber_cache":
			var cache_damage := _apply_player_damage(int(event_data.get("damage", 3)))
			_add_biomass(int(event_data.get("biomass", 5)))
			return {
				"lines": [
					"I crack the amber shell and pull the hard piece loose.",
					_build_damage_summary(int(event_data.get("damage", 3)), cache_damage),
					"Biomass: %d." % biomass
				]
			}
		"probe_amber_cache":
			var probed_shield := _restore_player_shield(int(event_data.get("shield", 2)))
			_add_danger(-1)
			return {
				"lines": [
					"I test the shell until it gives me a clean path around the pressure.",
					"Shield restored: %d. Danger settles to %d." % [probed_shield, danger]
				]
			}
		"seal_amber_wound":
			var restored_shield := _restore_player_shield(int(event_data.get("shield", 5)))
			_add_corruption(1)
			return {
				"lines": [
					"The amber hardens over me and restores %d shield." % restored_shield,
					"Corruption rises to %d." % corruption
				]
			}
		"leave_amber":
			return {
				"lines": [
					"I leave the amber sealed in the wall.",
					"It watches me go."
				]
			}
		"slip_green_spores":
			_add_danger(-1)
			return {
				"lines": [
					"I hold my breath and pass under the spore drift clean.",
					"Danger settles to %d." % danger
				]
			}
		"disturb_green_spores":
			var spore_heal := _restore_player_health(int(event_data.get("heal", 3)))
			_add_corruption(1)
			_add_danger(1)
			return {
				"lines": [
					"I stir the spores and let the green dust knit into the cuts.",
					"Health restored: %d. Corruption: %d. Danger: %d." % [spore_heal, corruption, danger]
				]
			}
		"take_green_tunnel":
			var green_heal := _restore_player_health(int(event_data.get("heal", 4)))
			_add_corruption(1)
			return {
				"lines": [
					"The soft tunnel carries me forward and mends %d health." % green_heal,
					"It leaves residue behind. Corruption: %d." % corruption
				]
			}
		"cut_green_spine":
			var green_damage := _apply_player_damage(int(event_data.get("damage", 4)))
			_add_biomass(int(event_data.get("biomass", 5)))
			return {
				"lines": [
					"I cut through the rigid spine and tear biomass free.",
					_build_damage_summary(int(event_data.get("damage", 4)), green_damage),
					"Biomass: %d." % biomass
				]
			}
		"listen_at_green_split":
			_add_danger(-1)
			return {
				"lines": [
					"I wait, listen, and pick the calmer pulse.",
					"Danger settles to %d." % danger
				]
			}
		"cut_red_wall":
			var wall_damage := _apply_player_damage(int(event_data.get("damage", 3)))
			_add_biomass(int(event_data.get("biomass", 4)))
			_add_corruption(1)
			return {
				"lines": [
					"I cut the breathing wall open before it can close around the blade.",
					_build_damage_summary(int(event_data.get("damage", 3)), wall_damage),
					"Biomass: %d. Corruption: %d." % [biomass, corruption]
				]
			}
		"listen_red_wall":
			_add_danger(-1)
			return {
				"lines": [
					"I tap once and wait until the corridor answers.",
					"Danger settles to %d." % danger
				]
			}
		"open_red_artery":
			_add_biomass(int(event_data.get("biomass", 6)))
			_add_corruption(1)
			return {
				"lines": [
					"I open the swollen artery and collect what spills out.",
					"Biomass: %d. Corruption: %d." % [biomass, corruption]
				]
			}
		"brace_through_red_split":
			return _build_damage_result(int(event_data.get("damage", 4)), [
				"I force the dry lane open with my body."
			], "The junction yields, but it costs me flesh.")
		"mark_red_branch":
			_add_danger(-1)
			return {
				"lines": [
					"I trace the pulse pattern and choose the safer branch.",
					"Danger settles to %d." % danger
				]
			}
		"rush_red_split":
			var rush_damage := _apply_player_damage(int(event_data.get("damage", 4)))
			_add_danger(1)
			return {
				"lines": [
					"I rush the split before the wall decides where to burst.",
					_build_damage_summary(int(event_data.get("damage", 4)), rush_damage),
					"Danger rises to %d." % danger
				]
			}
		"vent_red_split":
			var vent_damage := _apply_player_damage(int(event_data.get("damage", 2)))
			_add_biomass(int(event_data.get("biomass", 4)))
			_add_danger(-1)
			return {
				"lines": [
					"I cut a vent and let the pressure bleed out hot.",
					_build_damage_summary(int(event_data.get("damage", 2)), vent_damage),
					"Biomass: %d. Danger settles to %d." % [biomass, danger]
				]
			}
		"push_through_spikes":
			return _build_damage_result(int(event_data.get("damage", 8)), [
				"The corridor closes until I force myself through the spikes."
			], "The passage opens only after it has taken its cut.")
		"break_spike_lane":
			var spike_break_damage := int(event_data.get("break_damage", 5))
			var spike_damage := _apply_player_damage(spike_break_damage)
			_add_biomass(int(event_data.get("biomass", 4)))
			return {
				"lines": [
					"I break the spike line one joint at a time.",
					_build_damage_summary(spike_break_damage, spike_damage),
					"Biomass: %d." % biomass
				]
			}
		"observe_organ_chamber":
			var observed_shield := _restore_player_shield(int(event_data.get("shield", 3)))
			_add_danger(-1)
			return {
				"lines": [
					"I slow my breathing until the chamber loses the rhythm.",
					"Shield restored: %d. Danger settles to %d." % [observed_shield, danger]
				]
			}
		"cut_heart_cords":
			var cord_damage := _apply_player_damage(int(event_data.get("damage", 4)))
			_add_biomass(int(event_data.get("biomass", 6)))
			_add_corruption(1)
			return {
				"lines": [
					"I cut the hanging cords and catch what spills before it clots.",
					_build_damage_summary(int(event_data.get("damage", 4)), cord_damage),
					"Biomass: %d. Corruption: %d." % [biomass, corruption]
				]
			}
		"scavenge_bones":
			var bone_damage := _apply_player_damage(int(event_data.get("damage", 2)))
			_add_biomass(int(event_data.get("biomass", 5)))
			return {
				"lines": [
					"I strip the pile before the marrow nerves finish waking.",
					_build_damage_summary(int(event_data.get("damage", 2)), bone_damage),
					"Biomass: %d." % biomass
				]
			}
		"probe_bones":
			_add_danger(-1)
			return {
				"lines": [
					"I probe the heap from a distance and find the quiet route through.",
					"Danger settles to %d." % danger
				]
			}
		"disturb_pool":
			var pool_heal := _restore_player_health(int(event_data.get("heal", 10)))
			_add_corruption(2)
			return {
				"lines": [
					"I break the surface and let the pool answer first.",
					"Health restored: %d. Corruption rises to %d." % [pool_heal, corruption]
				]
			}
		"pay_resin_toll":
			var toll_cost := int(event_data.get("biomass_cost", 5))
			if biomass < toll_cost:
				merchant_claim += 1
				_add_danger(1)
				return {
					"lines": [
						"I press my palm to the resin slot. It wants %d biomass. I only have %d." % [toll_cost, biomass],
						"The slot closes on the debt. Claim: %d. Danger rises to %d." % [merchant_claim, danger]
					]
				}
			biomass -= toll_cost
			_add_danger(-1)
			return {
				"lines": [
					"I feed %d biomass into the amber toll and the corridor quiets." % toll_cost,
					"Biomass: %d. Danger settles to %d." % [biomass, danger]
				]
			}
		"skip_resin_toll":
			merchant_claim += 1
			_add_danger(1)
			return {
				"lines": [
					"I leave the toll hungry. Resin clicks behind me like teeth counting.",
					"Tally lines crawl under the plaque. Claim: %d. Danger rises to %d." % [merchant_claim, danger]
				]
			}
		"turn_baffle":
			baffle_mutes += 1
			var baffle_drop := 2 if baffle_mutes == 1 else 1
			_add_danger(-baffle_drop)
			var baffle_lines: Array[String] = [
				"I twist the baffle until the lane stops carrying my scent.",
				"Danger settles to %d." % danger
			]
			if baffle_mutes >= 2:
				if _enqueue_director_event_once("smother_hunter_arrival", "smother_hunter"):
					baffle_lines.append("The air stays too still behind me. Thin diaphragms tighten in the vents.")
			return {"lines": baffle_lines}
		"break_baffle":
			var baffle_damage := _apply_player_damage(int(event_data.get("damage", 2)))
			baffle_mutes = 0
			_add_biomass(int(event_data.get("biomass", 3)))
			_add_danger(1)
			return {
				"lines": [
					"I break the baffle wheel and tear out its wet hinge.",
					_build_damage_summary(int(event_data.get("damage", 2)), baffle_damage),
					"Biomass: %d. Danger rises to %d." % [biomass, danger]
				]
			}
		"follow_marked_plates":
			marked_route_streak += 1
			_add_danger(-1)
			var plate_lines: Array[String] = [
				"I follow the clean plate line and let the corridor think I obey.",
				"Danger settles to %d. Marked route streak: %d." % [danger, marked_route_streak]
			]
			if marked_route_streak >= 2:
				plate_lines.append("Minute teeth in the seams turn to match my stride.")
			if marked_route_streak >= 3:
				if _enqueue_director_event_once("plate_snare", "plate_snare"):
					plate_lines.append("The plates remember the shape of my steps.")
			return {"lines": plate_lines}
		"break_marked_pattern":
			var pattern_damage := _apply_player_damage(int(event_data.get("damage", 2)))
			marked_route_streak = 0
			_add_danger(-1)
			return {
				"lines": [
					"I step wrong on purpose and let the plates bite air.",
					_build_damage_summary(int(event_data.get("damage", 2)), pattern_damage),
					"Danger settles to %d. The marked streak breaks." % danger
				]
			}
		"leave_merchant":
			if _merchant_purchase_made:
				_merchant_purchase_made = false
				return {
					"lines": [
						"I leave with his bargain still moving under my skin.",
						"He lets the scale close."
					]
				}
			merchant_refusals += 1
			_add_danger(1)
			return {
				"lines": [
					"I leave the merchant to its clicking teeth.",
					"Danger rises to %d. He remembers the refusal." % danger
				]
			}
		"run":
			_add_danger(1)
			return {
				"lines": [
					"I run for the next chamber without looking back.",
					"Danger rises to %d." % danger
				]
			}
		_:
			return {}

	return {}


func _with_director_lines(result: Dictionary, director_lines: Array[String]) -> Dictionary:
	if director_lines.is_empty():
		return result

	var updated := result.duplicate(true)
	var lines: Array = []
	var existing_lines = updated.get("lines", [])
	if existing_lines is Array:
		lines = existing_lines.duplicate()

	for line in director_lines:
		if line != "":
			lines.append(line)
	updated["lines"] = lines
	return updated


func _record_action_pattern(action_id: String, event_data: Dictionary) -> Array[String]:
	var base_action := _base_action_id(action_id)
	var event_type := str(event_data.get("type", ""))
	var axes: Array[String] = []

	if (event_type == "combat" or event_type == "boss") and ["proceed", "run", "retreat"].has(base_action):
		_add_pressure_axis(axes, "avoid_combat")
		_add_pressure_axis(axes, "danger")
		if base_action == "proceed":
			_add_danger(1)

	match base_action:
		"combat":
			_add_pressure_axis(axes, "combat")
		"take_mutation", "buy_mutation":
			_add_pressure_axis(axes, "corruption")
		"take_symbiote", "activate_symbiote":
			_add_pressure_axis(axes, "dependence")
		"drink_pool", "disturb_pool", "seal_amber_wound", "take_green_tunnel", "disturb_green_spores", "harvest_eggs", "open_red_artery", "cut_red_wall", "cut_heart_cords":
			_add_pressure_axis(axes, "corruption")
		"run", "leave_merchant", "track_hatchling", "rush_red_split", "disturb_green_spores":
			_add_pressure_axis(axes, "danger")
		"skip_resin_toll", "break_baffle":
			_add_pressure_axis(axes, "danger")
			_add_pressure_axis(axes, "debt")
		"retreat":
			_add_pressure_axis(axes, "safety")
			_add_pressure_axis(axes, "danger")
			_add_danger(1)
		"harvest_eggs", "siphon_amber", "overdraw_amber", "break_amber_cache", "inspect_cracked_egg", "scavenge_bones", "open_red_artery", "cut_green_spine", "cut_red_wall", "vent_red_split", "cut_heart_cords":
			_add_pressure_axis(axes, "greed")
		"pay_resin_toll", "turn_baffle", "follow_marked_plates":
			_add_pressure_axis(axes, "safety")
		"study_pool", "listen_at_green_split", "mark_red_branch", "listen_red_wall", "probe_amber_cache", "slip_green_spores", "probe_bones", "observe_organ_chamber", "leave_amber", "leave_symbiote", "leave_mutation", "slip_between_eggs", "break_marked_pattern":
			_add_pressure_axis(axes, "safety")

	var lines: Array[String] = []
	for axis in axes:
		var count := _increment_pressure(axis)
		for line in _evaluate_pressure_axis(axis, count):
			lines.append(line)
	return lines


func _base_action_id(action_id: String) -> String:
	if action_id.begins_with("take_symbiote:"):
		return "take_symbiote"
	if action_id.begins_with("activate_symbiote:"):
		return "activate_symbiote"
	if action_id.begins_with("buy_mutation:"):
		return "buy_mutation"
	return action_id


func _add_pressure_axis(axes: Array[String], axis: String) -> void:
	if axis != "" and not axes.has(axis):
		axes.append(axis)


func _increment_pressure(axis: String) -> int:
	var count := int(pressure_counts.get(axis, 0)) + 1
	pressure_counts[axis] = count
	return count


func _get_pressure_count(axis: String) -> int:
	return int(pressure_counts.get(axis, 0))


func _evaluate_pressure_axis(axis: String, count: int) -> Array[String]:
	var lines: Array[String] = []
	var warning_threshold := int(deck_config.get("pressure_warning_threshold", 3))
	var lock_threshold := int(deck_config.get("pressure_lock_threshold", 6))

	match axis:
		"corruption":
			var corruption_warning_threshold := int(deck_config.get("corruption_warning_threshold", warning_threshold))
			if count >= warning_threshold or corruption >= corruption_warning_threshold:
				if _enqueue_director_event_once("director_corruption_warning", "corruption_warning"):
					lines.append("The walls accept the new shape too quickly.")
			var corruption_ending_threshold := int(deck_config.get("corruption_ending_threshold", 8))
			if count >= lock_threshold or corruption >= corruption_ending_threshold:
				if _lock_ending_pressure("corruption"):
					lines.append("The run tilts. Corruption has the stronger claim.")
		"danger", "avoid_combat":
			var danger_warning_threshold := int(deck_config.get("danger_warning_threshold", warning_threshold))
			if count >= warning_threshold or danger >= danger_warning_threshold or _get_pressure_count("avoid_combat") >= danger_warning_threshold:
				if _enqueue_director_event_once("director_danger_warning", "danger_warning"):
					lines.append("Something has learned the route behind me.")
			var hunter_ending_threshold := int(deck_config.get("hunter_ending_threshold", 8))
			var hunter_avoidance_threshold := int(deck_config.get("hunter_avoidance_threshold", 4))
			if count >= lock_threshold or danger >= hunter_ending_threshold or _get_pressure_count("avoid_combat") >= hunter_avoidance_threshold:
				if _lock_ending_pressure("hunter"):
					lines.append("The run tilts. The hunter has the scent.")
		"greed":
			if count >= warning_threshold:
				if _enqueue_director_event_once("director_greed_warning", "greed_warning"):
					lines.append("The organism starts pricing my appetite.")
			if count >= lock_threshold:
				_add_danger(1)
		"safety":
			if count >= warning_threshold:
				if _enqueue_director_event_once("director_safety_warning", "safety_warning"):
					lines.append("The quiet route is starting to close.")
			if count >= lock_threshold:
				_add_danger(1)
		"combat":
			if count >= warning_threshold:
				if _enqueue_director_event_once("director_combat_warning", "combat_warning"):
					lines.append("Killing through every room is making me loud.")
			if count >= lock_threshold:
				_add_danger(1)
		"dependence":
			if count >= warning_threshold:
				if _enqueue_director_event_once("director_dependence_warning", "dependence_warning"):
					lines.append("Too much under my skin is answering before I do.")
		"debt":
			if count >= warning_threshold:
				if _enqueue_director_event_once("director_debt_warning", "debt_warning"):
					lines.append("The ledger starts to breathe behind me.")

	return lines


func _enqueue_director_event_once(event_id: String, warning_key: String) -> bool:
	if _director_triggered_warnings.has(warning_key):
		return false
	_director_triggered_warnings[warning_key] = true
	if special_events.has(event_id) and not _pending_director_events.has(event_id):
		_pending_director_events.append(event_id)
	return true


func _lock_ending_pressure(lock_id: String) -> bool:
	if _ending_locks.has(lock_id):
		return false
	_ending_locks[lock_id] = true
	if ending_pressure == "":
		ending_pressure = lock_id
	return true


func _is_ending_locked(lock_id: String) -> bool:
	return bool(_ending_locks.get(lock_id, false))


func _is_balanced_eligible() -> bool:
	if ending_pressure != "":
		return false
	var corruption_limit := int(deck_config.get("balanced_corruption_limit", 5))
	var danger_limit := int(deck_config.get("balanced_danger_limit", 5))
	var pressure_limit := int(deck_config.get("balanced_pressure_limit", 4))
	if corruption > corruption_limit or danger > danger_limit:
		return false
	for count_variant in pressure_counts.values():
		if int(count_variant) > pressure_limit:
			return false
	return true


func _get_available_symbiote_ids() -> Array[String]:
	var available_ids: Array[String] = []
	for symbiote_id_variant in symbiotes_by_id.keys():
		var symbiote_id := str(symbiote_id_variant)
		if symbiote_id != "" and not owned_symbiotes.has(symbiote_id):
			available_ids.append(symbiote_id)
	return available_ids


func _draw_symbiote_choices(available_ids: Array[String], choice_count: int) -> Array[String]:
	var pool := available_ids.duplicate()
	var choices: Array[String] = []
	var target_count = min(max(choice_count, 1), pool.size())
	while choices.size() < target_count and not pool.is_empty():
		var index := _rng.randi_range(0, pool.size() - 1)
		choices.append(pool[index])
		pool.remove_at(index)
	return choices


func _normalize_symbiote_choices(raw_choices: Variant) -> Array[String]:
	var choices: Array[String] = []
	if not raw_choices is Array:
		return choices
	for choice in raw_choices:
		var symbiote_id := str(choice)
		if symbiote_id != "" and not choices.has(symbiote_id):
			choices.append(symbiote_id)
	return choices


func _normalize_string_array(raw_values: Variant) -> Array[String]:
	var values: Array[String] = []
	if not raw_values is Array:
		return values
	for value in raw_values:
		var text := str(value)
		if text != "":
			values.append(text)
	return values


func _take_symbiote_from_event(symbiote_id: String, event_data: Dictionary) -> Dictionary:
	if symbiote_id == "" or not symbiotes_by_id.has(symbiote_id):
		return {
			"lines": [
				"The host spasms before I can find a clean bond.",
				"Nothing comes with me."
			]
		}

	var symbiote_data: Dictionary = symbiotes_by_id.get(symbiote_id, {})
	var symbiote_name := str(symbiote_data.get("name", symbiote_id))
	if owned_symbiotes.has(symbiote_id):
		return {
			"lines": [
				"%s recognizes what is already under my skin." % symbiote_name,
				"I leave the host twitching behind."
			]
		}

	owned_symbiotes.append(symbiote_id)
	symbiote_health[symbiote_id] = int(symbiote_data.get("max_health", 1))
	var choices := _normalize_symbiote_choices(event_data.get("symbiote_choices", []))
	var lost_choices: Array[String] = []
	for choice_id in choices:
		if choice_id != symbiote_id:
			lost_choices.append(choice_id)
	var lost_names := _describe_symbiote_choices(lost_choices)
	if lost_names == "":
		lost_names = "The others"

	return {
		"lines": [
			"%s latches on and sinks into me." % symbiote_name,
			"%s die with the host. One dependency comes with me." % lost_names
		],
		"buttons": [
			{"label": "Activate: %s" % symbiote_name, "action": "activate_symbiote:%s" % symbiote_id},
			{"label": "Carry the bond forward", "action": "proceed"}
		]
	}


func _describe_symbiote_choices(symbiote_ids: Array[String]) -> String:
	var names: Array[String] = []
	for symbiote_id in symbiote_ids:
		var symbiote_data: Dictionary = symbiotes_by_id.get(symbiote_id, {})
		names.append(str(symbiote_data.get("name", symbiote_id)))
	if names.is_empty():
		return ""
	if names.size() == 1:
		return names[0]
	if names.size() == 2:
		return "%s and %s" % [names[0], names[1]]

	var last_name: String = names.pop_back()
	return "%s, and %s" % [", ".join(names), last_name]


func _injure_symbiote(symbiote_id: String, amount: int) -> void:
	if not symbiote_health.has(symbiote_id):
		return
	var remaining_health := int(symbiote_health.get(symbiote_id, 0)) - int(max(amount, 0))
	if remaining_health <= 0:
		_kill_symbiote(symbiote_id)
	else:
		symbiote_health[symbiote_id] = remaining_health


func _kill_symbiote(symbiote_id: String) -> void:
	owned_symbiotes.erase(symbiote_id)
	symbiote_health.erase(symbiote_id)
	symbiote_cooldowns.erase(symbiote_id)
	active_symbiotes.erase(symbiote_id)


func _start_symbiote_cooldown(symbiote_id: String, rooms: int) -> void:
	if rooms <= 0 or not owned_symbiotes.has(symbiote_id):
		return
	symbiote_cooldowns[symbiote_id] = max(int(symbiote_cooldowns.get(symbiote_id, 0)), rooms)


func _tick_symbiote_cooldowns() -> void:
	var expired_ids: Array[String] = []
	for symbiote_id_variant in symbiote_cooldowns.keys():
		var symbiote_id := str(symbiote_id_variant)
		var remaining := int(symbiote_cooldowns.get(symbiote_id, 0)) - 1
		if remaining <= 0:
			expired_ids.append(symbiote_id)
		else:
			symbiote_cooldowns[symbiote_id] = remaining

	for symbiote_id in expired_ids:
		symbiote_cooldowns.erase(symbiote_id)


func _advance_symbiote_room_state() -> void:
	_tick_symbiote_cooldowns()
	if active_symbiotes.has("impermeable_barrier"):
		active_symbiotes.erase("impermeable_barrier")
		_start_symbiote_cooldown("impermeable_barrier", 4)
	if active_symbiotes.has("pheromones"):
		active_symbiotes.erase("pheromones")
		_start_symbiote_cooldown("pheromones", 2)


func _get_mutation_cost(mutation_data: Dictionary) -> int:
	return int(max(int(mutation_data.get("biomass_cost", 6)), 0))


func _apply_owned_mutation_combat_effects(stats: Dictionary) -> void:
	for mutation_id in owned_mutations:
		var mutation_data: Dictionary = mutations_by_id.get(str(mutation_id), {})
		var effects: Dictionary = mutation_data.get("effects", {})
		if effects.is_empty():
			continue

		if effects.has("damage_multiplier"):
			stats["damage"] = int(round(float(stats.get("damage", 0)) * float(effects.get("damage_multiplier", 1.0))))
		if effects.has("damage_delta"):
			stats["damage"] = int(max(int(stats.get("damage", 0)) + int(effects.get("damage_delta", 0)), 0))
		if effects.has("initiative_delta"):
			stats["initiative"] = clamp(float(stats.get("initiative", 0.0)) + float(effects.get("initiative_delta", 0.0)), 0.0, 1.0)
		if effects.has("speed_multiplier"):
			stats["speed"] = max(float(stats.get("speed", 1.0)) * float(effects.get("speed_multiplier", 1.0)), 0.01)
		if effects.has("contact_damage"):
			stats["contact_damage"] = int(stats.get("contact_damage", 0)) + int(effects.get("contact_damage", 0))
		if effects.has("battle_start_shield"):
			stats["shield"] = int(stats.get("shield", 0)) + int(effects.get("battle_start_shield", 0))
		if effects.has("max_health_delta"):
			stats["health"] = int(max(int(stats.get("health", 1)) + int(effects.get("max_health_delta", 0)), 1))


func _apply_owned_mutation_state_bounds() -> void:
	var max_health := int(deck_config.get("base_player_stats", {}).get("health", int(player_state.get("health", 1))))
	var max_shield := int(deck_config.get("base_player_stats", {}).get("shield", int(player_state.get("shield", 0))))
	for mutation_id in owned_mutations:
		var mutation_data: Dictionary = mutations_by_id.get(str(mutation_id), {})
		var effects: Dictionary = mutation_data.get("effects", {})
		max_health += int(effects.get("max_health_delta", 0))
		max_shield += int(effects.get("max_shield_delta", 0))

	player_state["health"] = int(clamp(int(player_state.get("health", 1)), 1, max(max_health, 1)))
	player_state["shield"] = int(clamp(int(player_state.get("shield", 0)), 0, max(max_shield, 0)))


func _add_biomass(amount: int) -> int:
	biomass = int(max(biomass + amount, 0))
	return biomass


func _add_corruption(amount: int) -> int:
	corruption = int(max(corruption + amount, 0))
	return corruption


func _apply_barrier_to_event_damage(raw_damage: int) -> Dictionary:
	var damage := int(max(raw_damage, 0))
	var result := {
		"remaining_damage": damage,
		"symbiote_blocked": 0,
		"symbiote_injured": false
	}
	if not active_symbiotes.has("impermeable_barrier"):
		return result

	var barrier_state: Dictionary = active_symbiotes.get("impermeable_barrier", {})
	var barrier_armor := int(barrier_state.get("armor", 0))
	if barrier_armor <= 0:
		active_symbiotes.erase("impermeable_barrier")
		return result

	var blocked: int = int(min(barrier_armor, damage))
	barrier_armor -= blocked
	result["symbiote_blocked"] = blocked
	result["remaining_damage"] = int(max(damage - blocked, 0))

	if barrier_armor <= 0:
		active_symbiotes.erase("impermeable_barrier")
		_injure_symbiote("impermeable_barrier", 1)
		_start_symbiote_cooldown("impermeable_barrier", 4)
		result["symbiote_injured"] = true
	else:
		barrier_state["armor"] = barrier_armor
		active_symbiotes["impermeable_barrier"] = barrier_state
	return result


func _apply_player_damage(raw_damage: int) -> Dictionary:
	var barrier_result := _apply_barrier_to_event_damage(raw_damage)
	var armor_value := int(player_state.get("armor", 0))
	var non_negative_damage: int = int(max(int(barrier_result.get("remaining_damage", raw_damage)), 0))
	var mitigated_by_armor: int = int(min(armor_value, non_negative_damage))
	var post_armor_damage: int = int(max(non_negative_damage - mitigated_by_armor, 0))
	var current_shield := int(player_state.get("shield", 0))
	var shield_lost: int = int(min(current_shield, post_armor_damage))
	player_state["shield"] = current_shield - shield_lost
	var remaining_damage: int = int(max(post_armor_damage - shield_lost, 0))
	var current_health := int(player_state.get("health", 0))
	var health_lost: int = int(min(current_health, remaining_damage))
	player_state["health"] = current_health - health_lost
	var mitosis_triggered := false
	if int(player_state["health"]) <= 0 and active_symbiotes.has("mitosis_unit"):
		_kill_symbiote("mitosis_unit")
		player_state["health"] = 1
		mitosis_triggered = true
	return {
		"symbiote_blocked": int(barrier_result.get("symbiote_blocked", 0)),
		"symbiote_injured": bool(barrier_result.get("symbiote_injured", false)),
		"mitosis_triggered": mitosis_triggered,
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
	var summary := "%d damage hit. Barrier blocked %d, armor blocked %d, shield lost %d, health lost %d." % [
		raw_damage,
		int(damage_result.get("symbiote_blocked", 0)),
		int(damage_result.get("mitigated_by_armor", 0)),
		int(damage_result.get("shield_lost", 0)),
		int(damage_result.get("health_lost", 0))
	]
	if bool(damage_result.get("symbiote_injured", false)):
		summary += " Impermeable Barrier loses 1 health."
	if bool(damage_result.get("mitosis_triggered", false)):
		summary += " Mitosis Unit dies in my place."
	return summary


func _add_danger(amount: int) -> void:
	danger = int(max(danger + amount, 0))
	_sync_heart_rate()


func _sync_heart_rate() -> void:
	if not is_inside_tree():
		return
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
