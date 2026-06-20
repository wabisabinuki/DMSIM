"""パワーアタッカー（PowerAttackerAbility）。

「攻撃中、このクリーチャーのパワーを +N する」。攻撃宣言から攻撃終了までの間、
このクリーチャーが現在の攻撃クリーチャーであれば常時パワーが上がる**常在型**能力
（誘発型ではない）。攻撃中かどうかは `game.state.current_attacker`
（`CombatManager` が攻撃宣言時にセットし攻撃終了時にクリアする）で判定する。
"""

from abilities.active_condition import active_if_matches
from abilities.base.continuous_ability import ContinuousAbility
from zones.zone_type import ZoneType


class PowerAttackerAbility(ContinuousAbility):

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
        if getattr(creature, "zone", None) != ZoneType.BATTLE:
            return power

        state = getattr(self.game, "state", None)
        current_attacker = getattr(state, "current_attacker", None)
        if current_attacker is not creature:
            return power

        if not active_if_matches(
            self.active_if,
            self.owner_card,
            self.game,
        ):
            return power

        return power + self.amount


def build_power_attacker_ability(
    spec,
    card,
    game,
):
    amount = spec.get("amount", spec.get("value"))
    if amount is None:
        raise ValueError("power_attacker requires amount")

    return PowerAttackerAbility(
        owner_card=card,
        game=game,
        amount=amount,
        active_if=spec.get("active_if"),
    )
