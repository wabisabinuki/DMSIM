"""自分の山札の上から N 枚を指定ゾーンへ移す効果（マナ加速などの汎用部品）。

「山札の上から2枚をマナゾーンに置いてもよい」のような、枚数が固定で位置選択を伴わない
山札トップ操作に使う。``optional`` のときは all-or-nothing で実行可否を1度だけ尋ねる
（テキスト「N枚を〜してもよい」型。枚数を選ばせる「最大N枚」とは別物）。
"""

from effects.base.base_effect import BaseEffect
from effects.zones.zone_effect_utils import parse_zone
from zones.zone_type import ZoneType


class MoveDeckTopEffect(BaseEffect):

    def __init__(
        self,
        game,
        player,
        amount,
        to_zone,
        optional=False,
        tapped=None,
        prompt=None,
    ):
        super().__init__()
        self.game = game
        self.player = player
        self.amount = amount
        self.to_zone = to_zone
        self.optional = optional
        self.tapped = tapped
        self.prompt = prompt

    def resolve(self):
        to_zone = parse_zone(self.to_zone)
        pile = list(self.player.deck.cards[: self.amount])
        if not pile:
            return False

        if self.optional and not self._confirm(len(pile)):
            return False

        moved_any = False
        for card in pile:
            moved = self.game.card_mover.move(
                card=card,
                owner=self.player,
                from_zone=ZoneType.DECK,
                to_zone=to_zone,
                reason="move_deck_top",
            )
            if moved:
                moved_any = True
                if self.tapped is not None:
                    card.tapped = bool(self.tapped)

        return moved_any

    def _confirm(self, count):
        prompt = self.prompt or (
            f"山札の上から{count}枚を{parse_zone(self.to_zone).name}へ置きますか？"
        )
        return bool(
            self.game.choice_manager.select(
                self.player,
                [True, False],
                prompt,
            )
        )
