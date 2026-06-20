"""
期間のある効果を追跡・管理し、期間終了時に自動的にクリーンアップするマネージャー。
"""

from effects import DurationEffect
from core.protocols import HasGameState
from ui.debug_log import debug_print


class DurationEffectManager:
    """
    期間限定効果を追跡・管理。

    ゲームループまたはターン管理から定期的に呼び出され、
    期間終了した効果を自動的に削除。

    使用例:
        manager = DurationEffectManager(game_context)
        effect = TimedPowerModifierEffect(...)
        manager.register_duration_effect(effect)
        ...
        manager.check_and_cleanup_expired_effects()
    """

    def __init__(self, game: HasGameState):
        """
        Args:
            game: ゲーム状態へのアクセス
        """
        self.game = game
        self.active_duration_effects = []

    def register_duration_effect(
        self,
        effect: DurationEffect,
    ):
        """
        期間制限のある効果を登録。

        Args:
            effect: DurationEffect インスタンス
        """
        if effect not in self.active_duration_effects:
            self.active_duration_effects.append(effect)
            debug_print(
                f"[DurationEffectManager] Registered effect: {effect}"
            )

    def unregister_duration_effect(
        self,
        effect: DurationEffect,
    ):
        """
        効果の登録を解除。

        Args:
            effect: DurationEffect インスタンス
        """
        if effect in self.active_duration_effects:
            self.active_duration_effects.remove(effect)
            debug_print(
                f"[DurationEffectManager] Unregistered effect: {effect}"
            )

    def check_and_cleanup_expired_effects(self):
        """
        すべての登録済み効果を確認し、期間終了した効果を削除。

        各ターンの終了時に呼び出すことを想定。
        """
        expired_effects = []

        for effect in self.active_duration_effects:
            if effect.has_duration_expired():
                expired_effects.append(effect)

        for effect in expired_effects:
            effect.unapply()
            self.unregister_duration_effect(effect)
            debug_print(
                f"[DurationEffectManager] Expired effect: {effect}"
            )

    def clear_all_effects(self):
        """
        すべての期間限定効果をクリア（ゲーム終了時など）。
        """
        effects_to_clear = (
            self.active_duration_effects[:]
        )
        for effect in effects_to_clear:
            effect.unapply()
            self.unregister_duration_effect(effect)

        debug_print(
            "[DurationEffectManager] All duration effects cleared"
        )

    def get_active_effects_for_card(self, card):
        """
        特定のカードに適用されている期間限定効果を取得。

        Args:
            card: カード

        Returns:
            list: そのカードに適用されている DurationEffect のリスト
        """
        return [
            effect
            for effect in self.active_duration_effects
            if effect.source_card == card
            or (
                hasattr(effect, "target_card")
                and effect.target_card == card
            )
        ]

    def __str__(self):
        return (
            f"DurationEffectManager("
            f"{len(self.active_duration_effects)} active)"
        )
