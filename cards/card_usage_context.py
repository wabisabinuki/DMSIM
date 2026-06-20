"""
CardUsageContext: ツインパクトカードの使用状態を管理。
ランタイムで「現在どちらの面を使用しているか」を追跡します。
"""

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from cards.card_face import CardFace


class CardUsageContext:
    """
    ツインパクトカードの使用状態を保持するコンテキスト。
    
    例：
    - クリーチャー側として詠唱: CardUsageContext(card, selected_face=creature_face)
    - 呪文側として詠唱: CardUsageContext(card, selected_face=spell_face)
    - ただし手札にある間はselected_faceはNone
    """

    def __init__(
        self,
        card,
        selected_face: Optional["CardFace"] = None,
    ):
        self.card = card
        self.selected_face = selected_face

    def get_current_cost(self) -> int:
        """現在使用中の面のコストを取得"""
        if self.selected_face:
            return self.selected_face.cost
        raise ValueError(
            f"Card {self.card.name} has no selected face in this context"
        )

    def get_current_civilization(self) -> int:
        """現在使用中の面の文明を取得（フォールバック: カード全体）"""
        if self.selected_face:
            return self.selected_face.civilization
        # フォールバック: カード全体の文明
        return self.card.get_all_civilizations()

    def has_selected_face(self) -> bool:
        """面が選択されているか"""
        return self.selected_face is not None

    def is_creature_face(self) -> bool:
        """クリーチャー面が選択されているか"""
        if not self.selected_face:
            return False
        return self.selected_face.is_creature()

    def is_spell_face(self) -> bool:
        """呪文面が選択されているか"""
        if not self.selected_face:
            return False
        return self.selected_face.is_spell()

    def __str__(self):
        face_info = (
            str(self.selected_face)
            if self.selected_face
            else "No face selected"
        )
        return (
            f"CardUsageContext({self.card.name}: {face_info})"
        )
