"""
破壊アクションを実行するハンドラ。

単体破壊・複数破壊のいずれも、内部的には「対象カードのリスト」を
2フェーズで処理する。

  フェーズ1（試行・置換）:
    対象すべてに対して DestroyAttemptEvent を発行し、置換効果を適用する。
    この時点ではどのカードも移動させない。これにより、置換効果や
    条件評価は「どのカードもまだバトルゾーンにいる」同時状態の盤面を見る。

  フェーズ2（確定・移動）:
    置換されたカードは置換先へ移動、キャンセルされたカードは何もしない。
    実際に破壊されるカード群に対して DestroyEvent をまとめて発行してから、
    一括で墓地へ移動する。

単体破壊は [card] を渡すだけで、同じ経路を通る。
"""

from core.action_handlers.base_action_handler import (
    BaseActionHandler
)

from events.destroy_event import (
    DestroyEvent
)

from events.destroy_attempt_event import (
    DestroyAttemptEvent
)

from core.pending_cards import is_card_pending
from core.seal_utils import is_ignored_by_seal

from zones.zone_type import (
    ZoneType
)

from ui.card_display import format_card_name


class DestroyActionHandler(
    BaseActionHandler
):

    def process(
        self,
        action,
    ):

        cards = getattr(
            action,
            "cards",
            None,
        )
        if cards is None:
            cards = [action.target_card]

        self.destroy_cards(cards)

    def destroy_cards(
        self,
        cards,
    ):

        targets = self._collect_destroyable(cards)
        if not targets:
            return

        # フェーズ1: 対象すべての試行イベント発行＋置換適用（移動はしない）。
        # 他カードの置換の副作用で既にバトルゾーンを離れたカードは飛ばす。
        attempts = [
            self._attempt_destroy(card)
            for card in targets
            if card.zone == ZoneType.BATTLE
            and not is_card_pending(card)
        ]

        # フェーズ2: 置換結果の確定と一括破壊
        self._finalize_attempts(attempts)

    def _collect_destroyable(
        self,
        cards,
    ):

        targets = []
        seen = set()

        for card in cards:
            if card is None or id(card) in seen:
                continue
            seen.add(id(card))

            if (
                card.zone != ZoneType.BATTLE
                or is_card_pending(card)
                or is_ignored_by_seal(card)
            ):
                continue

            targets.append(card)

        return targets

    def _attempt_destroy(
        self,
        card,
    ):

        attempt_event = DestroyAttemptEvent(
            card,
            card.owner,
        )

        self.game_controller\
            .replacement_manager\
            .apply(
                attempt_event
            )

        return attempt_event

    def _finalize_attempts(
        self,
        attempts,
    ):

        to_destroy = []

        for attempt_event in attempts:

            if attempt_event.cancelled:
                continue

            if attempt_event.replaced:
                self._apply_replacement_move(
                    attempt_event
                )
                continue

            to_destroy.append(attempt_event)

        self._destroy_finalized(to_destroy)

    def _apply_replacement_move(
        self,
        attempt_event,
    ):

        self.game_controller\
            .card_mover.move(
                card=attempt_event.card,
                owner=attempt_event.owner,
                from_zone=(
                    attempt_event.from_zone
                ),
                to_zone=(
                    attempt_event.to_zone
                ),
                reason="destroy_replacement",
                apply_replacements=False,
            )

    def _destroy_finalized(
        self,
        attempts,
    ):

        # 置換適用後、なお破壊が確定したカード群。
        # フェーズ1中の副作用（他カードの置換コスト等）で既に
        # バトルゾーンを離れたものは除外する。
        confirmed = [
            attempt_event
            for attempt_event in attempts
            if attempt_event.card.zone == ZoneType.BATTLE
            and not is_card_pending(attempt_event.card)
        ]

        if not confirmed:
            return

        # 破壊は同時。まず全カードの DestroyEvent を発行してから移動する。
        for attempt_event in confirmed:
            self.game_controller\
                .event_manager\
                .publish(
                    DestroyEvent(
                        attempt_event.card,
                        attempt_event.owner,
                    )
                )

        for attempt_event in confirmed:
            card = attempt_event.card

            if (
                card.zone != ZoneType.BATTLE
                or is_card_pending(card)
            ):
                continue

            self.game_controller\
                .card_mover.move(
                    card=card,
                    owner=attempt_event.owner,
                    from_zone=ZoneType.BATTLE,
                    to_zone=ZoneType.GRAVEYARD,
                    reason="destroy",
                    apply_replacements=False,
                )

            print(
                f"{format_card_name(card)} "
                f"was destroyed"
            )
