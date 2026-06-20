"""Base support for activated abilities."""

from abilities.base.base_ability import BaseAbility
from actions.activate_ability_action import ActivateAbilityAction


class ActivatedAbility(BaseAbility):
    """Ability that can produce an explicit player action."""

    def __init__(self):
        super().__init__()

    def can_activate(
        self,
        player,
    ):
        return False

    def activate(
        self,
        action,
    ):
        raise NotImplementedError

    def get_activate_actions(
        self,
        player,
        source_card,
    ):
        if not self.can_activate(player):
            return []

        return [
            ActivateAbilityAction(
                player,
                self,
                source_card,
            )
        ]
