"""Event aliases shared by v2 ability implementations."""

from events.attack_event import AttackDeclaredEvent, AttackEndedEvent
from events.battle_event import (
    BattleDeclaredEvent,
    BattleEndEvent,
    BattleLostEvent,
    BattleStartEvent,
    BattleWonEvent,
)
from events.battle_zone_enter_event import BattleZoneEnterEvent
from events.block_event import BlockDeclaredEvent
from events.card_executed_event import CardExecutedEvent
from events.card_state_event import CardTappedEvent, CardUntappedEvent
from events.destroy_attempt_event import DestroyAttemptEvent
from events.destroy_event import DestroyEvent
from events.shield_break_attempt_event import ShieldBreakAttemptEvent
from events.shield_break_event import ShieldBreakEvent
from events.spell_cast_event import SpellCastEvent
from events.summon_event import SummonEvent
from events.target_event import CardChosenEvent
from events.turn_event import TurnEndEvent, TurnStartEvent
from events.zone_change_attempt_event import ZoneChangeAttemptEvent
from events.zone_change_event import ZoneChangeEvent


EVENT_ALIASES = {
    "battle": "battle_start",
    "battle_declared": "battle_declared",
    "battle_end": "battle_end",
    "battle_ended": "battle_end",
    "battle_lost": "battle_lost",
    "battle_start": "battle_start",
    "battle_started": "battle_start",
    "battle_won": "battle_won",
    "attack_ended": "attack_ended",
    "block_declared": "block_declared",
    "card_chosen": "card_chosen",
    "card_executed": "card_executed",
    "destroy": "destroy",
    "destroy_attempt": "destroy_attempt",
    "entered_battle_zone": "enter_battle",
    "cast": "spell_cast",
    "cast_spell": "spell_cast",
    "left_battle_zone": "zone_change",
    "shield_break": "shield_break",
    "shield_break_attempt": "shield_break_attempt",
    "shield_broken": "shield_break",
    "spell_cast": "spell_cast",
    "summon": "summon",
    "tap": "tap",
    "turn_end": "turn_end",
    "turn_ended": "turn_end",
    "turn_start": "turn_start",
    "turn_started": "turn_start",
    "untap": "untap",
    "zone_change": "zone_change",
    "zone_change_attempt": "zone_change_attempt",
    "zone_changed": "zone_change",
}

EVENT_TYPES = {
    "attack_declared": AttackDeclaredEvent,
    "attack_ended": AttackEndedEvent,
    "battle_declared": BattleDeclaredEvent,
    "battle_end": BattleEndEvent,
    "battle_lost": BattleLostEvent,
    "battle_start": BattleStartEvent,
    "battle_won": BattleWonEvent,
    "block_declared": BlockDeclaredEvent,
    "card_chosen": CardChosenEvent,
    "card_executed": CardExecutedEvent,
    "destroy": DestroyEvent,
    "destroy_attempt": DestroyAttemptEvent,
    "enter_battle": BattleZoneEnterEvent,
    "shield_break": ShieldBreakEvent,
    "shield_break_attempt": ShieldBreakAttemptEvent,
    "spell_cast": SpellCastEvent,
    "summon": SummonEvent,
    "tap": CardTappedEvent,
    "turn_end": TurnEndEvent,
    "turn_start": TurnStartEvent,
    "untap": CardUntappedEvent,
    "zone_change": ZoneChangeEvent,
    "zone_change_attempt": ZoneChangeAttemptEvent,
}


def event_name(
    value,
):
    if isinstance(
        value,
        list,
    ):
        return [
            event_name(item)
            for item in value
        ]

    return EVENT_ALIASES.get(
        value,
        value,
    )


def event_types(
    value,
):
    if isinstance(
        value,
        (list, tuple),
    ):
        if not value:
            raise ValueError("event list cannot be empty")

        return tuple(
            event_types(item)[0]
            for item in value
        )

    name = event_name(value)
    if name not in EVENT_TYPES:
        raise ValueError(
            f"Unknown v2 event: {value}"
        )

    return (
        EVENT_TYPES[name],
    )
