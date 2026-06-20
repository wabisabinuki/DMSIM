"""
JSON定義からイベント・条件・効果を組み立てる汎用誘発型能力。
"""

from abilities.base.triggered_ability import TriggeredAbility
from abilities.active_condition import active_if_matches
from core.condition_evaluator import ConditionEvaluator
from effects import PackagedEffect, build_effects, is_creature_card
from events.attack_event import AttackDeclaredEvent
from events.attack_event import AttackEndedEvent
from events.battle_event import (
    BattleEndEvent,
    BattleLostEvent,
    BattleStartEvent,
    BattleWonEvent,
)
from events.block_event import BlockDeclaredEvent
from events.battle_zone_enter_event import BattleZoneEnterEvent
from events.card_state_event import CardTappedEvent, CardUntappedEvent
from events.destroy_event import DestroyEvent
from events.shield_break_event import ShieldBreakEvent
from events.spell_cast_event import SpellCastEvent
from events.summon_event import SummonEvent
from events.target_event import CardChosenEvent
from events.turn_event import TurnEndEvent, TurnStartEvent
from events.zone_change_event import ZoneChangeEvent
from zones.zone_type import ZoneType
from core.pending_cards import is_card_pending
from core.seal_utils import is_ignored_by_seal, is_seal_card


EVENT_TYPES = {
    "attack_declared": AttackDeclaredEvent,
    "attack_ended": AttackEndedEvent,
    "battle_end": BattleEndEvent,
    "battle_lost": BattleLostEvent,
    "battle_start": BattleStartEvent,
    "battle_won": BattleWonEvent,
    "block_declared": BlockDeclaredEvent,
    "card_chosen": CardChosenEvent,
    "enter_battle": BattleZoneEnterEvent,
    "destroy": DestroyEvent,
    "shield_break": ShieldBreakEvent,
    "spell_cast": SpellCastEvent,
    "summon": SummonEvent,
    "tap": CardTappedEvent,
    "turn_end": TurnEndEvent,
    "turn_start": TurnStartEvent,
    "untap": CardUntappedEvent,
    "zone_change": ZoneChangeEvent,
}


ZONE_TYPES = {
    "battle": ZoneType.BATTLE,
    "deck": ZoneType.DECK,
    "graveyard": ZoneType.GRAVEYARD,
    "hand": ZoneType.HAND,
    "mana": ZoneType.MANA,
    "shield": ZoneType.SHIELD,
}


