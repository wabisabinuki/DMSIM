"""Event published when a creature blocks an attack."""

from events.base_event import BaseEvent
from ui.card_display import format_card_name


class BlockDeclaredEvent(BaseEvent):

    def __init__(
        self,
        player,
        blocker,
        attacker,
        original_target,
        attack_id=None,
    ):
        super().__init__()
        self.player = player
        self.blocker = blocker
        self.attacker = attacker
        self.target = blocker
        self.original_target = original_target
        self.attack_id = attack_id

    def __str__(self):
        return (
            "BlockDeclaredEvent("
            f"{format_card_name(self.blocker)} blocks "
            f"{format_card_name(self.attacker)}"
            ")"
        )
