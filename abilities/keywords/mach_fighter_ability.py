"""
マッハファイター能力。
このクリーチャーが出たターン間、相手のクリーチャーに攻撃できる。
"""

from abilities.base.continuous_ability import ContinuousAbility


class MachFighterAbility(ContinuousAbility):
    """
    マッハファイター能力。

    効果: このクリーチャーが出たターン間、
    相手のクリーチャーに攻撃できる。

    実装: ContinuousAbilityとして定義し、
    攻撃判定時にattack_validatorでチェックする。
    """

    def __str__(self):
        return "Mach Fighter"
