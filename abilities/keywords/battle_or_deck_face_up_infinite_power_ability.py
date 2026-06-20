"""Power becomes effectively infinite while battling or revealed in deck."""

from abilities.base.continuous_ability import ContinuousAbility
from zones.zone_type import ZoneType


INFINITE_POWER = 1_000_000_000


class BattleOrDeckFaceUpInfinitePowerAbility(ContinuousAbility):

    def __init__(
        self,
        owner_card,
        game,
    ):
        super().__init__()
        self.owner_card = owner_card
        self.game = game

    def modify_power(
        self,
        creature,
        power,
    ):
        if creature is not self.owner_card:
            return power

        if self._is_battling(creature) or self._is_face_up_in_deck(creature):
            return max(
                power,
                INFINITE_POWER,
            )

        return power

    def _is_battling(
        self,
        creature,
    ):
        state = getattr(
            self.game,
            "state",
            None,
        )
        participants = (
            getattr(state, "current_battle_attacker", None),
            getattr(state, "current_battle_defender", None),
        )
        return creature in participants

    def _is_face_up_in_deck(
        self,
        creature,
    ):
        return (
            getattr(creature, "zone", None) == ZoneType.DECK
            and bool(getattr(creature, "deck_face_up", False))
        )


def build_battle_or_deck_face_up_infinite_power_ability(
    spec,
    card,
    game,
):
    return BattleOrDeckFaceUpInfinitePowerAbility(
        owner_card=card,
        game=game,
    )
