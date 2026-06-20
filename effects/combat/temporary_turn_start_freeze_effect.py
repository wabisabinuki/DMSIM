"""Temporarily prevents a card from untapping at turn start."""

from effects.base.enchant_effect import EnchantEffect
from effects.combat.target_reference import resolve_target_reference


class TemporaryTurnStartFreezeEffect(EnchantEffect):

    def __init__(
        self,
        game,
        target,
        duration_type,
        source_card=None,
    ):
        super().__init__(
            source_card=source_card,
            target_card=None,
            duration_type=duration_type,
            game=game,
            attachment_attr="temporary_turn_start_freezes",
        )
        self.target = target

    def can_attempt(
        self,
    ):
        return self._target() is not None

    def can_resolve(
        self,
        game_state,
    ):
        return self._target() is not None

    def resolve(
        self,
    ):
        target_card = self._target()
        if target_card is None:
            return False

        self.target_card = target_card
        return super().resolve()

    def prevents_turn_start_untap_for(
        self,
        player,
    ):
        if not self.is_active:
            return False

        return getattr(
            self.target_card,
            "owner",
            None,
        ) == player

    def _target(
        self,
    ):
        return resolve_target_reference(
            self.target,
            self.package_context,
        )

    def __str__(
        self,
    ):
        return (
            "TemporaryTurnStartFreezeEffect("
            f"target={self.target_card}, "
            f"until {self.duration_type})"
        )
