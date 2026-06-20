"""Just Diver keyword ability."""

from abilities.base.base_ability import BaseAbility
from core.duration_type import DurationType
from effects.combat.temporary_just_diver_effect import (
    TemporaryJustDiverEffect,
)
from events.battle_zone_enter_event import BattleZoneEnterEvent


class JustDiverAbility(BaseAbility):

    def __init__(
        self,
        owner_card,
        game,
    ):
        super().__init__()
        self.owner_card = owner_card
        self.game = game
        self.event_manager = None

    def register(
        self,
        event_manager,
    ):
        self.event_manager = event_manager
        event_manager.subscribe(
            BattleZoneEnterEvent,
            self.on_event,
        )

    def unregister(
        self,
    ):
        if self.event_manager is None:
            return

        self.event_manager.unsubscribe(
            BattleZoneEnterEvent,
            self.on_event,
        )
        self.event_manager = None

    def on_event(
        self,
        event,
    ):
        if event.card != self.owner_card:
            return

        TemporaryJustDiverEffect(
            game=self.game,
            target_card=self.owner_card,
            duration_type=DurationType.UNTIL_START_OF_CONTROLLER_TURN,
        ).resolve()
