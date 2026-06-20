"""
開発・検証用に領域変更やイベント発火をコンソールに見やすくフォーマットして出力するデバッグプリンタ。
"""

from actions.attack_action import AttackAction
from core.game_step import GameStep
from ui.card_display import (
    civilization_label,
    format_battle_card,
    format_card_name,
    format_mana_zone_heading,
    ordered_battle_zone_cards,
    tap_state_label,
)


class DebugPrinter:

    def __init__(
        self,
        context=None,
    ):

        self.context = context

    def bind_context(
        self,
        context,
    ):

        self.context = context

    def print_board_state(
        self,
        game_state,
    ):

        print("\n=== BOARD STATE ===")

        for player in game_state.players:

            print(f"\n[{player.name}]")

            print(
                f"Shields: {self._shield_count(player)} | "
                f"Hand: {len(player.hand.cards)} | "
                f"Deck: {len(player.deck.cards)} | "
                f"Graveyard: "
                f"{len(player.graveyard.cards)}"
            )

            print(
                f"\n{format_mana_zone_heading(player)}:"
            )

            if player.mana_zone.cards:

                for card in (
                    player.mana_zone.cards[:]
                ):

                    print(
                        f" - [{tap_state_label(card)}] "
                        f"[{civilization_label(card)}] "
                        f"{format_card_name(card)}"
                    )

            else:

                print(" - Empty")

            print("\nBattle Zone:")

            self._print_battle_zone(
                game_state,
                player,
            )

        print("\n===================\n")

    def print_battlezone_state(
        self,
        game_state,
    ):

        print("\n=== BOARD STATE ===")

        for player in game_state.players:

            print(f"\n[{player.name}]")

            print("\nBattle Zone:")

            self._print_battle_zone(
                game_state,
                player,
            )

        print("\n===================\n")

    def _print_battle_zone(
        self,
        game_state,
        player,
    ):

        entries = ordered_battle_zone_cards(player)
        if not entries:
            print(" - Empty")
            return

        attackable = self._attackable_cards(
            game_state,
            player,
        )

        for card, is_attached_seal in entries:
            prefix = "    * " if is_attached_seal else " - "
            print(
                f"{prefix}"
                f"{format_battle_card(card, card in attackable)}"
            )

    def _attackable_cards(
        self,
        game_state,
        player,
    ):

        if game_state.step != GameStep.ATTACK:
            return set()

        if player is not game_state.current_player:
            return set()

        if self.context is None:
            return set()

        actions = (
            self.context
            .action_generator
            .get_attack_step_actions(
                player
            )
        )

        return {
            action.attacker
            for action in actions
            if isinstance(action, AttackAction)
        }

    def _shield_count(
        self,
        player,
    ):

        shield_count = getattr(
            player.shield_zone,
            "shield_count",
            None,
        )
        if shield_count is not None:
            return shield_count()

        return len(player.shield_zone.cards)
