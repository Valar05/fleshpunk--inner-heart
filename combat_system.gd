class_name CombatSystem
extends RefCounted


static func simulate_combat(player_stats: Dictionary, enemy_stats: Dictionary, rng: RandomNumberGenerator) -> Dictionary:
	var player := _normalize_stats(player_stats)
	var enemy := _normalize_stats(enemy_stats)
	var player_starting_health: int = player.health
	var player_starting_shield: int = player.shield
	var enemy_starting_health: int = enemy.health
	var combat_log: Array[String] = []
	var rounds: int = 0

	var ambush_triggered: bool = rng.randf() < float(player.ambush_chance)
	if ambush_triggered:
		var ambush_result := _apply_attack(player, enemy)
		combat_log.append("Ambush strike for %d total damage." % ambush_result.total_damage)

	var first_attacker := "player"
	if enemy.health > 0:
		first_attacker = _roll_initiative(player, enemy, rng)

	while player.health > 0 and enemy.health > 0:
		rounds += 1
		if first_attacker == "player":
			var player_turn := _apply_attack(player, enemy)
			combat_log.append("Round %d: player hits for %d total damage." % [rounds, player_turn.total_damage])
			if enemy.health <= 0:
				break

			var enemy_turn := _apply_attack(enemy, player)
			combat_log.append("Round %d: enemy hits for %d total damage." % [rounds, enemy_turn.total_damage])
		else:
			var enemy_turn := _apply_attack(enemy, player)
			combat_log.append("Round %d: enemy hits for %d total damage." % [rounds, enemy_turn.total_damage])
			if player.health <= 0:
				break

			var player_turn := _apply_attack(player, enemy)
			combat_log.append("Round %d: player hits for %d total damage." % [rounds, player_turn.total_damage])

	return {
		"ambush_triggered": ambush_triggered,
		"initiative_winner": first_attacker,
		"player_won": player.health > 0 and enemy.health <= 0,
		"enemy_won": enemy.health > 0 and player.health <= 0,
		"rounds": rounds,
		"player_damage_taken": player_starting_health - player.health,
		"player_shield_lost": player_starting_shield - player.shield,
		"player_remaining_health": player.health,
		"player_remaining_shield": player.shield,
		"enemy_damage_taken": enemy_starting_health - enemy.health,
		"enemy_remaining_health": enemy.health,
		"enemy_remaining_shield": enemy.shield,
		"combat_log": combat_log
	}


static func _normalize_stats(stats: Dictionary) -> Dictionary:
	return {
		"damage": int(stats.get("damage", 1)),
		"armor": int(stats.get("armor", 0)),
		"shield": int(stats.get("shield", 0)),
		"health": int(stats.get("health", 1)),
		"ambush_chance": clamp(float(stats.get("ambush_chance", 0.0)), 0.0, 1.0),
		"initiative": clamp(float(stats.get("initiative", 0.5)), 0.0, 1.0)
	}


static func _roll_initiative(player: Dictionary, enemy: Dictionary, rng: RandomNumberGenerator) -> String:
	var player_score: float = rng.randf() + float(player.initiative)
	var enemy_score: float = rng.randf() + float(enemy.initiative)
	if is_equal_approx(player_score, enemy_score):
		return "player" if rng.randf() < 0.5 else "enemy"
	return "player" if player_score > enemy_score else "enemy"


static func _apply_attack(attacker: Dictionary, defender: Dictionary) -> Dictionary:
	var mitigated_damage: int = max(int(attacker.damage) - int(defender.armor), 0)
	var shield_damage: int = min(int(defender.shield), mitigated_damage)
	defender.shield -= shield_damage
	var health_damage: int = max(mitigated_damage - shield_damage, 0)
	defender.health = max(defender.health - health_damage, 0)
	return {
		"total_damage": shield_damage + health_damage,
		"health_damage": health_damage,
		"shield_damage": shield_damage
	}