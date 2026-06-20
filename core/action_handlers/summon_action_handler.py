"""
クリーチャーの召喚アクションを実行するハンドラ。手札からバトルゾーンへの安全な移動と召喚イベント発行を処理します。
"""

from core.action_handlers.base_action_handler import (
    BaseActionHandler
)

from events.summon_event import (
    SummonEvent
)

from zones.zone_type import (
    ZoneType
)

from cards.twin_pact_card import (
    TwinPactCard
)

from cards.card import (
    SpecialType
)

from abilities.keywords.evolution_ability import EvolutionAbility
from core.evolution_support import stack_evolution_sources

from ui.card_display import format_card_name
from core.pending_cards import (
    begin_pending,
    end_pending,
    is_card_pending,
)
from core.seal_utils import is_ignored_by_seal, is_seal_card
from core.play_history import record_play


class SummonActionHandler(
    BaseActionHandler
):

    def process(
        self,
        action,
    ):

        player = action.player

        card = action.card

        if isinstance(card, TwinPactCard):
            card.select_creature_face()

        from_zone = (
            getattr(
                card,
                "zone",
                None,
            )
            or ZoneType.HAND
        )

        evolution_source = None
        if self._requires_evolution_source(card):
            evolution_source = (
                action.evolution_source
                or self._choose_evolution_source(
                    player,
                    card,
                )
            )

            if evolution_source is None:
                return
        elif self._can_optionally_evolve(card):
            evolution_source = (
                action.evolution_source
                if action.evolution_source is not None
                else self._choose_optional_evolution_source(
                    player,
                    card,
                )
            )

            if evolution_source is not None and not self._is_valid_source(
                player,
                card,
                evolution_source,
            ):
                return

        play_permission = self._choose_play_permission(
            action,
            player,
            card,
        )
        if (
            self._has_play_permissions(action)
            and play_permission is None
        ):
            return

        begin_pending(
            card,
            reason="summon",
        )

        # 進化元を先に確定しておき、コスト計算（ソウルシフト等）から参照できる
        # ようにする。順序は「召喚宣言 → 進化元選択 → マナ支払い → 出す」。
        card._soulshift_source = evolution_source

        try:
            if not action.ignore_cost:

                alternative_cost = getattr(
                    action,
                    "alternative_cost",
                    None,
                )
                if alternative_cost is not None:
                    if not alternative_cost.pay(
                        self.game_controller,
                        player,
                        card,
                    ):
                        return

                else:
                    if not player.can_play(
                        card,
                        self.game_controller,
                    ):
                        return

                    # 実際の召喚時のみ、任意のコスト軽減（「してもよい」）の
                    # 使用可否をプレイヤーへ尋ね、その選択を確定（consume）する。
                    # 採用された場合のみ使用回数を消費するため、ここで consume
                    # して問題ない（採用＝軽減後の額で can_play 済みなので
                    # tap_mana は必ず成功する。辞退時は何も消費しない）。
                    try:
                        play_cost = card.get_current_cost(
                            player=player,
                            game=self.game_controller,
                            consume=True,
                            interactive=True,
                        )
                    except TypeError:
                        play_cost = card.get_current_cost()

                    if not player.tap_mana(
                        play_cost,
                        spending_card=card,
                        choice_manager=(
                            self.game_controller
                            .choice_manager
                        ),
                    ):
                        return

            self._prepare_as_enters_battle_abilities(
                card,
                player,
            )

            self.game_controller.event_manager.publish(
                SummonEvent(
                    player,
                    card,
                    from_zone=from_zone,
                    evolution_source=evolution_source,
                    ignore_cost=action.ignore_cost,
                    play_method=action.play_method,
                )
            )

            moved = self.game_controller\
                .card_mover.move(
                    card=card,
                    owner=player,
                    from_zone=from_zone,
                    to_zone=(
                        ZoneType.BATTLE
                    ),
                    reason="summon",
                    publish_battle_enter=False,
                )

            if not moved:
                return

            if card.zone != ZoneType.BATTLE:
                # 出るかわりに別ゾーンへ置換された（超次元ゾーンなど）。進化元が
                # バトルゾーン以外（墓地・手札・マナ）から供給される進化なら、選んだ
                # 進化元も進化クリーチャーと同じ置換先へ一緒に動かす。バトルゾーンの
                # 進化元は元から盤面にいるため巻き込まない。
                if evolution_source is not None:
                    self._follow_evolution_source_on_redirect(
                        player,
                        card,
                        evolution_source,
                    )
                return

            record_play(
                self.game_controller,
                player,
                card,
                "summon",
                from_zone,
                action,
            )

            self._mark_play_permission_used(
                play_permission,
                player,
                card,
            )

            if evolution_source is not None:
                self._stack_evolution_sources(
                    player,
                    card,
                    evolution_source,
                )

            if getattr(
                card,
                "is_evolution",
                False,
            ):
                card.summoning_sick = False
            else:
                card.summoning_sick = True

            # 出たターンを記録（マッハファイター判定用）
            card.summon_turn = self.game_controller.state.turn

            self.game_controller.card_mover.publish_battle_enter(
                card=card,
                owner=player,
                from_zone=from_zone,
                reason="summon",
                cost_skipped=action.ignore_cost,
            )

            if evolution_source is not None:
                print(
                    f"{player.name} summoned "
                    f"{format_card_name(card)} "
                    f"from {self._format_sources(evolution_source)}"
                )
            else:
                print(
                    f"{player.name} summoned "
                    f"{format_card_name(card)}"
                )
        finally:
            card._soulshift_source = None
            end_pending(card)

    def _choose_play_permission(
        self,
        action,
        player,
        card,
    ):
        permissions = self._valid_play_permissions(
            action,
            player,
            card,
        )
        if not permissions:
            return None

        prompt = self._play_permission_prompt(
            permissions,
            player,
            card,
        )
        selected = (
            self.game_controller
            .choice_manager
            .select(
                player,
                permissions,
                prompt=prompt,
                auto_choose_single=True,
            )
        )
        action.selected_play_permission = selected
        return selected

    def _has_play_permissions(
        self,
        action,
    ):
        return bool(
            self._action_play_permissions(
                action
            )
        )

    def _valid_play_permissions(
        self,
        action,
        player,
        card,
    ):
        return [
            permission
            for permission in self._action_play_permissions(
                action
            )
            if self._permission_allows(
                permission,
                player,
                card,
            )
        ]

    def _action_play_permissions(
        self,
        action,
    ):
        permissions = []
        seen = set()

        def add(permission):
            if permission is None:
                return
            key = id(permission)
            if key in seen:
                return
            seen.add(key)
            permissions.append(permission)

        for permission in getattr(
            action,
            "play_permissions",
            (),
        ):
            add(permission)

        add(
            getattr(
                action,
                "play_permission",
                None,
            )
        )

        return permissions

    def _permission_allows(
        self,
        permission,
        player,
        card,
    ):
        can_use = getattr(
            permission,
            "can_use_for",
            None,
        )
        if can_use is None:
            return True

        return bool(
            can_use(
                player,
                card,
            )
        )

    def _play_permission_prompt(
        self,
        permissions,
        player,
        card,
    ):
        for permission in permissions:
            prompt = getattr(
                permission,
                "selection_prompt",
                None,
            )
            if prompt is not None:
                return prompt(
                    player,
                    card,
                )

        return (
            "Choose play permission "
            f"for {format_card_name(card)}"
        )

    def _mark_play_permission_used(
        self,
        permission,
        player,
        card,
    ):
        if permission is None:
            return

        mark_used = getattr(
            permission,
            "mark_used",
            None,
        )
        if mark_used is None:
            return

        mark_used(
            player,
            card,
        )

    def _prepare_as_enters_battle_abilities(
        self,
        card,
        player,
    ):

        for ability in card.abilities:
            prepare = getattr(
                ability,
                "prepare_to_enter_battle",
                None,
            )
            if prepare is not None:
                prepare(player)

    def _choose_evolution_source(
        self,
        player,
        card,
    ):

        choices = self._evolution_source_candidates(
            player,
            card,
        )

        if not choices:
            return None

        ability = self._evolution_ability(card)
        source_count = getattr(
            ability,
            "source_count",
            1,
        )

        if source_count != 1:
            return (
                self.game_controller
                .choice_manager
                .select(
                    player,
                    choices,
                    prompt=(
                        "Choose evolution sources "
                        f"for {card.name}"
                    ),
                    min_count=source_count,
                    max_count=source_count,
                )
            )

        return (
            self.game_controller
            .choice_manager
            .select(
                player,
                choices,
                prompt=(
                    "Choose evolution source "
                    f"for {card.name}"
                ),
            )
        )

    def _choose_optional_evolution_source(
        self,
        player,
        card,
    ):

        choices = [
            None,
            *self._evolution_source_candidates(
                player,
                card,
            ),
        ]

        if len(choices) == 1:
            return None

        return (
            self.game_controller
            .choice_manager
            .select(
                player,
                choices,
                prompt=(
                    "Choose NEO evolution source "
                    f"for {card.name} "
                    "(skip for normal summon)"
                ),
            )
        )

    def _evolution_source_candidates(
        self,
        player,
        card,
    ):

        if (
            card.has_special_type(
                SpecialType.DREAM
            )
            and any(
                candidate is not card
                and not is_card_pending(candidate)
                and not is_seal_card(candidate)
                and not is_ignored_by_seal(candidate)
                and candidate.has_special_type(
                    SpecialType.DREAM
                )
                and candidate.name == card.name
                for candidate in player.battle_zone.cards
            )
        ):
            return []

        ability = self._evolution_ability(card)
        if ability is None:
            return []

        return ability.source_candidates(
            player,
            card,
        )

    def _requires_evolution_source(
        self,
        card,
    ):

        return (
            card.has_special_type(
                SpecialType.EVOLUTION
            )
            and not card.has_special_type(
                SpecialType.NEO
            )
            and self._evolution_ability(card) is not None
        )

    def _can_optionally_evolve(
        self,
        card,
    ):

        return card.has_special_type(
            SpecialType.NEO
        )

    def _stack_evolution_sources(
        self,
        player,
        card,
        sources,
    ):

        stack_evolution_sources(
            player,
            card,
            sources,
        )

    def _follow_evolution_source_on_redirect(
        self,
        player,
        card,
        evolution_source,
    ):

        ability = self._evolution_ability(card)
        if (
            ability is None
            or ability.source_zone == ZoneType.BATTLE
        ):
            return

        sources = (
            evolution_source
            if isinstance(evolution_source, list)
            else [evolution_source]
        )
        for source in sources:
            self.game_controller.card_mover.move(
                card=source,
                owner=player,
                from_zone=ability.source_zone,
                to_zone=card.zone,
                reason="evolution_source_follow",
            )

    def _is_valid_source(
        self,
        player,
        card,
        source,
    ):

        sources = (
            source
            if isinstance(source, list)
            else [source]
        )
        candidates = self._evolution_source_candidates(
            player,
            card,
        )
        ability = self._evolution_ability(card)
        source_count = getattr(
            ability,
            "source_count",
            1,
        )
        return (
            len(sources) == source_count
            and len(set(id(source) for source in sources))
            == len(sources)
            and all(
                candidate in candidates
                for candidate in sources
            )
        )

    def _format_sources(
        self,
        sources,
    ):

        if not isinstance(
            sources,
            list,
        ):
            sources = [sources]

        return ", ".join(
            format_card_name(source)
            for source in sources
        )

    def _evolution_ability(
        self,
        card,
    ):

        for ability in getattr(
            card,
            "abilities",
            [],
        ):
            if isinstance(
                ability,
                EvolutionAbility,
            ):
                return ability

        return None
