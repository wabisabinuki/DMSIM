"""
シールドゾーンから手札へ加わる時にコストを支払わずに
即座にプレイできるシールド・トリガー能力（ShieldTriggerAbility）を定義。
"""

from abilities.base.base_ability import (
    BaseAbility
)

from events.zone_change_attempt_event import (
    ZoneChangeAttemptEvent
)

from core.protocols import ShieldTriggerContext

from ui.trigger_debug import (
    log_shield_trigger_enqueue,
)

from zones.zone_type import ZoneType


class ConditionalShieldTriggerAbility(BaseAbility):
    """コントローラーの盤面状況が条件を満たす時のみ機能するS・トリガー。"""

    def __init__(
        self,
        owner_card,
        game,
        condition=None,
    ):
        self.owner_card = owner_card
        self.game = game
        self.condition = condition
        super().__init__()

    def register(self, event_manager):
        self.event_manager = event_manager
        event_manager.subscribe(ZoneChangeAttemptEvent, self.on_event)

    def unregister(self):
        self.event_manager.unsubscribe(ZoneChangeAttemptEvent, self.on_event)

    def on_event(self, event):
        if event.card != self.owner_card:
            return
        if (
            event.from_zone != ZoneType.SHIELD
            or event.to_zone != ZoneType.HAND
        ):
            return
        if getattr(self.owner_card, "s_trigger_suppressed", False):
            return
        if not self._condition_met():
            return

        log_shield_trigger_enqueue(self.owner_card)
        self.game.shield_trigger_resolver.enqueue(self.owner_card)

    def _condition_met(self):
        if self.condition is None:
            return True
        from core.condition_evaluator import ConditionEvaluator
        evaluator = ConditionEvaluator(self.game)
        context = {
            "source_card": self.owner_card,
            "player": getattr(self.owner_card, "owner", None),
        }
        return evaluator.evaluate(self.condition, context)


class ShieldTriggerAbility(
    BaseAbility
):

    def __init__(
        self,
        owner_card,
        game: ShieldTriggerContext,
    ):

        self.owner_card = (
            owner_card
        )
        self.game = game

        super().__init__()

    def register(
        self,
        event_manager,
    ):

        self.event_manager = (
            event_manager
        )

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

        if getattr(
            self.owner_card,
            "s_trigger_suppressed",
            False,
        ):
            return

        log_shield_trigger_enqueue(
            self.owner_card
        )

        self.game.shield_trigger_resolver.enqueue(
            self.owner_card
        )
