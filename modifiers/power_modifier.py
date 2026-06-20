"""
カードのパワーを加算・減算または上書きするための具体的なパワー修飾子クラス。
"""

from modifiers.base_modifier import (
    BaseModifier
)


class PowerModifier(
    BaseModifier
):
    """Power modifier.

    kind="add"      : power += amount  (default)
    kind="multiply" : power *= factor  (amount ignored)
    kind="divide"   : power //= factor (amount ignored)
    """

    def __init__(
        self,
        amount=0,
        source=None,
        duration=None,
        kind="add",
        factor=1,
    ):

        super().__init__()

        self.amount = amount

        self.source = source

        self.duration = duration

        self.kind = kind

        self.factor = factor
