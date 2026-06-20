"""
効果の解決対象や攻撃対象などの選択肢を提示・管理する選択抽象基底クラス。
"""


class ChoiceOption(int):
    """Integer choice that also carries stable test-facing metadata."""

    def __new__(
        cls,
        index,
        choice_id=None,
        label=None,
    ):
        obj = int.__new__(
            cls,
            index,
        )
        obj.index = int(index)
        obj.choice_id = choice_id
        obj.id = choice_id
        obj.label = label
        return obj

    def __str__(
        self,
    ):
        if self.label is not None:
            return str(self.label)

        if self.choice_id is not None:
            return str(self.choice_id)

        return str(self.index)


class ChoiceManager:

    def choose(
        self,
        player,
        choices,
        prompt,
    ):

        raise NotImplementedError
