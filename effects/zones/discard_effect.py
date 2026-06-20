"""
プレイヤーが自分の手札から指定枚数を選んで墓地へ置く効果。
"""

from effects.base.base_effect import BaseEffect
from effects.zones.zone_effect_utils import resolve_player
from core.pending_cards import visible_cards
from zones.zone_type import ZoneType


class DiscardEffect(BaseEffect):

    def __init__(
        self,
        player,
        amount,
        game,
        optional=False,
        store_as=None,
        target_player="self",
    ):
        super().__init__()

        self.player = player
        self.amount = amount
        self.game = game
        self.optional = optional
        self.store_as = store_as
        self.target_player = target_player

    def resolve(self):
        discarded = []
        # 捨てる手札の持ち主＝選ぶプレイヤー。target_player="opponent" で
        # 「相手は自身の手札を1枚選び、捨てる」を表現する。
        actor = resolve_player(
            self.game,
            self.player,
            self.target_player,
        )

        for _ in range(self.amount):
            hand_cards = visible_cards(
                actor.hand.cards
            )

            if not hand_cards:
                break

            card = self.game.target_selector.select(
                actor,
                hand_cards,
                prompt="Choose a card to discard",
                can_skip=self.optional,
            )

            if card is None:
                break

            self.game.card_mover.move(
                card=card,
                owner=actor,
                from_zone=ZoneType.HAND,
                to_zone=ZoneType.GRAVEYARD,
                reason="discard",
            )

            discarded.append(card)

            print(
                f"{actor.name} discarded "
                f"{card.name}"
            )

        if self.store_as:
            if self.amount == 1:
                self.package_context[self.store_as] = (
                    discarded[0] if discarded else None
                )
            else:
                self.package_context[self.store_as] = discarded

        # 1枚でも捨てたら成功（True）。後続の connector: "then" 効果は
        # 何も捨てなかった場合に実行されない（「そうしたら」の表現）。
        return bool(discarded)
