"""
攻撃対象や効果の対象となるカード、プレイヤーを選択するためのヘルパークラス。
"""

from core.pending_cards import is_card_pending
from core.seal_utils import is_ignored_by_seal
from events.target_event import CardChosenEvent


class TargetSelector:

    def __init__(
        self,
        context,
    ):

        self.context = context

    def select(
        self,
        player,
        options,
        prompt="Choose option",
        auto_choose_single=True,
        can_skip=False,
    ):

        options = self._visible_options(options)
        choice_player = self._choice_player_for(
            player,
            options,
        )

        if can_skip:
            options = [None] + options

        selected = (
            self.context
            .choice_manager
            .select(
                choice_player,
                options,
                prompt,
                auto_choose_single=(
                    auto_choose_single
                ),
            )
        )
        self._publish_card_chosen(
            choice_player,
            selected,
            prompt,
        )
        return selected

    def select_multiple(
        self,
        player,
        options,
        prompt="Choose options",
        min_count=1,
        max_count=None,
        can_skip=False,
    ):
        options = self._visible_options(options)
        choice_player = self._choice_player_for(
            player,
            options,
        )

        if can_skip:
            min_count = 0
        
        if max_count is None:
            max_count = len(options)

        res = (
            self.context
            .choice_manager
            .select(
                choice_player,
                options,
                prompt,
                min_count=min_count,
                max_count=max_count,
            )
        )
        if res is None:
            return []
        if isinstance(res, list):
            selected = res
        else:
            selected = [res]

        for choice in selected:
            self._publish_card_chosen(
                choice_player,
                choice,
                prompt,
            )

        return selected

    def _visible_options(
        self,
        options,
    ):

        return [
            option
            for option in options
            if (
                option is None
                or (
                    not is_card_pending(option)
                    and not is_ignored_by_seal(option)
                )
            )
        ]

    def _choice_player_for(
        self,
        player,
        options,
    ):
        for ability in self._choice_replacement_abilities():
            replacement = getattr(
                ability,
                "choice_player_for",
                None,
            )
            if replacement is None:
                continue

            choice_player = replacement(
                player,
                options,
            )
            if choice_player is not None:
                return choice_player

        return player

    def _choice_replacement_abilities(
        self,
    ):
        abilities = []
        state = getattr(
            self.context,
            "state",
            None,
        )
        for player in getattr(
            state,
            "players",
            (),
        ):
            for zone in (
                player.battle_zone,
                player.mana_zone,
                player.graveyard,
                player.shield_zone,
            ):
                for card in zone.cards:
                    if is_card_pending(card):
                        continue

                    abilities.extend(
                        getattr(
                            card,
                            "abilities",
                            (),
                        )
                    )

        return abilities

    def _publish_card_chosen(
        self,
        player,
        choice,
        prompt,
    ):
        if choice is None:
            return

        if not hasattr(choice, "owner"):
            return

        self.context.event_manager.publish(
            CardChosenEvent(
                player,
                choice,
                prompt=prompt,
            )
        )
