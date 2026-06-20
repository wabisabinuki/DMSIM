"""
ターンの開始時や終了時など、特定のターンステップ進行に伴うトリガー解決を補助するクラス。
"""

from abilities.base.triggered_ability import (
    TriggeredAbility
)

from ui.trigger_debug import (
    log_turn_trigger_batch,
    log_turn_trigger_skip,
)

from zones.zone_type import ZoneType


class TurnTriggerResolver:
    """
    「ターンのはじめに」「ターンの終わりに」能力を
    参照時点のゾーンでフィルタし、1件ずつ解決する。
    """

    _REFERENCE_ZONES = (
        ZoneType.HAND,
        ZoneType.BATTLE,
        ZoneType.MANA,
        ZoneType.SHIELD,
    )

    def __init__(self, context):

        self.context = context

    def resolve(
        self,
        event_type,
        event,
        turn_player,
    ):

        queue = (
            self._build_queue(
                event_type,
                turn_player,
            )
        )

        log_turn_trigger_batch(
            event_type,
            turn_player,
            len(queue),
        )

        for (
            ability,
            ref_zone,
            ref_zcc,
        ) in queue:

            card = ability.owner_card

            if card.zone != ref_zone:
                log_turn_trigger_skip(
                    ability,
                    "参照時とゾーンが異なる",
                )
                continue

            if (
                card.zone_change_counter
                != ref_zcc
            ):
                log_turn_trigger_skip(
                    ability,
                    "参照時とカードが同一でない",
                )
                continue

            if not ability.can_trigger(event):
                log_turn_trigger_skip(
                    ability,
                    "ゾーン等により誘発不可",
                )
                continue

            if not ability.condition(event):
                log_turn_trigger_skip(
                    ability,
                    "誘発条件を満たさない",
                )
                continue

            self.context.trigger_manager\
                .process_trigger(
                    ability,
                    event,
                )

            self.context.game_loop.resolve()

    def _build_queue(
        self,
        event_type,
        turn_player,
    ):

        listeners = (
            self.context.event_manager
            .get_listeners(event_type)
        )

        queue = []

        for listener in listeners:

            if not hasattr(
                listener,
                "__self__",
            ):
                continue

            ability = listener.__self__

            if not isinstance(
                ability,
                TriggeredAbility,
            ):
                continue

            card = ability.owner_card

            if card.owner != turn_player:
                continue

            if card.zone not in (
                self._REFERENCE_ZONES
            ):
                continue

            queue.append(
                (
                    ability,
                    card.zone,
                    card.zone_change_counter,
                )
            )

        return queue
