"""Put a creature into the battle zone without treating it as a summon."""

from cards.twin_pact_card import TwinPactCard
from effects.zones.move_card_effect import MoveCardEffect
from effects.zones.zone_effect_utils import merge_filter_spec


class PutCreatureFromZoneEffect(MoveCardEffect):

    def __init__(
        self,
        player,
        game,
        from_zone,
        amount=1,
        target_player="self",
        filter_spec=None,
        selection=None,
        optional=True,
        prompt=None,
        tapped=False,
        store_as=None,
        reason=None,
        summoning_sick=True,
    ):
        super().__init__(
            player=player,
            game=game,
            from_zone=from_zone,
            to_zone="battle",
            amount=amount,
            target_player=target_player,
            filter_spec=merge_filter_spec(
                {
                    "type": "creature",
                },
                filter_spec,
            ),
            selection=selection,
            optional=optional,
            prompt=(
                prompt
                or "Choose a creature to put into the battle zone"
            ),
            tapped=tapped,
            store_as=store_as,
            reason=reason or "put_creature",
        )
        self.summoning_sick = summoning_sick

    def _usage_type(
        self,
    ):
        return "creature"

    def _before_move(
        self,
        card,
    ):
        if isinstance(
            card,
            TwinPactCard,
        ):
            card.select_creature_face()

    def _after_move(
        self,
        card,
        owner,
    ):
        super()._after_move(
            card,
            owner,
        )

        if getattr(
            card,
            "is_evolution",
            False,
        ):
            card.summoning_sick = False
        else:
            card.summoning_sick = bool(
                self.summoning_sick
            )

        card.summon_turn = self.game.state.turn
