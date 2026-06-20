"""
ゲームの進行状況（ターン開始、マナチャージ、召喚など）をコンソールに出力するプレゼンタークラス。
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ui.debug_printer import DebugPrinter
from ui.debug_log import set_debug_enabled


@runtime_checkable
class GamePresenter(Protocol):
    """ゲーム進行の表示・ログ（コア層から分離）"""

    def on_turn_start(
        self,
        turn: int,
        player_name: str,
        is_extra_turn: bool = False,
    ) -> None:
        ...

    def on_main_step_board(
        self,
        game_state,
    ) -> None:
        ...

    def on_turn_end_board(
        self,
        game_state,
    ) -> None:
        ...

    def on_mana_charged(
        self,
        player_name: str,
        card_name: str,
    ) -> None:
        ...


class NullGamePresenter:
    """表示なし（テスト・ヘッドレス用）"""

    def __init__(self):
        set_debug_enabled(False)

    def on_turn_start(
        self,
        turn,
        player_name,
        is_extra_turn=False,
    ):
        pass

    def on_main_step_board(
        self,
        game_state,
    ):
        pass

    def on_turn_end_board(
        self,
        game_state,
    ):
        pass

    def on_mana_charged(
        self,
        player_name,
        card_name,
    ):
        pass


class CLIGamePresenter:
    """CLI 向けの表示実装"""

    def __init__(
        self,
        debug_printer=None,
        debug=False,
    ):

        self.debug = bool(debug)
        set_debug_enabled(self.debug)
        self._debug = (
            debug_printer
            or DebugPrinter()
        )

    def bind_context(
        self,
        context,
    ):

        bind = getattr(
            self._debug,
            "bind_context",
            None,
        )
        if bind is not None:
            bind(context)

    def on_turn_start(
        self,
        turn,
        player_name,
        is_extra_turn=False,
    ):

        print()
        if is_extra_turn:
            print(f"=== Turn {turn}（追加ターン） ===")
        else:
            print(f"=== Turn {turn} ===")
        print(f"{player_name}'s turn")

    def on_main_step_board(
        self,
        game_state,
    ):

        if not self.debug:
            return

        self._debug.print_board_state(
            game_state
        )

    def on_turn_end_board(
        self,
        game_state,
    ):

        if not self.debug:
            return

        self._debug.print_board_state(
            game_state
        )

    def on_mana_charged(
        self,
        player_name,
        card_name,
    ):

        print(
            f"{player_name} charged "
            f"{card_name} to mana"
        )
