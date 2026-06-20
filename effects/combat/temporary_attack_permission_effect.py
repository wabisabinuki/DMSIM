"""
期間限定の一時的な攻撃権を付与する効果。
例: マッハファイター「このクリーチャーは出たターン間、相手のクリーチャーに攻撃できる」
"""

from effects.base.duration_effect import DurationEffect
from core.duration_type import DurationType
from core.protocols import HasGameState


class TemporaryAttackPermissionEffect(DurationEffect):
    """
    一定期間、特定の攻撃制限を解除する効果。

    例: 「このターンの間、相手のクリーチャーに攻撃できる」（マッハファイター）

    このカードに `temporary_attack_permission` フラグを立て、
    戦闘マネージャーがこれを確認して攻撃制限をスキップさせる。
    """

    def __init__(
        self,
        source_card,
        duration_type: DurationType,
        game: HasGameState,
        duration_turns: int = 0,
        permission_type: str = "mach_fighter",
    ):
        """
        Args:
            source_card: この効果を与えるカード
            duration_type: 期間タイプ
            game: ゲーム状態へのアクセス
            duration_turns: UNTIL_END_OF_X_TURNS の場合のターン数
            permission_type: 攻撃権のタイプ
                - "mach_fighter": 出たターン間、相手のクリーチャーに攻撃可
        """
        super().__init__(
            source_card,
            duration_type,
            game,
            duration_turns,
        )
        self.permission_type = permission_type

    def resolve(self):
        """
        カードに一時的な攻撃権フラグを設定し、期間を登録。
        """
        if not self.source_card:
            print(
                "[Effect] Source card not found - "
                "temporary attack permission not applied"
            )
            return

        # カードに属性を設定
        if not hasattr(
            self.source_card,
            "temporary_attack_permission",
        ):
            self.source_card.temporary_attack_permission = (
                {}
            )

        self.source_card.temporary_attack_permission[
            self.permission_type
        ] = True

        # 期間情報を登録
        self.register_duration()
        self.is_active = True

        print(
            f"[Effect] Applied temporary {self.permission_type} "
            f"to {self.source_card} "
            f"until {self.duration_type}"
        )

    def unapply(self):
        """
        期間終了時、一時的な攻撃権フラグを削除。
        """
        if hasattr(
            self.source_card,
            "temporary_attack_permission",
        ):
            if (
                self.permission_type
                in self.source_card.temporary_attack_permission
            ):
                del self.source_card.temporary_attack_permission[
                    self.permission_type
                ]
                print(
                    f"[Effect] Removed temporary {self.permission_type} "
                    f"from {self.source_card}"
                )

        super().unapply()

    def __str__(self):
        return (
            f"TemporaryAttackPermissionEffect("
            f"{self.permission_type}, "
            f"until {self.duration_type})"
        )
