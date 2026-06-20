"""
Read-only CLI board view renderer.
"""

from core.pending_cards import visible_cards
from core.seal_utils import is_seal_card
from ui.card_display import (
    EVOLUTION_SOURCE_SEPARATOR,
    civilization_label,
    format_card_name,
    format_mana_zone_heading,
    ordered_battle_zone_cards,
    tap_state_label,
)


class BoardViewRenderer:
    """Render public board information from the turn player's view."""

    DETAIL_COMMANDS = {
        "om": ("opponent_mana", "Opponent Mana Zone"),
        "og": ("opponent_graveyard", "Opponent Graveyard"),
        "os": ("opponent_shields", "Opponent Shields"),
        "pg": ("player_graveyard", "Player Graveyard"),
        "ps": ("player_shields", "Player Shields"),
    }

    def __init__(
        self,
        context=None,
    ):

        self.context = context

    def render_board(
        self,
        fallback_player=None,
    ):

        player = self._turn_player(
            fallback_player,
        )
        opponent = self._opponent_for(
            player,
        )

        lines = [
            "",
            f"=== BOARD VIEW ({self._player_name(player)}) ===",
        ]

        lines.extend(
            self._render_opponent_summary(
                opponent,
            )
        )
        lines.extend(
            self._render_player_summary(
                player,
            )
        )
        lines.extend(
            [
                "",
                (
                    "Commands: om opponent mana | og opponent graveyard | "
                    "os opponent shields | pg player graveyard | "
                    "ps player shields | <card id> details | b back"
                ),
                "==================",
            ]
        )

        return "\n".join(lines)

    def render_detail(
        self,
        command,
        fallback_player=None,
    ):

        command = command.lower()
        card_detail = self._render_card_detail(
            command,
            fallback_player,
        )
        if card_detail is not None:
            return card_detail

        if command not in self.DETAIL_COMMANDS:
            return None

        player = self._turn_player(
            fallback_player,
        )
        opponent = self._opponent_for(
            player,
        )
        detail_type, title = self.DETAIL_COMMANDS[command]

        target_player = (
            opponent
            if detail_type.startswith("opponent")
            else player
        )

        if target_player is None:
            return "\n".join(
                [
                    "",
                    f"=== {title} ===",
                    " - Unavailable",
                ]
            )

        if detail_type.endswith("mana"):
            prefix = (
                "om"
                if target_player is opponent
                else "pm"
            )
            return self._render_titled_zone(
                self._mana_title(
                    target_player,
                    title,
                ),
                self._mana_lines(
                    target_player,
                    prefix,
                ),
            )

        if detail_type.endswith("graveyard"):
            prefix = (
                "og"
                if target_player is opponent
                else "pg"
            )
            return self._render_titled_zone(
                title,
                self._card_name_lines(
                    target_player.graveyard.cards,
                    prefix,
                ),
            )

        if detail_type.endswith("shields"):
            prefix = (
                "os"
                if target_player is opponent
                else "ps"
            )
            return self._render_titled_zone(
                title,
                self._shield_lines(
                    target_player,
                    prefix,
                ),
            )

        return None

    def _render_opponent_summary(
        self,
        opponent,
    ):

        lines = [
            "",
            f"[Opponent: {self._player_name(opponent)}]",
        ]

        if opponent is None:
            lines.append("Unavailable")
            return lines

        lines.append(
            "Hand: "
            f"{len(opponent.hand.cards)} | "
            "Deck: "
            f"{len(opponent.deck.cards)} | "
            "Graveyard: "
            f"{len(opponent.graveyard.cards)} | "
            "Mana: "
            f"{len(opponent.mana_zone.cards)} | "
            "Shields: "
            f"{self._shield_count(opponent)}"
        )
        lines.append("")
        lines.append("Battle Zone:")
        lines.extend(
            self._battle_lines(
                opponent,
                "ob",
            )
        )
        return lines

    def _render_player_summary(
        self,
        player,
    ):

        lines = [
            "",
            f"[Player: {self._player_name(player)}]",
        ]

        if player is None:
            lines.append("Unavailable")
            return lines

        lines.append(
            "Deck: "
            f"{len(player.deck.cards)} | "
            "Graveyard: "
            f"{len(player.graveyard.cards)} | "
            "Shields: "
            f"{self._shield_count(player)}"
        )
        lines.append("")
        lines.append("Hand:")
        lines.extend(
            self._card_name_lines(
                visible_cards(
                    player.hand.cards,
                ),
                "ph",
            )
        )
        lines.append("")
        lines.append(
            f"{format_mana_zone_heading(player)}:"
        )
        lines.extend(
            self._mana_lines(
                player,
                "pm",
            )
        )
        lines.append("")
        lines.append("Battle Zone:")
        lines.extend(
            self._battle_lines(
                player,
                "pb",
            )
        )
        return lines

    def _render_titled_zone(
        self,
        title,
        zone_lines,
    ):

        return "\n".join(
            [
                "",
                f"=== {title} ===",
                *zone_lines,
            ]
        )

    def _mana_title(
        self,
        player,
        title,
    ):

        return format_mana_zone_heading(
            player,
            title,
        )

    def _card_name_lines(
        self,
        cards,
        prefix=None,
    ):

        cards = list(
            visible_cards(cards)
        )
        if not cards:
            return [" - Empty"]

        return [
            self._card_line(
                card,
                prefix,
                index,
            )
            for index, card in enumerate(
                cards,
                start=1,
            )
        ]

    def _mana_lines(
        self,
        player,
        prefix,
    ):

        cards = visible_cards(
            player.mana_zone.cards,
        )
        if not cards:
            return [" - Empty"]

        lines = []
        for index, card in enumerate(
            cards,
            start=1,
        ):
            lines.append(
                f" - {self._card_ref(prefix, index)}"
                f"[{tap_state_label(card)}] "
                f"[{civilization_label(card)}] "
                f"{format_card_name(card)}"
            )

        return lines

    def _battle_lines(
        self,
        player,
        ref_prefix,
    ):

        entries = ordered_battle_zone_cards(player)
        if not entries:
            return [" - Empty"]

        lines = []
        for index, (card, is_attached_seal) in enumerate(
            entries,
            start=1,
        ):
            prefix = "    * " if is_attached_seal else " - "
            lines.append(
                f"{prefix}{self._card_ref(ref_prefix, index)}"
                f"{self._format_battle_card(card)}"
            )

        return lines

    def _shield_lines(
        self,
        player,
        ref_prefix,
    ):

        slots = self._shield_slots(player)
        if not slots:
            return [" - Empty"]

        lines = []
        for index, slot in enumerate(
            slots,
            start=1,
        ):
            ref = (
                self._card_ref(ref_prefix, index)
                if self._slot_has_public_card(slot)
                else ""
            )
            lines.append(
                f" - {index}: {ref}{self._format_shield_slot(slot)}"
            )
        return lines

    def _card_line(
        self,
        card,
        prefix,
        index,
    ):

        return (
            f" - {self._card_ref(prefix, index)}"
            f"{format_card_name(card)}"
        )

    def _card_ref(
        self,
        prefix,
        index,
    ):

        if not prefix:
            return ""

        return f"{prefix}{index} "

    def _render_card_detail(
        self,
        command,
        fallback_player=None,
    ):

        lookup = self._public_card_lookup(
            fallback_player,
        )
        card = lookup.get(command)
        if card is None:
            return None

        return self._format_card_detail(
            command,
            card,
        )

    def _public_card_lookup(
        self,
        fallback_player=None,
    ):

        player = self._turn_player(
            fallback_player,
        )
        opponent = self._opponent_for(
            player,
        )
        lookup = {}

        self._add_zone_lookup(
            lookup,
            "ph",
            visible_cards(
                getattr(player.hand, "cards", ())
            ) if player is not None else (),
        )
        self._add_zone_lookup(
            lookup,
            "pm",
            visible_cards(
                getattr(player.mana_zone, "cards", ())
            ) if player is not None else (),
        )
        self._add_zone_lookup(
            lookup,
            "pg",
            visible_cards(
                getattr(player.graveyard, "cards", ())
            ) if player is not None else (),
        )
        self._add_zone_lookup(
            lookup,
            "pb",
            [
                card
                for card, _ in ordered_battle_zone_cards(player)
            ] if player is not None else (),
        )
        self._add_shield_lookup(
            lookup,
            "ps",
            player,
        )

        self._add_zone_lookup(
            lookup,
            "om",
            visible_cards(
                getattr(opponent.mana_zone, "cards", ())
            ) if opponent is not None else (),
        )
        self._add_zone_lookup(
            lookup,
            "og",
            visible_cards(
                getattr(opponent.graveyard, "cards", ())
            ) if opponent is not None else (),
        )
        self._add_zone_lookup(
            lookup,
            "ob",
            [
                card
                for card, _ in ordered_battle_zone_cards(opponent)
            ] if opponent is not None else (),
        )
        self._add_shield_lookup(
            lookup,
            "os",
            opponent,
        )

        return lookup

    def _add_zone_lookup(
        self,
        lookup,
        prefix,
        cards,
    ):

        for index, card in enumerate(
            list(cards),
            start=1,
        ):
            lookup[f"{prefix}{index}"] = card

    def _add_shield_lookup(
        self,
        lookup,
        prefix,
        player,
    ):

        if player is None:
            return

        for index, slot in enumerate(
            self._shield_slots(player),
            start=1,
        ):
            public_cards = self._public_slot_cards(slot)
            if public_cards:
                lookup[f"{prefix}{index}"] = public_cards[0]

    def _format_card_detail(
        self,
        card_ref,
        card,
    ):

        lines = [
            "",
            f"=== Card Detail ({card_ref}) ===",
            f"Name: {self._detail_card_name(card)}",
        ]

        card_types = self._card_types(card)
        if card_types:
            lines.append(
                f"Type: {card_types}"
            )

        if hasattr(card, "cost"):
            lines.append(
                f"Cost: {getattr(card, 'cost')}"
            )

        lines.append(
            f"Civilization: {civilization_label(card)}"
        )

        current_power = getattr(
            card,
            "get_current_power",
            None,
        )
        if current_power is not None:
            lines.append(
                f"Power: {self._detail_power_text(card)}"
            )

        races = getattr(
            card,
            "race_ja",
            None,
        ) or getattr(
            card,
            "race",
            None,
        )
        if races:
            if isinstance(races, str):
                race_text = races
            else:
                race_text = ", ".join(
                    str(race)
                    for race in races
                )
            lines.append(
                f"Race: {race_text}"
            )

        if hasattr(card, "tapped"):
            lines.append(
                f"State: {tap_state_label(card)}"
            )

        if getattr(
            card,
            "summoning_sick",
            False,
        ):
            lines.append("Summoning Sick: yes")

        if getattr(
            card,
            "is_hyper_mode_active",
            False,
        ):
            lines.append("Hyper Mode: active")

        effect_texts = getattr(
            card,
            "effect_texts_ja",
            (),
        ) or ()
        if isinstance(effect_texts, str):
            effect_texts = [effect_texts]
        if effect_texts:
            lines.append("Text:")
            lines.extend(
                f" - {text}"
                for text in effect_texts
            )

        return "\n".join(lines)

    def _detail_power_text(
        self,
        card,
    ):

        current_power = card.get_current_power()
        hyper_power = getattr(
            card,
            "hyper_power",
            None,
        )
        if (
            hyper_power is not None
            and not getattr(
                card,
                "is_hyper_mode_active",
                False,
            )
        ):
            return (
                f"{current_power} "
                f"(Hyper Mode: {hyper_power})"
            )

        return str(current_power)

    def _detail_card_name(
        self,
        card,
    ):

        return getattr(
            card,
            "name",
            format_card_name(card),
        )

    def _card_types(
        self,
        card,
    ):

        card_types = getattr(
            card,
            "card_types",
            (),
        )
        labels = []
        for card_type in card_types:
            labels.append(
                getattr(
                    card_type,
                    "name",
                    str(card_type),
                )
            )

        return "/".join(labels)

    def _format_battle_card(
        self,
        card,
    ):

        if is_seal_card(card):
            return format_card_name(
                card,
                mark_battle_label=False,
            )

        parts = [
            (
                f"[{tap_state_label(card)}] "
                f"{format_card_name(card, mark_battle_label=False)}"
            )
        ]

        current_power = getattr(
            card,
            "get_current_power",
            None,
        )
        if current_power is not None:
            parts.append(
                f"Power: {current_power()}"
            )

        if getattr(
            card,
            "summoning_sick",
            False,
        ):
            parts.append("Summoning Sick")

        if getattr(
            card,
            "is_hyper_mode_active",
            False,
        ):
            parts.append("Hyper Mode")

        line = " | ".join(parts)

        sources = self._evolution_source_names(card)
        if sources:
            line = (
                f"{line} "
                f"(source: {EVOLUTION_SOURCE_SEPARATOR.join(sources)})"
            )

        return line

    def _format_shield_slot(
        self,
        slot,
    ):

        cards = self._slot_cards(slot)
        if not cards:
            return "[FACE DOWN]"

        labels = []
        for card in cards:
            if self._is_face_up_shield(card):
                labels.append(
                    f"{format_card_name(card)} [FACE UP]"
                )
            else:
                labels.append("[FACE DOWN]")

        return " / ".join(labels)

    def _slot_has_public_card(
        self,
        slot,
    ):

        return bool(
            self._public_slot_cards(slot)
        )

    def _public_shield_cards(
        self,
        player,
    ):

        if player is None:
            return []

        cards = []
        for slot in self._shield_slots(player):
            cards.extend(
                self._public_slot_cards(slot)
            )

        return cards

    def _public_slot_cards(
        self,
        slot,
    ):

        return [
            card
            for card in self._slot_cards(slot)
            if self._is_face_up_shield(card)
        ]

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

        return len(
            visible_cards(
                player.shield_zone.cards,
            )
        )

    def _shield_slots(
        self,
        player,
    ):

        shield_zone = player.shield_zone
        slots = getattr(
            shield_zone,
            "slots",
            None,
        )
        if slots:
            return list(slots)

        return [
            [card]
            for card in visible_cards(
                shield_zone.cards,
            )
        ]

    def _slot_cards(
        self,
        slot,
    ):

        cards = getattr(
            slot,
            "cards",
            None,
        )
        if cards is None:
            cards = slot

        return visible_cards(cards)

    def _is_face_up_shield(
        self,
        card,
    ):

        return bool(
            getattr(
                card,
                "shield_face_up",
                False,
            )
        )

    def _evolution_source_names(
        self,
        card,
    ):

        names = []
        for source in getattr(
            card,
            "evolution_sources",
            [],
        ):
            names.append(
                format_card_name(
                    source,
                    mark_evolution=False,
                    mark_battle_label=False,
                )
            )
            names.extend(
                self._evolution_source_names(
                    source,
                )
            )

        return names

    def _turn_player(
        self,
        fallback_player,
    ):

        state = getattr(
            self.context,
            "state",
            None,
        )
        current_player = getattr(
            state,
            "current_player",
            None,
        )
        return current_player or fallback_player

    def _opponent_for(
        self,
        player,
    ):

        if player is None:
            return None

        state = getattr(
            self.context,
            "state",
            None,
        )
        players = getattr(
            state,
            "players",
            (),
        )
        for candidate in players:
            if candidate is not player:
                return candidate

        return None

    def _player_name(
        self,
        player,
    ):

        if player is None:
            return "Unavailable"

        return getattr(
            player,
            "name",
            str(player),
        )
