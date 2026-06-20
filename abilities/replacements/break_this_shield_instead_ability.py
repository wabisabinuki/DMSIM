"""Replace a shield break by breaking this shield instead."""

from abilities.base.replacement_ability import ReplacementAbility
from core.pending_cards import is_card_pending
from events.shield_break_attempt_event import ShieldBreakAttemptEvent
from zones.zone_type import ZoneType


class BreakThisShieldInsteadAbility(ReplacementAbility):
    replacement_priority = 10

    def __init__(
        self,
        owner_card,
        game,
        optional=True,
        prompt=None,
    ):
        super().__init__()
        self.owner_card = owner_card
        self.game = game
        self.optional = optional
        self.prompt = prompt or "かわりにこのシールドをブレイクしますか？"

    def applies(
        self,
        event,
    ):
        if not isinstance(
            event,
            ShieldBreakAttemptEvent,
        ):
            return False

        if not self._is_active():
            return False

        if event.player is not self.owner_card.owner:
            return False

        own_slot = self._own_slot()
        event_slot = self._slot_for(
            event.shield_card,
        )
        if own_slot is None or event_slot is None:
            return False

        if own_slot is not event_slot:
            return True

        return event.shield_card is self._this_shield()

    def replace(
        self,
        event,
    ):
        if self.optional:
            proceed = self.game.choice_manager.select(
                self.owner_card.owner,
                [
                    True,
                    False,
                ],
                prompt=self.prompt,
            )
            if not proceed:
                return False

        shield = self._this_shield()
        if shield is None:
            return False

        shield_cards = self._shield_cards_for(
            shield,
        )
        if not shield_cards:
            return False

        event.shield_card = shield
        event.card = shield
        event.shield_cards = shield_cards
        event.consume_remaining_breaks = True
        return True

    def _is_active(
        self,
    ):
        return (
            self.game is not None
            and self.owner_card.zone == ZoneType.SHIELD
            and self.owner_card.shield_face_up
            and not is_card_pending(self.owner_card)
        )

    def _own_slot(
        self,
    ):
        owner = self.owner_card.owner
        if owner is None:
            return None

        return self._slot_for(
            self.owner_card,
        )

    def _slot_for(
        self,
        card,
    ):
        owner = self.owner_card.owner
        slot_for = getattr(
            owner.shield_zone,
            "slot_for",
            None,
        )
        if slot_for is None:
            return None

        return slot_for(card)

    def _this_shield(
        self,
    ):
        slot = self._own_slot()
        if slot is None:
            return None

        visible_shield_card = getattr(
            slot,
            "visible_shield_card",
            None,
        )
        if visible_shield_card is None:
            return self.owner_card

        return visible_shield_card()

    def _shield_cards_for(
        self,
        shield,
    ):
        owner = self.owner_card.owner
        shield_cards = getattr(
            owner.shield_zone,
            "shield_cards",
            None,
        )
        if shield_cards is not None:
            cards = shield_cards(shield)
            return cards or [shield]

        slot_cards = getattr(
            owner.shield_zone,
            "slot_cards",
            None,
        )
        if slot_cards is not None:
            cards = slot_cards(shield)
            return cards or [shield]

        return [shield]
