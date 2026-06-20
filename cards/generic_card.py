"""
未実装カードタイプのひな形カード。
"""

from cards.card import Card


class GenericCard(Card):

    def __init__(
        self,
        name,
        cost,
        civilizations,
        card_types,
        name_ja=None,
        effect_name_ja=None,
        effect_texts_ja=None,
    ):

        super().__init__(
            name=name,
            cost=cost,
            civilizations=civilizations,
            card_types=card_types,
            name_ja=name_ja,
            effect_name_ja=effect_name_ja,
            effect_texts_ja=effect_texts_ja,
        )
