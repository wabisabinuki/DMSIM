"""
クリーチャー同士のバトル、パワー比較、破壊処理、タップ処理などの戦闘シーケンスを管理するマネージャ。
"""

from actions.attack_creature_action import (
    AttackCreatureAction
)

from actions.destroy_action import (
    DestroyAction
)

from cards.creature_card import (
    CreatureCard
)

from cards.twin_pact_card import (
    TwinPactCard
)

from core.player import (
    Player
)

from events.attack_event import (
    AttackDeclaredEvent,
    AttackEndedEvent,
)

from abilities.keywords.slayer_ability import (
    SlayerAbility
)

from abilities.base.static_ability import StaticAbility

from core.card_filter_evaluator import CardFilterEvaluator

from events.battle_event import (
    BattleDeclaredEvent,
    BattleEndEvent,
    BattleLostEvent,
    BattleStartEvent,
    BattleWonEvent,
)

from events.block_event import (
    BlockDeclaredEvent
)

from events.card_state_event import (
    CardTappedEvent,
)

from events.shield_break_choice_event import (
    ShieldBreakChoiceEvent
)

from core.shield_break_batch import break_shields_batch

from core.game_step import (
    AttackSubStep,
    GameStep,
)

from zones.zone_type import (
    ZoneType
)

from ui.card_display import format_card_name
from ui.debug_log import debug_print


