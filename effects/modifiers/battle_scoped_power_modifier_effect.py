"""Power modifier that is removed when the current battle ends."""

from effects.base.base_effect import BaseEffect
from events.battle_event import BattleEndEvent
from events.zone_change_event import ZoneChangeEvent
from modifiers.power_modifier import PowerModifier
from core.pending_cards import is_card_pending
from zones.zone_type import ZoneType


class BattleScopedPowerModifierEffect(BaseEffect):
    """Apply a power modifier until the related battle ends."""

    def __init__(
        self,
        source_card,
        target_card,
        amount,
        game,
        battle_id=None,
    ):
        super().__init__()
        self.source_card = source_card
        self.target_card = target_card
        self.amount = amount
        self.game = game
        self.battle_id = battle_id
        self.applied_modifier = None
        self._registered = False

    def resolve(self):
        if (
            self.target_card is None
            or getattr(self.target_card, "zone", None) != ZoneType.BATTLE
            or is_card_pending(self.target_card)
        ):
            return False

        modifier = PowerModifier(
            self.amount,
            source=self.source_card,
        )
        modifier.source_effect = self
        self.target_card.power_modifiers.append(modifier)
        self.applied_modifier = modifier
        self._subscribe()
        return True

    def _subscribe(self):
        if self._registered:
            return

        self.game.event_manager.subscribe(
            BattleEndEvent,
            self._on_battle_end,
        )
        self.game.event_manager.subscribe(
            ZoneChangeEvent,
            self._on_zone_change,
        )
        self._registered = True

    def _on_battle_end(
        self,
        event,
    ):
        if self.battle_id is not None and event.battle_id != self.battle_id:
            return

        if (
            self.battle_id is None
            and self.target_card
            not in (
                getattr(event, "attacker", None),
                getattr(event, "defender", None),
            )
        ):
            return

        self.unapply()

    def _on_zone_change(
        self,
        event,
    ):
        if event.card is not self.target_card:
            return

        if event.from_zone != ZoneType.BATTLE:
            return

        self.unapply()

    def unapply(self):
        if self.applied_modifier in getattr(
            self.target_card,
            "power_modifiers",
            (),
        ):
            self.target_card.power_modifiers.remove(
                self.applied_modifier
            )

        if self._registered:
            self.game.event_manager.unsubscribe(
                BattleEndEvent,
                self._on_battle_end,
            )
            self.game.event_manager.unsubscribe(
                ZoneChangeEvent,
                self._on_zone_change,
            )
            self._registered = False

    def __str__(self):
        return (
            "BattleScopedPowerModifierEffect("
            f"{self.amount:+d})"
        )
