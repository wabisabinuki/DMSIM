"""Escape keyword replacement ability."""

from abilities.base.replacement_ability import ReplacementAbility
from events.destroy_attempt_event import DestroyAttemptEvent
from zones.zone_type import ZoneType


class EscapeAbility(ReplacementAbility):

    def __init__(
        self,
        owner_card,
        game,
    ):
        super().__init__()
        self.owner_card = owner_card
        self.game = game

    def applies(
        self,
        event,
    ):
        return (
            isinstance(event, DestroyAttemptEvent)
            and event.card == self.owner_card
            and self.owner_card.zone == ZoneType.BATTLE
            and bool(self._shield_options())
        )

    def replace(
        self,
        event,
    ):
        shield = self.game.target_selector.select(
            self.owner_card.owner,
            self._shield_options(),
            prompt="Choose a shield for Escape",
            can_skip=True,
        )
        if shield is None:
            return False

        shield_cards = self._shield_cards_for(shield)
        # S・トリガーの無効化はこの移動の解決中のみ。移動後は必ず元へ戻す。
        previous_suppressed = [
            (
                shield_card,
                getattr(
                    shield_card,
                    "s_trigger_suppressed",
                    False,
                ),
            )
            for shield_card in shield_cards
        ]
        for shield_card in shield_cards:
            shield_card.s_trigger_suppressed = True

        try:
            moved = self.game.card_mover.move(
                card=shield,
                owner=shield.owner,
                from_zone=ZoneType.SHIELD,
                to_zone=ZoneType.HAND,
                reason="escape",
            )
        finally:
            for shield_card, was_suppressed in previous_suppressed:
                shield_card.s_trigger_suppressed = was_suppressed

        if not moved:
            return False

        event.cancelled = True
        return True

    def _shield_options(
        self,
    ):
        visible_shields = getattr(
            self.owner_card.owner.shield_zone,
            "visible_shields",
            None,
        )
        if visible_shields is not None:
            return visible_shields()

        return list(self.owner_card.owner.shield_zone.cards)

    def _shield_cards_for(
        self,
        shield,
    ):

        shield_zone = self.owner_card.owner.shield_zone
        shield_cards = getattr(
            shield_zone,
            "shield_cards",
            None,
        )
        if shield_cards is None:
            slot_cards = getattr(
                shield_zone,
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
