"""Z Rush marker ability.

Z Rush is handled by state-based actions when a shield leaves. It does not
subscribe to events or create effects.
"""

from abilities.base.continuous_ability import (
    ContinuousAbility
)


class ZRushAbility(ContinuousAbility):

    def __init__(
        self,
        owner_card=None,
        game=None,
    ):

        super().__init__()
        self.owner_card = owner_card
        self.game = game
