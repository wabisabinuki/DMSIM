"""
呪文カードを定義するクラス。詠唱時の呪文効果や呪文固有の属性を管理します。
"""

# cards/spell_card.py

from cards.card import Card, CardType

from core.protocols import (
    PlayableContext,
    SpellCastContext,
)

from actions.cast_spell_action import (
    CastSpellAction
)

from actions.cast_spell_action import (
    CastSpellAction
)


class SpellCard(Card):

    def __init__(
        self,
        name,
        civilizations,
        cost,
        name_ja=None,
        effect_name_ja=None,
        effect_texts_ja=None,
    ):

        super().__init__(
            name=name,
            cost=cost,
            civilizations=civilizations,
            card_types=CardType.SPELL,
            name_ja=name_ja,
            effect_name_ja=effect_name_ja,
            effect_texts_ja=effect_texts_ja,
        )

    # 呪文ごとにoverride
    def create_effects(
        self,
        game: SpellCastContext,
        player,
    ):

        return []

    def use(
        self,
        game: PlayableContext,
        player,
        ignore_cost=False,
    ):

        action = CastSpellAction(
            player,
            self,
            ignore_cost,
        )

        game.action_processor.process(action)

    def play_without_cost(
        self,
        game: PlayableContext,
        player,
    ):

        action = CastSpellAction(
            player=player,
            spell=self,
            ignore_cost=True,
        )

        game.action_processor.process(action)

    def get_available_actions(
        self,
        game: PlayableContext,
        player,
    ):

        actions = []

        if self.zone.name == "HAND":

            if player.can_play(self):

                actions.append(

                    CastSpellAction(
                        player,
                        self,
                    )

                )

        return actions
