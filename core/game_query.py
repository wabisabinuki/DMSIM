"""
バトルゾーンのクリーチャー一覧、スピードアタッカーの有無、アクティブなブロッカーなど、ゲーム状態に関する問い合わせを行うクエリクラス。
"""

from abilities.keywords.blocker_ability import (
    BlockerAbility
)
from abilities.traits.unblockable_ability import (
    UnblockableAbility
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

from zones.zone_type import (
    ZoneType
)

from core.pending_cards import is_card_pending
from core.seal_utils import is_ignored_by_seal, is_seal_card


class GameQuery:

    def __init__(
        self,
        context,
    ):

        self.context = context

    def get_opponent(
        self,
        player,
    ):

        for p in (
            self.context.state.players
        ):

            if p != player:
                return p

        return None

    def get_creatures(
        self,
        controller=None,
        tapped=None,
    ):

        result = []

        players = (
            [controller]
            if controller
            else self.context.state.players
        )

        for player in players:

            for card in (
                player
                .battle_zone
                .cards
            ):

                if is_card_pending(card):
                    continue

                if is_ignored_by_seal(card):
                    continue

                if not self._is_creature(card):
                    continue

                if tapped is not None:

                    if (
                        card.tapped
                        != tapped
                    ):

                        continue

                result.append(card)

        return result

    def get_attack_targets(
        self,
        attacker,
    ):

        opponent = (
            self.get_opponent(
                attacker.owner
            )
        )

        result = []

        # creature targets
        for creature in (
            self.get_creatures(
                controller=opponent
            )
        ):

            validator = (
                self.context.attack_validator
            )

            if validator.can_attack_target(
                attacker,
                creature,
            ):

                result.append(
                    creature
                )

        # player target（「相手プレイヤーを攻撃できない」制限や
        # 攻撃先誘導がある場合は候補に入れない）
        if self.context.attack_validator.can_attack_target(
            attacker,
            opponent,
        ):
            result.append(opponent)

        return result

    def get_blockers(
        self,
        attacker,
        target,
    ):

        defending_player = (
            target.owner
            if self._is_creature(target)
            else target
        )

        blockers = []

        unblockable_abilities = (
            self._get_unblockable_abilities(
                attacker
            )
        )

        # 相手を選ばない「ブロックされない」を持つ場合は誰もブロックできない。
        if any(
            ability.is_unconditional()
            for ability in unblockable_abilities
        ):
            return blockers

        for creature in (
            self.get_creatures(
                controller=(
                    defending_player
                ),
                tapped=False,
            )
        ):

            if not creature.has_ability(
                BlockerAbility
            ):
                continue

            if not self._has_active_blocker(
                creature,
            ):
                continue

            if self._is_block_prevented(
                creature,
            ):
                continue

            if self._is_attacker_protected_from_blocker(
                attacker,
                creature,
            ):
                continue

            # 条件付き「ブロックされない」（例: 自身よりパワーが小さい
            # クリーチャーにブロックされない）
            if self._is_unblockable_by(
                attacker,
                creature,
                unblockable_abilities,
            ):
                continue

            # custom block rule
            if hasattr(
                creature,
                "can_block",
            ):

                if not creature.can_block(
                    attacker,
                    target,
                ):

                    continue

            blockers.append(
                creature
            )

        return blockers

    def get_guardmen(
        self,
        attacker,
        target,
    ):
        """ガードマンで攻撃先を変更できる候補クリーチャーを返す。

        ガードマンは、相手クリーチャーが自分の「他の」クリーチャーを攻撃した時、
        自身をタップして攻撃先を自身へ移し替える防御的能力。ブロッカーと同様に
        攻撃先を変更するが、別系統の能力なので独立に判定する。
        """

        # プレイヤー攻撃（クリーチャー以外への攻撃）はガードマンで変更できない。
        if not self._is_creature(target):
            return []

        defending_player = target.owner

        # 攻撃元が相手クリーチャーである必要がある。
        # （自分のクリーチャーが攻撃している時は自分のガードマンを使えない）
        if attacker.owner is defending_player:
            return []

        guardmen = []

        for creature in (
            self.get_creatures(
                controller=defending_player,
                tapped=False,
            )
        ):

            # ガードマン自身は攻撃先とは別の自分のクリーチャー。
            if creature is target:
                continue

            if not self._has_active_guardman(
                creature,
            ):
                continue

            guardmen.append(
                creature
            )

        return guardmen

    def _has_active_guardman(
        self,
        creature,
    ):

        from abilities.keywords.guardman_ability import (
            GuardmanAbility
        )

        for ability in getattr(
            creature,
            "abilities",
            [],
        ):
            if not isinstance(
                ability,
                GuardmanAbility,
            ):
                continue

            is_active = getattr(
                ability,
                "is_active_for",
                None,
            )
            if is_active is None:
                return True

            if is_active(creature):
                return True

        return False

    def _get_unblockable_abilities(
        self,
        attacker,
    ):
        # 能力無視を受けている間はブロックされない能力を参照しない。
        if attacker.are_abilities_ignored():
            return []

        return [
            ability
            for ability in attacker.abilities
            if isinstance(
                ability,
                UnblockableAbility,
            )
        ]

    def _is_unblockable_by(
        self,
        attacker,
        blocker,
        unblockable_abilities,
    ):
        return any(
            ability.blocks_blocker(
                attacker,
                blocker,
            )
            for ability in unblockable_abilities
        )

    def _is_attacker_protected_from_blocker(
        self,
        attacker,
        blocker,
    ):

        for protection in getattr(
            attacker,
            "temporary_just_diver_effects",
            [],
        ):
            prevents = getattr(
                protection,
                "prevents_being_blocked_by",
                None,
            )
            if prevents is not None and prevents(blocker):
                return True

        return False

    def _has_active_blocker(
        self,
        creature,
    ):

        for ability in getattr(
            creature,
            "abilities",
            [],
        ):
            if not isinstance(
                ability,
                BlockerAbility,
            ):
                continue

            is_active = getattr(
                ability,
                "is_active_for",
                None,
            )
            if is_active is None:
                return True

            if is_active(creature):
                return True

        return False

    def _is_block_prevented(
        self,
        creature,
    ):

        for restriction in getattr(
            creature,
            "temporary_combat_restrictions",
            [],
        ):
            if restriction.prevents_block():
                return True

        return False

    def get_selectable_creatures(
        self,
        source=None,
        controller=None,
    ):

        result = []

        for creature in (
            self.get_creatures(
                controller=controller
            )
        ):

            # 将来的に:
            # untargetable
            # cannot_be_chosen
            # stealth
            # etc
            if not self._can_be_chosen_by(
                creature,
                source,
            ):
                continue

            result.append(
                creature
            )

        return result

    def _can_be_chosen_by(
        self,
        creature,
        source,
    ):

        if source is None:
            return True

        source_player = getattr(
            source,
            "owner",
            source,
        )

        for ability in getattr(
            creature,
            "abilities",
            [],
        ):
            if hasattr(
                ability,
                "can_be_chosen_by",
            ) and not ability.can_be_chosen_by(
                source_player,
                creature,
            ):
                return False

        return True

    def get_battle_cards(
        self,
        controller=None,
    ):

        result = []

        players = (
            [controller]
            if controller
            else self.context.state.players
        )

        for player in players:
            for card in player.battle_zone.cards:
                if is_card_pending(card):
                    continue

                if is_ignored_by_seal(card):
                    continue

                result.append(card)
                result.extend(
                    self._evolution_sources(
                        card
                    )
                )

        return result

    def _evolution_sources(
        self,
        card,
    ):

        sources = []

        for source in getattr(
            card,
            "evolution_sources",
            [],
        ):
            if is_card_pending(source):
                continue

            if is_ignored_by_seal(source):
                continue

            sources.append(source)
            sources.extend(
                self._evolution_sources(
                    source
                )
            )

        return sources

    def _is_creature(
        self,
        card,
    ):

        # 封印カードは裏向きのカードでありクリーチャーではない。
        # （CreatureCard インスタンスのまま封印されるため明示的に除外する）
        if is_seal_card(card):
            return False

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
