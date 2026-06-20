"""バトル中パワー修整（BattlePowerAbility）。

「バトル中、このクリーチャーのパワーを +N する」。バトル成立（``BattleDeclaredEvent``）
からバトル終了までの間、このクリーチャーがそのバトルの参加者（攻撃側・防御側の
どちらか）であれば常時パワーが上がる**常在型**能力（誘発型ではない）。

攻撃／ブロックだけでなく「バトルさせる」効果による強制バトルも対象。バトル参加者は
``game.state.current_battle_attacker`` / ``current_battle_defender``（``CombatManager``
がバトル成立時にセットし終了時にクリアする）で判定する。パワーアタッカー
（``PowerAttackerAbility``）の「バトル全般」版。
"""

from abilities.active_condition import active_if_matches
from abilities.base.continuous_ability import ContinuousAbility
from zones.zone_type import ZoneType


class BattlePowerAbility(ContinuousAbility):

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
        participants = (
            getattr(state, "current_battle_attacker", None),
            getattr(state, "current_battle_defender", None),
        )
        if creature not in participants:
            return power

        if not active_if_matches(
            self.active_if,
            self.owner_card,
            self.game,
        ):
            return power

        return power + self.amount


def build_battle_power_ability(
    spec,
    card,
    game,
):
    amount = spec.get("amount", spec.get("value"))
    if amount is None:
        raise ValueError("battle_power requires amount")

    return BattlePowerAbility(
        owner_card=card,
        game=game,
        amount=amount,
        active_if=spec.get("active_if"),
    )
