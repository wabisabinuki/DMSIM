"""フィールド。エレメントとして手札からバトルゾーンに「展開」する。

展開するとバトルゾーンに横向き（反時計回り90度＝アンタップ状態）で置かれる。
CLI では向きは表示上の概念で、ゲーム動作には影響しないため tapped=False とする。

派生タイプ D2フィールド（special_types に "d2"）は「お互いの場に合計1枚」しか
存在できず、D2フィールドが展開されたとき状況起因処理（StateBasedActions の
_apply_d2_field_supersede）で先にあったD2フィールドが破壊される。発火は展開時のみ。
"""

from actions.use_card_action import UseCardAction
from cards.card import Card, CardType
from core.pending_cards import (
    begin_pending,
    end_pending,
    is_card_pending,
)
from events.card_executed_event import CardExecutedEvent
from zones.zone_type import ZoneType


class FieldCard(Card):

    def __init__(
        self,
        name,
        cost,
        civilizations,
        card_types=None,
        special_types=None,
        name_ja=None,
        effect_name_ja=None,
        effect_texts_ja=None,
        game=None,
    ):
        super().__init__(
            name=name,
            cost=cost,
            civilizations=civilizations,
            card_types=card_types or (CardType.FIELD,),
            special_types=special_types,
            name_ja=name_ja,
            effect_name_ja=effect_name_ja,
            effect_texts_ja=effect_texts_ja,
        )
        # Dスイッチ（D2フィールド）の「上下逆さま」状態。展開中は1度だけ反転でき、
        # バトルゾーンを離れるとリセットされる（再展開すれば再び使える）。
        self.d_switch_flipped = False

    def can_exist_in_battle_alone(
        self,
    ):
        return True

    def reset_battle_state(
        self,
    ):
        # バトルゾーンを離れる時に CardMover から呼ばれる。
        self.tapped = False
        # 再展開すれば Dスイッチを再び使えるよう、離脱時にリセットする。
        self.d_switch_flipped = False

    # --- 展開（手札 → バトルゾーンに単体で出す） ---

    def can_use(
        self,
        game,
        player,
        ignore_cost=False,
    ):
        if self.owner is not player:
            return False

        if getattr(self, "zone", None) != ZoneType.HAND:
            return False

        if is_card_pending(self):
            return False

        if not ignore_cost and not player.can_play(self):
            return False

        return True

    def use(
        self,
        game,
        player,
        ignore_cost=False,
    ):
        if not self.can_use(
            game,
            player,
            ignore_cost=ignore_cost,
        ):
            return False

        if not ignore_cost:
            if not player.tap_mana(
                self._current_cost(player, game),
                spending_card=self,
                choice_manager=(
                    game.choice_manager
                ),
            ):
                return False

        from_zone = (
            getattr(self, "zone", None)
            or ZoneType.HAND
        )
        pending_started = begin_pending(
            self,
            reason="deploy_field",
        )

        try:
            moved = game.card_mover.move(
                card=self,
                owner=player,
                from_zone=from_zone,
                to_zone=ZoneType.BATTLE,
                reason="deploy_field",
            )
            if moved:
                # 横向き（アンタップ）でバトルゾーンに置かれる。
                self.tapped = False
                game.event_manager.publish(
                    CardExecutedEvent(
                        player=player,
                        card=self,
                        from_zone=from_zone,
                        ignore_cost=ignore_cost,
                    )
                )
                # D2フィールドは展開時に状況起因処理を武装する。
                # 展開（use）以外の場登場ではこの経路を通らないため発火しない。
                if is_d2_field(self):
                    game.state_based_actions.note_d2_field_deployed(
                        self
                    )
                return True

            return False
        finally:
            if pending_started and is_card_pending(self):
                end_pending(self)

    def play_without_cost(
        self,
        game,
        player,
    ):
        return self.use(
            game,
            player,
            ignore_cost=True,
        )

    def get_available_actions(
        self,
        game,
        player,
    ):
        if self.can_use(game, player):
            return [
                UseCardAction(
                    player,
                    self,
                )
            ]

        return []

    def _current_cost(
        self,
        player,
        game,
    ):
        try:
            return self.get_current_cost(
                player=player,
                game=game,
            )
        except TypeError:
            return self.get_current_cost()


def is_d2_field(
    card,
):
    """D2フィールド（フィールドかつ special_type "d2"）かどうかを返す。"""

    return (
        card.has_card_type(CardType.FIELD)
        and card.has_special_type("d2")
    )
