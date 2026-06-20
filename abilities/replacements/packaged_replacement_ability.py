"""Packaged replacement ability built from reusable replacement steps."""

from abilities.base.replacement_ability import (
    ReplacementAbility,
)
from abilities.active_condition import active_if_matches
from core.condition_evaluator import ConditionEvaluator
from events.shield_break_attempt_event import (
    ShieldBreakAttemptEvent,
)
from events.destroy_attempt_event import DestroyAttemptEvent
from events.zone_change_attempt_event import (
    ZoneChangeAttemptEvent,
)
from events.zone_change_event import ZoneChangeEvent
from core.pending_cards import first_visible_card
from zones.zone_type import ZoneType


EVENT_TYPES = {
    "shield_break_attempt": ShieldBreakAttemptEvent,
    "destroy_attempt": DestroyAttemptEvent,
    "zone_change_attempt": ZoneChangeAttemptEvent,
}


class PackagedReplacementAbility(ReplacementAbility):

    def __init__(
        self,
        owner_card,
        game,
        event,
        condition,
        replace_effects,
        finalize_effects=None,
        active_if=None,
        cancel_event=True,
    ):
        super().__init__()
        self.owner_card = owner_card
        self.game = game
        self.event_name = event
        self.condition_name = condition
        self.replace_effects = replace_effects
        self.finalize_effects = finalize_effects or []
        self.active_if = active_if
        self.cancel_event = cancel_event
        self.pending_replacement_count = 0

    def applies(
        self,
        event,
    ):

        return (
            self._event_matches(event)
            and self._condition_matches(event)
            and self._is_active()
        )

    def _event_matches(
        self,
        event,
    ):

        event_type = self._event_type()
        if isinstance(
            event,
            event_type,
        ):
            return True

        return (
            self.event_name == "zone_change_attempt"
            and isinstance(event, DestroyAttemptEvent)
        )

    def replace(
        self,
        event,
    ):

        for effect_spec in self.replace_effects:
            applied = self._apply_replace_effect(
                effect_spec,
                event,
            )
            if applied is False:
                return False

        self.pending_replacement_count += 1

        if self.cancel_event:
            event.cancelled = True

    def finalize_pending_replacements(
        self,
    ):

        count = self.pending_replacement_count
        self.pending_replacement_count = 0

        if count <= 0:
            return

        for effect_spec in self.finalize_effects:
            self._apply_finalize_effect(
                effect_spec,
                count,
            )

    def _event_type(
        self,
    ):

        if self.event_name not in EVENT_TYPES:
            raise ValueError(
                f"Unknown replacement event: {self.event_name}"
            )

        return EVENT_TYPES[self.event_name]

    def _condition_matches(
        self,
        event,
    ):
        if isinstance(self.condition_name, dict):
            return ConditionEvaluator(
                self.game
            ).evaluate(
                self.condition_name,
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

        if self.condition_name == "breaker_self":
            return getattr(
                event,
                "breaker",
                None,
            ) == self.owner_card

        if self.condition_name == "self_battle_to_graveyard":
            return (
                getattr(event, "card", None) == self.owner_card
                and getattr(event, "from_zone", None) == ZoneType.BATTLE
                and getattr(event, "to_zone", None) == ZoneType.GRAVEYARD
                and self.owner_card.zone == ZoneType.BATTLE
            )

        if self.condition_name == "own_creature_leaves_battle":
            return (
                getattr(event, "owner", None) == self.owner_card.owner
                and getattr(event, "from_zone", None) == ZoneType.BATTLE
                and getattr(event, "to_zone", None) != ZoneType.BATTLE
                and self._is_creature(getattr(event, "card", None))
                and self.owner_card.zone == ZoneType.BATTLE
            )

        raise ValueError(
            f"Unknown replacement condition: {self.condition_name}"
        )

    def _is_active(
        self,
    ):
        return active_if_matches(
            self.active_if,
            self.owner_card,
            self.game,
        )

    def _apply_replace_effect(
        self,
        effect_spec,
        event,
    ):

        effect_id = _effect_id(effect_spec)

        if effect_id == "put_attempt_shield_on_bottom":
            self._put_attempt_shield_on_bottom(event)
            return

        if effect_id == "change_destination_to_hand":
            event.to_zone = ZoneType.HAND
            return

        if effect_id == "move_own_mana_to_graveyard":
            return self._move_own_mana_to_graveyard(
                effect_spec,
            )

        raise ValueError(
            f"Unknown replacement replace effect: {effect_id}"
        )

    def _apply_finalize_effect(
        self,
        effect_spec,
        replacement_count,
    ):

        effect_id = _effect_id(effect_spec)

        if effect_id == "draw_each_player":
            amount = self._resolve_amount(
                effect_spec.get("amount", 1),
                replacement_count,
            )
            self._draw_each_player_without_replacement(
                amount,
            )
            return

        raise ValueError(
            f"Unknown replacement finalize effect: {effect_id}"
        )

    def _resolve_amount(
        self,
        amount,
        replacement_count,
    ):

        if amount == "replacement_count":
            return replacement_count

        if isinstance(amount, dict):
            if amount.get("from") == "replacement_count":
                return replacement_count

        return amount

    def _put_attempt_shield_on_bottom(
        self,
        event,
    ):

        owner = event.player
        shield = event.shield_card
        shield_cards = self._shield_cards_for(
            event,
            owner,
            shield,
        )

        self.game.card_mover.pre_freeze_sources_for_many(
            shield_cards
        )

        self._remove_shield_cards(
            owner,
            shield_cards,
        )

        for shield_card in shield_cards:
            owner.deck.cards.append(shield_card)
            shield_card.zone = ZoneType.DECK
            shield_card.shield_face_up = False
            shield_card.zone_change_counter += 1

        self.game.state_based_actions.note_shield_left()
        self.game.state_based_actions.check_and_apply()

        for shield_card in shield_cards:
            self.game.event_manager.publish(
                ZoneChangeEvent(
                    card=shield_card,
                    owner=owner,
                    from_zone=ZoneType.SHIELD,
                    to_zone=ZoneType.DECK,
                    reason="shield_break_replacement",
                )
            )

    def _shield_cards_for(
        self,
        event,
        owner,
        shield,
    ):

        shield_cards = getattr(
            event,
            "shield_cards",
            None,
        )
        if shield_cards:
            return list(shield_cards)

        shield_cards = getattr(
            owner.shield_zone,
            "shield_cards",
            None,
        )
        if shield_cards is None:
            slot_cards = getattr(
                owner.shield_zone,
                "slot_cards",
                None,
            )
            if slot_cards is None:
                return [shield]

            cards = slot_cards(shield)
            return cards or [shield]

        cards = shield_cards(shield)
        if not cards:
            return [shield]

        return cards

    def _remove_shield_cards(
        self,
        owner,
        cards,
    ):

        remove_cards = getattr(
            owner.shield_zone,
            "remove_cards",
            None,
        )
        if remove_cards is not None:
            remove_cards(cards)
            return

        for card in cards:
            owner.shield_zone.remove(card)

    def _move_own_mana_to_graveyard(
        self,
        effect_spec,
    ):
        owner = self.owner_card.owner
        amount = int(effect_spec.get("amount", 1))
        if len(owner.mana_zone.cards) < amount:
            return False

        if effect_spec.get("optional", False):
            proceed = self.game.choice_manager.select(
                owner,
                [True, False],
                prompt=effect_spec.get(
                    "confirm_prompt",
                    "Put mana cards into graveyard for replacement?",
                ),
            )
            if not proceed:
                return False

        chosen = self.game.choice_manager.select(
            owner,
            list(owner.mana_zone.cards),
            prompt=effect_spec.get(
                "prompt",
                "Choose mana cards to put into graveyard",
            ),
            min_count=amount,
            max_count=amount,
        )
        if chosen is None:
            return False
        if not isinstance(chosen, list):
            chosen = [chosen]
        chosen = [
            card
            for card in chosen
            if card in owner.mana_zone.cards
        ]
        if len(chosen) < amount:
            return False

        for card in chosen[:amount]:
            moved = self.game.card_mover.move(
                card=card,
                owner=owner,
                from_zone=ZoneType.MANA,
                to_zone=ZoneType.GRAVEYARD,
                reason="replacement_cost",
                apply_replacements=False,
            )
            if not moved:
                return False

        return True

    def _is_creature(
        self,
        card,
    ):
        if card is None:
            return False

        return "CREATURE" in {
            card_type.name
            for card_type in getattr(card, "card_types", set())
        }

    def _draw_each_player_without_replacement(
        self,
        amount,
    ):

        for player in self.game.state.players:
            for _ in range(amount):
                self._draw_without_replacement(
                    player,
                )

    def _draw_without_replacement(
        self,
        player,
    ):

        card = first_visible_card(
            player.deck.cards
        )
        if card is None:
            self.game.state.declare_loss(
                player,
                reason="deck_out",
            )
            return False

        self.game.card_mover.pre_freeze_sources_for(
            card
        )

        player.deck.remove(card)
        if not player.deck.cards:
            self.game.state.declare_loss(
                player,
                reason="deck_out",
            )
        player.hand.add(card)
        card.zone = ZoneType.HAND
        card.zone_change_counter += 1

        self.game.event_manager.publish(
            ZoneChangeEvent(
                card=card,
                owner=player,
                from_zone=ZoneType.DECK,
                to_zone=ZoneType.HAND,
                reason="replacement_draw",
            )
        )

        return True


def _effect_id(effect_spec):
    effect_id = effect_spec.get("effect_id")
    if effect_id is not None:
        return effect_id

    return effect_spec["id"]
