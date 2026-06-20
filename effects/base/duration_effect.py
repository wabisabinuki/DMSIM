"""
期間のある効果（一時的なバフ・デバフなど）の基底クラス。
期間終了時に自動的に削除される効果を実装するために使用。
"""

from effects.base.base_effect import BaseEffect
from core.duration_type import DurationType
from core.protocols import HasGameState


class DurationEffect(BaseEffect):
    """
    期間限定の効果を表す基底クラス。

    例: 「次のターン終わりまで +3000」

    ライフサイクル:
    1. 生成: Trigger 発動時に create_effects() で生成
    2. キューイング: EffectResolver に追加
    3. 解決: resolve() で実行 → 期間管理マネージャーに登録
    4. 期間追跡: 各ターン終了時に期間をチェック
    5. クリーンアップ: 期間終了時に自動削除

    期間タイプ:
    - UNTIL_END_OF_TURN: 現在のターン終了時に削除
    - UNTIL_END_OF_OPPONENT_TURN: 相手ターン終了時に削除
    - UNTIL_END_OF_X_TURNS: X ターン後に削除
    """

    def __init__(
        self,
        source_card,
        duration_type: DurationType,
        game: HasGameState,
        duration_turns: int = 0,
    ):
        """
        Args:
            source_card: この効果を与えるカード
            duration_type: 期間タイプ (DurationType)
            game: ゲーム状態へのアクセス
            duration_turns: UNTIL_END_OF_X_TURNS の場合のターン数
        """
        super().__init__()
        self.source_card = source_card
        self.duration_type = duration_type
        self.game = game
        self.duration_turns = duration_turns

        # 登録時のターン情報（期間計算用）
        self.registered_turn = None
        self.registered_player_index = None

        # 効果が有効か
        self.is_active = False

    def register_duration(self):
        """
        ゲーム状態に期間情報を記録。
        resolve() 実行時に呼び出す。
        """
        current_state = self.game.state
        self.registered_turn = current_state.turn
        self.registered_player_index = current_state.turn_player_index

    def has_duration_expired(self) -> bool:
        """
        期間が終了したかを判定。

        Returns:
            True: 期間終了 → 効果は削除される
            False: 期間中 → 効果は継続
        """
        if not self.is_active:
            return True

        # 永続効果は期間終了しない（カードが離れた時の解除は別経路で扱う）。
        if self.duration_type == DurationType.PERMANENT:
            return False

        current_state = self.game.state

        if self.duration_type == DurationType.UNTIL_END_OF_TURN:
            # 次のターン開始 = 期間終了
            return (
                current_state.turn > self.registered_turn
                or current_state.turn_player_index != self.registered_player_index
            )

        elif (
            self.duration_type
            == DurationType.UNTIL_END_OF_OPPONENT_TURN
        ):
            # 相手ターン終了 = 元のプレイヤーのターンに戻った
            # 1. 元のプレイヤーのターン → ターン数が2以上進む
            if current_state.turn > self.registered_turn + 1:
                return True

            # 2. 現在のターン内で相手のターンが終わった場合
            #   （元のプレイヤーのターン中に相手ターン完了）
            if (
                current_state.turn == self.registered_turn + 1
                and current_state.turn_player_index == self.registered_player_index
            ):
                return True

            return False

        elif (
            self.duration_type == DurationType.UNTIL_END_OF_X_TURNS
        ):
            # X ターン後に終了
            turns_elapsed = (
                current_state.turn - self.registered_turn
            )
            return turns_elapsed > self.duration_turns

        elif (
            self.duration_type
            == DurationType.UNTIL_START_OF_CONTROLLER_TURN
        ):
            return (
                current_state.turn > self.registered_turn
                and current_state.turn_player_index
                == self.registered_player_index
            )

        return False

    def unapply(self):
        """
        期間終了時に効果を削除。
        子クラスで override して、修正やフラグを削除。
        """
        self.is_active = False

    def resolve(self):
        """
        効果を解決してゲーム状態を変更。
        期間管理マネージャーに登録される。

        子クラスで実装。
        """
        raise NotImplementedError

    def __str__(self):
        return (
            f"{self.__class__.__name__}("
            f"duration={self.duration_type})"
        )
