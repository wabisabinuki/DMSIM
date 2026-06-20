"""
スレイヤー能力。
このクリーチャーがバトルする時、バトルの後、相手のクリーチャーを破壊する。

実装: ContinuousAbility のマーカーとして定義し、CombatManager が
BattleStartEvent（バトルする時）の誘発解決後に has_ability で捕捉し、
バトルの後タイミングで相手クリーチャーを破壊する。
バトル中に自身が破壊されていても破壊は実行される（捕捉済みのため）。
"""

from abilities.base.continuous_ability import ContinuousAbility


class SlayerAbility(ContinuousAbility):
    """
    スレイヤー能力。

    効果: このクリーチャーがバトルする時、バトルの後、
    バトル相手のクリーチャーを破壊する。

    実装: マーカー能力。CombatManager.process_battle が
    バトル開始時点の保持状況を捕捉し、バトルの後に破壊を行う。
    """

    def __str__(self):
        return "Slayer"
