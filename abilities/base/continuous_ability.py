"""
バトルゾーンに存在する間、継続的にゲーム状態やカードプロパティに修飾子（Modifier）を適用する能力の基底クラス。
"""

from abilities.base.base_ability import (
    BaseAbility
)


class ContinuousAbility(
    BaseAbility
):
    def __init__(self):
        super().__init__()

    pass
