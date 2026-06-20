"""
特定のイベントを別のイベントへ置き換える置換効果能力（ReplacementAbility）の基底クラス。
"""

from abilities.base.continuous_ability \
    import ContinuousAbility


class ReplacementAbility(
    ContinuousAbility
):

    def applies(
        self,
        event,
    ):

        return False

    def replace(
        self,
        event,
    ):

        pass
