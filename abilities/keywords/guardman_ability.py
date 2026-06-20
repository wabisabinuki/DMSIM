"""ガードマン能力。

このクリーチャーをタップして、相手クリーチャーの攻撃先を、自分の他の
クリーチャーからこのクリーチャーに変更してもよい。

ブロッカーと同様に「攻撃先を移し替える」防御的な能力であり、置換効果として
バトルそのものを肩代わりするスーパーガードマン（`SuperGuardmanAbility`）とは
実装が異なる。`GameQuery.get_guardmen()` が候補を集め、
`CombatManager.try_guardman()` が攻撃先を変更する。
"""

from abilities.base.continuous_ability import (
    ContinuousAbility
)
from abilities.active_condition import active_if_matches


class GuardmanAbility(
    ContinuousAbility
):

    def __init__(
        self,
        active_if=None,
    ):
        super().__init__()
        self.active_if = active_if

    def is_active_for(
        self,
        creature,
    ):
        return active_if_matches(
            self.active_if,
            creature,
            None,
        )
