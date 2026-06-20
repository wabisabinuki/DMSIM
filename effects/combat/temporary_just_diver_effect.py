"""Temporary protection created by Just Diver."""

from effects.base.enchant_effect import EnchantEffect


class TemporaryJustDiverEffect(EnchantEffect):

    def __init__(
        self,
        game,
        target_card,
        duration_type,
    ):
        super().__init__(
            source_card=target_card,
            target_card=target_card,
            duration_type=duration_type,
            game=game,
            attachment_attr="temporary_just_diver_effects",
        )

    def prevents_being_attacked_by(
        self,
        attacker,
    ):
        return (
            self.is_active
            and attacker is not None
            and attacker.owner != self.target_card.owner
        )

    def prevents_being_blocked_by(
        self,
        blocker,
    ):
        return (
            self.is_active
            and blocker is not None
            and blocker.owner != self.target_card.owner
        )
