"""コントローラーのマナゾーンにあるカードへ「すべての文明」を付与する常在型能力
（ManaAllCivilizationsAbility）を定義。

``card.civilizations`` は書き換えない。``Player.mana_civilizations(card)`` が
バトルゾーンの常在能力の ``mana_civilizations_for(card, player)`` を参照し、
支払い計算や ``has_civilization`` 判定のときだけ全文明扱いにする。

発生源がバトルゾーンを離れた場合、保留・封印・無視状態の場合は効果を失う。
"""

from abilities.base.continuous_ability import ContinuousAbility
from cards.card import Civilization
from core.pending_cards import is_card_pending
from core.seal_utils import is_ignored_by_seal, is_seal_card
from zones.zone_type import ZoneType


ALL_CIVILIZATIONS = (
    Civilization.FIRE
    | Civilization.WATER
    | Civilization.NATURE
    | Civilization.LIGHT
    | Civilization.DARKNESS
)


class ManaAllCivilizationsAbility(ContinuousAbility):

    def __init__(
        self,
        owner_card,
    ):
        super().__init__()
        self.owner_card = owner_card

    def mana_civilizations_for(
        self,
        mana_card,
        player,
    ):
        """``player`` のマナゾーンにある ``mana_card`` が追加で提供できる文明ビット
        を返す（この能力が有効なら全文明）。

        この能力が有効でない、または対象が ``player`` のマナゾーンに属していない
        場合は ``None`` を返す（意見なし）。
        """

        if not self._is_active(player):
            return None

        if mana_card not in player.mana_zone.cards:
            return None

        return ALL_CIVILIZATIONS

    def _is_active(
        self,
        player,
    ):
        owner = self.owner_card

        if getattr(owner, "zone", None) != ZoneType.BATTLE:
            return False

        if is_card_pending(owner):
            return False

        if is_seal_card(owner) or is_ignored_by_seal(owner):
            return False

        if getattr(owner, "owner", None) is not player:
            return False

        return True


def build_mana_all_civilizations_ability(
    spec,
    card,
    game,
):
    return ManaAllCivilizationsAbility(
        owner_card=card,
    )
