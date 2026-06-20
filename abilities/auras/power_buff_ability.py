"""固定値のパワー修正を持ち主クリーチャーへ与える常在型能力（PowerBuffAbility）。

`grant_rule`（ScopedGrantAbility）と組み合わせて「自分のクリーチャーすべての
パワーを+2000する」のような全体修正を表現する。`active_if`（condition DSL の
dict、または "hyper_mode"）はパワー参照のたびに評価されるため、
「相手のターン中だけ」のようなターン依存の条件も書ける。
"""

from abilities.base.continuous_ability import ContinuousAbility
from abilities.active_condition import active_if_matches
from zones.zone_type import ZoneType


class PowerBuffAbility(ContinuousAbility):

    def __init__(
        self,
        owner_card,
        game,
        amount,
        active_if=None,
    ):
        super().__init__()
        self.owner_card = owner_card
        self.game = game
        self.amount = int(amount)
        self.active_if = active_if

    def modify_power(
        self,
        creature,
        power,
    ):
        # 常在型能力はバトルゾーンにいる間だけ機能する。
        if getattr(creature, "zone", None) != ZoneType.BATTLE:
            return power

        if not active_if_matches(
            self.active_if,
            self.owner_card,
            self.game,
        ):
            return power

        return power + self.amount


def build_power_buff_ability(
    spec,
    card,
    game,
):
    return PowerBuffAbility(
        owner_card=card,
        game=game,
        amount=spec.get("amount", 0),
        active_if=spec.get("active_if"),
    )
