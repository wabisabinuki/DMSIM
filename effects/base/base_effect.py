"""
すべての効果（Effect）の抽象基底クラス。ゲーム状態を書き換える唯一の実体を定義します。
"""

class BaseEffect:
    """
    ゲーム状態を変更する唯一の存在

    Effect は以下のライフサイクルを持つ：
    1. 生成: Trigger 発動時に Ability.create_effects() で生成
    2. キューイング: EffectResolver に追加
    3. 解決: resolve() で実行

    継続条件対応版:
    - trigger_snapshot: Trigger 時点のカード状態
    - condition_context: 条件評価のコンテキスト
    - can_resolve(): 解決前に条件を検証
    """

    def __init__(self):
        self.source_card = None
        self.source_info = None
        self.trigger_snapshot = None
        self.condition_context = None
        self.package_context = {}
        self.ignore_source_continuity = False

    def can_resolve(self, game_state) -> bool:
        """
        Effect を解決可能か判定

        デフォルト: source_card が同一（zcc が変わっていない）
        継続条件がある場合は子クラスで override

        Args:
            game_state: GameState

        Returns:
            True: 解決可能
            False: 解決不可（スキップ）
        """
        if getattr(
            self,
            "ignore_source_continuity",
            False,
        ):
            return True

        if self.trigger_snapshot is None:
            # Snapshot なしなら常に解決可能
            return True

        if not self.trigger_snapshot.is_same_card(
            self.source_card
        ):
            # カードが別物 → 解決不可
            return False

        return True

    def resolve(self):
        """
        Effect を解決してゲーム状態を変更

        子クラスで実装
        """
        raise NotImplementedError

    def __str__(self):
        return (
            f"{self.__class__.__name__}()"
        )
