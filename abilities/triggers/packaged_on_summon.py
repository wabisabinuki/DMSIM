"""
バトルゾーンに出た時に複数の効果を1つの複合効果としてキューに積む能力。
"""

from abilities.base.triggered_ability import TriggeredAbility
from effects import PackagedEffect, build_effects
from events.battle_zone_enter_event import BattleZoneEnterEvent


class PackagedOnSummonAbility(TriggeredAbility):

    def __init__(
        self,
        owner_card,
        game,
        effect_specs,
        label=None,
    ):
        self.owner_card = owner_card
        self.effect_specs = effect_specs
        self.label = label

        def condition(event):
            return event.card == self.owner_card

        super().__init__(
            BattleZoneEnterEvent,
            condition,
            game,
        )

    def create_effects(
        self,
        event,
    ):
        return [
            PackagedEffect(
                build_effects(
                    self.effect_specs,
                    self.game,
                    event.player,
                ),
                label=self.label,
            )
        ]
