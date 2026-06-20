"""
継続効果などの有効条件を評価する際、コンテキスト情報を保持するクラス。
"""

class ConditionContext:
    """
    Trigger 条件の評価時点を明確にする

    Trigger 発動時と Effect 解決時で評価する情報が異なる場合がある：
    - Trigger 時点: Event 情報が新鮮
    - Resolution 時点: Game State が最新

    このクラスで両方の情報を保持し、正確な条件判定を可能にする。

    用途:
    - 「このカードが場にいる限り」という継続条件の判定
    - Trigger 発動後のゲーム状態変化への対応
    """

    def __init__(
        self,
        event,
        trigger_snapshot,
        game_state,
        source_info=None,
    ):
        """
        Args:
            event: Trigger を発動させた Event
            trigger_snapshot: CardSnapshot - Trigger 発動時のカード状態
            game_state: GameState - Effect 解決時のゲーム状態
        """
        self.event = event
        self.trigger_snapshot = trigger_snapshot
        self.game_state = game_state
        self.source_info = source_info

    def evaluate_at_trigger(self) -> bool:
        """
        Trigger 発動時の条件を再評価

        Returns:
            True: 条件成立
            False: 条件不成立
        """
        # デフォルト: Event 時点の情報で評価
        # 子クラスで override 可能
        return True

    def evaluate_at_resolution(self) -> bool:
        """
        Effect 解決時の条件を検証

        Returns:
            True: 条件成立（Effect 解決可能）
            False: 条件不成立（Effect 解決不可）
        """
        # デフォルト: 常に成立
        # 子クラスで override 可能（継続条件の判定など）
        return True

    def __str__(self):
        return (
            f"ConditionContext("
            f"event={self.event.__class__.__name__}, "
            f"snapshot={self.trigger_snapshot}"
            f")"
        )
