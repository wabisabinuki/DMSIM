"""
カードの領域移動（Deck, Hand, Battle, Shields, Mana, Graveyard等）を安全に実行するモジュール。移動試行、置換効果の適用、移動確定、イベント発行の3ステップ移動を担います。
"""

from events.zone_change_attempt_event import (
    ZoneChangeAttemptEvent
)

from events.zone_change_event import (
    ZoneChangeEvent
)

from events.battle_zone_enter_event import (
    BattleZoneEnterEvent
)

from zones.zone_type import (
    ZoneType
)

from core.battle_display_labels import (
    clear_battle_display_label,
    ensure_battle_display_label,
)

from core.pending_cards import (
    begin_pending,
    end_pending,
    is_card_pending,
)
from core.seal_utils import is_ignored_by_seal, is_seal_card
from ui.card_display import format_card_name
from ui.debug_log import is_debug_enabled


_ZONE_LABELS = {
    "DECK": "山札",
    "HAND": "手札",
    "BATTLE": "バトルゾーン",
    "SHIELD": "シールド",
    "MANA": "マナ",
    "GRAVEYARD": "墓地",
    "EXILE": "追放",
    "SUPER_DIMENSION": "超次元",
}


class SwapMove:

    def __init__(
        self,
        card,
        owner,
        from_zone,
        to_zone,
        reason=None,
        publish_battle_enter=True,
    ):

        self.card = card
        self.owner = owner
        self.from_zone = from_zone
        self.to_zone = to_zone
        self.reason = reason
        self.publish_battle_enter = publish_battle_enter


class SwapResult:

    def __init__(
        self,
        succeeded,
        reason=None,
    ):

        self.succeeded = bool(succeeded)
        self.reason = reason

    def __bool__(
        self,
    ):

        return self.succeeded