class CombatManager:

    def __init__(
        self,
        context,
    ):

        self.context = context

    def process_attack(
        self,
        action,
    ):

        attacker_player = (
            action.player
        )

        attacker = (
            action.attacker
        )

        target = (
            action.target
        )

        validator = (
            self.context
            .attack_validator
        )

        if not validator.can_attack(
            attacker
        ):
            return

        if not validator.can_attack_target(
            attacker,
            target,
        ):
            return

        state = self.context.state
        state.step = GameStep.ATTACK
        attack_id = getattr(
            state,
            "attack_id_counter",
            0,
        ) + 1
        state.attack_id_counter = attack_id
        state.current_attack_id = attack_id
        # パワーアタッカー等「攻撃中」の常在型能力が参照する現在の攻撃クリーチャー。
        # 攻撃終了（_publish_attack_ended）でクリアする。
        state.current_attacker = attacker
        # パワード・ブロッカー等「ブロック中」の常在型能力が参照する現在のブロッカー。
        # ブロック宣言（try_block）でセットし、攻撃終了でクリアする。
        state.current_blocker = None

        # 攻撃クリーチャー指定ステップ
        state.attack_sub_step = (
            AttackSubStep.DECLARE_ATTACKER
        )

        if not attacker.tapped:
            attacker.tapped = True
            self.context.event_manager.publish(
                CardTappedEvent(
                    attacker_player,
                    attacker,
                    reason="attack",
                )
            )

        print(
            f"{format_card_name(attacker)} attacks "
            f"{format_card_name(target)}"
        )

        event = AttackDeclaredEvent(
            attacker_player,
            attacker,
            target,
            attack_id=attack_id,
        )

        self.context\
            .event_manager\
            .publish(event)

        debug_print(
            "[Debug] After attack event published"
        )

        self._resolve_attack_declared_turn_player_effects(
            attacker_player
        )

        attacker = self._current_attacker_or(
            attacker
        )
        if attacker.zone != ZoneType.BATTLE:
            self.context.effect_resolver.remove_attack_declared_effects(
                attack_id
            )
            self._publish_attack_ended(
                attacker_player,
                attacker,
                target,
                attack_id,
            )
            return

        self.context\
            .game_loop\
            .resolve()

        attacker = self._current_attacker_or(
            attacker
        )
        if attacker.zone != ZoneType.BATTLE:
            self._publish_attack_ended(
                attacker_player,
                attacker,
                target,
                attack_id,
            )
            return

        if self._is_creature(target):

            if target.zone != ZoneType.BATTLE:
                self._publish_attack_ended(
                    attacker_player,
                    attacker,
                    target,
                    attack_id,
                )
                return

        # ブロッククリーチャー指定ステップ
        state.attack_sub_step = (
            AttackSubStep.DECLARE_BLOCKER
        )

        attacker = self._current_attacker_or(
            attacker
        )

        # ガードマン: 相手クリーチャーが自分の「他の」クリーチャーを攻撃する時、
        # 自分のガードマンへ攻撃先を移し替えてもよい。ブロックの前に判定する。
        guarded_target = self.try_guardman(
            attacker,
            target,
        )

        final_target = (
            self.try_block(
                attacker,
                guarded_target,
            )
        )

        if self._is_creature(final_target):

            # バトルステップ
            state.attack_sub_step = (
                AttackSubStep.BATTLE
            )

            attacker = self._current_attacker_or(
                attacker
            )
            battle_action = (
                AttackCreatureAction(
                    attacker_player,
                    attacker,
                    final_target,
                )
            )

            self.process_battle(
                battle_action
            )

        elif isinstance(
            final_target,
            Player,
        ):

            # ダイレクトアタックステップ
            state.attack_sub_step = (
                AttackSubStep.DIRECT_ATTACK
            )

            attacker = self._current_attacker_or(
                attacker
            )
            self.process_player_attack(
                attacker,
                final_target,
            )

        if state.game_over:
            return

        # 攻撃終了ステップ
        attacker = self._current_attacker_or(
            attacker
        )
        self._publish_attack_ended(
            attacker_player,
            attacker,
            target,
            attack_id,
        )

    def _publish_attack_ended(
        self,
        player,
        attacker,
        target,
        attack_id,
    ):
        state = self.context.state
        state.attack_sub_step = (
            AttackSubStep.ATTACK_END
        )
        self.context.event_manager.publish(
            AttackEndedEvent(
                player,
                attacker,
                target,
                attack_id=attack_id,
            )
        )
        self.context.game_loop.resolve()
        state.attack_sub_step = (
            AttackSubStep.NONE
        )
        state.current_attacker = None
        state.current_blocker = None

    def _current_attacker_or(
        self,
        fallback,
    ):

        current = getattr(
            self.context.state,
            "current_attacker",
            None,
        )
        return current or fallback

    def _resolve_attack_declared_turn_player_effects(
        self,
        attacker_player,
    ):
        resolver = self.context.effect_resolver
        resolver.resolve_priority_group(
            self.context,
            resolver.priority_group_for_owner(
                self.context,
                attacker_player,
            ),
        )

    def try_guardman(
        self,
        attacker,
        target,
    ):

        guardmen = (
            self.context
            .query
            .get_guardmen(
                attacker,
                target,
            )
        )

        if not guardmen:
            return target

        defending_player = target.owner

        guardman = (
            self.context
            .target_selector
            .select(
                defending_player,
                guardmen,
                prompt="Choose guardman",
                can_skip=True,
            )
        )

        if guardman is None:
            return target

        if not guardman.tapped:
            guardman.tapped = True
            self.context.event_manager.publish(
                CardTappedEvent(
                    defending_player,
                    guardman,
                    reason="guardman",
                )
            )

        print(
            f"{format_card_name(guardman)} guards "
            f"{format_card_name(target)}!"
        )

        return guardman

    def try_block(
        self,
        attacker,
        target,
    ):

        blockers = (
            self.context
            .query
            .get_blockers(
                attacker,
                target,
            )
        )

        if not blockers:
            return target

        defending_player = (
            target.owner
            if self._is_creature(target)
            else target
        )

        blocker = (
            self.context
            .target_selector
            .select(
                defending_player,
                blockers,
                prompt="Choose blocker",
                can_skip=True,
            )
        )

        if blocker is None:
            return target

        if not blocker.tapped:
            blocker.tapped = True
            self.context.event_manager.publish(
                CardTappedEvent(
                    defending_player,
                    blocker,
                    reason="block",
                )
            )

        print(
            f"{format_card_name(blocker)} blocks!"
        )

        self.context.event_manager.publish(
            BlockDeclaredEvent(
                defending_player,
                blocker,
                attacker,
                target,
                attack_id=getattr(
                    self.context.state,
                    "current_attack_id",
                    None,
                ),
            )
        )

        # パワード・ブロッカー等「ブロック中」の常在型能力が参照する現在のブロッカー。
        # このあとのバトル（process_battle）で有効になり、攻撃終了でクリアされる。
        self.context.state.current_blocker = blocker

        return blocker

    def process_player_attack(
        self,
        attacker,
        target_player,
    ):

        # shield break
        if self._shield_options(target_player):

            break_count = self._choose_break_count(
                attacker,
                target_player,
            )

            shields_to_break = (
                self._choose_shields_to_break(
                    attacker,
                    target_player,
                    break_count,
                )
            )

            # 同時ブレイクとしてバッチ処理する
            # （全試行＋置換 → 全通知 → 一括移動）。
            break_shields_batch(
                self.context,
                shields_to_break,
                attacker,
            )

            self.context.replacement_manager.finalize_pending_replacements()

            print(
                f"{format_card_name(attacker)} broke "
                f"{target_player.name}'s shield"
            )

            resolver = (
                self.context
                .shield_trigger_resolver
            )

            resolver.resolve()

            debug_print(
                "[Debug] After shield check resolved"
            )

            self.context\
                .game_loop\
                .resolve()

            if self.context.state.game_over:
                return

        # direct attack
        else:

            won = self.context.state.declare_win(
                attacker.owner,
                loser=target_player,
                reason="direct_attack",
            )

            if won:
                print(
                    f"{format_card_name(attacker)} wins!"
                )

    def _choose_break_count(
        self,
        attacker,
        target_player,
    ):

        options = self._break_options(
            attacker,
        )

        event = ShieldBreakChoiceEvent(
            attacker,
            target_player,
            options,
        )
        self.context.event_manager.publish(
            event
        )

        if len(options) == 1:
            return options[0]

        return self.context.choice_manager.select(
            attacker.owner,
            options,
            prompt=(
                "Choose breaker option "
                f"for {format_card_name(attacker)}"
            ),
        )

    def _choose_shields_to_break(
        self,
        attacker,
        target_player,
        break_count,
    ):
        shields = self._shield_options(
            target_player
        )
        amount = min(
            break_count,
            len(shields),
        )

        if amount <= 0:
            return []

        if amount == 1:
            shield = self.context.target_selector.select(
                attacker.owner,
                shields,
                prompt="Choose a shield to break",
            )
            return [] if shield is None else [shield]

        chosen = self.context.target_selector.select_multiple(
            attacker.owner,
            shields,
            prompt="Choose shields to break",
            min_count=amount,
            max_count=amount,
        )
        return chosen[:amount]

    def _shield_options(
        self,
        player,
    ):

        visible_shields = getattr(
            player.shield_zone,
            "visible_shields",
            None,
        )
        if visible_shields is not None:
            return visible_shields()

        return list(player.shield_zone.cards)

    def _break_options(
        self,
        attacker,
    ):

        options = sorted(
            set(
                attacker.get_break_options()
            )
        )
        for limit in self._break_limits_for(attacker):
            options = [
                min(option, limit)
                for option in options
            ]

        return sorted(
            set(options)
        )

    def _break_limits_for(
        self,
        attacker,
    ):
        limits = []
        for player in self.context.state.players:
            for zone in (
                player.battle_zone,
                player.shield_zone,
            ):
                for card in zone.cards[:]:
                    for ability in getattr(card, "abilities", ()):
                        limit = self._break_limit_from_ability(
                            ability,
                            attacker,
                        )
                        if limit is not None:
                            limits.append(limit)

        return limits

    def _break_limit_from_ability(
        self,
        ability,
        attacker,
    ):
        if not isinstance(ability, StaticAbility):
            return None

        if ability.static_type != "break_modifier":
            return None

        modifier = getattr(ability, "modifier", {}) or {}
        limit = modifier.get(
            "max",
            modifier.get("max_breaks"),
        )
        if limit is None:
            return None

        source = ability.owner_card
        if not ability.is_active(
            player=getattr(source, "owner", None),
        ):
            return None

        if not self._break_limit_applies(
            ability,
            attacker,
        ):
            return None

        return int(limit)

    def _break_limit_applies(
        self,
        ability,
        attacker,
    ):
        applies_to = getattr(ability, "applies_to", {}) or {}
        source = ability.owner_card
        source_owner = getattr(source, "owner", None)
        player_ref = applies_to.get("player")
        if player_ref is not None:
            expected = self._break_limit_player(
                source_owner,
                player_ref,
            )
            if attacker.owner is not expected:
                return False

        filter_spec = applies_to.get("filter")
        if filter_spec is None:
            filter_spec = {
                key: value
                for key, value in applies_to.items()
                if key not in (
                    "player",
                    "card",
                )
            }

        if filter_spec:
            return CardFilterEvaluator(
                self.context
            ).matches(
                attacker,
                filter_spec,
                {
                    "controller": source_owner,
                    "player": source_owner,
                    "source_card": source,
                },
            )

        return True

    def _break_limit_player(
        self,
        source_owner,
        ref,
    ):
        if ref in (
            "self",
            "controller",
            "owner",
        ):
            return source_owner

        if ref == "opponent":
            return self.context.query.get_opponent(
                source_owner
            )

        return ref

    def _is_creature(
        self,
        card,
    ):

        if isinstance(
            card,
            CreatureCard,
        ):
            return True

        return (
            isinstance(card, TwinPactCard)
            and
            isinstance(card.selected_face, CreatureCard)
        )

    def process_battle(
        self,
        action,
    ):

        attacker = (
            action.attacker
        )

        defender = (
            action.target_creature
        )

        print(
            f"{format_card_name(attacker)} battles "
            f"{format_card_name(defender)}"
        )

        state = self.context.state
        battle_id = getattr(
            state,
            "battle_id_counter",
            0,
        ) + 1
        state.battle_id_counter = battle_id

        event_manager = (
            self.context.event_manager
        )

        # 1. バトル成立の宣言。スーパーガードマン等「バトルする時、かわりに
        #    〜」の置換効果はここに反応してバトルの参加者を差し替える。
        #    置換適用後（差し替え後）の参加者で以降を進める。
        declared = BattleDeclaredEvent(
            attacker.owner,
            attacker,
            defender,
            battle_id=battle_id,
        )
        self.context.replacement_manager.apply(declared)
        attacker = declared.attacker
        defender = declared.defender

        # 置換効果を含む「バトル中」の常在型能力はここから有効になる。
        # 「バトル中、パワー+N」等が参照する現在のバトル参加者をここでセットし、
        # バトル終了（BattleEndEvent 発行後）でクリアする。
        state.current_battle_attacker = attacker
        state.current_battle_defender = defender
        event_manager.publish(declared)

        # 2. 「バトルする時」の誘発を解決する。
        event_manager.publish(
            BattleStartEvent(
                attacker.owner,
                attacker,
                defender,
                battle_id=battle_id,
            )
        )

        self.context\
            .game_loop\
            .resolve()

        # スレイヤーの判定はバトル開始（誘発解決後）の状態で捕捉する。
        # バトルで自身が破壊されても「バトルの後」の破壊は実行される。
        attacker_slayer = (
            self._has_slayer(attacker)
        )

        defender_slayer = (
            self._has_slayer(defender)
        )

        # 3. 誘発の解決でどちらかがバトルゾーンを離れていたら
        #    バトル不成立。「バトルの後」タイミングも発生しない。
        if (
            attacker.zone != ZoneType.BATTLE
            or defender.zone != ZoneType.BATTLE
        ):
            return

        attacker_power = (
            attacker.get_current_power()
        )

        defender_power = (
            defender.get_current_power()
        )

        print(
            f"{format_card_name(attacker)}"
            f" ({attacker_power}) "
            f"vs "
            f"{format_card_name(defender)}"
            f" ({defender_power})"
        )

        attacker_destroyed = (
            defender_power
            >= attacker_power
        )

        defender_destroyed = (
            attacker_power
            >= defender_power
        )

        # 「すべてのバトルに勝つ」効果を反映
        attacker_wins_all = getattr(
            attacker,
            "wins_all_battles_this_turn",
            False,
        )
        defender_wins_all = getattr(
            defender,
            "wins_all_battles_this_turn",
            False,
        )

        if attacker_wins_all and defender_wins_all:
            # 両者が「すべてのバトルに勝つ」場合は相打ち
            attacker_destroyed = True
            defender_destroyed = True
        elif attacker_wins_all:
            attacker_destroyed = False
            defender_destroyed = True
        elif defender_wins_all:
            attacker_destroyed = True
            defender_destroyed = False

        # 勝敗イベント。同パワーは両者敗北（BattleLostEvent のみ）。
        if defender_destroyed and not attacker_destroyed:
            event_manager.publish(
                BattleWonEvent(
                    attacker.owner,
                    attacker,
                    defender,
                )
            )
        elif attacker_destroyed and not defender_destroyed:
            event_manager.publish(
                BattleWonEvent(
                    defender.owner,
                    defender,
                    attacker,
                )
            )

        if attacker_destroyed:
            event_manager.publish(
                BattleLostEvent(
                    attacker.owner,
                    attacker,
                    defender,
                )
            )

        if defender_destroyed:
            event_manager.publish(
                BattleLostEvent(
                    defender.owner,
                    defender,
                    attacker,
                )
            )

        if attacker_destroyed:

            destroy_action = (
                DestroyAction(
                    attacker.owner,
                    attacker,
                )
            )

            self.context\
                .action_processor\
                .process(
                    destroy_action
                )

        if defender_destroyed:

            destroy_action = (
                DestroyAction(
                    defender.owner,
                    defender,
                )
            )

            self.context\
                .action_processor\
                .process(
                    destroy_action
                )

        # 4. 敗北による破壊（ZoneChangeEvent）と誘発の解決。
        self.context\
            .game_loop\
            .resolve()

        # 5. バトルの後: スレイヤーによる破壊。
        self._resolve_slayer_destroys(
            attacker,
            attacker_slayer,
            defender,
            defender_slayer,
        )

        # 6. 「バトルの後」タイミング。
        event_manager.publish(
            BattleEndEvent(
                attacker.owner,
                attacker,
                defender,
                battle_id=battle_id,
            )
        )

        # 「バトル中」の常在型能力の参照をクリアする。
        state.current_battle_attacker = None
        state.current_battle_defender = None

        self.context\
            .game_loop\
            .resolve()

    def _has_slayer(
        self,
        card,
    ):

        return card.has_ability(
            SlayerAbility
        )

    def _resolve_slayer_destroys(
        self,
        attacker,
        attacker_slayer,
        defender,
        defender_slayer,
    ):

        destroyed_any = False

        if (
            attacker_slayer
            and defender.zone == ZoneType.BATTLE
        ):
            print(
                f"{format_card_name(defender)} is "
                "destroyed by slayer"
            )
            self.context.action_processor.process(
                DestroyAction(
                    defender.owner,
                    defender,
                )
            )
            destroyed_any = True

        if (
            defender_slayer
            and attacker.zone == ZoneType.BATTLE
        ):
            print(
                f"{format_card_name(attacker)} is "
                "destroyed by slayer"
            )
            self.context.action_processor.process(
                DestroyAction(
                    attacker.owner,
                    attacker,
                )
            )
            destroyed_any = True

        if destroyed_any:
            self.context\
                .game_loop\
                .resolve()
