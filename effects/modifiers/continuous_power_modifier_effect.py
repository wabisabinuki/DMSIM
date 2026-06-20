"""
常時パワー増減能力などによって、他のクリーチャーに継続的に適用されるパワー増減修飾子の効果。
"""

from effects.base.base_effect import BaseEffect

from core.protocols import HasGameState
from modifiers.power_modifier import PowerModifier
from zones.zone_type import ZoneType


class ContinuousPowerModifierEffect(BaseEffect):
    """
    継続的な Power 修正を適用する Effect

    例: 「このクリーチャーが場にいる限り、+2/+2」

    継続条件対応の典型例:
    - source_card がまだ Battle Zone に留まっているか確認
    - Zone を離れたら無効化
    - 複数 Effect が重複する場合の管理
    """

    def __init__(
        self,
        source_card,
        modifier_amount: int,
        game: HasGameState,
    ):
        """
        Args:
            source_card: 修正を与えるカード
            modifier_amount: Power 修正量（+ または -）
            game: ゲーム状態へのアクセス
        """
        super().__init__()
        self.source_card = source_card
        self.modifier_amount = modifier_amount
        self.game = game
        self.applied_modifier = None

    def can_resolve(self, game_state) -> bool:
        """
        継続条件判定: source_card がまだ場に留まっているか

        Returns:
            True: source_card が場にいる → 修正を適用可能
            False: source_card が場を離れた → 修正を適用不可
        """
        # デフォルトチェック: カードが同一か
        if not super().can_resolve(game_state):
            return False

        # このカードが場（Battle Zone）に留まっているか確認
        if not self.trigger_snapshot.is_still_in_battle(
            self.source_card
        ):
            # カードが場を離れた → 修正を削除
            return False

        return True

    def resolve(self):
        """
        Power 修正を適用

        継続条件を確認してから修正を適用
        条件が満たされなければ何もしない
        """
        if not self.can_resolve(
            self.game.state
        ):
            print(
                f"[Effect] "
                f"{self.source_card} is no longer "
                f"on field - modifier not applied"
            )
            return

        # Power 修正を作成
        modifier = PowerModifier(
            self.modifier_amount
        )

        # 修正のソースを設定（後で削除する際に特定）
        modifier.source_effect = self

        # カードに修正を追加
        self.source_card.power_modifiers.append(
            modifier
        )

        # 修正を保存（手動削除用）
        self.applied_modifier = modifier

        print(
            f"[Effect] Applied {self.modifier_amount:+d} "
            f"power to {self.source_card}"
        )

    def unapply(self):
        """
        修正を削除（カードが場を離れたとき など）
        """
        if self.applied_modifier is not None:
            if (
                self.applied_modifier
                in self.source_card.power_modifiers
            ):
                self.source_card.power_modifiers.remove(
                    self.applied_modifier
                )
                print(
                    f"[Effect] Removed {self.modifier_amount:+d} "
                    f"power from {self.source_card}"
                )

    def __str__(self):
        return (
            f"ContinuousPowerModifierEffect("
            f"{self.modifier_amount:+d})"
        )
