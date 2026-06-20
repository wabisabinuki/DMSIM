"""コントローラーのマナゾーンにあるカードの「マナの数字」を変更する常在型能力
（ManaNumberAbility）を定義。

マナの数字とは、そのカードをマナとしてタップしたときに生み出すマナの量を指す。
通常は1だが、この能力が有効な間は指定した値（例: 2）として扱われる。
ただし、必要な文明の数は軽減されない。各文明はそれぞれ別々のマナカードから
生み出す必要がある（コスト計算上の総量だけが変化する）。
"""

from abilities.base.continuous_ability import ContinuousAbility
from core.pending_cards import is_card_pending
from zones.zone_type import ZoneType


class ManaNumberAbility(ContinuousAbility):

    def __init__(
        self,
        owner_card,
        value=2,
        min_card_types=4,
    ):
        super().__init__()
        self.owner_card = owner_card
        self.value = value
        self.min_card_types = min_card_types

    def mana_value_for(
        self,
        mana_card,
        player,
    ):
        """対象のマナカードについて、この能力が定めるマナの数字を返す。

        この能力が有効でない、または対象が ``player`` のマナゾーンに
        属していない場合は ``None`` を返す（意見なし）。
        """

        if not self._is_active(player):
            return None

        if mana_card not in player.mana_zone.cards:
            return None

        return self.value

    def _is_active(
        self,
        player,
    ):
        if getattr(self.owner_card, "zone", None) != ZoneType.BATTLE:
            return False

        if is_card_pending(self.owner_card):
            return False

        if getattr(self.owner_card, "owner", None) is not player:
            return False

        return (
            self._count_card_types(player.mana_zone)
            >= self.min_card_types
        )

    def _count_card_types(
        self,
        mana_zone,
    ):
        types = set()

        for card in mana_zone.cards:
            if is_card_pending(card):
                continue

            for card_type in getattr(card, "card_types", ()):
                types.add(card_type)

        return len(types)


def build_mana_number_ability(
    spec,
    card,
    game,
):
    return ManaNumberAbility(
        owner_card=card,
        value=spec.get("value", 2),
        min_card_types=spec.get("min_card_types", 4),
    )
