"""Continuous trait that prevents spell casting."""

from abilities.base.continuous_ability import (
    ContinuousAbility,
)
from abilities.active_condition import active_if_matches


class CannotCastSpellsAbility(ContinuousAbility):

    def __init__(
        self,
        affected_player="opponent",
        active_if=None,
        max_cost=None,
        exact_cost=None,
        civilizations=None,
    ):

        super().__init__()
        self.affected_player = affected_player
        self.active_if = active_if
        self.max_cost = max_cost
        self.exact_cost = exact_cost
        self.civilizations = civilizations

    def is_active_for(
        self,
        source_card,
    ):

        return active_if_matches(
            self.active_if,
            source_card,
            None,
        )

    def prevents_spell_cast(
        self,
        source_card,
        player,
        spell=None,
    ):

        if not self.is_active_for(source_card):
            return False

        if self.affected_player == "opponent":
            affected = player != source_card.owner
        elif self.affected_player == "controller":
            affected = player == source_card.owner
        elif self.affected_player == "all":
            affected = True
        else:
            affected = False

        if not affected:
            return False

        return self._matches_spell(spell)

    def _matches_spell(
        self,
        spell,
    ):

        if spell is None:
            return True

        cost = self._spell_cost(spell)
        if self.max_cost is not None and cost > self.max_cost:
            return False

        if self.exact_cost is not None and cost != self.exact_cost:
            return False

        if self.civilizations is not None:
            spell_civilizations = self._spell_civilizations(spell)
            if (
                spell_civilizations
                & self.civilizations
            ) == 0:
                return False

        return True

    def _spell_cost(
        self,
        spell,
    ):

        face = getattr(
            spell,
            "spell_face",
            None,
        )
        if face is not None:
            return face.cost

        return spell.cost

    def _spell_civilizations(
        self,
        spell,
    ):

        face = getattr(
            spell,
            "spell_face",
            None,
        )
        if face is not None:
            return face.civilizations

        return spell.civilizations
