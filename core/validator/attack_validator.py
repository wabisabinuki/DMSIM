"""
攻撃アクション（攻撃対象、タップ状態、召喚酔いなど）に特化したバリデータ。
"""

from cards.creature_card import (
    CreatureCard
)

from cards.twin_pact_card import (
    TwinPactCard
)

from core.player import (
    Player
)

from core.pending_cards import is_card_pending
from core.seal_utils import is_ignored_by_seal, is_seal_card


class AttackValidator:

    def __init__(
        self,
        context,
    ):

        self.context = context

    def can_attack(
        self,
        attacker,
    ):

        if is_card_pending(attacker):
            return False

        if is_seal_card(attacker) or is_ignored_by_seal(attacker):
            return False

        if attacker.tapped:
            return False

        if self._is_attack_prevented(
            attacker,
        ):
            return False

        if self._is_attack_forbidden_by_continuous(
            attacker,
        ):
            return False

        if attacker.summoning_sick:

            from abilities.keywords.speed_attacker import (
                SpeedAttackerAbility
            )
            from abilities.keywords.mach_fighter_ability import (
                MachFighterAbility
            )

            has_speed_attacker = attacker.has_ability(
                SpeedAttackerAbility
            )

            has_mach_fighter_this_turn = (
                attacker.has_ability(
                    MachFighterAbility
                )
                and
                hasattr(attacker, "summon_turn")
                and
                attacker.summon_turn == self.context.state.turn
            )

            if not (
                has_speed_attacker
                or has_mach_fighter_this_turn
            ):

                return False

        return True

    def _is_attack_prevented(
        self,
        attacker,
    ):

        for restriction in getattr(
            attacker,
            "temporary_combat_restrictions",
            [],
        ):
            if restriction.prevents_attack():
                return True

        return False

    def _is_attack_forbidden_by_continuous(
        self,
        attacker,
    ):

        ignore_own = self._ignores_own_attack_forbid(
            attacker,
        )

        for player in self.context.state.players:
            for card in player.battle_zone.cards:
                if is_card_pending(card):
                    continue

                if is_seal_card(card) or is_ignored_by_seal(card):
                    continue

                # 「攻撃できない能力を無視する」: 攻撃クリーチャー自身が持つ
                # 攻撃禁止能力（own）だけをスキップ。外部由来は無視しない。
                if ignore_own and card is attacker:
                    continue

                for ability in getattr(
                    card,
                    "abilities",
                    [],
                ):
                    forbids = getattr(
                        ability,
                        "forbids_attack",
                        None,
                    )
                    if forbids is not None and forbids(
                        card,
                        attacker,
                    ):
                        return True

        return False

    def _ignores_own_attack_forbid(
        self,
        attacker,
    ):

        from abilities.traits.ignore_own_attack_forbid_ability import (
            IgnoreOwnAttackForbidAbility
        )

        return attacker.has_ability(
            IgnoreOwnAttackForbidAbility
        )

    def can_attack_target(
        self,
        attacker,
        target,
    ):

        if not self._can_attack_target_base(
            attacker,
            target,
        ):
            return False

        # 「可能ならこのクリーチャーを攻撃する」誘導が有効な場合、
        # 攻撃先は誘導クリーチャー（のうち攻撃可能なもの）に限られる。
        lure_targets = self._lure_targets(attacker)
        if lure_targets and target not in lure_targets:
            return False

        return True

    def _can_attack_target_base(
        self,
        attacker,
        target,
    ):

        if self._is_creature(target):
            if is_card_pending(target):
                return False

            if is_seal_card(target) or is_ignored_by_seal(target):
                return False

            if self._is_attack_target_prevented(
                attacker,
                target,
            ):
                return False

            # マッハファイターがある場合、出たターン間は相手のクリーチャーに攻撃可能
            from abilities.keywords.mach_fighter_ability import (
                MachFighterAbility
            )

            if attacker.has_ability(
                MachFighterAbility
            ):
                # 出たターンかどうかを確認
                current_turn = self.context.state.turn
                if (hasattr(attacker, "summon_turn") and
                    attacker.summon_turn == current_turn):
                    return True

            temporary_permissions = getattr(
                attacker,
                "temporary_attack_permission",
                {},
            )
            if temporary_permissions.get("mach_fighter"):
                return True

            if not target.tapped:
                if not self._attacker_allows_untapped(attacker):
                    return False

        else:
            # プレイヤーへの攻撃。「相手プレイヤーを攻撃できない」制限を確認する。
            if self._is_player_attack_prevented(attacker):
                return False

            if attacker.summoning_sick:

                from abilities.keywords.speed_attacker import (
                    SpeedAttackerAbility
                )

                if not attacker.has_ability(
                    SpeedAttackerAbility
                ):
                    return False

        return True

    def _attacker_allows_untapped(
        self,
        attacker,
    ):
        """攻撃側がアンタップしているクリーチャーを攻撃できる能力を持つか。"""

        for ability in getattr(
            attacker,
            "abilities",
            [],
        ):
            allows = getattr(
                ability,
                "allows_attacking_untapped",
                None,
            )
            if allows is not None and allows():
                return True

        return False

    def _is_player_attack_prevented(
        self,
        attacker,
    ):

        for restriction in getattr(
            attacker,
            "temporary_combat_restrictions",
            [],
        ):
            prevents = getattr(
                restriction,
                "prevents_attack_player",
                None,
            )
            if prevents is not None and prevents():
                return True

        ignore_own = self._ignores_own_attack_forbid(
            attacker,
        )

        for player in self.context.state.players:
            for card in player.battle_zone.cards:
                if is_card_pending(card):
                    continue

                if is_seal_card(card) or is_ignored_by_seal(card):
                    continue

                # 自身が持つ「プレイヤーを攻撃できない」能力（own）だけをスキップ。
                if ignore_own and card is attacker:
                    continue

                for ability in getattr(
                    card,
                    "abilities",
                    [],
                ):
                    forbids = getattr(
                        ability,
                        "forbids_attack_player",
                        None,
                    )
                    if forbids is not None and forbids(
                        card,
                        attacker,
                    ):
                        return True

        return False

    def _lure_targets(
        self,
        attacker,
    ):
        """attacker の攻撃先を誘導するクリーチャー（攻撃可能なもの）を返す。"""

        targets = []

        for player in self.context.state.players:
            if player is attacker.owner:
                continue

            for card in player.battle_zone.cards:
                if is_card_pending(card):
                    continue

                if is_seal_card(card) or is_ignored_by_seal(card):
                    continue

                for ability in getattr(
                    card,
                    "abilities",
                    [],
                ):
                    lures = getattr(
                        ability,
                        "lures_attack",
                        None,
                    )
                    if (
                        lures is not None
                        and lures(card, attacker)
                        and self._can_attack_target_base(
                            attacker,
                            card,
                        )
                    ):
                        targets.append(card)
                        break

        return targets

    def _is_attack_target_prevented(
        self,
        attacker,
        target,
    ):

        for protection in getattr(
            target,
            "temporary_just_diver_effects",
            [],
        ):
            prevents = getattr(
                protection,
                "prevents_being_attacked_by",
                None,
            )
            if prevents is not None and prevents(attacker):
                return True

        return False

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
