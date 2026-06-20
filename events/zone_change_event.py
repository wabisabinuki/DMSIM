"""
カードの移動が完了した事実を通知するイベントクラス。トリガー判定の契機となります。
"""

from ui.card_display import format_card_name


class ZoneChangeEvent:

    def __init__(
        self,
        card,
        owner,
        from_zone,
        to_zone,
        reason,
        from_shield_face_up=False,
        evolution_sources=None,
    ):

        self.card = card
        self.owner = owner

        self.from_zone = from_zone
        self.to_zone = to_zone

        self.reason = reason
        self.from_shield_face_up = from_shield_face_up

        # このカードが場を離れる移動でのみ、離れる直前に解放された進化元
        # （その下にあったカード）を保持する。「離れた時、その下に〜があれば」
        # 系の誘発が、解放済み（クリア済み）の進化元を参照できるようにするため。
        self.evolution_sources = (
            list(evolution_sources)
            if evolution_sources
            else []
        )

    def __str__(
        self,
    ):

        return (

            f"ZoneChangeEvent("
            f"{format_card_name(self.card)}: "
            f"{self.from_zone.name}"
            f" -> "
            f"{self.to_zone.name}"
            f")"

        )
