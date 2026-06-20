"""Evaluate structured card filter JSON safely."""

from cards.card import CardType
from cards.creature_card import CreatureCard
from cards.spell_card import SpellCard
from cards.twin_pact_card import TwinPactCard
from core.dsl_compare import COMPARISON_OPERATORS, compare_values
from core.pending_cards import is_card_pending
from core.seal_utils import is_ignored_by_seal, is_seal_card
from core.ref_resolver import RefResolver
from effects.composition.card_predicates import (
    CARD_TYPE_NAMES,
    CIVILIZATION_BITS,
    matches_card_filter as matches_legacy_card_filter,
)


CARD_FILTER_FIELDS = frozenset(
    (
        "card_type",
        "type",
        "civilization",
        "civilizations",
        "controller",
        "cost",
        "power",
        "race_ja",
        "is_evolution",
        "shield_face_up",
        "tapped",
        "zone",
        "has_keyword",
        "has_keyword_contains",
        "special_type",
        "special_types",
    )
)

LOWERCASE_EXPECTED_FIELDS = frozenset(
    (
        "card_type",
        "type",
        "civilization",
        "civilizations",
        "zone",
        "has_keyword",
        "special_type",
        "special_types",
    )
)

KEYWORD_ALIASES = {
    "s・トリガー": "shield_trigger",
    "sトリガー": "shield_trigger",
    "shield trigger": "shield_trigger",
}


