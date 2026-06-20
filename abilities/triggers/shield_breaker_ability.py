"""Triggered ability that breaks shields when its source is destroyed."""

from abilities.base.triggered_ability import TriggeredAbility
from effects import PackagedEffect, build_effects
from events.destroy_event import DestroyEvent


class ShieldBreakerAbility(TriggeredAbility):

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

        super().__init__(
            DestroyEvent,
            lambda event: event.card == self.owner_card,
            game,
        )

    def create_effects(
        self,
        event,
    ):
        effect = PackagedEffect(
            build_effects(
                self.effect_specs,
                self.game,
                self.owner_card.owner,
            ),
            label=self.label,
        )
        effect.ignore_source_continuity = True
        return [
            effect
        ]
