"""
自動テストやデモ用のAI・自動選択マネージャ。プレイヤーの介入なしに自動的に選択肢を処理します。
"""

from actions.finish_attack_step_action import (
    FinishAttackStepAction,
)

from actions.proceed_to_attack_step_action import (
    ProceedToAttackStepAction,
)


class AutoChoiceManager:
    """
    テスト用: 可能な限り自動で選択する。
    メインは攻撃ステップへ、攻撃は終了を優先する。
 マナチャージはスキップ（None）を優先する。
    """

    def select(
        self,
        player,
        choices,
        prompt,
        min_count=1,
        max_count=1,
        auto_choose_single=True,
    ):

        if not choices:

            if min_count == 0:
                return []

            return None

        if (
            auto_choose_single
            and len(choices) == 1
            and min_count == 1
            and max_count == 1
        ):

            return choices[0]

        if min_count == 0 and max_count != 1:

            return []

        preferred = (
            ProceedToAttackStepAction,
            FinishAttackStepAction,
        )

        for action_type in preferred:

            for choice in choices:

                if isinstance(
                    choice,
                    action_type,
                ):

                    return choice

        if None in choices:

            return None

        return choices[0]

    def format_choice(
        self,
        choice,
    ):

        return str(choice)
