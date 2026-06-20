"""Replacement ability implementation for v2 JSON specs."""

from abilities.base.replacement_ability import ReplacementAbility
from abilities.v2.replacement_attempt_matcher import (
    ReplacementAttemptMatcher,
)
from abilities.v2.spec_schema import ability_id
from core.condition_evaluator import ConditionEvaluator
from core.effect_argument_resolver import EffectArgumentResolver
from core.pending_cards import first_visible_card
from events.zone_change_event import ZoneChangeEvent
from effects.effect_factory import EffectFactory
from effects.zones.zone_effect_utils import parse_zone
from zones.zone_type import ZoneType


class JsonReplacementAbility(ReplacementAbility):
    COST_HANDLERS = {
        "pay_mana": "_pay_mana_cost",
        "move_cards": "_pay_move_cards_cost",
    }

    REPLACE_ACTION_HANDLERS = {
        "move_event_card": "_move_event_card",
        "put_attempt_shield_on_bottom": "_move_event_card",
        "draw": "_draw_replace_action",
    }

    BATCH_EFFECT_HANDLERS = {
        "draw": "_apply_batch_draw",
    }

    def __init__(
        self,
        owner_card,
        game,
        spec,
    ):
        super().__init__()
        self.owner_card = owner_card
        self.game = game
        self.spec = dict(spec)
        self.ability_id = ability_id(spec, "v2_replacement")
        self.replacement_type = spec.get("type")
        self.attempt = spec.get("attempt", {})
        self.condition_spec = spec.get(
            "condition",
            {
                "type": "always",
            },
        )
        self.active_if_spec = spec.get(
            "active_if",
            {
                "type": "always",
            },
        )
        self.optional = spec.get("optional", False)
        self.costs = spec.get("costs", [])
        self.replace_with = spec.get("replace_with", {})
        self.after_replacement_batch = spec.get(
            "after_replacement_batch",
            spec.get("after_replacements", {}),
        )
        self.pending_replacement_count = 0
        self.args = EffectArgumentResolver(game)
        self.attempt_matcher = ReplacementAttemptMatcher(
            game,
            owner_card,
            self.attempt,
        )
        self._configure_active_zones(
            spec.get("active_zones", spec.get("active_zone"))
        )

    def applies(
        self,
        event,
    ):
        return (
            self._in_active_zone()
            and self.attempt_matcher.matches(event)
            and self._conditions_match(event)
        )

    def _in_active_zone(
        self,
    ):
        # 誘発能力と同様、置換能力もカードが「アクティブなゾーン」にある間だけ
        # 働く。active_zones 未指定なら既定はバトルゾーン。これにより、マナ／
        # 墓地／手札などに置かれたクリーチャーの置換効果（例: 他クリーチャーの
        # 破壊を肩代わりする能力）が誤って発動するのを防ぐ。他ゾーンで働く能力
        # （手札からの身代わり、表向きシールドの G城 等）は spec で active_zones
        # を明示する。
        if self.active_zones == "any":
            return True

        active_zones = (
            self.active_zones
            if self.active_zones
            else [ZoneType.BATTLE]
        )
        return getattr(
            self.owner_card,
            "zone",
            None,
        ) in active_zones

    def _configure_active_zones(
        self,
        zones,
    ):
        if zones is None:
            return

        if zones == "any":
            self.active_zones = "any"
            return

        if isinstance(
            zones,
            str,
        ):
            zones = [
                zones,
            ]

        self.active_zones = [
            parse_zone(zone)
            for zone in zones
        ]

    def replace(
        self,
        event,
    ):
        if self.optional:
            proceed = self.game.choice_manager.select(
                self.owner_card.owner,
                [
                    True,
                    False,
                ],
                prompt=self.spec.get(
                    "prompt",
                    "Apply replacement effect?",
                ),
            )
            if not proceed:
                return False

        if not self._pay_costs():
            return False

        self._apply_replace_with(event)
        self.pending_replacement_count += 1
        return True

    def finalize_pending_replacements(
        self,
    ):
        count = self.pending_replacement_count
        self.pending_replacement_count = 0
        if count <= 0:
            return

        self._apply_after_replacement_batch(count)

    def _conditions_match(
        self,
        event,
    ):
        evaluator = ConditionEvaluator(
            self.game
        )
        context = self._condition_context(event)
        return evaluator.evaluate(
            self.active_if_spec,
            context,
        ) and evaluator.evaluate(
            self.condition_spec,
            context,
        )

    def _condition_context(
        self,
        event,
    ):
        return {
            "game": self.game,
            "player": self.owner_card.owner,
            "controller": self.owner_card.owner,
            "event_player": getattr(
                event,
                "player",
                getattr(event, "owner", None),
            ),
            "source_card": self.owner_card,
            "event": event,
            "ability": self,
        }

    def _pay_costs(
        self,
    ):
        for cost in self.costs:
            cost_type = cost.get("type")
            handler_name = self.COST_HANDLERS.get(cost_type)
            if handler_name is None:
                raise ValueError(
                    f"Unknown replacement cost: {cost_type}"
                )
            if not getattr(self, handler_name)(cost):
                return False

        return True

    def _pay_mana_cost(
        self,
        cost,
    ):
        return self.owner_card.owner.tap_mana(
            int(cost.get("amount", 0)),
            choice_manager=(
                self.game.choice_manager
            ),
        )

    def _pay_move_cards_cost(
        self,
        cost,
    ):
        context = self.args.context(
            self.owner_card.owner,
            source_card=self.owner_card,
        )
        amount = int(
            self.args.value(
                cost.get("amount", 1),
                context,
            )
        )
        source = cost.get("from", {})
        player = self.args.player(
            source.get("player", "controller"),
            context,
        )
        from_zone = self.args.zone(
            source.get("zone"),
            context,
        )
        to_zone = self.args.zone(
            cost.get("to_zone", cost.get("to")),
            context,
        )
        cards = list(
            player.get_zone(from_zone).cards
        )
        if len(cards) < amount:
            return False

        if cost.get("optional", False):
            proceed = self.game.choice_manager.select(
                player,
                [True, False],
                prompt=cost.get(
                    "confirm_prompt",
                    "Pay replacement cost?",
                ),
            )
            if not proceed:
                return False

        chosen = self.game.choice_manager.select(
            player,
            cards,
            prompt=cost.get(
                "prompt",
                "Choose cards for replacement cost",
            ),
            min_count=amount,
            max_count=amount,
        )
        if chosen is None:
            return False
        if not isinstance(chosen, list):
            chosen = [chosen]

        chosen = [
            card
            for card in chosen
            if card in cards
        ]
        if len(chosen) < amount:
            return False

        for card in chosen[:amount]:
            if not self.game.card_mover.move(
                card=card,
                owner=player,
                from_zone=from_zone,
                to_zone=to_zone,
                reason=cost.get("reason", "replacement_cost"),
                apply_replacements=False,
            ):
                return False

        return True

    def _apply_replace_with(
        self,
        event,
    ):
        replace_with = self.replace_with or {}

        to_zone = replace_with.get(
            "to_zone",
            replace_with.get("destination_zone"),
        )
        if to_zone is not None:
            if isinstance(to_zone, list):
                to_zone = self.game.choice_manager.select(
                    self.owner_card.owner,
                    to_zone,
                    prompt=replace_with.get(
                        "prompt",
                        "Choose destination zone",
                    ),
                )
            event.to_zone = self.args.zone(
                to_zone,
                self.args.context(
                    self.owner_card.owner,
                    source_card=self.owner_card,
                    event=event,
                ),
            )

        if replace_with.get("cancel_event"):
            event.cancelled = True

        for action in replace_with.get("actions", []):
            self._apply_replace_action(
                action,
                event,
            )

        for effect in EffectFactory(
            self.game
        ).build_many(
            replace_with.get("effects", []),
            getattr(
                event,
                "player",
                self.owner_card.owner,
            ),
            source_card=self.owner_card,
        ):
            effect.source_card = self.owner_card
            effect.resolve()

    def _apply_replace_action(
        self,
        action,
        event,
    ):
        action_type = action.get("type")
        handler_name = self.REPLACE_ACTION_HANDLERS.get(action_type)
        if handler_name is not None:
            return getattr(self, handler_name)(
                action,
                event,
            )

        raise ValueError(
            f"Unknown replacement action: {action_type}"
        )

    def _move_event_card(
        self,
        action,
        event,
    ):
        context = self.args.context(
            self.owner_card.owner,
            source_card=self.owner_card,
            event=event,
        )
        default_card = (
            {
                "ref": "event.shield_card"
            }
            if hasattr(event, "shield_card")
            else {
                "ref": "event.card"
            }
        )
        card = self.args.value(
            action.get("card", default_card),
            context,
        )
        if card is None:
            return False

        owner = getattr(
            card,
            "owner",
            getattr(event, "owner", getattr(event, "player", None)),
        )
        from_zone = self.args.zone(
            action.get(
                "from_zone",
                getattr(card, "zone", None),
            ),
            context,
        )
        to_zone = self.args.zone(
            action.get("to_zone", action.get("to")),
            context,
        )
        return self.game.card_mover.move(
            card=card,
            owner=owner,
            from_zone=from_zone,
            to_zone=to_zone,
            reason=action.get("reason", "replacement"),
            apply_replacements=bool(
                action.get("apply_replacements", False)
            ),
        )

    def _draw_replace_action(
        self,
        action,
        event,
    ):
        """「かわりにカードをN枚引く」置換アクション。

        通常の ``draw`` 効果は置換を再適用してしまい無限再帰になるため、
        置換を経由しない ``_draw_without_replacement``（reason:
        ``replacement_draw``）でN枚引く。引く側は既定でイベントの持ち主
        （＝置換された元のドローを行うプレイヤー）。
        """
        context = self.args.context(
            self.owner_card.owner,
            source_card=self.owner_card,
            event=event,
        )
        amount = int(
            self.args.value(
                action.get("amount", 1),
                context,
            )
        )
        if "player" in action:
            player = self.args.player(
                action["player"],
                context,
            )
        else:
            player = (
                getattr(event, "owner", None)
                or self.owner_card.owner
            )

        drawn_any = False
        for _ in range(amount):
            if not self._draw_without_replacement(player):
                break
            drawn_any = True

        return drawn_any

    def _apply_after_replacement_batch(
        self,
        count,
    ):
        batch = self.after_replacement_batch or {}
        context = self.args.context(
            self.owner_card.owner,
            source_card=self.owner_card,
        )
        context["replacement"] = {
            "count": count,
        }
        # ``replacement.count`` のドット参照は RefResolver の ``count`` パート
        # ハンドラ（コレクション要素数）に解決されてしまうため、バッチ件数は
        # フラットキー ``replacement_count`` 経由で参照する。
        context["replacement_count"] = count

        for effect in batch.get("effects", []):
            self._apply_batch_effect(
                effect,
                context,
            )

    def _apply_batch_effect(
        self,
        effect,
        context,
    ):
        effect_type = effect.get("type")
        handler_name = self.BATCH_EFFECT_HANDLERS.get(effect_type)
        if handler_name is not None:
            return getattr(self, handler_name)(
                effect,
                context,
            )

        raise ValueError(
            f"Unknown replacement batch effect: {effect_type}"
        )

    def _apply_batch_draw(
        self,
        effect,
        context,
    ):
        amount = int(
            self.args.value(
                effect.get("amount", 1),
                context,
            )
        )
        player_spec = effect.get("player", "controller")
        players = (
            self.game.state.players
            if player_spec in (
                "each_player",
                "all_players",
            )
            else [
                self.args.player(
                    player_spec,
                    context,
                )
            ]
        )
        for player in players:
            for _ in range(amount):
                self._draw_without_replacement(player)

    def _draw_without_replacement(
        self,
        player,
    ):
        card = first_visible_card(
            player.deck.cards
        )
        if card is None:
            self.game.state.declare_loss(
                player,
                reason="deck_out",
            )
            return False

        self.game.card_mover.pre_freeze_sources_for(
            card
        )

        player.deck.remove(card)
        if not player.deck.cards:
            self.game.state.declare_loss(
                player,
                reason="deck_out",
            )
        player.hand.add(card)
        card.zone = ZoneType.HAND
        card.zone_change_counter += 1

        self.game.event_manager.publish(
            ZoneChangeEvent(
                card=card,
                owner=player,
                from_zone=ZoneType.DECK,
                to_zone=ZoneType.HAND,
                reason="replacement_draw",
            )
        )

        return True

    @property
    def event_name(
        self,
    ):
        return self.attempt_matcher.event_name()
