"""Triggered ability implementation for v2 JSON specs."""

from abilities.base.triggered_ability import TriggeredAbility
from abilities.v2.spec_schema import ability_id
from abilities.v2.trigger_matcher import TriggerMatcher
from core.condition_evaluator import ConditionEvaluator
from core.pending_cards import is_card_pending
from core.seal_utils import is_ignored_by_seal, is_seal_card
from core.target_resolver import TargetResolver
from effects.effect_context import EffectContext
from effects.composition.packaged_effect import PackagedEffect
from effects.effect_factory import EffectFactory
from effects.zones.zone_effect_utils import parse_zone


class JsonTriggeredAbility(TriggeredAbility):

    def __init__(
        self,
        owner_card,
        game,
        spec,
    ):
        self.owner_card = owner_card
        self.game = game
        self.spec = dict(spec)
        self.ability_id = ability_id(spec, "v2_triggered")
        self.trigger = spec.get("trigger", {})
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
        self.targets = spec.get("targets", [])
        self.effect_specs = spec.get("effects", [])
        self.label = spec.get("label", self.ability_id)
        self.trigger_matcher = TriggerMatcher(
            game,
            owner_card,
        )
        self.ignore_source_continuity = bool(
            spec.get("ignore_source_continuity", False)
        )
        self.requires_trigger_declaration = bool(
            spec.get("requires_trigger_declaration", False)
        )
        self.trigger_declaration_optional = bool(
            spec.get("trigger_declaration_optional", True)
        )
        self._first_time_turns = {}
        super().__init__(
            self.trigger_matcher.event_types(
                self.trigger
            ),
            self._matches,
            game,
        )
        self._configure_active_zones(
            spec.get("active_zones", spec.get("active_zone"))
        )

    def can_trigger(
        self,
        event,
    ):
        if self.active_zones != "any":
            return super().can_trigger(
                event
            )

        if is_card_pending(
            self.owner_card
        ):
            return False

        if (
            is_seal_card(self.owner_card)
            or is_ignored_by_seal(self.owner_card)
        ):
            return False

        if getattr(
            self.owner_card,
            "is_evolution_source",
            False,
        ):
            return False

        return True

    def _matches(
        self,
        event,
    ):
        context = self._condition_context(event)
        if not self.trigger_matcher.matches(
            self.trigger,
            event,
            context,
        ):
            return False

        evaluator = ConditionEvaluator(
            self.game
        )
        # 「各ターンはじめて」等の消費型条件は、トリガーとなったイベント
        # （例：このターン最初の攻撃）に紐づくため active_if とは独立に
        # 評価・消費する。先に active_if で短絡すると、能力が非アクティブな
        # 間に起きた最初の攻撃でカウンターが消費されず、後でアクティブに
        # なった次の攻撃で誤って発動してしまう。両方を必ず評価する。
        condition_ok = evaluator.evaluate(
            self.condition_spec,
            context,
        )
        active_ok = evaluator.evaluate(
            self.active_if_spec,
            context,
        )
        return condition_ok and active_ok

    def _condition_context(
        self,
        event,
    ):
        return {
            "game": self.game,
            "player": self.owner_card.owner,
            "controller": self.owner_card.owner,
            "event_player": getattr(event, "player", None),
            "source_card": self.owner_card,
            "event": event,
            "ability": self,
        }

    def create_effects(
        self,
        event,
    ):
        player = self.owner_card.owner
        source_info = getattr(
            self,
            "_pending_source_info",
            None,
        )
        package_context = {
            "event": event,
            "source_info": source_info,
        }
        effect_context = EffectContext.from_package_context(
            package_context
        )
        effect_context.store(
            "event",
            event,
        )
        if source_info is not None:
            effect_context.store(
                "source_info",
                source_info,
            )
        target_resolution = TargetResolver(
            self.game
        ).resolve(
            self.targets,
            {
                "game": self.game,
                "player": player,
                "controller": self.owner_card.owner,
                "source_card": self.owner_card,
                "source_info": source_info,
                "event": event,
                "package_context": package_context,
                "effect_context": effect_context,
            },
        )
        if not target_resolution.success:
            return []

        # 効果の試行可否（can_attempt）はトリガー時点ではなく解決時に判定する。
        # トリガー時点で除外すると、解決までに状態が変わって実行できるはずの
        # 効果（例: ターン終わりに解決時点のクリーチャー数を数える、破壊された
        # 自分を墓地から出す）を取りこぼす。逆に解決時点でも条件を満たさない
        # 効果（例: 火以外のスペース・チャージ）は、積まれた後の解決で何もせず
        # キューから取り除かれる。
        effects = EffectFactory(
            self.game
        ).build_many(
            self.effect_specs,
            player,
            source_card=self.owner_card,
        )

        package = PackagedEffect(
            effects,
            label=self.label,
        )
        package.package_context = package_context
        package.ignore_source_continuity = (
            self.ignore_source_continuity
        )
        package.source_info = source_info
        package.requires_trigger_declaration = (
            self.requires_trigger_declaration
        )
        package.trigger_declaration_optional = (
            self.trigger_declaration_optional
        )
        return [
            package,
        ]

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

    @property
    def event_name(
        self,
    ):
        return self.trigger_matcher.event_name(
            self.trigger
        )