class CardMover:

    def __init__(
        self,
        context,
    ):

        self.context = context

    def pre_freeze_sources_for(
        self,
        card,
    ):
        self.pre_freeze_sources_for_many(
            [
                card,
            ]
        )

    def pre_freeze_sources_for_many(
        self,
        cards,
    ):
        expanded = []
        seen = set()
        for card in cards:
            self._collect_source_tree(
                card,
                expanded,
                seen,
            )

        if not expanded:
            return

        resolver = getattr(
            self.context,
            "effect_resolver",
            None,
        )
        if resolver is None:
            return

        resolver.freeze_sources_for_many(
            expanded,
            trigger_manager=getattr(
                self.context,
                "trigger_manager",
                None,
            ),
        )

    def _collect_source_tree(
        self,
        card,
        result,
        seen,
    ):
        if card is None:
            return

        card_id = id(card)
        if card_id in seen:
            return

        seen.add(card_id)
        result.append(card)

        for child in getattr(
            card,
            "evolution_sources",
            (),
        ) or ():
            self._collect_source_tree(
                child,
                result,
                seen,
            )

    def move(
        self,
        card,
        owner,
        from_zone,
        to_zone,
        reason=None,
        evolution_mode="stack",
        shield_face_up=None,
        shield_stack_on=None,
        publish_battle_enter=True,
        apply_replacements=True,
    ):

        auto_pending_started = False
        if (
            to_zone == ZoneType.BATTLE
            and not is_card_pending(card)
        ):
            auto_pending_started = begin_pending(
                card,
                reason=reason or "enter_battle",
            )

        try:
            return self._move_core(
                card=card,
                owner=owner,
                from_zone=from_zone,
                to_zone=to_zone,
                reason=reason,
                evolution_mode=evolution_mode,
                shield_face_up=shield_face_up,
                shield_stack_on=shield_stack_on,
                publish_battle_enter=publish_battle_enter,
                apply_replacements=apply_replacements,
            )
        finally:
            if (
                auto_pending_started
                and is_card_pending(card)
            ):
                end_pending(card)

    def swap(
        self,
        first,
        second,
        reason=None,
        apply_replacements=True,
    ):

        first = self._swap_move(first, reason)
        second = self._swap_move(second, reason)

        for move in (
            first,
            second,
        ):
            blocked_reason = self._preflight_swap_move(
                move,
                apply_replacements=apply_replacements,
            )
            if blocked_reason is not None:
                return SwapResult(
                    False,
                    blocked_reason,
                )

        self.pre_freeze_sources_for_many(
            [
                first.card,
                second.card,
            ]
        )

        moved_first = self.move(
            card=first.card,
            owner=first.owner,
            from_zone=first.from_zone,
            to_zone=first.to_zone,
            reason=first.reason,
            publish_battle_enter=first.publish_battle_enter,
            apply_replacements=False,
        )
        if not moved_first:
            return SwapResult(
                False,
                "first_move_failed",
            )

        moved_second = self.move(
            card=second.card,
            owner=second.owner,
            from_zone=second.from_zone,
            to_zone=second.to_zone,
            reason=second.reason,
            publish_battle_enter=second.publish_battle_enter,
            apply_replacements=False,
        )
        if not moved_second:
            return SwapResult(
                False,
                "second_move_failed",
            )

        return SwapResult(True)

    def move_shield_slots_to_hand_batch(
        self,
        shields,
        owner,
        reason=None,
        apply_replacements=True,
    ):
        """Move selected shield slots to hand as one simultaneous batch."""

        attempts = []
        for shield in shields:
            attempt_event = ZoneChangeAttemptEvent(
                card=shield,
                owner=owner,
                from_zone=ZoneType.SHIELD,
                to_zone=ZoneType.HAND,
                reason=reason,
            )

            if self._state_definitions_prevent(attempt_event):
                continue

            if apply_replacements:
                self.context.replacement_manager.apply(
                    attempt_event
                )

            if attempt_event.cancelled:
                continue

            if (
                attempt_event.from_zone != ZoneType.SHIELD
                or attempt_event.to_zone != ZoneType.HAND
            ):
                continue

            attempts.append(attempt_event)

        if not attempts:
            return False

        source = owner.get_zone(ZoneType.SHIELD)
        destination = owner.get_zone(ZoneType.HAND)
        groups = []
        all_slot_cards = []
        moved_a_shield = False

        for attempt_event in attempts:
            slot_cards = self._shield_move_cards(
                source,
                attempt_event.card,
            )
            if not slot_cards:
                slot_cards = [attempt_event.card]

            groups.append(slot_cards)
            all_slot_cards.extend(slot_cards)
            moved_a_shield = moved_a_shield or any(
                not self._is_active_fortified_castle(slot_card)
                for slot_card in slot_cards
            )

        self._declare_shield_checks(
            owner,
            all_slot_cards,
            reason,
        )

        self.pre_freeze_sources_for_many(
            all_slot_cards
        )

        events = []
        for slot_cards in groups:
            self._remove_shield_cards(
                source,
                slot_cards,
            )
            for slot_card in slot_cards:
                from_shield_face_up = bool(
                    getattr(
                        slot_card,
                        "shield_face_up",
                        False,
                    )
                )
                slot_card.zone_change_counter += 1
                destination.add(slot_card)
                slot_card.zone = ZoneType.HAND
                slot_card.shield_face_up = False
                slot_card.deck_face_up = False
                end_pending(slot_card)

                events.append(
                    ZoneChangeEvent(
                        card=slot_card,
                        owner=owner,
                        from_zone=ZoneType.SHIELD,
                        to_zone=ZoneType.HAND,
                        reason=reason,
                        from_shield_face_up=from_shield_face_up,
                    )
                )

        if moved_a_shield:
            self.context.state_based_actions.note_shield_left()
            self.context.state_based_actions.check_and_apply()

        for event in events:
            self._before_zone_change_event(event)
            self._apply_state_definitions_after_move(event)
            self.context.event_manager.publish(event)
            self._after_zone_change_event(event)

        if reason != "shield_break":
            self._resolve_non_break_shield_check(owner)

        return True

    def _swap_move(
        self,
        value,
        reason,
    ):

        if isinstance(
            value,
            SwapMove,
        ):
            if value.reason is None:
                value.reason = reason
            return value

        move = SwapMove(
            card=value["card"],
            owner=value["owner"],
            from_zone=value["from_zone"],
            to_zone=value["to_zone"],
            reason=value.get("reason", reason),
            publish_battle_enter=value.get(
                "publish_battle_enter",
                True,
            ),
        )
        return move

    def _preflight_swap_move(
        self,
        move,
        apply_replacements=True,
    ):

        if (
            move.from_zone == ZoneType.BATTLE
            and is_ignored_by_seal(move.card)
        ):
            return "card_ignored_by_seal"

        if getattr(
            move.card,
            "zone",
            None,
        ) != move.from_zone:
            return "card_not_in_source_zone"

        source = move.owner.get_zone(
            move.from_zone
        )
        if move.card not in source.cards:
            return "card_not_in_source_zone"

        attempt_event = ZoneChangeAttemptEvent(
            card=move.card,
            owner=move.owner,
            from_zone=move.from_zone,
            to_zone=move.to_zone,
            reason=move.reason,
        )

        if self._state_definitions_prevent(
            attempt_event
        ):
            return "state_definition_prevents_move"

        if (
            apply_replacements
            and self.context.replacement_manager.would_replace(
                attempt_event
            )
        ):
            return "replacement_would_apply"

        return None

    def _move_core(
        self,
        card,
        owner,
        from_zone,
        to_zone,
        reason=None,
        evolution_mode="stack",
        shield_face_up=None,
        shield_stack_on=None,
        publish_battle_enter=True,
        apply_replacements=True,
    ):

        if (
            from_zone == ZoneType.BATTLE
            and is_ignored_by_seal(card)
        ):
            return False

        # 移動試行event
        attempt_event = (
            ZoneChangeAttemptEvent(
                card=card,
                owner=owner,
                from_zone=from_zone,
                to_zone=to_zone,
                reason=reason,
            )
        )

        if self._state_definitions_prevent(
            attempt_event
        ):
            return False

        # replacement適用
        if apply_replacements:
            self.context\
                .replacement_manager\
                .apply(
                    attempt_event
                )

        # キャンセル
        if attempt_event.cancelled:

            return False

        if (
            is_card_pending(card)
            and attempt_event.from_zone == attempt_event.to_zone
            and getattr(
                card,
                "pending_origin_zone",
                None,
            )
            == attempt_event.to_zone
        ):
            end_pending(card)
            return True

        source = owner.get_zone(
            attempt_event.from_zone
        )

        destination = owner.get_zone(
            attempt_event.to_zone
        )

        if (
            attempt_event.from_zone == ZoneType.SHIELD
            and attempt_event.to_zone != ZoneType.SHIELD
        ):
            return self._move_shield_slot(
                card=card,
                owner=owner,
                from_zone=attempt_event.from_zone,
                to_zone=attempt_event.to_zone,
                reason=reason,
                source=source,
                destination=destination,
                publish_battle_enter=publish_battle_enter,
            )

        if (
            attempt_event.from_zone == ZoneType.BATTLE
            and evolution_mode == "card"
        ):
            if self._detach_evolution_source(
                card,
                owner,
                attempt_event.from_zone,
                attempt_event.to_zone,
                reason,
                destination,
            ):
                return True

            if getattr(
                card,
                "evolution_sources",
                None,
            ):
                return self._move_evolution_top_only(
                    card,
                    owner,
                    attempt_event.from_zone,
                    attempt_event.to_zone,
                    reason,
                    source,
                    destination,
                )

        evolution_sources = []
        self.pre_freeze_sources_for(
            card
        )
        if (
            attempt_event.from_zone
            == ZoneType.BATTLE
            and hasattr(card, "clear_evolution_sources")
        ):
            evolution_sources = (
                card.clear_evolution_sources()
            )

        # battle離脱時
        if (
            attempt_event.from_zone
            == ZoneType.BATTLE
        ):

            card.reset_battle_state()

        # zone change counter
        card.zone_change_counter += 1

        from_shield_face_up = (
            bool(getattr(card, "shield_face_up", False))
            if attempt_event.from_zone == ZoneType.SHIELD
            else False
        )

        # remove/add
        source.remove(card)
        self._check_deck_empty_after_move(
            owner,
            attempt_event.from_zone,
        )

        self._add_to_destination(
            destination,
            card,
            attempt_event.to_zone,
            shield_stack_on,
        )

        # zone更新
        card.zone = (
            attempt_event.to_zone
        )
        if (
            attempt_event.from_zone != ZoneType.DECK
            or attempt_event.to_zone != ZoneType.DECK
        ):
            card.deck_face_up = False

        end_pending(card)

        if attempt_event.to_zone == ZoneType.SHIELD:
            card.shield_face_up = bool(shield_face_up)
            card.register_abilities(
                self.context.event_manager
            )
        elif attempt_event.from_zone == ZoneType.SHIELD:
            card.shield_face_up = False

        if attempt_event.to_zone == ZoneType.BATTLE:
            ensure_battle_display_label(
                card,
                owner,
            )
            self._finalize_battle_enter_seal(
                card,
            )

        if (
            attempt_event.from_zone == ZoneType.SHIELD
            and attempt_event.to_zone != ZoneType.SHIELD
        ):
            self.context.state_based_actions.note_shield_left()
            self.context.state_based_actions.check_and_apply()

        # 完了event
        event = ZoneChangeEvent(
            card=card,
            owner=owner,
            from_zone=(
                attempt_event.from_zone
            ),
            to_zone=(
                attempt_event.to_zone
            ),
            reason=reason,
            from_shield_face_up=from_shield_face_up,
            evolution_sources=evolution_sources,
        )

        self._before_zone_change_event(event)

        self._apply_state_definitions_after_move(
            event
        )

        # publish
        self.context\
            .event_manager\
            .publish(
                event
            )

        self._after_zone_change_event(event)

        if (
            publish_battle_enter
            and attempt_event.to_zone == ZoneType.BATTLE
        ):
            self.publish_battle_enter(
                card=card,
                owner=owner,
                from_zone=attempt_event.from_zone,
                reason=reason,
            )

        # 全誘発のトリガーチェック・待機（入場イベント発行）が済んでから封印解除
        if attempt_event.to_zone == ZoneType.BATTLE:
            self._apply_seal_removal_on_enter(
                card,
                owner,
            )

        if (
            attempt_event.from_zone == ZoneType.BATTLE
            and attempt_event.to_zone != ZoneType.BATTLE
        ):
            clear_battle_display_label(card)

        for source_card in evolution_sources:
            self._move_evolution_source(
                source_card,
                owner,
                attempt_event.from_zone,
                attempt_event.to_zone,
                reason,
                destination,
            )

        return True

    def _check_deck_empty_after_move(
        self,
        owner,
        from_zone,
    ):
        if from_zone != ZoneType.DECK:
            return False

        if owner.deck.cards:
            return False

        return self.context.state.declare_loss(
            owner,
            reason="deck_out",
        )

    def _move_shield_slot(
        self,
        card,
        owner,
        from_zone,
        to_zone,
        reason,
        source,
        destination,
        publish_battle_enter=True,
    ):

        slot_cards = self._shield_move_cards(
            source,
            card,
        )
        if not slot_cards:
            slot_cards = [card]

        moved_a_shield = any(
            not self._is_active_fortified_castle(slot_card)
            for slot_card in slot_cards
        )

        if (
            from_zone == ZoneType.SHIELD
            and to_zone == ZoneType.HAND
        ):
            self._declare_shield_checks(
                owner,
                slot_cards,
                reason,
            )

        self.pre_freeze_sources_for_many(
            slot_cards
        )

        self._remove_shield_cards(
            source,
            slot_cards,
        )

        events = []
        for slot_card in slot_cards:
            from_shield_face_up = bool(
                getattr(
                    slot_card,
                    "shield_face_up",
                    False,
                )
            )
            slot_card.zone_change_counter += 1
            destination.add(slot_card)
            slot_card.zone = to_zone
            slot_card.shield_face_up = False
            slot_card.deck_face_up = False
            end_pending(slot_card)

            if to_zone == ZoneType.BATTLE:
                ensure_battle_display_label(
                    slot_card,
                    owner,
                )
                self._finalize_battle_enter_seal(
                    slot_card,
                )

            events.append(
                ZoneChangeEvent(
                    card=slot_card,
                    owner=owner,
                    from_zone=from_zone,
                    to_zone=to_zone,
                    reason=reason,
                    from_shield_face_up=from_shield_face_up,
                )
            )

        if moved_a_shield:
            self.context.state_based_actions.note_shield_left()
            self.context.state_based_actions.check_and_apply(
                skip_orphaned_castles=(
                    reason == "shield_break"
                )
            )

        for event in events:
            self._before_zone_change_event(event)
            self._apply_state_definitions_after_move(
                event
            )
            self.context.event_manager.publish(
                event
            )
            self._after_zone_change_event(event)

            if (
                publish_battle_enter
                and to_zone == ZoneType.BATTLE
            ):
                self.publish_battle_enter(
                    card=event.card,
                    owner=owner,
                    from_zone=from_zone,
                    reason=reason,
                )

        # 全カードのトリガーチェック・待機が済んでから封印を外す
        if to_zone == ZoneType.BATTLE:
            for event in events:
                self._apply_seal_removal_on_enter(
                    event.card,
                    owner,
                )

        if (
            from_zone == ZoneType.SHIELD
            and to_zone == ZoneType.HAND
            and reason != "shield_break"
        ):
            self._resolve_non_break_shield_check(
                owner
            )

        return True

    def _declare_shield_checks(
        self,
        owner,
        cards,
        reason,
    ):

        for card in cards:
            self.context.event_manager.publish(
                ZoneChangeAttemptEvent(
                    card=card,
                    owner=owner,
                    from_zone=ZoneType.SHIELD,
                    to_zone=ZoneType.HAND,
                    reason=reason,
                )
            )

        resolver = getattr(
            self.context,
            "shield_trigger_resolver",
            None,
        )
        if resolver is None:
            return

        resolver.declare_triggers(
            owner
        )

    def _resolve_non_break_shield_check(
        self,
        owner,
    ):

        resolver = getattr(
            self.context,
            "shield_trigger_resolver",
            None,
        )
        if resolver is None:
            return

        has_pending_for = getattr(
            resolver,
            "has_pending_for",
            None,
        )
        if (
            has_pending_for is not None
            and not has_pending_for(owner)
        ):
            return

        resolver.resolve()

    def _shield_slot_cards(
        self,
        source,
        card,
    ):

        slot_cards = getattr(
            source,
            "slot_cards",
            None,
        )
        if slot_cards is None:
            return [card]

        return slot_cards(card)

    def _shield_move_cards(
        self,
        source,
        card,
    ):

        if self._is_active_fortified_castle(card):
            return [card]

        shield_cards = getattr(
            source,
            "shield_cards",
            None,
        )
        if shield_cards is not None:
            cards = shield_cards(card)
            return cards or [card]

        return self._shield_slot_cards(
            source,
            card,
        )

    def _remove_shield_slot(
        self,
        source,
        card,
    ):

        remove_slot = getattr(
            source,
            "remove_slot",
            None,
        )
        if remove_slot is None:
            source.remove(card)
            return [card]

        return remove_slot(card)

    def _remove_shield_cards(
        self,
        source,
        cards,
    ):

        remove_cards = getattr(
            source,
            "remove_cards",
            None,
        )
        if remove_cards is not None:
            return remove_cards(cards)

        removed = []
        for card in cards:
            source.remove(card)
            removed.append(card)

        return removed

    def _is_active_fortified_castle(
        self,
        card,
    ):

        return (
            getattr(
                card,
                "is_fortified_castle",
                False,
            )
            and getattr(
                card,
                "shield_face_up",
                False,
            )
        )

    def _add_to_destination(
        self,
        destination,
        card,
        to_zone,
        shield_stack_on,
    ):

        if (
            to_zone == ZoneType.SHIELD
            and hasattr(destination, "slots")
        ):
            destination.add(
                card,
                stack_on=shield_stack_on,
            )
            return

        destination.add(card)

    def _apply_state_definitions_after_move(
        self,
        event,
    ):
        for ability in self._collect_state_definition_abilities():
            apply_after_move = getattr(
                ability,
                "after_zone_change",
                None,
            )
            if apply_after_move is not None:
                apply_after_move(event)

    def publish_battle_enter(
        self,
        card,
        owner,
        from_zone,
        reason=None,
        cost_skipped=False,
    ):

        card.register_abilities(
            self.context.event_manager
        )

        event = BattleZoneEnterEvent(
            player=owner,
            card=card,
            from_zone=from_zone,
            reason=reason,
            cost_skipped=cost_skipped,
        )

        self.context.event_manager.publish(
            event
        )

    def _finalize_battle_enter_seal(
        self,
        card,
    ):
        # 出たカード自身が封印カードなら、封印関係を確定する。
        # （封印を「外す」処理ではないため入場時に即座に行う）
        seal_manager = getattr(
            self.context,
            "seal_manager",
            None,
        )
        if seal_manager is None:
            return

        seal_manager.finalize_seal_attachment(
            card
        )

    def _apply_seal_removal_on_enter(
        self,
        card,
        owner,
    ):
        # 同文明コマンドの登場による封印解除。
        # ルール上の順序は「①出す → ②全誘発のトリガーをチェックし待機 →
        # ③封印を外す → ④cip等を解決」なので、入場イベント（②）を発行し
        # 終えた後に呼び出す。これにより封印中のクリーチャーは②の時点では
        # まだ無視されており、自身を解除した登場には誘発しない。
        seal_manager = getattr(
            self.context,
            "seal_manager",
            None,
        )
        if seal_manager is None:
            return

        seal_manager.handle_card_entered_battle(
            card,
            owner,
        )

    def _before_zone_change_event(
        self,
        event,
    ):

        self._log_zone_change(event)

        seal_manager = getattr(
            self.context,
            "seal_manager",
            None,
        )
        if seal_manager is None:
            return

        seal_manager.before_zone_change_event(
            event
        )

    def _after_zone_change_event(
        self,
        event,
    ):

        seal_manager = getattr(
            self.context,
            "seal_manager",
            None,
        )
        if seal_manager is None:
            return

        seal_manager.after_zone_change_event(
            event
        )

    def _log_zone_change(
        self,
        event,
    ):

        if is_debug_enabled():
            return

        if event.from_zone == event.to_zone:
            return

        owner_name = getattr(
            getattr(event, "owner", None),
            "name",
            "Unknown",
        )
        print(
            f"移動: {owner_name} | "
            f"{format_card_name(event.card)} | "
            f"{self._zone_label(event.from_zone)} -> "
            f"{self._zone_label(event.to_zone)}"
        )

    def _zone_label(
        self,
        zone,
    ):

        name = getattr(
            zone,
            "name",
            str(zone),
        )
        return _ZONE_LABELS.get(
            name,
            name,
        )

    def _state_definitions_prevent(
        self,
        event,
    ):
        for ability in self._collect_state_definition_abilities():
            prevents = getattr(
                ability,
                "prevents_zone_change",
                None,
            )
            if prevents is not None and prevents(event):
                return True

        return False

    def _collect_state_definition_abilities(
        self,
    ):
        abilities = []

        for player in self.context.state.players:
            for zone in (
                player.battle_zone,
                player.mana_zone,
                player.graveyard,
                player.shield_zone,
            ):
                for card in zone.cards:
                    if (
                        is_card_pending(card)
                        or is_seal_card(card)
                        or is_ignored_by_seal(card)
                    ):
                        continue

                    abilities.extend(
                        card.abilities
                    )

            # プレイヤーに付与された期間限定の離脱防止ガード（極限ファイナル革命等）。
            abilities.extend(
                getattr(player, "separation_guards", [])
            )

        return abilities

    def _move_evolution_source(
        self,
        card,
        owner,
        from_zone,
        to_zone,
        reason,
        destination,
    ):

        self.pre_freeze_sources_for(
            card
        )

        if from_zone == ZoneType.BATTLE:
            if hasattr(card, "reset_battle_state"):
                card.reset_battle_state()

        card.zone_change_counter += 1
        destination.add(card)
        card.zone = to_zone
        if from_zone != ZoneType.DECK or to_zone != ZoneType.DECK:
            card.deck_face_up = False
        end_pending(card)

        if to_zone == ZoneType.BATTLE:
            ensure_battle_display_label(
                card,
                owner,
            )

        event = ZoneChangeEvent(
            card=card,
            owner=owner,
            from_zone=from_zone,
            to_zone=to_zone,
            reason=reason,
        )

        self._log_zone_change(event)

        self.context\
            .event_manager\
            .publish(
                event
            )

        if to_zone == ZoneType.BATTLE:
            self.publish_battle_enter(
                card=card,
                owner=owner,
                from_zone=from_zone,
                reason=reason,
            )

        if (
            from_zone == ZoneType.BATTLE
            and to_zone != ZoneType.BATTLE
        ):
            clear_battle_display_label(card)

        card.is_evolution_source = False

    def _detach_evolution_source(
        self,
        card,
        owner,
        from_zone,
        to_zone,
        reason,
        destination,
    ):

        top = self._find_evolution_parent(
            owner,
            card,
        )
        if top is None:
            return False

        source_index = top.evolution_sources.index(
            card
        )
        self.pre_freeze_sources_for_many(
            [
                top,
                card,
            ]
        )
        top.release_evolution_source(card)
        nested_sources = (
            card.clear_evolution_sources()
            if hasattr(
                card,
                "clear_evolution_sources",
            )
            else []
        )
        self._move_detached_card(
            card,
            owner,
            from_zone,
            to_zone,
            reason,
            destination,
        )
        self._reattach_nested_sources(
            top,
            nested_sources,
            source_index,
        )
        self._refresh_neo_evolution_state(top)
        return True

    def _reattach_nested_sources(
        self,
        parent,
        sources,
        index,
    ):

        if not sources or not hasattr(
            parent,
            "add_evolution_source",
        ):
            return

        for offset, source_card in enumerate(
            sources
        ):
            parent.add_evolution_source(
                source_card
            )
            if source_card in parent.evolution_sources:
                parent.evolution_sources.remove(
                    source_card
                )
                parent.evolution_sources.insert(
                    index + offset,
                    source_card,
                )

    def _move_evolution_top_only(
        self,
        card,
        owner,
        from_zone,
        to_zone,
        reason,
        source,
        destination,
    ):

        index = source.cards.index(card)
        remaining_sources = list(
            card.evolution_sources
        )
        self.pre_freeze_sources_for_many(
            [
                card,
                *remaining_sources,
            ]
        )

        for source_card in remaining_sources:
            card.release_evolution_source(
                source_card,
                reactivate=False,
            )

        card.zone_change_counter += 1
        source.remove(card)
        destination.add(card)
        card.zone = to_zone
        if from_zone != ZoneType.DECK or to_zone != ZoneType.DECK:
            card.deck_face_up = False
        end_pending(card)
        if hasattr(card, "reset_battle_state"):
            card.reset_battle_state()

        self._reconstruct_evolution_sources(
            owner,
            from_zone,
            reason,
            source,
            index,
            remaining_sources,
        )

        event = ZoneChangeEvent(
            card=card,
            owner=owner,
            from_zone=from_zone,
            to_zone=to_zone,
            reason=reason,
            evolution_sources=remaining_sources,
        )

        self._log_zone_change(event)

        self.context\
            .event_manager\
            .publish(
                event
            )

        if to_zone == ZoneType.BATTLE:
            self.publish_battle_enter(
                card=card,
                owner=owner,
                from_zone=from_zone,
                reason=reason,
            )

        if to_zone != ZoneType.BATTLE:
            clear_battle_display_label(card)

        return True

    def _reconstruct_evolution_sources(
        self,
        owner,
        from_zone,
        reason,
        battle_zone,
        index,
        candidates,
    ):

        pending = list(candidates)

        while pending:
            candidate = pending.pop(0)
            self.pre_freeze_sources_for(
                candidate
            )
            nested_sources = (
                candidate.clear_evolution_sources()
                if hasattr(
                    candidate,
                    "clear_evolution_sources",
                )
                else []
            )

            if self._can_remain_in_battle(
                candidate
            ):
                self._promote_reconstructed_card(
                    owner,
                    from_zone,
                    battle_zone,
                    index,
                    candidate,
                    nested_sources + pending,
                )
                return

            self._move_rejected_reconstruction_card(
                candidate,
                owner,
                from_zone,
                reason,
            )
            pending = nested_sources + pending

    def _can_remain_in_battle(
        self,
        card,
    ):

        return bool(
            getattr(
                card,
                "can_exist_in_battle_alone",
                lambda: False,
            )()
        )

    def _promote_reconstructed_card(
        self,
        owner,
        from_zone,
        battle_zone,
        index,
        card,
        remaining_sources,
    ):

        battle_zone.cards.insert(
            index,
            card,
        )
        card.zone = from_zone
        card.owner = owner
        card.is_evolution_source = False
        ensure_battle_display_label(
            card,
            owner,
        )
        self._restore_promoted_card_state(
            card
        )
        card.register_abilities(
            self.context.event_manager
        )

        if hasattr(
            card,
            "add_evolution_source",
        ):
            for source_card in remaining_sources:
                card.add_evolution_source(
                    source_card
                )

    def _move_rejected_reconstruction_card(
        self,
        card,
        owner,
        from_zone,
        reason,
    ):

        graveyard = owner.get_zone(
            ZoneType.GRAVEYARD
        )
        self._move_evolution_source(
            card,
            owner,
            from_zone,
            ZoneType.GRAVEYARD,
            reason or "evolution_reconstruct",
            graveyard,
        )

    def _restore_promoted_card_state(
        self,
        card,
    ):

        if hasattr(
            card,
            "restore_promoted_face",
        ):
            card.restore_promoted_face()

        summon_turn = getattr(
            card,
            "summon_turn",
            None,
        )
        if summon_turn != self.context.state.turn:
            card.summoning_sick = False

    def _move_detached_card(
        self,
        card,
        owner,
        from_zone,
        to_zone,
        reason,
        destination,
    ):

        self.pre_freeze_sources_for(
            card
        )

        card.zone_change_counter += 1
        if hasattr(
            card,
            "reset_battle_state",
        ):
            card.reset_battle_state()
        destination.add(card)
        card.zone = to_zone
        if from_zone != ZoneType.DECK or to_zone != ZoneType.DECK:
            card.deck_face_up = False
        end_pending(card)

        if to_zone == ZoneType.BATTLE:
            ensure_battle_display_label(
                card,
                owner,
            )

        event = ZoneChangeEvent(
            card=card,
            owner=owner,
            from_zone=from_zone,
            to_zone=to_zone,
            reason=reason,
        )

        self._log_zone_change(event)

        self.context\
            .event_manager\
            .publish(
                event
            )

        if to_zone == ZoneType.BATTLE:
            self.publish_battle_enter(
                card=card,
                owner=owner,
                from_zone=from_zone,
                reason=reason,
            )

        if (
            from_zone == ZoneType.BATTLE
            and to_zone != ZoneType.BATTLE
        ):
            clear_battle_display_label(card)

    def _refresh_neo_evolution_state(
        self,
        card,
    ):

        if not getattr(
            card,
            "is_neo",
            False,
        ):
            return

        if getattr(
            card,
            "is_evolution",
            False,
        ):
            card.summoning_sick = False
            return

        card.summoning_sick = (
            getattr(
                card,
                "summon_turn",
                None,
            )
            == self.context.state.turn
        )

    def _find_evolution_parent(
        self,
        owner,
        target,
    ):

        for card in owner.battle_zone.cards:
            found = self._find_evolution_parent_in(
                card,
                target,
            )
            if found is not None:
                return found

        return None

    def _find_evolution_parent_in(
        self,
        card,
        target,
    ):

        for source in getattr(
            card,
            "evolution_sources",
            [],
        ):
            if source is target:
                return card

            found = self._find_evolution_parent_in(
                source,
                target,
            )
            if found is not None:
                return found

        return None
