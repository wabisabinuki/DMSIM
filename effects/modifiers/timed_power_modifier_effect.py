"""
期間限定のパワー修正効果。
例: 「次のターン終わりまで +3000」
"""

from effects.base.duration_effect import DurationEffect
from core.duration_type import DurationType
from core.protocols import HasGameState
from modifiers.power_modifier import PowerModifier
from zones.zone_type import ZoneType


class TimedPowerModifierEffect(DurationEffect):
    """
    一定期間、パワーを増減する効果。

    例:
    - 「このターンの終わりまで +3000」
    - 「次の相手ターンの終わりまで -2000」
    """

    def __init__(
        self,
        source_card,
        target_card,
        modifier_amount: int,
        duration_type: DurationType,
        game: HasGameState,
        duration_turns: int = 0,
    ):
        """
        Args:
            source_card: 効果の発生源（能力を持つカード）
            target_card: パワーを修正されるカード
            modifier_amount: パワー修正量（+ または -）
            duration_type: 期間タイプ
            game: ゲーム状態へのアクセス
            duration_turns: UNTIL_END_OF_X_TURNS の場合のターン数
        """
        super().__init__(
            source_card,
            duration_type,
            game,
            duration_turns,
        )
        self.target_card = target_card
        self.modifier_amount = modifier_amount
        self.applied_modifier = None

    def can_resolve(self, game_state) -> bool:
        """
        期間限定効果は target_card が場に残っているか確認。
        """
        if not super().can_resolve(game_state):
            return False

        # 対象カードが場にいるか確認。スナップショットが無い場合
        # （呪文の効果など）は現在のゾーンだけで判定する。
        if self.trigger_snapshot is None:
            return (
                getattr(
                    self.target_card,
                    "zone",
                    None,
                )
                == ZoneType.BATTLE
            )

        if not self.trigger_snapshot.is_still_in_battle(
            self.target_card
        ):
            return False

        return True

    def resolve(self):
        """
        パワー修正を適用し、期間を登録。
        """
        if not self.can_resolve(self.game.state):
            print(
                f"[Effect] {self.target_card} is no longer "
                f"on field - timed modifier not applied"
            )
            return

        # 修正を作成
        modifier = PowerModifier(self.modifier_amount)
        modifier.source_effect = self

        # カードに修正を追加
        self.target_card.power_modifiers.append(modifier)
        self.applied_modifier = modifier

        # 期間情報を登録
        self.register_duration()
        manager = getattr(
            self.game,
            "duration_effect_manager",
            None,
        )
        register = getattr(
            manager,
            "register_duration_effect",
            None,
        )
        if register is not None:
            register(self)
        self.is_active = True

        print(
            f"[Effect] Applied timed {self.modifier_amount:+d} "
            f"power to {self.target_card} "
            f"until {self.duration_type}"
        )

    def unapply(self):
        """
        期間終了時、パワー修正を削除。
        """
        if self.applied_modifier is not None:
            if (
                self.applied_modifier
                in self.target_card.power_modifiers
            ):
                self.target_card.power_modifiers.remove(
                    self.applied_modifier
                )
                print(
                    f"[Effect] Removed timed {self.modifier_amount:+d} "
                    f"power from {self.target_card}"
                )

        super().unapply()

    def __str__(self):
        return (
            f"TimedPowerModifierEffect("
            f"{self.modifier_amount:+d}, "
            f"until {self.duration_type})"
        )
