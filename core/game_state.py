"""
ゲームの稼働状態、ターンプレイヤー、プレイヤー情報、ゲーム終了判定などを保持するデータクラス。
"""

# core/game_state.py

from core.game_step import (
    AttackSubStep,
    GameStep,
)


class GameState:
    def __init__(
        self,
        players,
        enforce_victory_conditions=True,
    ):
        self.players = players
        self.enforce_victory_conditions = bool(
            enforce_victory_conditions
        )

        self.turn_player_index = 0
        self.turn = 1
        # 「このターンの後に自分のターンを追加する」のような追加ターンの待ち行列。
        # advance_to_next_turn が通常の手番交代より先にここから取り出す。
        self.pending_extra_turns = []
        # 追加ターン（挿入ターン）の実行中、通常の手番ローテーションを巻き戻す
        # ためのインデックス。挿入ターンは正規のローテーションを進めない。
        self._extra_turn_return_index = None
        self.step = GameStep.TURN_START
        self.attack_sub_step = (
            AttackSubStep.NONE
        )
        self.game_over = False
        self.winner = None
        self.loser = None
        self.win_reason = None
        self.loss_reason = None
        self.play_history = []
        # 現在解決中の効果のコントローラー（誰のカード効果か）。zone_change 等の
        # 「相手のカードの効果によって」判定に使う。効果解決の外（バトル・SBA・
        # ルール処理）では None。
        self.current_effect_controller = None

    @property
    def current_player(self):
        return self.players[self.turn_player_index]

    @property
    def is_current_turn_extra(self):
        """現在のターンが追加（挿入）ターンかどうか。

        追加ターンの実行中だけ ``_extra_turn_return_index`` が退避値を保持し、
        追加ターン終了後の通常進行では None に戻る。
        """

        return self._extra_turn_return_index is not None

    def next_turn(self):
        self.turn_player_index = (
            self.turn_player_index + 1
        ) % len(self.players)

        self.turn += 1

    def grant_extra_turn(self, player):
        """player に追加ターンを1回与える（現在のターンの後に挿入）。"""

        self.pending_extra_turns.append(player)

    def advance_to_next_turn(self):
        """次の手番へ進む。追加ターンが待機していれば通常交代より優先する。

        追加ターンは正規の手番ローテーションを消費しない「挿入」として扱う。
        挿入ターンが終わったら、挿入前のローテーション位置を復元してから
        通常の手番交代を行うため、ターン順は「相手 → 自分(追加) → 自分(通常)」の
        ように本来の手番に上書きされない。
        """

        # 直前のターンが挿入された追加ターンだった場合、まず正規の
        # ローテーション位置を復元する。
        if self._extra_turn_return_index is not None:
            self.turn_player_index = self._extra_turn_return_index
            self._extra_turn_return_index = None

        if self.pending_extra_turns:
            next_player = self.pending_extra_turns.pop(0)
            self._extra_turn_return_index = self.turn_player_index
            self.turn_player_index = self.players.index(next_player)
            self.turn += 1
            return

        self.next_turn()

    def declare_win(
        self,
        winner,
        loser=None,
        reason=None,
    ):
        """勝利を明示的に記録する。

        「負けない」効果は敗者側に適用されるため、勝利宣言も敗者の
        loss_prevented を確認して止める。
        """

        if self.game_over:
            return False

        if not self.enforce_victory_conditions:
            return False

        if winner is None:
            return False

        loser = loser or self.opponent_of(winner)
        if loser is not None and self.loss_prevented(loser):
            return False

        self.game_over = True
        self.winner = winner
        self.loser = loser
        self.win_reason = reason
        self.loss_reason = reason
        return True

    def declare_loss(
        self,
        loser,
        winner=None,
        reason=None,
    ):
        """敗北を明示的に記録する。敗者が勝者でもある場合は勝利を優先する。"""

        if self.game_over:
            return False

        if not self.enforce_victory_conditions:
            return False

        if loser is None:
            return False

        if self.loss_prevented(loser):
            return False

        winner = winner or self.opponent_of(loser)
        if winner is loser:
            return self.declare_win(
                winner,
                loser=None,
                reason=reason,
            )

        self.game_over = True
        self.winner = winner
        self.loser = loser
        self.win_reason = reason
        self.loss_reason = reason
        return True

    def declare_results(
        self,
        winners=None,
        losers=None,
        reason=None,
    ):
        """同時の勝利/敗北結果を適用する。

        カード効果などで同じプレイヤーが勝利条件と敗北条件を同時に満たす
        場合、そのプレイヤーは勝利する。
        """

        if self.game_over:
            return False

        if not self.enforce_victory_conditions:
            return False

        original_losers = [
            player
            for player in (losers or [])
            if player is not None
        ]

        winners = [
            player
            for player in (winners or [])
            if player is not None
        ]
        losers = [
            player
            for player in original_losers
            if player is not None and player not in winners
        ]

        for winner in winners:
            loser = (
                None
                if winner in original_losers
                else self.opponent_of(winner)
            )
            if loser is None or not self.loss_prevented(loser):
                self.game_over = True
                self.winner = winner
                self.loser = loser
                self.win_reason = reason
                self.loss_reason = reason
                return True

        for loser in losers:
            if not self.loss_prevented(loser):
                return self.declare_loss(
                    loser,
                    reason=reason,
                )

        return False

    def opponent_of(
        self,
        player,
    ):
        opponents = [
            candidate
            for candidate in self.players
            if candidate is not player
        ]
        return opponents[0] if len(opponents) == 1 else None

    def loss_prevented(
        self,
        player,
    ):
        return getattr(player, "loss_prevented", 0) > 0
