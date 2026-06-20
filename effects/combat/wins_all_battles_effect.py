"""
一定期間、対象クリーチャーがすべてのバトルに勝つようにする効果。

例: 「このターン、このクリーチャーはすべてのバトルに勝つ。」

`card.wins_all_battles_this_turn` フラグを立て、CombatManager の
バトル解決がこれを参照する。期間終了時にフラグを解除する。
"""

from effects.base.duration_effect import DurationEffect
from core.duration_type import DurationType
from core.protocols import HasGameState


class WinsAllBattlesEffect(DurationEffect):
    """
    対象クリーチャーが期間中、すべてのバトルに勝つようにする。

    バトルの勝敗判定は CombatManager.process_battle が
    `wins_all_battles_this_turn` フラグを参照して行う。
    """

    def __init__(
        self,
        source_card,
        target_card,
        duration_type: DurationType,
        game: HasGameState,
        duration_turns: int = 0,
    ):
        super().__init__(
            source_card,
            duration_type,
            game,
            duration_turns,
        )
        self.target_card = target_card
        self._applied = False

    def can_resolve(self, game_state) -> bool:
        if not super().can_resolve(game_state):
            return False

        if (
            self.trigger_snapshot is not None
            and not self.trigger_snapshot.is_still_in_battle(
                self.target_card
            )
        ):
            return False

        return True

    def resolve(self):
        if not self.can_resolve(self.game.state):
            return

        self.target_card.wins_all_battles_this_turn = True
        self._applied = True

        self.register_duration()
        self.is_active = True
        self.game.duration_effect_manager.register_duration_effect(
            self
        )

        print(
            f"[Effect] {self.target_card} wins all battles "
            f"until {self.duration_type}"
        )

    def unapply(self):
        if self._applied:
            self.target_card.wins_all_battles_this_turn = False
            self._applied = False
            print(
                f"[Effect] {self.target_card} no longer "
                f"wins all battles"
            )

        super().unapply()

    def __str__(self):
        return (
            f"WinsAllBattlesEffect("
            f"until {self.duration_type})"
        )
