"""Handler for activated ability actions."""

from core.action_handlers.base_action_handler import BaseActionHandler


class ActivateAbilityActionHandler(BaseActionHandler):

    def process(
        self,
        action,
    ):
        action.ability.activate(action)
