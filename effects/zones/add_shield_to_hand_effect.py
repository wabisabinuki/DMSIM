"""Effect that adds one of your shields to hand without using S Trigger."""

from effects.base.base_effect import BaseEffect


class AddShieldToHandEffect(BaseEffect):

    def __init__(
        self,
        player,
        game,
        target="own_shields",
        amount=1,
        optional=True,
        exclude_face_up=False,
        disable_s_trigger=True,
    ):
        super().__init__()
        self.player = player
        self.game = game
        self.target = target
        self.amount = amount
        self.optional = optional
        self.exclude_face_up = exclude_face_up
        self.disable_s_trigger = disable_s_trigger

    def can_attempt(self):
        shields = self._shield_options()
        if self.optional:
            return bool(shields)

        return len(shields) >= self._amount()

    def resolve(self):
        shields = self._shield_options()
        if not shields:
            return False

        selected = self._choose_shields(shields)
        if not selected:
            return False

        shield_cards = [
            shield_card
            for shield in selected
            for shield_card in self._shield_cards_for(
                shield.owner,
                shield,
            )
        ]
        previous_suppressed = [
            (
                shield_card,
                getattr(
                    shield_card,
                    "s_trigger_suppressed",
                    False,
                ),
            )
            for shield_card in shield_cards
        ]
        for shield_card in shield_cards:
            shield_card.s_trigger_suppressed = (
                self.disable_s_trigger
            )

        try:
            moved = self.game.card_mover.move_shield_slots_to_hand_batch(
                shields=selected,
                owner=self.player,
                reason=(
                    "shield_to_hand_no_trigger"
                    if self.disable_s_trigger
                    else "shield_to_hand"
                ),
            )
        finally:
            for shield_card, was_suppressed in previous_suppressed:
                shield_card.s_trigger_suppressed = was_suppressed

        return moved

    def _choose_shields(self, shields):
        amount = self._amount()
        if amount <= 0:
            return []

        if len(shields) < amount and not self.optional:
            return []

        amount = min(amount, len(shields))
        if amount == 1:
            shield = self.game.target_selector.select(
                self.player,
                shields,
                prompt="Choose a shield to add to hand",
                can_skip=self.optional,
            )
            return [] if shield is None else [shield]

        selected = self.game.target_selector.select_multiple(
            self.player,
            shields,
            prompt="Choose shields to add to hand",
            min_count=0 if self.optional else amount,
            max_count=amount,
            can_skip=self.optional,
        )
        selected = selected[:amount]
        if len(selected) < amount and not self.optional:
            return []

        return selected

    def _amount(self):
        return int(self.amount)

    def _shield_options(self):
        if self.target != "own_shields":
            raise ValueError(
                f"Unknown shield target: {self.target}"
            )

        visible_shields = getattr(
            self.player.shield_zone,
            "visible_shields",
            None,
        )
        if visible_shields is not None:
            shields = visible_shields()
        else:
            shields = list(self.player.shield_zone.cards)

        if self.exclude_face_up:
            shields = [
                shield
                for shield in shields
                if not self._shield_has_face_up_card(shield)
            ]

        return shields

    def _shield_has_face_up_card(self, shield):
        for shield_card in self._shield_cards_for(
            shield.owner,
            shield,
        ):
            if getattr(
                shield_card,
                "shield_face_up",
                False,
            ):
                return True

        return False

    def _shield_cards_for(
        self,
        player,
        shield,
    ):

        shield_cards = getattr(
            player.shield_zone,
            "shield_cards",
            None,
        )
        if shield_cards is None:
            slot_cards = getattr(
                player.shield_zone,
                "slot_cards",
                None,
            )
            if slot_cards is None:
                return [shield]

            cards = slot_cards(shield)
            return cards or [shield]

        cards = shield_cards(shield)
        if not cards:
            return [shield]

        return cards
