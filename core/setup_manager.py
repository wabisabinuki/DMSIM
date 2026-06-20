"""
ゲーム開始時のセットアップ（シールドの配置、手札5枚のドロー、能力の登録など）を管理するクラス。
"""

# - game setup
# - 初期シャッフル
# - シールド生成
# - 初期ドロー
# - owner設定
# - 初期ability登録

import random

from zones.zone_type import (
    ZoneType
)


class SetupManager:

    def __init__(
        self,
        context,
    ):

        self.context = context

    def setup_game(self):

        for player in (
            self.context.state.players
        ):

            self.setup_player(
                player
            )

    def setup_player(
        self,
        player,
    ):

        self.assign_card_owners(
            player
        )

        self.register_abilities(
            player
        )

        self.shuffle_deck(
            player
        )

        self.setup_shields(
            player
        )

        self.draw_opening_hand(
            player
        )

        

    def assign_card_owners(
        self,
        player,
    ):

        for card in player.deck.cards:

            card.owner = player
            card.zone = ZoneType.DECK

    def register_abilities(
        self,
        player,
    ):

        for card in player.deck.cards:

            card.register_abilities(
                self.context.event_manager
            )

    def shuffle_deck(
        self,
        player,
    ):

        random.shuffle(
            player.deck.cards
        )

    def setup_shields(
        self,
        player,
    ):

        for _ in range(5):

            card = (
                player.deck.cards[0]
            )

            self.context.card_mover.move(
                card=card,
                owner=player,
                from_zone=(
                    ZoneType.DECK
                ),
                to_zone=(
                    ZoneType.SHIELD
                ),
                reason=(
                    "setup_shield"
                ),
            )

    def draw_opening_hand(
        self,
        player,
    ):

        player.draw(
            self.context.controller,
            5,
        )
