"""G Strike keyword ability."""

from abilities.base.base_ability import BaseAbility
from events.zone_change_attempt_event import ZoneChangeAttemptEvent
from ui.trigger_debug import log_g_strike_enqueue
from zones.zone_type import ZoneType


class GStrikeAbility(BaseAbility):

    def __init__(
        self,
        owner_card,
        game,
    ):
        self.owner_card = owner_card
        self.game = game
        super().__init__()

    def register(
        self,
        event_manager,
    ):
        self.event_manager = event_manager
        event_manager.subscribe(
            ZoneChangeAttemptEvent,
            self.on_event,
        )

    def unregister(
        self,
    ):
        self.event_manager.unsubscribe(
            ZoneChangeAttemptEvent,
            self.on_event,
        )

    def on_event(
        self,
        event,
    ):
        if event.card != self.owner_card:
            return

        if (
            event.from_zone != ZoneType.SHIELD
            or event.to_zone != ZoneType.HAND
        ):
            return

        log_g_strike_enqueue(
            self.owner_card
        )
        self.game.shield_trigger_resolver.enqueue_g_strike(
            self.owner_card,
            self,
        )
