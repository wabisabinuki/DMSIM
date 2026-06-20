"""Temporarily grants registry-authored abilities to target cards."""

from core.effect_argument_resolver import EffectArgumentResolver
from core.creature_scope import creatures_for_scope
from effects.base.duration_effect import DurationEffect


class TemporaryAbilityEffect(DurationEffect):

    def __init__(
        self,
        game,
        player,
        target,
        ability,
        duration_type,
        source_card=None,
        scope=None,
    ):
        super().__init__(
            source_card=source_card,
            duration_type=duration_type,
            game=game,
        )
        self.player = player
        self.target = target
        self.scope = scope
        self.ability_spec = dict(ability)
        self.args = EffectArgumentResolver(game)
        self.grants = []

    def can_attempt(
        self,
    ):
        return bool(
            self._targets()
        )

    def can_resolve(
        self,
        game_state,
    ):
        return True

    def resolve(
        self,
    ):
        from abilities.registry import create_ability

        targets = self._targets()
        if not targets:
            return False

        for target in targets:
            abilities = create_ability(
                self.ability_spec,
                target,
                self.game,
            )
            if not isinstance(
                abilities,
                list,
            ):
                abilities = [
                    abilities,
                ]

            for ability in abilities:
                target.abilities.append(
                    ability
                )
                registered = self._register_if_needed(
                    target,
                    ability,
                )
                self.grants.append(
                    (
                        target,
                        ability,
                        registered,
                    )
                )

        self.register_duration()
        self.is_active = True
        self.game.duration_effect_manager.register_duration_effect(
            self
        )
        return True

    def unapply(
        self,
    ):
        for target, ability, registered in self.grants:
            if registered:
                ability.unregister()
            if ability in target.abilities:
                target.abilities.remove(
                    ability
                )

        self.grants = []
        super().unapply()

    def _targets(
        self,
    ):
        if self.scope is not None:
            if self.source_card is None:
                return []

            return creatures_for_scope(
                self.game,
                self.scope,
                self.source_card,
            )

        return self.args.cards(
            self.target,
            self._context(),
        )

    def _context(
        self,
    ):
        return self.args.context(
            self.player,
            source_card=self.source_card,
            package_context=self.package_context,
        )

    def _register_if_needed(
        self,
        target,
        ability,
    ):
        if not getattr(
            target,
            "abilities_registered",
            False,
        ):
            return False

        register = getattr(
            ability,
            "register",
            None,
        )
        if register is None:
            return False

        register(
            self.game.event_manager
        )
        return True

    def __str__(
        self,
    ):
        return (
            "TemporaryAbilityEffect("
            f"{self.ability_spec.get('id', 'ability')}, "
            f"until {self.duration_type})"
        )