class CardFilterEvaluator:
    """Interpreter for the CardFilter DSL used by targets and conditions."""

    FIELD_GETTERS = {
        "card_type": "_field_card_type",
        "type": "_field_card_type",
        "civilization": "_field_civilizations",
        "civilizations": "_field_civilizations",
        "controller": "_field_controller",
        "cost": "_field_cost",
        "power": "_field_power",
        "race_ja": "_field_races_ja",
        "is_evolution": "_field_is_evolution",
        "shield_face_up": "_field_shield_face_up",
        "tapped": "_field_tapped",
        "zone": "_field_zone",
        "has_keyword": "_field_has_keyword",
        "has_keyword_contains": "_field_has_keyword",
        "special_type": "_field_special_types",
        "special_types": "_field_special_types",
    }

    def __init__(
        self,
        game,
    ):
        self.game = game
        self.refs = RefResolver(game)

    def matches(
        self,
        card,
        filter_spec,
        context=None,
    ):
        context = context or {}

        if card is None or is_card_pending(card):
            return False

        if is_ignored_by_seal(card):
            return False

        spec = filter_spec or {}
        if not isinstance(spec, dict):
            raise ValueError(
                f"card filter must be an object: {spec!r}"
            )
        context = {
            **context,
            "usage_type": context.get("usage_type")
            or _usage_type_from_spec(spec),
        }

        for key, value in spec.items():
            if key == "and":
                if not all(
                    self.matches(card, item, context)
                    for item in _as_list(value)
                ):
                    return False
                continue

            if key == "or":
                if not any(
                    self.matches(card, item, context)
                    for item in _as_list(value)
                ):
                    return False
                continue

            if key == "not":
                if self.matches(card, value, context):
                    return False
                continue

            if key not in CARD_FILTER_FIELDS:
                raise ValueError(
                    f"Unknown card filter key: {key}"
                )

            if not self._matches_field(
                card,
                key,
                value,
                context,
            ):
                return False

        return True

    def _matches_field(
        self,
        card,
        field,
        expression,
        context,
    ):
        actual = self._field_value(
            card,
            field,
            context,
        )

        if isinstance(expression, dict) and set(expression) != {"ref"}:
            _require_comparison_object(expression)
            for operator, raw_expected in expression.items():
                expected = self._expected_value(
                    field,
                    raw_expected,
                    context,
                )
                if field == "race_ja":
                    if not self._matches_race_ja(
                        actual,
                        operator,
                        expected,
                    ):
                        return False
                    continue
                if field == "has_keyword_contains":
                    if not self._matches_has_keyword_contains(
                        actual,
                        operator,
                        expected,
                    ):
                        return False
                    continue
                if not compare_values(
                    actual,
                    operator,
                    expected,
                ):
                    return False
            return True

        expected = self._expected_value(
            field,
            expression,
            context,
        )
        if field == "race_ja":
            return self._matches_race_ja(
                actual,
                "eq",
                expected,
            )
        if field == "has_keyword_contains":
            return self._matches_has_keyword_contains(
                actual,
                "eq",
                expected,
            )
        return compare_values(
            actual,
            "eq",
            expected,
        )

    def _field_value(
        self,
        card,
        field,
        context,
    ):
        getter_name = self.FIELD_GETTERS.get(field)
        if getter_name is not None:
            return getattr(self, getter_name)(
                card,
                context,
            )

        raise ValueError(
            f"Unknown card filter key: {field}"
        )

    def _expected_value(
        self,
        field,
        value,
        context,
    ):
        resolved = self.refs.resolve(
            value,
            context,
        )

        if field == "controller" and isinstance(
            resolved,
            str,
        ):
            if resolved in (
                "controller",
                "self",
                "owner",
            ):
                return self.refs.resolve_ref(
                    "controller",
                    context,
                )
            if resolved == "opponent":
                return self.refs.resolve_ref(
                    "opponent",
                    context,
                )

        if field in LOWERCASE_EXPECTED_FIELDS:
            if isinstance(
                resolved,
                str,
            ):
                lowered = resolved.lower()
                if field == "has_keyword":
                    return KEYWORD_ALIASES.get(
                        lowered,
                        lowered,
                    )
                return lowered

            if isinstance(
                resolved,
                list,
            ):
                values = [
                    item.lower() if isinstance(item, str) else item
                    for item in resolved
                ]
                if field == "has_keyword":
                    return [
                        (
                            KEYWORD_ALIASES.get(item, item)
                            if isinstance(item, str)
                            else item
                        )
                        for item in values
                    ]
                return values

        return resolved

    def _field_card_type(
        self,
        card,
        context,
    ):
        return self._card_type_names(card)

    def _field_civilizations(
        self,
        card,
        context,
    ):
        if is_seal_card(card):
            return set()

        return self._civilization_names(
            getattr(
                card,
                "civilizations",
                0,
            )
        )

    def _field_controller(
        self,
        card,
        context,
    ):
        return getattr(
            card,
            "owner",
            None,
        )

    def _field_cost(
        self,
        card,
        context,
    ):
        if is_seal_card(card):
            return 0

        return self._card_cost(
            card,
            context,
            usage_type=self._usage_type(context),
        )

    def _field_power(
        self,
        card,
        context,
    ):
        return self._card_power(card)

    def _field_races_ja(
        self,
        card,
        context,
    ):
        races = set()
        if is_seal_card(card):
            return races

        for race in _as_list(
            getattr(
                card,
                "race_ja",
                (),
            )
        ):
            races.add(str(race))

        creature_face = getattr(
            card,
            "creature_face",
            None,
        )
        if creature_face is not None:
            for race in _as_list(
                getattr(
                    creature_face,
                    "race_ja",
                    (),
                )
            ):
                races.add(str(race))

        return races

    def _field_is_evolution(
        self,
        card,
        context,
    ):
        return bool(
            getattr(
                card,
                "is_evolution",
                False,
            )
        )

    def _field_shield_face_up(
        self,
        card,
        context,
    ):
        return bool(
            getattr(
                card,
                "shield_face_up",
                False,
            )
        )

    def _field_tapped(
        self,
        card,
        context,
    ):
        return bool(
            getattr(
                card,
                "tapped",
                False,
            )
        )

    def _field_zone(
        self,
        card,
        context,
    ):
        zone = getattr(
            card,
            "zone",
            None,
        )
        return (
            zone.name.lower()
            if zone is not None
            else None
        )

    def _field_special_types(
        self,
        card,
        context,
    ):
        """Return a frozenset of this card's special type tags (lowercased).

        ``special_type: "galaxy"`` distinguishes G城 (GalaxyCastle) from a
        plain 城, which both share ``card_type: "castle"``.
        """
        return frozenset(
            str(special_type).lower()
            for special_type in getattr(
                card,
                "special_types",
                (),
            )
        )

    def _field_has_keyword(
        self,
        card,
        context,
    ):
        """Return a frozenset of keyword ability IDs this card has.

        Allows filter specs like {"has_keyword": "shield_trigger"} using
        the existing _equals collection-membership check in dsl_compare.
        """
        keyword_ids = set()
        for ability in getattr(card, "abilities", ()):
            ability_id = getattr(ability, "ability_id", None)
            if ability_id:
                keyword_ids.add(ability_id)
        return frozenset(keyword_ids)

    def _card_type_names(
        self,
        card,
    ):
        names = set()
        if is_seal_card(card):
            return names

        if getattr(card, "is_element", False):
            names.add("element")
        if _is_creature_card(card):
            names.add("creature")
        if _is_spell_card(card):
            names.add("spell")
        if (
            "creature" not in names
            or (
                isinstance(card, TwinPactCard)
                and card.spell_face is not None
            )
        ):
            names.add("non_creature")

        for card_type in getattr(
            card,
            "card_types",
            (),
        ):
            for name, mapped_type in CARD_TYPE_NAMES.items():
                if mapped_type == card_type:
                    names.add(name.replace(" ", "_"))

        return names

    def _civilization_names(
        self,
        civilizations,
    ):
        return {
            name
            for name, bit in CIVILIZATION_BITS.items()
            if civilizations & bit
        }

    def _card_cost(
        self,
        card,
        context,
        usage_type=None,
    ):
        if isinstance(card, TwinPactCard):
            key = (
                str(usage_type).lower()
                if usage_type is not None
                else None
            )
            if key == "creature" and card.creature_face is not None:
                return card.creature_face.cost
            if key == "spell" and card.spell_face is not None:
                return card.spell_face.cost
            if (
                key == "non_creature"
                and card.spell_face is not None
            ):
                return card.spell_face.cost
            if card.selected_face is not None:
                return card.selected_face.cost

        return self.refs.resolve_ref(
            "source.cost",
            {
                **context,
                "source_card": card,
            },
        )

    def _card_power(
        self,
        card,
    ):
        get_current_power = getattr(
            card,
            "get_current_power",
            None,
        )
        if get_current_power is not None:
            return get_current_power()

        return getattr(
            card,
            "base_power",
            0,
        )

    def _usage_type(
        self,
        context,
    ):
        return context.get("usage_type")

    def _matches_race_ja(
        self,
        actual,
        operator,
        expected,
    ):
        matched = any(
            str(expected_race) in actual_race
            for expected_race in _as_list(expected)
            for actual_race in actual
        )
        if operator in (
            "eq",
            "contains",
        ):
            return matched
        if operator in (
            "ne",
            "not_contains",
        ):
            return not matched
        # race_ja は日本語の部分一致専用フィールド。一般の比較演算子に
        # フォールバックすると部分一致でない別の意味で黙って動くため拒否する。
        raise ValueError(
            f"Unsupported race_ja operator: {operator}"
        )

    def _matches_has_keyword_contains(
        self,
        actual,
        operator,
        expected,
    ):
        """ability_id の部分一致（例 "guardman" が "super_guardman" に一致）。

        `has_keyword` の完全一致と異なり、キーワード ID に指定文字列を
        含むかで判定する。スーパーガードマンが「ガードマン」を持つ
        クリーチャー（`guardman` / `super_guardman` 等）をまとめて対象に
        するために使う。
        """
        matched = any(
            str(expected_kw) in str(actual_kw)
            for expected_kw in _as_list(expected)
            for actual_kw in actual
        )
        if operator in (
            "eq",
            "contains",
        ):
            return matched
        if operator in (
            "ne",
            "not_contains",
        ):
            return not matched
        raise ValueError(
            f"Unsupported has_keyword_contains operator: {operator}"
        )


