"""Effects and helpers for Hyper Mode."""

from effects.base.base_effect import BaseEffect
from core.pending_cards import is_card_pending
from core.seal_utils import is_ignored_by_seal, is_seal_card


class UnlockHyperModeEffect(BaseEffect):

    def __init__(
        self,
        card,
        controller,
        game,
    ):

        super().__init__()
        self.card = card
        self.controller = controller
        self.game = game

    def resolve(
        self,
    ):

        if (
            is_card_pending(self.card)
            or is_seal_card(self.card)
            or is_ignored_by_seal(self.card)
        ):
            return False

        self.card.unlock_hyper_mode_until_next_turn_start(
            self.controller,
            self.game.state,
        )


def expire_hyper_modes_for_turn_start(
    player,
    game_state,
):

    for card in player.battle_zone.cards[:]:
        if (
            is_card_pending(card)
            or is_seal_card(card)
            or is_ignored_by_seal(card)
        ):
            continue

        if not getattr(
            card,
            "is_hyper_mode_active",
            False,
        ):
            continue

        # 失効は「コントローラーの次のターン開始」。固定オフセット
        # （hyper_mode_expires_on_turn）ではなく登録ターンを基準に判定するため、
        # 追加ターンが挟まってもコントローラーの最初のターン開始で正しく失効する。
        registered_turn = getattr(
            card,
            "hyper_mode_registered_turn",
            None,
        )
        if (
            getattr(
                card,
                "hyper_mode_controller",
                None,
            ) == player
            and registered_turn is not None
            and game_state.turn > registered_turn
        ):
            card.lock_hyper_mode()
