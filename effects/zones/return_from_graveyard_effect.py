"""Effect that returns a card instance from graveyard to battle."""

from effects.base.base_effect import BaseEffect
from core.pending_cards import is_card_pending
from zones.zone_type import ZoneType


class ReturnFromGraveyardEffect(BaseEffect):

    def __init__(
        self,
        game,
        target="self",
        tapped=False,
        optional=True,
    ):
        super().__init__()
        self.game = game
        self.target = target
        self.tapped = tapped
        self.optional = optional

    def can_attempt(self):
        card = self._target_card()
        owner = getattr(
            card,
            "owner",
            None,
        )
        return (
            card is not None
            and owner is not None
            and getattr(
                card,
                "zone",
                None,
            ) == ZoneType.GRAVEYARD
            and not is_card_pending(card)
            and card in owner.graveyard.cards
            and card.can_exist_in_battle_alone()
        )

    def resolve(self):
        card = self._target_card()
        if card is None or not self.can_attempt():
            return False

        if self.optional:
            proceed = self.game.choice_manager.select(
                card.owner,
                [True, False],
                prompt=f"Return {card.name} from graveyard?",
            )
            if not proceed:
                return False

        if hasattr(
            card,
            "lock_hyper_mode",
        ):
            card.lock_hyper_mode()

        moved = self.game.card_mover.move(
            card=card,
            owner=card.owner,
            from_zone=ZoneType.GRAVEYARD,
            to_zone=ZoneType.BATTLE,
            reason="return_from_graveyard",
        )
        if moved:
            card.tapped = bool(self.tapped)
            if hasattr(
                card,
                "lock_hyper_mode",
            ):
                card.lock_hyper_mode()

        return bool(moved)

    def _target_card(self):
        if self.target == "self":
            return self.source_card

        raise ValueError(
            f"Unknown return_from_graveyard target: {self.target}"
        )
