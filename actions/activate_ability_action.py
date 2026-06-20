"""Action for activating an activated ability."""


class ActivateAbilityAction:

    def __init__(
        self,
        player,
        ability,
        source_card,
    ):
        self.player = player
        self.ability = ability
        self.source_card = source_card
