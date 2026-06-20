"""「相手のクリーチャーが攻撃するなら、可能ならこのクリーチャーを攻撃する」常在能力。

攻撃を強制するのではなく、攻撃する場合の攻撃先をこのクリーチャーへ誘導する。
「可能なら」のため、このクリーチャーが正規の攻撃対象にならない場合
（アンタップ状態でマッハファイター等も無い場合など）は制限しない。
攻撃先の絞り込みは `AttackValidator.can_attack_target` が行う。
"""

from abilities.base.continuous_ability import ContinuousAbility
from abilities.active_condition import active_if_matches
from core.creature_scope import matches_creature_scope


class AttackLureAbility(ContinuousAbility):

    def __init__(
        self,
        active_if=None,
        scope="opponent_creatures",
    ):
        super().__init__()
        self.active_if = active_if
        self.scope = scope

    def is_active_for(
        self,
        source,
    ):
        return active_if_matches(
            self.active_if,
            source,
            None,
        )

    def lures_attack(
        self,
        source,
        attacker,
    ):
        return (
            self.is_active_for(source)
            and matches_creature_scope(
                self.scope,
                source,
                attacker,
                owner=attacker.owner,
            )
        )
