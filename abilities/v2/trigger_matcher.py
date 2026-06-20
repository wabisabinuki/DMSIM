"""Structured trigger matching for v2 JSON triggered abilities."""

from abilities.v2.event_map import event_name, event_types
from abilities.v2.spec_schema import (
    EVENT_KEYS,
    TRIGGER_EVENT_FIELDS,
    composite_sub_triggers,
    is_composite_trigger,
)
from core.card_filter_evaluator import CardFilterEvaluator
from core.dsl_compare import compare_values
from core.effect_argument_resolver import EffectArgumentResolver
from effects.zones.zone_effect_utils import parse_zone


class TriggerMatcher:
    """Resolve and match trigger specs without type-specific if chains."""

    FIELD_MATCHERS = {
        "subject": "_match_subject_field",
        "attacker": "_match_actor_field",
        "target": "_match_target_field",
        "player": "_match_player_field",
        "card": "_match_card_field",
        "filter": "_match_filter_field",
        "from_zone": "_match_from_zone_field",
        "to_zone": "_match_to_zone_field",
        "reason": "_match_reason_field",
    }

    # ``target`` 値がプレイヤーを指すキーワード。それ以外はカード参照として解決する。
    PLAYER_TARGET_KEYWORDS = frozenset(
        (
            "controller",
            "own",
            "owner",
            "opponent",
        )
    )

    SUBJECT_MATCHERS = {
        "self": "_match_subject_self",
        "any": "_match_subject_any",
        "any_card": "_match_subject_any",
        "controller": "_match_subject_controller",
        "own": "_match_subject_controller",
        "opponent": "_match_subject_opponent",
    }

    def __init__(
        self,
        game,
        owner_card,
    ):
        self.game = game
        self.owner_card = owner_card
        self.args = EffectArgumentResolver(game)
        self.card_filters = CardFilterEvaluator(game)

    def event_name(
        self,
        trigger,
    ):
        if is_composite_trigger(trigger):
            return [
                self.event_name(sub)
                for sub in composite_sub_triggers(trigger)
            ]

        return event_name(
            self.event_value(trigger)
        )

    def event_types(
        self,
        trigger,
    ):
        if is_composite_trigger(trigger):
            collected = []
            for sub in composite_sub_triggers(trigger):
                for event_type in self.event_types(sub):
                    if event_type not in collected:
                        collected.append(event_type)
            return tuple(collected)

        return event_types(
            self.event_value(trigger)
        )

    def event_value(
        self,
        trigger,
    ):
        for key in EVENT_KEYS:
            if key in trigger:
                return trigger[key]

        return None

    def matches(
        self,
        trigger,
        event,
        context,
    ):
        if is_composite_trigger(trigger):
            return self._match_composite(
                trigger,
                event,
                context,
            )

        if not self._event_matches_type(trigger, event):
            return False

        matcher_keys = [
            key
            for key in self.FIELD_MATCHERS
            if key in trigger
        ]
        if not matcher_keys:
            return self._match_subject_self(event)

        return all(
            getattr(self, handler_name)(
                trigger[key],
                event,
                context,
            )
            for key, handler_name in self.FIELD_MATCHERS.items()
            if key in matcher_keys
        )

    def _match_composite(
        self,
        trigger,
        event,
        context,
    ):
        kind = trigger.get("type")
        sub_results = (
            self.matches(sub, event, context)
            for sub in composite_sub_triggers(trigger)
        )
        if kind == "and":
            return all(sub_results)
        if kind == "not":
            return not any(sub_results)
        return any(sub_results)

    def _event_matches_type(
        self,
        trigger,
        event,
    ):
        """Scope a leaf trigger to the event type(s) it declares.

        A standalone trigger is already scoped by subscription, but inside a
        composite trigger every leaf is matched against every subscribed event
        type, so each leaf must reject events of a foreign type itself.
        """

        value = self.event_value(trigger)
        if value is None:
            return True

        return isinstance(
            event,
            event_types(value),
        )

    def _match_subject_field(
        self,
        value,
        event,
        context,
    ):
        subject = value or "self"
        handler_name = self.SUBJECT_MATCHERS.get(subject)
        if handler_name is None:
            raise ValueError(
                f"Unknown v2 trigger subject: {subject}"
            )

        return getattr(self, handler_name)(event)

    def _match_actor_field(
        self,
        value,
        event,
        context,
    ):
        expected = self.args.value(
            value,
            context,
        )
        actual = getattr(
            event,
            "attacker",
            None,
        )
        return actual is expected

    def _match_target_field(
        self,
        value,
        event,
        context,
    ):
        """攻撃・効果の対象（``event.target``）を照合する。

        ``target: "controller"`` のようにプレイヤーを指す場合はプレイヤー、
        それ以外はカード参照として解決して同一性を比較する。これにより
        「クリーチャーが自分（プレイヤー）を攻撃する時」や
        「このクリーチャーが攻撃される時」を表現できる。
        """

        actual = getattr(
            event,
            "target",
            None,
        )
        if actual is None:
            return False

        if (
            isinstance(value, str)
            and value in self.PLAYER_TARGET_KEYWORDS
        ):
            expected = self.args.player(
                value,
                context,
            )
        else:
            expected = self.args.value(
                value,
                context,
            )
        return actual is expected

    def _match_player_field(
        self,
        value,
        event,
        context,
    ):
        expected = self.args.player(
            value,
            context,
        )
        actual = getattr(
            event,
            "player",
            getattr(event, "owner", None),
        )
        return actual is expected

    def _match_card_field(
        self,
        value,
        event,
        context,
    ):
        expected = self.args.value(
            value,
            context,
        )
        return expected in self._event_cards(event)

    def _match_filter_field(
        self,
        value,
        event,
        context,
    ):
        return any(
            self.card_filters.matches(
                card,
                value,
                context,
            )
            for card in self._event_cards(event)
        )

    def _match_from_zone_field(
        self,
        value,
        event,
        context,
    ):
        return self._match_zone_expression(
            getattr(event, "from_zone", None),
            value,
            context,
        )

    def _match_to_zone_field(
        self,
        value,
        event,
        context,
    ):
        return self._match_zone_expression(
            getattr(event, "to_zone", None),
            value,
            context,
        )

    def _match_reason_field(
        self,
        value,
        event,
        context,
    ):
        return self._match_value_expression(
            getattr(event, "reason", None),
            value,
            context,
        )

    def _match_subject_self(
        self,
        event,
    ):
        return self.owner_card in self._event_cards(event)

    def _match_subject_any(
        self,
        event,
    ):
        return True

    def _match_subject_controller(
        self,
        event,
    ):
        return self._event_player(event) is self.owner_card.owner

    def _match_subject_opponent(
        self,
        event,
    ):
        player = self._event_player(event)
        return player is not None and player is not self.owner_card.owner

    def _event_cards(
        self,
        event,
    ):
        return tuple(
            card
            for card in (
                getattr(event, field, None)
                for field in TRIGGER_EVENT_FIELDS
            )
            if card is not None
        )

    def _event_player(
        self,
        event,
    ):
        return getattr(
            event,
            "player",
            getattr(event, "owner", None),
        )

    def _match_zone_expression(
        self,
        actual,
        value,
        context,
    ):
        if actual is not None:
            actual = parse_zone(actual).name.lower()

        return self._match_value_expression(
            actual,
            value,
            context,
            normalize_string=True,
        )

    def _match_value_expression(
        self,
        actual,
        value,
        context,
        normalize_string=False,
    ):
        if isinstance(value, dict) and set(value) != {"ref"}:
            return all(
                compare_values(
                    actual,
                    operator,
                    self._expected_value(
                        raw_expected,
                        context,
                        normalize_string=normalize_string,
                    ),
                )
                for operator, raw_expected in value.items()
            )

        return compare_values(
            actual,
            "eq",
            self._expected_value(
                value,
                context,
                normalize_string=normalize_string,
            ),
        )

    def _expected_value(
        self,
        value,
        context,
        normalize_string=False,
    ):
        expected = self.args.value(
            value,
            context,
        )
        if normalize_string:
            return _normalize_string_value(expected)

        return expected


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
