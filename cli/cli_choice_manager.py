"""
CLI環境で対話的にプレイヤーへ選択肢を提示し、入力を受け付ける選択肢マネージャ。
"""

import unicodedata

from ui.card_display import (
    civilization_label,
    format_action,
    format_card_name,
    tap_state_label,
)
from core.seal_utils import is_seal_card
from ui.board_view_renderer import BoardViewRenderer
from abilities.traits.look_top_deck_ability import LookTopDeckDuringTurnAbility
from core.mana_payment import (
    ManaPaymentSelection,
    card_civilizations,
    civilization_bits,
    civilization_candidates,
    payment_total,
    remaining_mana_candidates,
)


_CIVILIZATION_NAMES = {
    1 << 0: "Fire",
    1 << 1: "Water",
    1 << 2: "Nature",
    1 << 3: "Light",
    1 << 4: "Darkness",
}

_CIVILIZATION_NAMES_JA = {
    1 << 0: "火",
    1 << 1: "水",
    1 << 2: "自然",
    1 << 3: "光",
    1 << 4: "闇",
}


class CLIChoiceManager:

    def __init__(
        self,
        board_view_renderer=None,
    ):

        self.context = None
        self.board_view_renderer = (
            board_view_renderer
            or BoardViewRenderer()
        )

    def bind_context(
        self,
        context,
    ):

        self.context = context
        self.board_view_renderer.context = context

    def select(
        self,
        player,
        choices,
        prompt,
        min_count=1,
        max_count=1,
        auto_choose_single=True,
    ):

        if not choices:

            if min_count == 0:
                return []

            return None

        # 単一自動選択
        if (
            auto_choose_single
            and len(choices) == 1
            and min_count == 1
            and max_count == 1
        ):

            return choices[0]

        selected = []

        remaining = list(choices)

        while True:

            print()
            print(prompt)

            print(
                f"Selected:"
                f" {len(selected)}"
            )

            choice_lines = (
                self._format_choice_lines(
                    player,
                    remaining,
                )
            )

            for line in choice_lines:
                print(
                    line
                )

            # confirm
            if len(selected) >= min_count:

                print(
                    "c: Confirm"
                )

            if self._has_look_top_deck_ability(player):
                print("t: Look at top of deck")

            print("b: Board view")
            print("q: Quit")

            raw = input("> ").strip()

            # quit
            if raw.lower() == "q":
                raise SystemExit()

            # board view
            if raw.lower() == "b":
                self.show_board_view(player)
                continue

            # look at top of deck
            if raw.lower() == "t":
                self._show_top_of_deck(player)
                continue

            # confirm
            if raw.lower() == "c":

                if len(selected) >= min_count:

                    # single return
                    if (
                        max_count == 1
                    ):

                        return (
                            selected[0]
                            if selected
                            else None
                        )

                    return selected

                continue

            try:

                index = int(raw)

            except ValueError:

                print("Invalid input")
                continue

            if not (
                0 <= index
                < len(remaining)
            ):

                print("Invalid choice")
                continue

            choice = remaining[index]

            selected.append(choice)

            remaining.remove(choice)

            print(
                f"Selected: "
                f"{self.format_choice(choice)}"
            )

            # max到達
            if (
                max_count is not None
                and len(selected)
                >= max_count
            ):

                # single return
                if max_count == 1:
                    return selected[0]

                return selected

    def _has_look_top_deck_ability(self, player):
        if player is None:
            return False
        battle_zone = getattr(player, "battle_zone", None)
        if battle_zone is None:
            return False
        for card in battle_zone.cards:
            for ability in getattr(card, "abilities", []):
                if isinstance(ability, LookTopDeckDuringTurnAbility):
                    return True
        return False

    def _show_top_of_deck(self, player):
        deck = getattr(player, "deck", None)
        if deck is None or not deck.cards:
            print("[Top of deck: empty]")
            return
        top_card = deck.cards[0]
        name = format_card_name(top_card)
        cost = getattr(top_card, "cost", "?")
        races = getattr(top_card, "race", [])
        race_str = (
            ", ".join(str(r) for r in races)
            if races
            else "—"
        )
        print(f"[Top of deck: {name} | Cost: {cost} | Race: {race_str}]")

    def select_mana_to_pay(
        self,
        player,
        amount,
        required_civilizations,
        tappable_mana,
        mana_value,
        mana_civilizations=None,
        spending_card=None,
    ):
        if mana_civilizations is None:
            mana_civilizations = card_civilizations
        selected = []
        available = list(tappable_mana)
        required_bits = civilization_bits(
            required_civilizations
        )

        for index, civilization in enumerate(
            required_bits
        ):
            remaining_bits = required_bits[
                index + 1:
            ]
            paid = payment_total(
                selected,
                mana_value,
            )
            choices = civilization_candidates(
                amount,
                civilization,
                remaining_bits,
                paid,
                available,
                mana_value,
                mana_civilizations,
            )
            choice = self.select(
                player,
                choices,
                prompt=self._mana_prompt(
                    "Pay civilization mana",
                    spending_card,
                    amount,
                    paid,
                    civilization,
                ),
                auto_choose_single=False,
            )
            if choice is None:
                return None

            selected.append(choice)
            available.remove(choice.card)

        while payment_total(
            selected,
            mana_value,
        ) < amount:
            paid = payment_total(
                selected,
                mana_value,
            )
            choices = remaining_mana_candidates(
                amount,
                paid,
                available,
                mana_value,
            )
            choice = self.select(
                player,
                choices,
                prompt=self._mana_prompt(
                    "Pay remaining mana",
                    spending_card,
                    amount,
                    paid,
                ),
                auto_choose_single=False,
            )
            if choice is None:
                return None

            selected.append(choice)
            available.remove(choice.card)

        if selected:
            print(
                "Tapped mana: "
                + ", ".join(
                    self._format_paid_mana(
                        selection,
                        mana_value,
                    )
                    for selection in selected
                )
            )

        return selected

    def _mana_prompt(
        self,
        title,
        spending_card,
        amount,
        paid,
        civilization=None,
    ):
        target = (
            format_card_name(spending_card)
            if spending_card is not None
            else "mana cost"
        )
        prompt = (
            f"{title} for {target}"
        )
        if civilization is not None:
            prompt = (
                f"{prompt}: "
                f"{_civilization_name(civilization)}"
            )

        return (
            f"{prompt}\n"
            f"Cost: {amount} | Paid: {paid}"
        )

    def show_board_view(
        self,
        player,
    ):

        print(
            self.board_view_renderer.render_board(
                player,
            )
        )

        while True:
            raw = input("(board)> ").strip().lower()

            if raw == "b":
                return

            detail = self.board_view_renderer.render_detail(
                raw,
                player,
            )
            if detail is None:
                print("Invalid board command")
                continue

            print(detail)

    def format_choice(
        self,
        choice,
    ):

        if choice is None:
            return "Skip"

        if isinstance(
            choice,
            ManaPaymentSelection,
        ):
            return self._format_mana_choice(
                choice
            )

        # trigger
        if (
            isinstance(choice, tuple)
            and len(choice) == 3
        ):

            ability, event, _ = choice

            return (
                f"{format_card_name(ability.owner_card)} "
                f"({event})"
            )

        if hasattr(choice, "name"):
            return format_card_name(choice)

        return format_action(choice)

    def _format_choice_lines(
        self,
        player,
        choices,
    ):

        rows = [
            self._choice_row_data(
                player,
                choice,
            )
            for choice in choices
        ]
        index_width = max(
            1,
            len(str(len(choices) - 1)),
        )
        cost_width = max(
            [1]
            + [
                len(row["cost"])
                for row in rows
                if row is not None
            ]
        )
        civ_width = max(
            [1]
            + [
                _display_width(row["civilization"])
                for row in rows
                if row is not None
            ]
        )

        lines = []
        for index, choice in enumerate(choices):
            row = rows[index]
            if row is None:
                lines.append(
                    f"{index:>{index_width}}: "
                    f"{self.format_choice(choice)}"
                )
                continue

            cost_cell = (
                f"[{row['cost']}]"
                .rjust(cost_width + 2)
            )
            civ_cell = (
                _pad_cell(
                    row["civilization"],
                    civ_width,
                    align="left",
                )
            )
            lines.append(
                f"{index:>{index_width}}: "
                f"{cost_cell} | "
                f"{civ_cell} | "
                f"{row['name']}"
            )

        return lines

    def _choice_row_data(
        self,
        player,
        choice,
    ):

        card = self._choice_card(choice)
        if card is None:
            return None

        if not self._choice_details_are_public(
            player,
            choice,
            card,
        ):
            return None

        return {
            "cost": str(
                self._choice_cost(card)
            ),
            "civilization": self._choice_civilization_label(
                choice,
                card,
            ),
            "name": format_card_name(card),
        }

    def _choice_card(
        self,
        choice,
    ):

        if isinstance(
            choice,
            ManaPaymentSelection,
        ):
            return choice.card

        if hasattr(choice, "name"):
            return choice

        return None

    def _choice_details_are_public(
        self,
        player,
        choice,
        card,
    ):

        if isinstance(
            choice,
            ManaPaymentSelection,
        ):
            return True

        if is_seal_card(card):
            return False

        zone = getattr(
            card,
            "zone",
            None,
        )
        zone_name = getattr(
            zone,
            "name",
            None,
        )

        if zone_name == "SHIELD":
            return bool(
                getattr(
                    card,
                    "shield_face_up",
                    False,
                )
            )

        if zone_name == "DECK":
            return bool(
                getattr(
                    card,
                    "deck_face_up",
                    False,
                )
            )

        if (
            zone_name == "HAND"
            and player is not None
            and getattr(card, "owner", None) is not None
            and getattr(card, "owner", None) is not player
        ):
            return False

        return True

    def _choice_cost(
        self,
        card,
    ):

        return getattr(
            card,
            "cost",
            "?",
        )

    def _choice_civilization_label(
        self,
        choice,
        card,
    ):

        if (
            isinstance(choice, ManaPaymentSelection)
            and choice.civilization is not None
        ):
            return _civilization_name_ja(
                choice.civilization
            )

        return civilization_label_ja(card)

    def _format_mana_choice(
        self,
        choice,
    ):
        card = choice.card
        value = 1
        if getattr(card, "owner", None) is not None:
            value = card.owner.mana_value(card)

        parts = [
            (
                f"[{tap_state_label(card)}] "
                f"[{civilization_label(card)}] "
                f"{format_card_name(card)}"
            )
        ]
        if choice.civilization is not None:
            parts.append(
                f"as {_civilization_name(choice.civilization)}"
            )
        if value != 1:
            parts.append(
                f"(value {value})"
            )

        return " ".join(parts)

    def _format_paid_mana(
        self,
        selection,
        mana_value,
    ):
        text = format_card_name(
            selection.card
        )
        if selection.civilization is not None:
            text = (
                f"{text} as "
                f"{_civilization_name(selection.civilization)}"
            )

        value = mana_value(
            selection.card
        )
        if value != 1:
            text = (
                f"{text} (value {value})"
            )

        return text


def _civilization_name(
    civilization,
):
    return _CIVILIZATION_NAMES.get(
        civilization,
        str(civilization),
    )


def _civilization_name_ja(
    civilization,
):
    return _CIVILIZATION_NAMES_JA.get(
        civilization,
        str(civilization),
    )


def civilization_label_ja(card):
    civilizations = card_civilizations(card)
    names = [
        name
        for bit, name in _CIVILIZATION_NAMES_JA.items()
        if civilizations & bit
    ]
    return "/".join(names) if names else "無色"


def _pad_cell(
    value,
    width,
    align="left",
):
    cell = f"[{value}]"
    padding = max(
        0,
        width + 2 - _display_width(cell),
    )
    if align == "right":
        return (" " * padding) + cell

    return cell + (" " * padding)


def _display_width(
    value,
):
    width = 0
    for char in str(value):
        width += (
            2
            if unicodedata.east_asian_width(char) in ("F", "W")
            else 1
        )

    return width
