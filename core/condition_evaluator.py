"""Evaluate structured condition specs used by v2 JSON abilities."""

from core.card_filter_evaluator import CardFilterEvaluator
from core.condition_registry import condition_handler_name
from core.dsl_compare import compare_values
from core.pending_cards import visible_cards
from core.seal_utils import is_ignored_by_seal
from core.ref_resolver import RefResolver
from effects.zones.zone_effect_utils import parse_zone


class ConditionEvaluator:
    """Small interpreter for condition JSON objects."""

    def __init__(
        self,
        game,
    ):
        self.game = game
        self.refs = RefResolver(game)
        self.card_filters = CardFilterEvaluator(game)

    def evaluate(
        self,
        condition,
        context=None,
    ):
        context = context or {}

        if condition is None:
            return True

        if isinstance(condition, bool):
            return condition

        if isinstance(condition, str):
            raise ValueError(
                "condition must be an object, not a string"
            )

        if not isinstance(condition, dict):
            raise ValueError(
                f"condition must be an object: {condition!r}"
            )

        condition_type = condition.get("type")

        handler_name = condition_handler_name(condition_type)
        if handler_name is not None:
            return getattr(self, handler_name)(
                condition,
                context,
            )

        raise ValueError(
            f"Unknown condition type: {condition_type}"
        )

    def _evaluate_always(
        self,
        condition,
        context,
    ):
        return True

    def _evaluate_and(
        self,
        condition,
        context,
    ):
        return all(
            self.evaluate(item, context)
            for item in _as_list(
                condition.get(
                    "conditions",
                    condition.get("all"),
                )
            )
        )

    def _evaluate_or(
        self,
        condition,
        context,
    ):
        return any(
            self.evaluate(item, context)
            for item in _as_list(
                condition.get(
                    "conditions",
                    condition.get("any"),
                )
            )
        )

    def _evaluate_not(
        self,
        condition,
        context,
    ):
        return not self.evaluate(
            condition.get("condition"),
            context,
        )

    def _evaluate_source_has_state(
        self,
        condition,
        context,
    ):
        card = context.get("source_card")
        return self._card_has_state(
            card,
            condition.get("state"),
            condition.get("value", True),
        )

    def _evaluate_card_state(
        self,
        condition,
        context,
    ):
        card = self._resolve_card(
            condition.get("card", "self"),
            context,
        )
        return self._card_has_state(
            card,
            condition.get("state"),
            condition.get("value", True),
        )

    def _evaluate_event_actor_is(
        self,
        condition,
        context,
    ):
        event = context.get("event")
        actor_name = condition.get("actor")
        actual = getattr(
            event,
            actor_name,
            None,
        )
        expected = self._resolve_condition_value(
            condition.get("value"),
            context,
        )
        return actual is expected if _is_object(expected) else actual == expected

    def _evaluate_event_card_matches(
        self,
        condition,
        context,
    ):
        card = self._resolve_event_card(
            condition.get("card", "card"),
            context,
        )
        return self.card_filters.matches(
            card,
            condition.get("filter", {}),
            self._filter_context(context),
        )

    def _evaluate_event_card_is(
        self,
        condition,
        context,
    ):
        # イベントのカードが、指定した参照（既定は発生源）と同一かを判定する。
        # 「自分の他のクリーチャーが出た時」のような自己除外に、not と組み合わせて使う。
        event = context.get("event")
        if event is None:
            return False

        event_card = getattr(event, "card", None)
        target = self._resolve_card(
            condition.get("card", "source"),
            context,
        )
        return event_card is not None and event_card is target

    def _evaluate_event_zone_change_matches(
        self,
        condition,
        context,
    ):
        event = context.get("event")
        if event is None:
            return False

        card_value = condition.get("card")
        if card_value is not None:
            card = getattr(
                event,
                "card",
                None,
            )
            expected = self._resolve_condition_value(
                card_value,
                context,
            )
            if _is_object(expected):
                if card is not expected:
                    return False
            elif card != expected:
                return False

        if "card_filter" in condition:
            if not self.card_filters.matches(
                getattr(event, "card", None),
                condition.get("card_filter", {}),
                self._filter_context(context),
            ):
                return False

        if "player" in condition:
            expected_player = self._resolve_player(
                condition.get("player"),
                context,
            )
            actual_player = getattr(
                event,
                "owner",
                getattr(event, "player", None),
            )
            if actual_player is not expected_player:
                return False

        for key, attr in (
            ("from_zone", "from_zone"),
            ("to_zone", "to_zone"),
            ("reason", "reason"),
            ("from_shield_face_up", "from_shield_face_up"),
            ("from_seal", "from_seal"),
        ):
            if key not in condition:
                continue
            actual = getattr(
                event,
                attr,
                None,
            )
            if attr.endswith("zone") and actual is not None:
                actual = parse_zone(actual).name.lower()
            expected = condition[key]
            if isinstance(expected, dict):
                for operator, value in expected.items():
                    resolved = self.refs.resolve(
                        value,
                        context,
                    )
                    if isinstance(resolved, str):
                        resolved = resolved.lower()
                    if not compare_values(
                        actual,
                        operator,
                        resolved,
                    ):
                        return False
            else:
                if isinstance(expected, str):
                    expected = expected.lower()
                if actual != expected:
                    return False

        return True

    def _evaluate_event_player_is(
        self,
        condition,
        context,
    ):
        event = context.get("event")
        actual = self._event_player(
            event,
            context,
        )
        expected = self._resolve_player(
            condition.get("player", "controller"),
            context,
        )
        return actual is expected

    def _evaluate_event_value_matches(
        self,
        condition,
        context,
    ):
        event = context.get("event")
        if event is None:
            return False

        field = condition.get(
            "field",
            condition.get("attr"),
        )
        if not field:
            raise ValueError(
                "event_value_matches requires field"
            )

        actual = getattr(event, field, None)
        expected = self._resolve_condition_value(
            condition.get("value"),
            context,
        )
        operator = condition.get(
            "op",
            condition.get("operator", "eq"),
        )
        return compare_values(
            actual,
            operator,
            expected,
            allow_symbols=True,
        )

    def _evaluate_source_zone_is(
        self,
        condition,
        context,
    ):
        source = context.get("source_card")
        actual = getattr(
            source,
            "zone",
            None,
        )
        return self._matches_zone_expression(
            actual,
            condition.get("zone"),
            context,
        )

    def _evaluate_card_count_matches(
        self,
        condition,
        context,
    ):
        cards = self._condition_cards(
            condition,
            context,
        )
        filter_spec = condition.get("filter", {})
        if filter_spec:
            cards = [
                card
                for card in cards
                if self.card_filters.matches(
                    card,
                    filter_spec,
                    self._filter_context(context),
                )
            ]

        expected = self.refs.resolve(
            condition.get("value", condition.get("count", 0)),
            context,
        )
        operator = condition.get(
            "op",
            condition.get("operator", "eq"),
        )
        return compare_values(
            len(cards),
            operator,
            expected,
            allow_symbols=True,
        )

    def _evaluate_mana_armor(
        self,
        condition,
        context,
    ):
        """「マナ武装」条件の能力語。

        「自分（controller）のマナゾーンに <civilization> のカードが <count>
        枚以上あれば真」を表す。内部で `card_count_matches`（マナゾーン＋文明
        フィルタ）へ展開する。`active_if` を取るあらゆる能力・効果のゲートに使える。
        """

        civilizations = condition.get(
            "civilizations",
            condition.get("civilization"),
        )
        count = condition.get(
            "count",
            condition.get("value", 3),
        )
        synthesized = {
            "from": {
                "player": condition.get("player", "controller"),
                "zone": "mana",
            },
            "filter": {
                "civilization": civilizations,
            },
            "op": "gte",
            "value": count,
        }
        return self._evaluate_card_count_matches(
            synthesized,
            context,
        )

    def _evaluate_turn_stat(
        self,
        condition,
        context,
    ):
        """行動集計（TurnStatsManager）を参照する条件。

        例: 「このターンに2枚以上引いた」=
        {type:"turn_stat", stat:"cards_drawn", player:"controller",
         op:"gte", value:2}

        ``scope`` を ``"game"`` にすると per-turn ではなく per-game の集計を
        参照する（極限ファイナル革命の「このゲーム中に〜」など）。既定は
        ``"turn"``。
        """

        manager = getattr(self.game, "turn_stats_manager", None)
        if manager is None:
            return False

        player = self._resolve_player(
            condition.get("player", "controller"),
            context,
        )
        if condition.get("scope", "turn") == "game":
            actual = manager.get_game(
                player,
                condition.get("stat"),
            )
        else:
            actual = manager.get(
                player,
                condition.get("stat"),
            )
        operator = condition.get(
            "op",
            condition.get("operator", "gte"),
        )
        expected = self.refs.resolve(
            condition.get("value", condition.get("count", 1)),
            context,
        )
        return compare_values(
            actual,
            operator,
            expected,
            allow_symbols=True,
        )

    def _evaluate_once_per_turn(
        self,
        condition,
        context,
    ):
        return self._check_turn_counter(
            condition,
            context,
            consume=condition.get("consume", True),
        )

    def _evaluate_once_per_turn_available(
        self,
        condition,
        context,
    ):
        return self._check_turn_counter(
            condition,
            context,
            consume=False,
        )

    def _evaluate_battle_result_matches(
        self,
        condition,
        context,
    ):
        event = context.get("event")
        if event is None:
            return False

        for key in ("winner", "loser"):
            if key not in condition:
                continue
            actual = getattr(event, key, None)
            expected = self._resolve_condition_value(
                condition[key],
                context,
            )
            if not self._same_value(actual, expected):
                return False

        for key, event_key in (
            ("winner_player", "winner"),
            ("loser_player", "loser"),
        ):
            if key not in condition:
                continue
            card = getattr(event, event_key, None)
            actual = getattr(card, "owner", None)
            expected = self._resolve_player(
                condition[key],
                context,
            )
            if actual is not expected:
                return False

        for key, event_key in (
            ("winner_filter", "winner"),
            ("loser_filter", "loser"),
        ):
            if key not in condition:
                continue
            if not self.card_filters.matches(
                getattr(event, event_key, None),
                condition[key],
                self._filter_context(context),
            ):
                return False

        return True

    def _evaluate_choice_history_matches(
        self,
        condition,
        context,
    ):
        event = context.get("event")
        if event is None:
            return False

        if "player" in condition:
            actual_player = getattr(event, "player", None)
            expected_player = self._resolve_player(
                condition["player"],
                context,
            )
            if actual_player is not expected_player:
                return False

        if "card" in condition:
            actual = getattr(event, "card", None)
            expected = self._resolve_condition_value(
                condition["card"],
                context,
            )
            if not self._same_value(actual, expected):
                return False

        if "filter" in condition:
            if not self.card_filters.matches(
                getattr(event, "card", None),
                condition["filter"],
                self._filter_context(context),
            ):
                return False

        if "prompt" in condition:
            actual_prompt = getattr(event, "prompt", None)
            if not self._matches_value_expression(
                actual_prompt,
                condition["prompt"],
                context,
            ):
                return False

        return True

    def _evaluate_card_matches(
        self,
        condition,
        context,
    ):
        card = self._resolve_card(
            condition.get("card", "self"),
            context,
        )
        return self.card_filters.matches(
            card,
            condition.get("filter", {}),
            self._filter_context(context),
        )

    def _evaluate_player_zone_count(
        self,
        condition,
        context,
    ):
        player = self._resolve_player(
            condition.get("player", "controller"),
            context,
        )
        zone = parse_zone(condition.get("zone"))
        player_zone = player.get_zone(zone)
        shield_count = getattr(
            player_zone,
            "shield_count",
            None,
        )
        if shield_count is not None:
            actual = shield_count()
        else:
            actual = len(
                [
                    card
                    for card in visible_cards(
                        player_zone.cards
                    )
                    if not is_ignored_by_seal(card)
                ]
            )
        expected = self.refs.resolve(
            condition.get("value"),
            context,
        )
        operator = condition.get(
            "op",
            condition.get("operator", "eq"),
        )
        return compare_values(
            actual,
            operator,
            expected,
            allow_symbols=True,
        )

    def _evaluate_own_creature_power_is_highest(
        self,
        condition,
        context,
    ):
        # 「自分のクリーチャーのパワーが一番大きければ」。
        # 同値タイは「一番大きい」を満たす扱い（>= 比較）。
        player = self._resolve_player(
            condition.get("player", "controller"),
            context,
        )
        own_creatures = self.game.query.get_creatures(
            controller=player
        )
        if not own_creatures:
            return False

        own_max = max(
            creature.get_current_power()
            for creature in own_creatures
        )
        other_creatures = [
            creature
            for creature in self.game.query.get_creatures()
            if creature.owner is not player
        ]
        if not other_creatures:
            return True

        return own_max >= max(
            creature.get_current_power()
            for creature in other_creatures
        )

    def _evaluate_turn_player_is(
        self,
        condition,
        context,
    ):
        expected = self._resolve_player(
            condition.get("player", "controller"),
            context,
        )
        return self.game.state.current_player is expected

    def _evaluate_first_time_each_turn(
        self,
        condition,
        context,
    ):
        return self._check_turn_counter(
            condition,
            context,
            consume=True,
        )

    def _check_turn_counter(
        self,
        condition,
        context,
        consume,
    ):
        ability = context.get("ability")
        if ability is None:
            raise ValueError(
                f"{condition.get('type')} requires ability context"
            )

        turns = getattr(
            ability,
            "_first_time_turns",
            None,
        )
        if turns is None:
            turns = {}
            ability._first_time_turns = turns

        key = condition.get(
            "key",
            condition.get("type", "once_per_turn"),
        )
        turn = self.game.state.turn
        if turns.get(key) == turn:
            return False

        if consume:
            turns[key] = turn
        return True

    def _card_has_state(
        self,
        card,
        state,
        expected,
    ):
        if card is None:
            return False

        if state == "hyper_mode":
            actual = getattr(
                card,
                "is_hyper_mode_active",
                False,
            )
        else:
            actual = getattr(
                card,
                state,
                None,
            )

        return actual == expected

    def _condition_cards(
        self,
        condition,
        context,
    ):
        if "cards" in condition:
            value = self.refs.resolve(
                condition["cards"],
                context,
            )
            if hasattr(value, "cards"):
                return [
                    card
                    for card in visible_cards(value.cards)
                    if not is_ignored_by_seal(card)
                ]
            return [
                card
                for card in _as_list(value)
                if card is not None
                and not is_ignored_by_seal(card)
            ]

        source = condition.get("from")
        if source is None and "zone" in condition:
            source = {
                "player": condition.get("player", "controller"),
                "zone": condition.get("zone"),
            }

        if isinstance(source, dict):
            player = self._resolve_player(
                source.get("player", "controller"),
                context,
            )
            zone = parse_zone(source.get("zone"))
            if player is None:
                return []
            return [
                card
                for card in visible_cards(
                    player.get_zone(zone).cards
                )
                if not is_ignored_by_seal(card)
            ]

        raise ValueError(
            "card_count_matches requires cards or from"
        )

    def _event_player(
        self,
        event,
        context,
    ):
        if event is None:
            return context.get("event_player")

        for attr in (
            "player",
            "owner",
            "target_player",
        ):
            value = getattr(
                event,
                attr,
                None,
            )
            if value is not None:
                return value

        return context.get("event_player")

    def _same_value(
        self,
        actual,
        expected,
    ):
        return actual is expected if _is_object(expected) else actual == expected

    def _matches_zone_expression(
        self,
        actual,
        expression,
        context,
    ):
        if actual is not None:
            actual = parse_zone(actual).name.lower()
        return self._matches_value_expression(
            actual,
            expression,
            context,
            normalize_string=True,
        )

    def _matches_value_expression(
        self,
        actual,
        expression,
        context,
        normalize_string=False,
    ):
        if isinstance(expression, dict) and set(expression) != {"ref"}:
            for operator, value in expression.items():
                resolved = self.refs.resolve(
                    value,
                    context,
                )
                if normalize_string:
                    resolved = _normalize_expression_string(
                        resolved
                    )
                if not compare_values(
                    actual,
                    operator,
                    resolved,
                ):
                    return False
            return True

        expected = self.refs.resolve(
            expression,
            context,
        )
        if normalize_string:
            expected = _normalize_expression_string(
                expected
            )
        return compare_values(
            actual,
            "eq",
            expected,
        )

    def _resolve_condition_value(
        self,
        value,
        context,
    ):
        if value in (
            "self",
            "source",
            "source_card",
        ):
            return context.get("source_card")

        if value in (
            "controller",
            "owner",
        ):
            return self._resolve_player(
                "controller",
                context,
            )

        if value == "opponent":
            return self._resolve_player(
                "opponent",
                context,
            )

        return self.refs.resolve(
            value,
            context,
        )

    def _resolve_card(
        self,
        value,
        context,
    ):
        if value in (
            None,
            "self",
            "source",
            "source_card",
        ):
            return context.get("source_card")

        if isinstance(value, dict) and set(value) == {"ref"}:
            return self.refs.resolve(
                value,
                context,
            )

        return self._resolve_event_card(
            value,
            context,
        )

    def _resolve_event_card(
        self,
        value,
        context,
    ):
        event = context.get("event")
        if event is None:
            return None

        field = {
            "moved_card": "card",
            "self": None,
            "source": None,
            "source_card": None,
        }.get(
            value,
            value,
        )
        if field is None:
            return context.get("source_card")

        return getattr(
            event,
            field,
            None,
        )

    def _resolve_player(
        self,
        value,
        context,
    ):
        if value in (
            None,
            "controller",
            "self",
            "owner",
        ):
            return self.refs.resolve_ref(
                "controller",
                context,
            )

        if value == "opponent":
            return self.refs.resolve_ref(
                "opponent",
                context,
            )

        if isinstance(value, dict) and set(value) == {"ref"}:
            return self.refs.resolve(
                value,
                context,
            )

        return value

    def _filter_context(
        self,
        context,
    ):
        return {
            **context,
            "controller": self.refs.resolve_ref(
                "controller",
                context,
            ),
            "player": self.refs.resolve_ref(
                "controller",
                context,
            ),
        }


def _as_list(
    value,
):
    if value is None:
        return []

    if isinstance(value, list):
        return value

    return [value]


def _is_object(
    value,
):
    return not isinstance(
        value,
        (str, int, float, bool, type(None)),
    )


def _normalize_expression_string(
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