def matches_card_filter_dsl_or_legacy(
    game,
    card,
    filter_spec,
    context=None,
    usage_type=None,
):
    context = context or {}
    if _contains_removed_race_filter(filter_spec):
        raise ValueError(
            "race/races filters are no longer supported; use race_ja"
        )
    try:
        return CardFilterEvaluator(game).matches(
            card,
            filter_spec,
            {
                **context,
                "usage_type": usage_type
                or context.get("usage_type"),
            },
        )
    except ValueError:
        return matches_legacy_card_filter(
            card,
            filter_spec,
            context=context,
            usage_type=usage_type,
        )


def _require_comparison_object(
    value,
):
    for key in value:
        if key not in COMPARISON_OPERATORS:
            raise ValueError(
                f"Unknown comparison operator: {key}"
            )


def _is_creature_card(
    card,
):
    if getattr(
        card,
        "is_evolution_source",
        False,
    ):
        return False

    return isinstance(
        card,
        CreatureCard,
    ) or (
        isinstance(card, TwinPactCard)
        and card.creature_face is not None
    )


def _is_spell_card(
    card,
):
    return isinstance(
        card,
        SpellCard,
    ) or (
        isinstance(card, TwinPactCard)
        and card.spell_face is not None
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


def _usage_type_from_spec(
    spec,
):
    value = spec.get(
        "card_type",
        spec.get("type"),
    )
    if isinstance(value, str):
        return value

    return None


def _contains_removed_race_filter(
    value,
):
    if isinstance(value, dict):
        for key, item in value.items():
            if key in (
                "race",
                "races",
            ):
                return True
            if _contains_removed_race_filter(item):
                return True
        return False

    if isinstance(value, list):
        return any(
            _contains_removed_race_filter(item)
            for item in value
        )

    return False
