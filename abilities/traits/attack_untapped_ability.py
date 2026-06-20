"""このクリーチャーがアンタップしているクリーチャーも攻撃できるようにする常在型能力。

通常クリーチャーはタップしているクリーチャー（とプレイヤー）しか攻撃できないが、
この能力を持つ攻撃クリーチャーはアンタップしている相手クリーチャーも攻撃対象に
選べる。`AttackValidator._can_attack_target_base` が攻撃側の能力を走査して判定する。
"""

from abilities.active_condition import active_if_matches
from abilities.base.continuous_ability import ContinuousAbility


class AttackUntappedAbility(ContinuousAbility):

    def __init__(
        self,
        owner_card=None,
        game=None,
        active_if=None,
    ):
        super().__init__()
        self.owner_card = owner_card
        self.game = game
        self.active_if = active_if

    def allows_attacking_untapped(
        self,
    ):
        return active_if_matches(
            self.active_if,
            self.owner_card,
            self.game,
        )
