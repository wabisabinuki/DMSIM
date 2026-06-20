"""
N回選ぶ複合効果。同じ選択肢を複数回選べるが、
選択は上から順（インデックスが非減少）でなければならない。
"""

from effects.base.base_effect import BaseEffect
from core.choice_manager import ChoiceOption


class ChooseNEffectsEffect(BaseEffect):
    """
    M個の選択肢からN回選ぶ効果。

    ルール:
    - 同じ選択肢を複数回選んでよい。
    - 選択は必ず非減少順（前の選択と同じか後ろの選択肢のみ選べる）。
    - 選択後、選んだ効果を宣言順に実行する。
    """

    def __init__(
        self,
        player,
        game,
        choice_specs,
        n,
        prompt="効果を選んでください",
        source_card=None,
    ):
        super().__init__()
        self.player = player
        self.game = game
        self.choice_specs = choice_specs
        self.n = n
        self.prompt = prompt
        self._init_source_card = source_card

    def resolve(self):
        source = self.source_card or self._init_source_card
        min_index = 0
        selections = []

        for i in range(self.n):
            available_indices = list(range(min_index, len(self.choice_specs)))
            if not available_indices:
                break

            choice_options = [
                self._choice_option(idx)
                for idx in available_indices
            ]
            prompt = f"{self.prompt} ({i + 1}/{self.n})"

            choice_index = self.game.choice_manager.select(
                self.player,
                choice_options,
                prompt=prompt,
            )
            if choice_index is None:
                break

            selections.append(int(choice_index))
            min_index = int(choice_index)

        for choice_index in selections:
            from effects.registry import build_effects  # 循環インポートを避けるため遅延インポート
            effects = build_effects(
                self.choice_specs[choice_index].get("effects", []),
                self.game,
                self.player,
                source_card=source,
            )
            for effect in effects:
                effect.package_context = self.package_context
                effect.source_card = source
                effect.resolve()

        return bool(selections)

    def _choice_option(
        self,
        index,
    ):
        spec = self.choice_specs[index]
        if not isinstance(spec, dict):
            return ChoiceOption(index)

        return ChoiceOption(
            index,
            choice_id=spec.get(
                "choice_id",
                spec.get("id"),
            ),
            label=spec.get(
                "label",
                f"選択肢{index + 1}",
            ),
        )
