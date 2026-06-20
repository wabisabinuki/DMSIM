"""Replacement attempt matching for v2 replacement ability specs."""

from abilities.v2.event_map import event_name, event_types
from abilities.v2.spec_schema import EVENT_KEYS
from core.card_filter_evaluator import CardFilterEvaluator
from core.dsl_compare import compare_values
from core.effect_argument_resolver import EffectArgumentResolver
from events.destroy_attempt_event import DestroyAttemptEvent
from effects.zones.zone_effect_utils import parse_zone


class ReplacementAttemptMatcher:
    """Match replacement attempt specs against incoming events."""

    FIELD_MATCHERS = {
        "breaker": "_match_breaker",
        "card": "_match_card",
        "card_filter": "_match_card_filter",
        "from_zone": "_match_from_zone",
        "to_zone": "_match_to_zone",
    }

    def __init__(
        self,
        game,
        owner_card,
        attempt,
    ):
        self.game = game
        self.owner_card = owner_card
        self.attempt = attempt or {}
        self.args = EffectArgumentResolver(game)
        self.card_filters = CardFilterEvaluator(game)

    def event_name(
        self,
    ):
        return event_name(
            self.event_value()
        )

    def event_types(
        self,
    ):
        return event_types(
            self.event_value()
        )

    def event_value(
        self,
    ):
        for key in EVENT_KEYS:
            if key in self.attempt:
                return self.attempt[key]

        return None

    def matches(
        self,
        event,
    ):
        return (
            self._event_matches(event)
            and all(
                getattr(self, handler_name)(self.attempt[key], event)
                for key, handler_name in self.FIELD_MATCHERS.items()
                if key in self.attempt
            )
        )

    def _event_matches(
        self,
        event,
    ):
        if isinstance(event, self.event_types()):
            return True

        return (
            "zone_change_attempt" in _as_tuple(self.event_name())
            and isinstance(event, DestroyAttemptEvent)
        )

    def _match_breaker(
        self,
        value,
        event,
    ):
        context = self.args.context(
            self.owner_card.owner,
            source_card=self.owner_card,
            event=event,
        )
        expected = self.args.value(
            value,
            context,
        )
        return getattr(
            event,
            "breaker",
            None,
        ) is expected

    def _match_card(
        self,
        value,
        event,
    ):
        context = self.args.context(
            self.owner_card.owner,
            source_card=self.owner_card,
            event=event,
        )
        expected = self.args.value(
            value,
            context,
        )
        return getattr(
            event,
            "card",
            None,
        ) is expected

    def _match_card_filter(
        self,
        value,
        event,
    ):
        context = self.args.context(
            self.owner_card.owner,
            source_card=self.owner_card,
            event=event,
        )
        card = getattr(event, "card", None)

        # 移動試行中のカードは pending 状態になっている。CardFilterEvaluator は
        # pending カードを一律に除外するため、フィルタ評価の間だけ pending を
        # 外して「これから移動するカードの種別」で判定する（直後に必ず戻す）。
        was_pending = getattr(card, "is_pending", False)
        if was_pending:
            card.is_pending = False
        try:
            return self.card_filters.matches(
                card,
                value,
                context,
            )
        finally:
            if was_pending:
                card.is_pending = True

    def _match_from_zone(
        self,
        value,
        event,
    ):
        return self._match_zone_expression(
            getattr(event, "from_zone", None),
            value,
            event,
        )

    def _match_to_zone(
        self,
        value,
        event,
    ):
        return self._match_zone_expression(
            getattr(event, "to_zone", None),
            value,
            event,
        )

    def _match_zone_expression(
        self,
        actual,
        value,
        event,
    ):
        if actual is not None:
            actual = parse_zone(actual).name.lower()

        context = self.args.context(
            self.owner_card.owner,
            source_card=self.owner_card,
            event=event,
        )
        if isinstance(value, dict) and set(value) != {"ref"}:
            return all(
                compare_values(
                    actual,
                    operator,
                    _normalize_string_value(
                        self.args.value(raw_expected, context)
                    ),
                )
                for operator, raw_expected in value.items()
            )

        return compare_values(
            actual,
            "eq",
            _normalize_string_value(
                self.args.value(value, context)
            ),
        )


def _as_tuple(
    value,
):
    if isinstance(value, list):
        return tuple(value)

    return (value,)


def _normalize_string_value(
    value,
):
    if isinstance(value, str):
        return value.lower()

    if isinstance(value, list):
        return [
            item.lower() if isinstance(item, str) else item
            for item in value
        ]

    return value
