from cards.spell_card import SpellCard
from effects import build_effects


class GenericSpellCard(SpellCard):
    """JSON定義のeffect_specsから効果を生成する汎用呪文。"""

    def __init__(
        self,
        name,
        civilizations,
        cost,
        effect_specs=None,
        name_ja=None,
        effect_name_ja=None,
        effect_texts_ja=None,
    ):
        super().__init__(
            name=name,
            civilizations=civilizations,
            cost=cost,
            name_ja=name_ja,
            effect_name_ja=effect_name_ja,
            effect_texts_ja=effect_texts_ja,
        )
        self.effect_specs = effect_specs or []

    def create_effects(
        self,
        game,
        player,
    ):
        return build_effects(
            self.effect_specs,
            game,
            player,
        )
