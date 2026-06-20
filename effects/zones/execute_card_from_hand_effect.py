"""Backward-compatible wrapper for hand execution effects."""

from effects.zones.execute_card_from_zone_effect import (
    ExecuteCardFromZoneEffect,
)


class ExecuteCardFromHandEffect(ExecuteCardFromZoneEffect):

    def __init__(
        self,
        player,
        game,
        card_type="element",
        max_cost=None,
        optional=True,
        prompt=None,
        filter_spec=None,
        ignore_cost=True,
    ):
        filter_spec = dict(filter_spec or {})
        if max_cost is not None:
            filter_spec.setdefault(
                "max_cost",
                max_cost,
            )

        super().__init__(
            player=player,
            game=game,
            from_zone="hand",
            card_type=card_type,
            filter_spec=filter_spec,
            optional=optional,
            prompt=prompt,
            ignore_cost=ignore_cost,
        )
