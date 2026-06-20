"""
パワー0のクリーチャーの破壊、山札切れによる敗北、ダイレクトアタックによる勝敗判定など、ルール上自動で即時適用される状態定義処理（SBA）の判定と適用。
"""

from actions.destroy_action import (
    DestroyAction
)

from actions.destroy_multiple_action import (
    DestroyMultipleAction
)

from cards.creature_card import (
    CreatureCard
)

from cards.field_card import (
    is_d2_field
)

from abilities.triggers.z_rush_ability import (
    ZRushAbility
)

from abilities.traits.scoped_grant_ability import (
    ScopedGrantAbility
)

from zones.zone_type import (
    ZoneType
)

from ui.card_display import format_card_name
from core.pending_cards import is_card_pending
from core.seal_utils import is_ignored_by_seal, is_seal_card


class StateBasedActions:

    def __init__(
        self,
        context,
    ):

        self.context = context
        self.pending_shield_left_count = 0
        # 展開（プレイ）されたD2フィールドのキュー。展開時に1度だけ
        # supersede（既存D2フィールドの破壊）を行うために使う。
        self._d2_deploy_queue = []
        # 継続(非置換)能力をスコープ付与している ScopedGrantAbility の集合。
        # バトルゾーンを離れた付与元も後始末のため保持し続ける。
        self._scoped_grant_sources = set()

    def note_shield_left(
        self,
    ):

        self.pending_shield_left_count += 1

    def note_d2_field_deployed(
        self,
        card,
    ):
        # FieldCard.use（展開）からのみ呼ばれる。退化など展開以外の
        # 場登場ではこの経路を通らないため supersede は発火しない。
        self._d2_deploy_queue.append(card)

    def check_and_apply(
        self,
        skip_orphaned_castles=False,
    ):

        changed = False

        if self._apply_d2_field_supersede():
            changed = True

        if self._apply_z_rush_for_pending_shields():
            changed = True

        if (
            not skip_orphaned_castles
            and self._apply_orphaned_fortified_castles()
        ):
            changed = True

        if self._apply_invalid_crosses():
            changed = True

        seal_manager = getattr(
            self.context,
            "seal_manager",
            None,
        )
        if (
            seal_manager is not None
            and seal_manager.apply_orphaned_seals()
        ):
            changed = True

        if self._reconcile_scoped_grants():
            changed = True

        for player in (
            self.context.state.players
        ):

            for card in (
                player
                .battle_zone
                .cards[:]
            ):

                if is_card_pending(card):
                    continue

                if is_seal_card(card) or is_ignored_by_seal(card):
                    continue

                if not isinstance(
                    card,
                    CreatureCard,
                ):
                    continue

                power = (
                    card
                    .get_current_power()
                )

                # パワー0以下
                if power <= 0:

                    print(
                        f"[SBA] "
                        f"{format_card_name(card)} "
                        f"has {power} power"
                    )

                    destroy_action = (
                        DestroyAction(
                            player,
                            card,
                        )
                    )

                    self.context\
                        .action_processor\
                        .process(
                            destroy_action
                        )

                    changed = True

        return changed

    def _apply_d2_field_supersede(
        self,
    ):
        # D2フィールドは「お互いの場に合計1枚」。展開された新しいD2フィールドを
        # 除く、既にバトルゾーンにある全D2フィールドを破壊する。発火は展開時のみ
        # （キューに入っている＝use 経由で展開された）で、1度だけ。
        if not self._d2_deploy_queue:
            return False

        newcomers = [
            card
            for card in self._d2_deploy_queue
            if card.zone == ZoneType.BATTLE
            and not is_card_pending(card)
        ]
        # 展開のたびに1度だけ。処理（不発含む）したらキューを空にする。
        self._d2_deploy_queue = []

        if not newcomers:
            return False

        battle_d2_fields = [
            card
            for player in self.context.state.players
            for card in player.battle_zone.cards
            if not is_card_pending(card)
            and not is_seal_card(card)
            and not is_ignored_by_seal(card)
            and is_d2_field(card)
        ]

        targets = [
            card
            for card in battle_d2_fields
            if card not in newcomers
        ]

        if not targets:
            return False

        destroy_action = DestroyMultipleAction(
            self.context.state.current_player,
            targets,
        )
        self.context.action_processor.process(
            destroy_action
        )

        return True

    def _apply_orphaned_fortified_castles(
        self,
    ):

        moved_any = False

        for player in self.context.state.players:
            orphaned_castles = getattr(
                player.shield_zone,
                "orphaned_fortified_castles",
                None,
            )
            if orphaned_castles is None:
                continue

            for castle in orphaned_castles():
                if is_card_pending(castle):
                    continue

                moved = self.context.card_mover.move(
                    card=castle,
                    owner=castle.owner,
                    from_zone=ZoneType.SHIELD,
                    to_zone=ZoneType.GRAVEYARD,
                    reason="fortified_castle_orphaned",
                    apply_replacements=False,
                )
                moved_any = moved_any or bool(moved)

        return moved_any

    def _reconcile_scoped_grants(
        self,
    ):
        # バトルゾーン／シールドゾーンにある付与元を集める（新規参入も拾う）。
        # シールドゾーンは G城（active_zone: "shield" の grant_rule）のため。
        for player in self.context.state.players:
            for zone in (
                player.battle_zone,
                player.shield_zone,
            ):
                for card in zone.cards[:]:
                    if (
                        is_card_pending(card)
                        or is_seal_card(card)
                        or is_ignored_by_seal(card)
                    ):
                        continue
                    for ability in card.abilities:
                        if isinstance(
                            ability,
                            ScopedGrantAbility,
                        ):
                            self._scoped_grant_sources.add(ability)

        changed = False
        for grant in list(self._scoped_grant_sources):
            if grant.reconcile():
                changed = True

            # 付与元が場を離れ、後始末も済んだものは追跡対象から外す。
            if (
                not grant.is_grant_active()
                and not grant.has_active_true_grants()
            ):
                self._scoped_grant_sources.discard(grant)

        return changed

    def _apply_invalid_crosses(
        self,
    ):

        changed = False

        for player in self.context.state.players:
            for card in player.battle_zone.cards[:]:
                if is_seal_card(card) or is_ignored_by_seal(card):
                    continue

                detach = getattr(
                    card,
                    "detach_if_invalid",
                    None,
                )
                if detach is None:
                    continue

                if detach():
                    changed = True

        return changed

    def _apply_z_rush_for_pending_shields(
        self,
    ):

        if self.pending_shield_left_count <= 0:
            return False

        self.pending_shield_left_count = 0
        changed = False

        for player in self.context.state.players:
            for card in player.battle_zone.cards[:]:
                if is_card_pending(card):
                    continue

                if is_seal_card(card) or is_ignored_by_seal(card):
                    continue

                if not card.has_ability(
                    ZRushAbility
                ):
                    continue

                unlocked = (
                    card.unlock_hyper_mode_until_next_turn_start(
                        card.owner,
                        self.context.state,
                    )
                )
                changed = changed or unlocked

        return changed
