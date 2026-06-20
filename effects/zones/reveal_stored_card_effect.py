"""
PackageContextに保存されたカードを公開するための箱。
相手への公開UIは後で差し替える。
"""

from effects.base.base_effect import BaseEffect


class RevealStoredCardEffect(BaseEffect):

    def __init__(
        self,
        key,
    ):
        super().__init__()

        self.key = key

    def resolve(self):
        value = self.package_context.get(
            self.key
        )

        if value is None:
            return False

        cards = value if isinstance(value, list) else [value]

        for card in cards:
            print(
                f"{card.name} was revealed"
            )

        return bool(cards)
