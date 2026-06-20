"""Powered Breaker keyword ability.

Breaks 1 + floor(current_power / 6000) shields when attacking.
"""

from abilities.keywords.breaker_ability import BreakerAbility


class PoweredBreakerAbility(BreakerAbility):

    def __init__(self, active_if=None):
        super().__init__(break_count=1, active_if=active_if)

    def get_break_options(self, creature):
        if not self.is_active_for(creature):
            return []
        power = creature.get_current_power()
        return [1 + power // 6000]
