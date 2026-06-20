"""Generic shield breaker keyword abilities."""

from abilities.base.continuous_ability import (
    ContinuousAbility
)

from abilities.active_condition import active_if_matches


class BreakerAbility(ContinuousAbility):

    def __init__(
        self,
        break_count,
        active_if=None,
    ):

        super().__init__()
        self.break_count = break_count
        self.active_if = active_if

    def is_active_for(
        self,
        creature,
    ):

        return active_if_matches(
            self.active_if,
            creature,
            getattr(self, "game", None),
        )

    def get_break_options(
        self,
        creature,
    ):

        if not self.is_active_for(creature):
            return []

        return [self.break_count]
    

class WBreakerAbility(BreakerAbility):

    def __init__(
        self,
        active_if=None,
    ):

        super().__init__(
            break_count=2,
            active_if=active_if,
        )


class TBreakerAbility(BreakerAbility):

    def __init__(
        self,
        active_if=None,
    ):

        super().__init__(
            break_count=3,
            active_if=active_if,
        )

class QBreakerAbility(BreakerAbility):

    def __init__(
        self,
        active_if=None,
    ):

        super().__init__(
            break_count=4,
            active_if=active_if,
        )


class WorldBreakerAbility(BreakerAbility):

    def __init__(
        self,
        game,
        active_if=None,
    ):

        super().__init__(
            break_count=1,
            active_if=active_if,
        )
        self.game = game

    def get_break_options(
        self,
        creature,
    ):

        if not self.is_active_for(creature):
            return []

        opponent = self.game.query.get_opponent(
            creature.owner
        )
        shield_count = getattr(
            opponent.shield_zone,
            "shield_count",
            None,
        )
        return [
            max(
                1,
                shield_count()
                if shield_count is not None
                else len(opponent.shield_zone.cards),
            )
        ]
