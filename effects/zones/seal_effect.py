"""Effects for attaching seals."""

from core.effect_argument_resolver import EffectArgumentResolver
from effects.base.base_effect import BaseEffect


class AttachSealEffect(BaseEffect):

    def __init__(
        self,
        player,
        game,
        target="self",
        amount=1,
        seal_player=None,
    ):
        super().__init__()
        self.player = player
        self.game = game
        self.target = target
        self.amount = int(amount)
        self.seal_player = seal_player
        self.args = EffectArgumentResolver(game)

    def can_attempt(
        self,
    ):
        return bool(
            self._targets()
        )

    def resolve(
        self,
    ):
        attached = []
        for target in self._targets():
            player = self._seal_player(
                target,
            )
            attached.extend(
                self.game.seal_manager.attach_seals(
                    [target],
                    amount=self.amount,
                    player=player,
                )
            )

        return bool(attached)

    def _targets(
        self,
    ):
        context = self.args.context(
            self.player,
            source_card=self.source_card,
            package_context=self.package_context,
        )
        value = self.target
        if value in (
            None,
            "self",
            "source",
            "source_card",
        ):
            return [
                self.source_card,
            ] if self.source_card is not None else []

        return self.args.cards(
            value,
            context,
        )

    def _seal_player(
        self,
        target,
    ):
        if self.seal_player in (
            None,
            "target_owner",
        ):
            return getattr(
                target,
                "owner",
                self.player,
            )

        context = self.args.context(
            self.player,
            source_card=self.source_card,
            package_context=self.package_context,
        )
        return self.args.player(
            self.seal_player,
            context,
        )
