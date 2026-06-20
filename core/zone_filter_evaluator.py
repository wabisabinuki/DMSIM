"""Evaluate structured zone filter JSON safely."""

from core.dsl_compare import COMPARISON_OPERATORS, compare_values
from core.ref_resolver import RefResolver
from effects.zones.zone_effect_utils import parse_zone


ZONE_FILTER_FIELDS = frozenset(
    (
        "zone",
    )
)


class ZoneFilterEvaluator:
    """Interpreter for the ZoneFilter DSL."""

    def __init__(
        self,
        game,
    ):
        self.game = game
        self.refs = RefResolver(game)

    def matches(
        self,
        zone,
        filter_spec,
        context=None,
    ):
        context = context or {}
        spec = filter_spec or {}

        if not isinstance(spec, dict):
            raise ValueError(
                f"zone filter must be an object: {spec!r}"
            )

        for key, value in spec.items():
            if key == "and":
                if not all(
                    self.matches(zone, item, context)
                    for item in _as_list(value)
                ):
                    return False
                continue

            if key == "or":
                if not any(
                    self.matches(zone, item, context)
                    for item in _as_list(value)
                ):
                    return False
                continue

            if key == "not":
                if self.matches(zone, value, context):
                    return False
                continue

            if key not in ZONE_FILTER_FIELDS:
                raise ValueError(
                    f"Unknown zone filter key: {key}"
                )

            if not self._matches_field(
                zone,
                value,
                context,
            ):
                return False

        return True

    def _matches_field(
        self,
        zone,
        expression,
        context,
    ):
        actual = self._zone_name(zone)
        if isinstance(expression, dict) and set(expression) != {"ref"}:
            _require_comparison_object(expression)
            for operator, raw_expected in expression.items():
                expected = self._expected_value(
                    raw_expected,
                    context,
                )
                if not compare_values(
                    actual,
                    operator,
                    expected,
                ):
                    return False
            return True

        expected = self._expected_value(
            expression,
            context,
        )
        return compare_values(
            actual,
            "eq",
            expected,
        )

    def _expected_value(
        self,
        value,
        context,
    ):
        resolved = self.refs.resolve(
            value,
            context,
        )
        if isinstance(resolved, str):
            return resolved.lower()
        if isinstance(resolved, list):
            return [
                item.lower() if isinstance(item, str) else item
                for item in resolved
            ]
        return resolved

    def _zone_name(
        self,
        zone,
    ):
        if hasattr(zone, "zone"):
            zone = zone.zone

        return parse_zone(zone).name.lower()


def _require_comparison_object(
    value,
):
    for key in value:
        if key not in COMPARISON_OPERATORS:
            raise ValueError(
                f"Unknown comparison operator: {key}"
            )


def _as_list(
    value,
):
    if value is None:
        return []

    if isinstance(
        value,
        list,
    ):
        return value

    return [
        value,
    ]
