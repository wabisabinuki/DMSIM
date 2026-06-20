"""
攻撃が開始された事実を通知するイベントクラス。攻撃元と攻撃対象を保持します。
"""

from events.base_event import BaseEvent
from ui.card_display import format_card_name


class AttackDeclaredEvent(
    BaseEvent
):

    def __init__(
        self,
        player,
        attacker,
        target,
        attack_id=None,
    ):
        super().__init__()
        self.player = player

        self.attacker = attacker

        self.target = target

        self.attack_id = attack_id

    def __str__(self):
        return (
            f"AttackDeclaredEvent("
            f"{format_card_name(self.attacker)}"
            f" -> "
            f"{format_card_name(self.target)}"
            f")"
        )


class AttackEndedEvent(
    BaseEvent
):

    def __init__(
        self,
        player,
        attacker,
        target,
        attack_id=None,
    ):
        super().__init__()
        self.player = player
        self.attacker = attacker
        self.target = target
        self.attack_id = attack_id

    def __str__(self):
        return (
            f"AttackEndedEvent("
            f"{format_card_name(self.attacker)}"
            f" -> "
            f"{format_card_name(self.target)}"
            f")"
        )
