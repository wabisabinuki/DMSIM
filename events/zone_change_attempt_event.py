"""
カードの移動試行を通知するイベントクラス。置換効果の対象となります。
"""

class ZoneChangeAttemptEvent:

    def __init__(
        self,
        card,
        owner,
        from_zone,
        to_zone,
        reason,
    ):

        self.card = card
        self.owner = owner

        self.from_zone = from_zone
        self.to_zone = to_zone

        self.reason = reason

        self.replaced = False
        self.cancelled = False

    def __str__(
        self,
    ):

        return (
            "ZoneChangeAttemptEvent("
            f"{getattr(self.card, 'name', self.card)}: "
            f"{self.from_zone.name}"
            " -> "
            f"{self.to_zone.name}"
            ")"
        )
