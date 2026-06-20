"""パワード・ブロッカー（PoweredBlockerAbility）。

「ブロック中、このクリーチャーのパワーを +N する」。ブロック宣言
（``BlockDeclaredEvent``）からそのバトル終了までの間、このクリーチャーが現在の
ブロッカーであれば常時パワーが上がる**常在型**能力（誘発型ではない）。
ブロック中かどうかは ``game.state.current_blocker``（``CombatManager`` が
ブロック宣言時にセットし攻撃終了時にクリアする）で判定する。

パワーアタッカー（``PowerAttackerAbility``）の `current_attacker` 版で、
攻撃側ではなくブロック側のときにパワーを上げる点だけが異なる。
"""

from abilities.active_condition import active_if_matches
from abilities.base.continuous_ability import ContinuousAbility
from zones.zone_type import ZoneType


class PoweredBlockerAbility(ContinuousAbility):

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
        current_blocker = getattr(state, "current_blocker", None)
        if current_blocker is not creature:
            return power

        if not active_if_matches(
            self.active_if,
            self.owner_card,
            self.game,
        ):
            return power

        return power + self.amount


def build_powered_blocker_ability(
    spec,
    card,
    game,
):
    amount = spec.get("amount", spec.get("value"))
    if amount is None:
        raise ValueError("powered_blocker requires amount")

    return PoweredBlockerAbility(
        owner_card=card,
        game=game,
        amount=amount,
        active_if=spec.get("active_if"),
    )
