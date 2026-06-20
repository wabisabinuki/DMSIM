"""
自身のターン終了時にカードを1枚ドローするトリガー能力（DrawOnTurnEndAbility）を定義。
"""

from abilities.base.triggered_ability import (
    TriggeredAbility
)

from events.turn_event import (
    TurnEndEvent
)

from effects import (
    DrawEffect
)


class DrawOnTurnEndAbility(
    TriggeredAbility
):

    def __init__(
        self,
        owner_card,
        game,
    ):

        self.owner_card = owner_card

        def condition(event):

            return (
                event.player
                == self.owner_card.owner
            )

        super().__init__(
            TurnEndEvent,
            condition,
            game,
        )

    def create_effects(
        self,
        event,
    ):

        return [
            DrawEffect(
                player=event.player,
                amount=1,
                game=self.game,
            )
        ]
