"""Charger effect marker for spells."""

from effects.base.base_effect import BaseEffect


class ChargerEffect(BaseEffect):
    """Mark the source spell to move to mana after it finishes resolving."""

    def resolve(self):
        if self.source_card is None:
            return False

        self.source_card.charger_to_mana = True
        return True