class GenericTriggeredAbility(TriggeredAbility):

    def __init__(
        self,
        owner_card,
        game,
        event,
        condition,
        effects,
        label=None,
        resolution="packaged",
        active_if=None,
        active_zones=None,
        ignore_source_continuity=False,
    ):
        self.owner_card = owner_card
        self.event_name = event
        self.condition_name = condition
        self.effect_specs = effects
        self.label = label
        self.resolution = resolution
        self.active_if = active_if
        self.any_zone = active_zones == "any"
        self.ignore_source_continuity = bool(
            ignore_source_continuity
        )
        self._first_time_turns = {}

        super().__init__(
            self._event_types(event),
            self._condition(condition),
            game,
        )

        if active_zones and active_zones != "any":
            self.active_zones = [
                ZONE_TYPES[zone]
                for zone in active_zones
            ]

    def can_trigger(
        self,
        event,
    ):
        if getattr(
            self.owner_card,
            "is_evolution_source",
            False,
        ):
            return False

        if is_card_pending(self.owner_card):
            return False

        if (
            is_seal_card(self.owner_card)
            or is_ignored_by_seal(self.owner_card)
        ):
            return False

        if self.any_zone:
            return self._is_active()

        return (
            self._is_active()
            and super().can_trigger(event)
        )

    def _is_active(
        self,
    ):
        return active_if_matches(
            self.active_if,
            self.owner_card,
            self.game,
        )

    def create_effects(
        self,
        event,
    ):
        effects = build_effects(
            self.effect_specs,
            self.game,
            self._effect_player(event),
            source_card=self.owner_card,
        )

        if self.resolution == "separate":
            return effects

        effect = PackagedEffect(
            effects,
            label=self.label,
        )
        effect.ignore_source_continuity = (
            self.ignore_source_continuity
        )
        return [
            effect
        ]

    def _event_types(
        self,
        event,
    ):
        if isinstance(
            event,
            (list, tuple),
        ):
            if not event:
                raise ValueError("Trigger event list cannot be empty")

            return tuple(
                self._event_types(item)[0]
                for item in event
            )

        if event not in EVENT_TYPES:
            raise ValueError(f"Unknown trigger event: {event}")

        return (
            EVENT_TYPES[event],
        )

    def _condition(
        self,
        condition,
    ):
        if isinstance(
            condition,
            (list, tuple),
        ):
            return self._all_conditions(condition)

        if isinstance(
            condition,
            dict,
        ):
            if "type" in condition:
                return self._structured_condition(condition)
            if "all" in condition:
                return self._all_conditions(condition["all"])
            if "any" in condition:
                return self._any_conditions(condition["any"])
            raise ValueError(f"Unknown trigger condition object: {condition}")

        if condition == "first_time_each_turn":
            return self._first_time_each_turn(
                "first_time_each_turn"
            )
        if condition == "self":
            return self._is_self_event
        if condition == "controller":
            return self._is_controller_event
        if condition == "opponent_creatures":
            return self._is_opponent_creature_event
        if condition == "opponent":
            return self._is_opponent_event
        if condition == "opponent_chose_this":
            return self._is_opponent_chose_self_event
        if condition == "own_creature":
            return self._is_own_creature_event
        if condition == "controller_draw":
            return self._is_controller_draw_event
        if condition == "controller_to_shield":
            return self._is_controller_to_shield_event
        if condition == "to_opponent_graveyard":
            return self._is_to_opponent_graveyard_event
        if condition == "any":
            return lambda event: True

        raise ValueError(f"Unknown trigger condition: {condition}")

    def _structured_condition(
        self,
        condition,
    ):
        def matches(event):
            return ConditionEvaluator(
                self.game
            ).evaluate(
                condition,
                {
                    "game": self.game,
                    "player": self.owner_card.owner,
                    "controller": self.owner_card.owner,
                    "event_player": getattr(event, "player", None),
                    "source_card": self.owner_card,
                    "event": event,
                    "ability": self,
                },
            )

        return matches

    def _all_conditions(
        self,
        conditions,
    ):
        condition_names = self._condition_names(
            conditions
        )
        predicates = [
            self._condition(condition)
            for condition in condition_names
            if condition != "first_time_each_turn"
        ]
        first_time = (
            "first_time_each_turn"
            in condition_names
        )

        def matches(event):
            if not all(
                predicate(event)
                for predicate in predicates
            ):
                return False

            if first_time:
                return self._first_time_each_turn(
                    condition_names
                )(event)

            return True

        return matches

    def _any_conditions(
        self,
        conditions,
    ):
        predicates = [
            self._condition(condition)
            for condition in self._condition_names(
                conditions
            )
        ]
        return lambda event: any(
            predicate(event)
            for predicate in predicates
        )

    def _condition_names(
        self,
        conditions,
    ):
        if isinstance(
            conditions,
            str,
        ):
            return (conditions,)

        return tuple(conditions)

    def _first_time_each_turn(
        self,
        key,
    ):
        def matches(event):
            turn = self.game.state.turn
            if self._first_time_turns.get(key) == turn:
                return False

            self._first_time_turns[key] = turn
            return True

        return matches

    def _is_self_event(
        self,
        event,
    ):
        return (
            getattr(event, "card", None) == self.owner_card
            or
            getattr(event, "shield_card", None) == self.owner_card
            or
            getattr(event, "attacker", None) == self.owner_card
            or
            getattr(event, "target", None) == self.owner_card
            or
            getattr(event, "blocker", None) == self.owner_card
        )

    def _is_controller_event(
        self,
        event,
    ):
        return getattr(
            event,
            "player",
            None,
        ) == self.owner_card.owner

    def _is_opponent_creature_event(
        self,
        event,
    ):
        return (
            getattr(
                event,
                "player",
                None,
            )
            is not None
            and getattr(
                event,
                "player",
                None,
            ) != self.owner_card.owner
            and is_creature_card(
                getattr(
                    event,
                    "card",
                    None,
                )
            )
        )

    def _is_opponent_event(
        self,
        event,
    ):
        return (
            getattr(
                event,
                "player",
                None,
            )
            is not None
            and getattr(
                event,
                "player",
                None,
            ) != self.owner_card.owner
        )

    def _is_opponent_chose_self_event(
        self,
        event,
    ):
        return (
            self._is_self_event(event)
            and self._is_opponent_event(event)
        )

    def _is_own_creature_event(
        self,
        event,
    ):
        return (
            self._is_controller_event(event)
            and is_creature_card(
                getattr(
                    event,
                    "card",
                    None,
                )
            )
        )

    def _is_controller_draw_event(
        self,
        event,
    ):
        return (
            getattr(
                event,
                "owner",
                None,
            ) == self.owner_card.owner
            and getattr(
                event,
                "from_zone",
                None,
            ) == ZoneType.DECK
            and getattr(
                event,
                "to_zone",
                None,
            ) == ZoneType.HAND
            and getattr(
                event,
                "reason",
                None,
            )
            in (
                "draw",
                "replacement_draw",
            )
        )

    def _is_controller_to_shield_event(
        self,
        event,
    ):
        return (
            getattr(
                event,
                "owner",
                None,
            ) == self.owner_card.owner
            and getattr(
                event,
                "to_zone",
                None,
            ) == ZoneType.SHIELD
        )

    def _is_to_opponent_graveyard_event(
        self,
        event,
    ):
        return (
            getattr(
                event,
                "owner",
                None,
            )
            is not None
            and getattr(
                event,
                "owner",
                None,
            ) != self.owner_card.owner
            and getattr(
                event,
                "to_zone",
                None,
            ) == ZoneType.GRAVEYARD
        )

    def _effect_player(
        self,
        event,
    ):
        if self.condition_name == "opponent_chose_this":
            return self.owner_card.owner

        if self.condition_name == "opponent_creatures":
            return self.owner_card.owner

        return getattr(
            event,
            "player",
            self.owner_card.owner,
        )
