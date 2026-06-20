"""
特定のイベントを監視し、条件を満たしたときに即座に効果（Effect）を生成して解決キューに送るトリガー能力の基底クラス。
"""

from abilities.base.base_ability import (
    BaseAbility
)

from core.protocols import TriggerContext
from core.pending_cards import is_card_pending
from core.seal_utils import is_ignored_by_seal, is_seal_card
from zones.zone_type import ZoneType


class TriggeredAbility(
    BaseAbility
):

    def __init__(
        self,
        event_type,
        condition,
        game: TriggerContext,
    ):

        super().__init__()

        self.event_types = self._normalize_event_types(
            event_type
        )
        self.event_type = self.event_types[0]

        self.condition = (
            condition
        )

        self.game = game

        self.register_zcc = None

    def register(
        self,
        event_manager,
    ):

        self.event_manager = (
            event_manager
        )

        self.register_zcc = (
            self.owner_card
                .zone_change_counter
        )

        for event_type in self.event_types:
            event_manager.subscribe(
                event_type,
                self.on_event,
            )

    def unregister(
        self,
    ):

        for event_type in self.event_types:
            self.event_manager.unsubscribe(
                event_type,
                self.on_event,
            )

    def can_trigger(
        self,
        event,
    ):

        owner_card = getattr(self, "owner_card", None)
        if owner_card is None:
            return True

        if is_card_pending(owner_card):
            return False

        if is_seal_card(owner_card) or is_ignored_by_seal(owner_card):
            return False

        if getattr(
            owner_card,
            "is_evolution_source",
            False,
        ):
            return False

        active_zones = self.active_zones if self.active_zones else [ZoneType.BATTLE]
        return getattr(owner_card, "zone", None) in active_zones

    def on_event(
        self,
        event,
    ):

        if not self.can_trigger(event):
            return

        if not self.condition(event):
            return

        self.game.trigger_manager.process_trigger(
            self,
            event,
        )

    def execute(
        self,
        event,
    ):

        pass

    def __str__(self):

        return (
            self.__class__.__name__
        )

    def _normalize_event_types(
        self,
        event_type,
    ):
        if isinstance(
            event_type,
            (list, tuple),
        ):
            return tuple(event_type)

        return (
            event_type,
        )
