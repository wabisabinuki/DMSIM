"""
トリガーされた効果（Effect）をスタック/キューとして保持し、プレイヤーの選択順または自動で解決（resolve）するリゾルバー。
"""

from ui.trigger_debug import log_effect_resolve
from effects import DurationEffect
from events.attack_event import AttackDeclaredEvent


class EffectResolver:
    """
    Effect キューを管理し、順序づけて解決するマネージャー

    ライフサイクル:
    1. add_effect(): Effect を キューに追加
    2. resolve_next(): キューから Effect を選択・解決
    3. 継続条件チェック: can_resolve() で条件を検証
    4. SBA: Effect 解決後に State Based Actions をチェック
    """

    def __init__(
        self,
    ):

        self.effects = []
        self._resolving_effect_stack = []

    def add_effect(
        self,
        effect,
        controller=None,
        is_shield_trigger=False,
    ):

        if controller is not None:
            effect.effect_controller = controller

        if not hasattr(effect, "effect_controller"):
            effect.effect_controller = (
                self._effect_owner(effect)
            )

        effect.is_shield_trigger_effect = (
            bool(is_shield_trigger)
            or bool(
                getattr(
                    effect,
                    "is_shield_trigger_effect",
                    False,
                )
            )
        )

        self.effects.append(
            effect
        )

    def remove_effect(
        self,
        effect,
    ):

        if effect in self.effects:

            self.effects.remove(
                effect
            )

    def has_effects(
        self,
    ):

        return bool(
            self.effects
        )

    def priority_group_for_owner(
        self,
        context,
        owner,
        is_shield_trigger=False,
    ):

        return (
            0 if is_shield_trigger else 1,
            self._owner_priority(
                context,
                owner,
            ),
        )

    def remove_attack_declared_effects(
        self,
        attack_id,
    ):

        if attack_id is None:
            return

        self.effects = [
            effect
            for effect in self.effects
            if not self._is_attack_declared_effect(
                effect,
                attack_id,
            )
        ]

    def freeze_sources_for(
        self,
        card,
        trigger_manager=None,
    ):
        self.freeze_sources_for_many(
            [
                card,
            ],
            trigger_manager=trigger_manager,
        )

    def freeze_sources_for_many(
        self,
        cards,
        trigger_manager=None,
    ):
        card_ids = {
            id(card)
            for card in cards
            if card is not None
        }
        if not card_ids:
            return

        for effect in self._effects_for_source_freeze():
            for source_info in self._effect_source_infos(effect):
                source_card = getattr(
                    source_info,
                    "live_card",
                    None,
                )
                if id(source_card) in card_ids:
                    source_info.freeze()

        if trigger_manager is not None:
            freeze_pending = getattr(
                trigger_manager,
                "freeze_sources_for_many",
                None,
            )
            if freeze_pending is not None:
                freeze_pending(cards)

    def resolve_priority_group(
        self,
        context,
        group_key=None,
    ):
        """
        現在キュー上で最優先になっている単一の優先グループだけを解決する。
        """

        if context.resolving:
            return

        if context.state.game_over:
            self.effects.clear()
            return

        if not self.effects:
            return

        if group_key is None:
            group_key = self._next_group_key(
                context
            )

        context.resolving = True
        try:
            while self.effects and not context.state.game_over:
                changed = (
                    context
                    .state_based_actions
                    .check_and_apply()
                )
                if context.state.game_over:
                    self.effects.clear()
                    return
                if changed:
                    continue

                if not self.effects:
                    return

                if self._next_group_key(context) != group_key:
                    return

                effect = self._select_next_effect_for_group(
                    context,
                    group_key,
                )

                if effect is None:
                    return

                self._resolve_effect_from_queue(
                    context,
                    effect,
                )
        finally:
            context.resolving = False

    def resolve_next(
        self,
        context,
    ):
        """
        キューから Effect を選択・解決

        継続条件対応:
        1. Effect を選択
        2. can_resolve() で条件チェック
        3. 条件が満たされなければスキップ
        4. 条件が満たされれば解決
        5. SBA チェック
        """

        if context.state.game_over:
            self.effects.clear()
            return

        effect = self._select_next_effect(
            context
        )

        self._resolve_effect_from_queue(
            context,
            effect,
        )

    def resolve_specific_effects(
        self,
        context,
        effects,
    ):
        """
        特定の Effect を順序づけて解決（Shield Trigger など用）

        継続条件対応:
        - 各 Effect の can_resolve() をチェック
        """

        pending = effects[:]

        while pending and not context.state.game_over:

            effect = pending.pop(0)

            # queueにあるなら除去
            if effect in self.effects:

                self.effects.remove(
                    effect
                )

            # 継続条件チェック
            if hasattr(effect, 'can_resolve'):
                if not effect.can_resolve(
                    context.state
                ):
                    log_effect_resolve(
                        effect,
                        skipped=True,
                        reason="継続条件を満たさない",
                    )
                    continue

            self._resolve_effect(
                context,
                effect,
            )

            context\
                .state_based_actions\
                .check_and_apply()
            if context.state.game_over:
                self.effects.clear()
                return

    def _resolve_effect(
        self,
        context,
        effect,
    ):

        log_effect_resolve(effect)

        previous_resolving = context.resolving
        context.resolving = True
        previous_effect_controller = getattr(
            context.state,
            "current_effect_controller",
            None,
        )
        context.state.current_effect_controller = getattr(
            effect,
            "effect_controller",
            None,
        )
        try:
            self._resolving_effect_stack.append(
                effect
            )
            effect.resolve()
        finally:
            if (
                self._resolving_effect_stack
                and self._resolving_effect_stack[-1] is effect
            ):
                self._resolving_effect_stack.pop()
            elif effect in self._resolving_effect_stack:
                self._resolving_effect_stack.remove(
                    effect
                )
            context.resolving = previous_resolving
            context.state.current_effect_controller = (
                previous_effect_controller
            )

        # 期間管理 Effect の場合、期間管理マネージャーに登録
        if isinstance(effect, DurationEffect):
            context.duration_effect_manager.register_duration_effect(
                effect
            )

    def _resolve_effect_from_queue(
        self,
        context,
        effect,
    ):

        if effect is None:
            return

        if effect in self.effects:
            self.effects.remove(
                effect
            )

        # 継続条件チェック
        if hasattr(effect, 'can_resolve'):
            if not effect.can_resolve(
                context.state
            ):
                log_effect_resolve(
                    effect,
                    skipped=True,
                    reason="継続条件を満たさない",
                )
                return

        self._resolve_effect(
            context,
            effect,
        )

        if context.state.game_over:
            self.effects.clear()
            return

        # SBA チェック
        context\
            .state_based_actions\
            .check_and_apply()
        if context.state.game_over:
            self.effects.clear()

    def _select_next_effect(
        self,
        context,
    ):

        while self.effects:

            group_key = self._next_group_key(
                context
            )

            effect = self._select_next_effect_for_group(
                context,
                group_key,
            )

            if effect is not None:
                return effect

        return None

    def _select_next_effect_for_group(
        self,
        context,
        group_key,
    ):

        while self.effects:

            choices = self._choices_for_group(
                context,
                group_key,
            )

            if not choices:
                return None

            if self._declare_pending_effects(
                context,
                choices,
            ):
                continue

            owner = self._effect_owner(
                choices[0]
            )
            selecting_player = (
                owner
                or context.state.current_player
            )

            return (
                context
                .target_selector
                .select(
                    selecting_player,
                    choices,
                    "Choose an effect to resolve"
                )
            )

        return None

    def _next_group_key(
        self,
        context,
    ):

        return min(
            self._priority_key(
                context,
                effect,
                index,
            )[:2]
            for index, effect in enumerate(
                self.effects
            )
        )

    def _choices_for_group(
        self,
        context,
        group_key,
    ):

        return [
            effect
            for index, effect in enumerate(
                self.effects
            )
            if self._priority_key(
                context,
                effect,
                index,
            )[:2] == group_key
        ]

    def _declare_pending_effects(
        self,
        context,
        choices,
    ):

        pending = [
            effect
            for effect in choices
            if self._needs_declaration(
                effect
            )
        ]

        if not pending:
            return False

        mandatory = [
            effect
            for effect in pending
            if not getattr(
                effect,
                "trigger_declaration_optional",
                True,
            )
        ]
        for effect in mandatory:
            self._mark_declared(effect)

        optional = [
            effect
            for effect in pending
            if effect not in mandatory
        ]

        selected = []
        if optional:
            player = (
                self._effect_owner(optional[0])
                or context.state.current_player
            )
            selected = (
                context
                .choice_manager
                .select(
                    player,
                    optional,
                    "Choose hidden triggers to declare",
                    min_count=0,
                    max_count=len(optional),
                )
            )
            selected = self._selected_declarations(
                selected,
                optional,
            )

        for effect in optional:
            if effect in selected:
                self._mark_declared(effect)
            elif effect in self.effects:
                self.effects.remove(effect)

        return True

    def _needs_declaration(
        self,
        effect,
    ):

        return (
            getattr(
                effect,
                "requires_trigger_declaration",
                False,
            )
            and not getattr(
                effect,
                "trigger_declared",
                False,
            )
        )

    def _priority_key(
        self,
        context,
        effect,
        index,
    ):

        shield_trigger_priority = (
            0
            if getattr(
                effect,
                "is_shield_trigger_effect",
                False,
            )
            else 1
        )

        return (
            shield_trigger_priority,
            self._owner_priority(
                context,
                self._effect_owner(effect),
            ),
            index,
        )

    def _owner_priority(
        self,
        context,
        owner,
    ):

        players = context.state.players
        turn_index = context.state.turn_player_index

        if owner is None:
            return len(players)

        if owner not in players:
            return len(players)

        owner_index = players.index(owner)

        return (
            owner_index - turn_index
        ) % len(players)

    def _effect_owner(
        self,
        effect,
    ):

        controller = getattr(
            effect,
            "effect_controller",
            None,
        )
        if controller is not None:
            return controller

        player = getattr(
            effect,
            "player",
            None,
        )
        if player is not None:
            return player

        source_card = getattr(
            effect,
            "source_card",
            None,
        )
        if source_card is not None:
            return getattr(
                source_card,
                "owner",
                None,
            )

        return None

    def _effects_for_source_freeze(
        self,
    ):
        seen = set()
        for effect in (
            list(self.effects)
            + list(self._resolving_effect_stack)
        ):
            effect_id = id(effect)
            if effect_id in seen:
                continue
            seen.add(effect_id)
            yield effect

    def _effect_source_infos(
        self,
        effect,
        seen=None,
    ):
        seen = seen or set()
        if effect is None:
            return

        effect_id = id(effect)
        if effect_id in seen:
            return
        seen.add(effect_id)

        source_info = getattr(
            effect,
            "source_info",
            None,
        )
        if source_info is not None:
            yield source_info

        for child in getattr(
            effect,
            "effects",
            (),
        ) or ():
            yield from self._effect_source_infos(
                child,
                seen=seen,
            )

    def _mark_declared(
        self,
        effect,
    ):

        effect.trigger_declared = True

    def _is_attack_declared_effect(
        self,
        effect,
        attack_id,
    ):

        if getattr(
            effect,
            "attack_id",
            None,
        ) == attack_id:
            return True

        event = self._effect_event(
            effect,
        )
        return (
            isinstance(event, AttackDeclaredEvent)
            and getattr(
                event,
                "attack_id",
                None,
            ) == attack_id
        )

    def _effect_event(
        self,
        effect,
    ):

        package_context = getattr(
            effect,
            "package_context",
            None,
        )
        if isinstance(
            package_context,
            dict,
        ):
            event = package_context.get("event")
            if event is not None:
                return event

        condition_context = getattr(
            effect,
            "condition_context",
            None,
        )
        return getattr(
            condition_context,
            "event",
            None,
        )

    def _selected_declarations(
        self,
        selected,
        choices,
    ):

        if selected is None:
            return []

        if not isinstance(
            selected,
            list,
        ):
            selected = [
                selected,
            ]

        result = []
        for value in selected:
            effect = self._selected_declaration(
                value,
                choices,
            )
            if effect is not None:
                result.append(effect)

        return result

    def _selected_declaration(
        self,
        selected,
        choices,
    ):

        if selected in choices:
            return selected

        for effect in choices:
            source = getattr(
                effect,
                "source_card",
                None,
            )
            if selected is source:
                return effect

        return None
