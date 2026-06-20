"""Shared registry for structured condition DSL types."""


CONDITION_DEFINITIONS = {
    "always": {
        "handler": "_evaluate_always",
    },
    "and": {
        "handler": "_evaluate_and",
        "validator": "_validate_logical_condition",
    },
    "or": {
        "handler": "_evaluate_or",
        "validator": "_validate_logical_condition",
    },
    "not": {
        "handler": "_evaluate_not",
        "validator": "_validate_not_condition",
    },
    "source_has_state": {
        "handler": "_evaluate_source_has_state",
    },
    "event_actor_is": {
        "handler": "_evaluate_event_actor_is",
    },
    "event_card_matches": {
        "handler": "_evaluate_event_card_matches",
        "validator": "_validate_card_filter_condition",
    },
    "event_card_is": {
        "handler": "_evaluate_event_card_is",
    },
    "event_zone_change_matches": {
        "handler": "_evaluate_event_zone_change_matches",
        "validator": "_validate_event_zone_change_condition",
    },
    "event_player_is": {
        "handler": "_evaluate_event_player_is",
    },
    "event_value_matches": {
        "handler": "_evaluate_event_value_matches",
    },
    "source_zone_is": {
        "handler": "_evaluate_source_zone_is",
        "validator": "_validate_source_zone_condition",
    },
    "card_count_matches": {
        "handler": "_evaluate_card_count_matches",
        "validator": "_validate_card_count_condition",
    },
    "mana_armor": {
        "handler": "_evaluate_mana_armor",
    },
    "turn_stat": {
        "handler": "_evaluate_turn_stat",
    },
    "first_time_each_turn": {
        "handler": "_evaluate_first_time_each_turn",
    },
    "once_per_turn": {
        "handler": "_evaluate_once_per_turn",
    },
    "once_per_turn_available": {
        "handler": "_evaluate_once_per_turn_available",
    },
    "battle_result_matches": {
        "handler": "_evaluate_battle_result_matches",
        "validator": "_validate_battle_result_condition",
    },
    "choice_history_matches": {
        "handler": "_evaluate_choice_history_matches",
        "validator": "_validate_choice_history_condition",
    },
    "player_zone_count": {
        "handler": "_evaluate_player_zone_count",
        "validator": "_validate_player_zone_count_condition",
    },
    "own_creature_power_is_highest": {
        "handler": "_evaluate_own_creature_power_is_highest",
    },
    "turn_player_is": {
        "handler": "_evaluate_turn_player_is",
    },
    # Compatibility for existing structured JSON.
    "turn_player": {
        "handler": "_evaluate_turn_player_is",
    },
    "card_state": {
        "handler": "_evaluate_card_state",
    },
    "card_matches": {
        "handler": "_evaluate_card_matches",
        "validator": "_validate_card_filter_condition",
    },
}

CONDITION_TYPES = frozenset(CONDITION_DEFINITIONS)


def condition_handler_name(condition_type):
    definition = CONDITION_DEFINITIONS.get(condition_type)
    if definition is None:
        return None

    return definition.get("handler")


def condition_validator_name(condition_type):
    definition = CONDITION_DEFINITIONS.get(condition_type)
    if definition is None:
        return None

    return definition.get("validator")
