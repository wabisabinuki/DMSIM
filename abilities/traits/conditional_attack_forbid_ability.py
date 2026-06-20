"""条件を満たさない間、自身の攻撃を禁止する常在型能力。

「このターンに〜していなければ、このクリーチャーは攻撃できない」のように、
condition が満たされていない間だけ自分の攻撃を禁止する。`AttackValidator.
_is_attack_forbidden_by_continuous` が各クリーチャーの `forbids_attack` を走査する。
"""

from abilities.base.continuous_ability import ContinuousAbility
from core.condition_evaluator import ConditionEvaluator


class ConditionalAttackForbidAbility(ContinuousAbility):

    def __init__(
        self,
        owner_card,
        game,
        condition,
    ):
        super().__init__()
        self.owner_card = owner_card
        self.game = game
        self.condition = condition

    def forbids_attack(
        self,
        source,
        attacker,
    ):
        # source は能力の持ち主（バリデータが渡す）、attacker は攻撃クリーチャー。
        # 自身の攻撃だけを、条件が満たされていない間は禁止する。
        if attacker is not self.owner_card:
            return False

        if self.condition is None:
            return False

        met = ConditionEvaluator(self.game).evaluate(
            self.condition,
            {
                "game": self.game,
                "player": self.owner_card.owner,
                "controller": self.owner_card.owner,
                "source_card": self.owner_card,
            },
        )
        return not met
