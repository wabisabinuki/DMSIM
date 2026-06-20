"""
プレイヤーのアクションが現在のルール上、実行可能であるかを総合的にチェックするバリデータ。
"""

from actions.summon_action import (
    SummonAction
)

from actions.attack_action import (
    AttackAction
)

from actions.cast_spell_action import (
    CastSpellAction
)

from actions.proceed_to_attack_step_action import (
    ProceedToAttackStepAction,
)

from actions.finish_attack_step_action import (
    FinishAttackStepAction,
)

from actions.destroy_action import (
    DestroyAction
)

from actions.destroy_multiple_action import (
    DestroyMultipleAction
)

from actions.use_card_action import (
    UseCardAction
)

from actions.play_method import (
    PlayMethod,
)

from actions.activate_ability_action import (
    ActivateAbilityAction
)

from cards.creature_card import (
    CreatureCard
)

from cards.card import (
    SpecialType
)

from cards.twin_pact_card import (
    TwinPactCard
)

from abilities.keywords.evolution_ability import EvolutionAbility
from abilities.keywords.g_zero_ability import GZeroAbility

from core.game_step import GameStep
from core.player import (
    Player
)

from core.pending_cards import is_card_pending
from core.seal_utils import is_ignored_by_seal, is_seal_card
from zones.zone_type import ZoneType


class ActionValidator:

    def __init__(
        self,
        context,
    ):

        self.context = context

    def validate(
        self,
        action,
    ):

        executed_card = self._executed_card(action)
        if executed_card is not None and self._is_card_execution_prevented(
            action.player,
            executed_card,
        ):
            return False

        if isinstance(
            action,
            SummonAction,
        ):

            return self.validate_summon(
                action
            )

        if isinstance(
            action,
            AttackAction,
        ):

            return self.validate_attack(
                action
            )

        if isinstance(
            action,
            CastSpellAction,
        ):

            return self.validate_spell(
                action
            )

        if isinstance(
            action,
            ProceedToAttackStepAction,
        ):

            return True

        if isinstance(
            action,
            FinishAttackStepAction,
        ):

            return self.validate_finish_attack_step(
                action
            )

        if isinstance(
            action,
            DestroyAction,
        ):

            return True

        if isinstance(
            action,
            DestroyMultipleAction,
        ):

            return True

        if isinstance(
            action,
            UseCardAction,
        ):

            can_use = getattr(
                action.card,
                "can_use",
                None,
            )
            if can_use is not None:
                return can_use(
                    self.context.controller,
                    action.player,
                    ignore_cost=action.ignore_cost,
                )

            return True

        if isinstance(
            action,
            ActivateAbilityAction,
        ):

            return action.ability.can_activate(
                action.player
            )

        return False

    def validate_summon(
        self,
        action,
    ):

        player = action.player

        card = action.card

        if self._violates_dream_same_name_rule(
            player,
            card,
        ):
            return False

        if card.has_special_type(
            SpecialType.EVOLUTION
        ) and not card.has_special_type(
            SpecialType.NEO
        ) and not self._has_evolution_source(
            player,
            card,
            action.evolution_source,
        ):
            return False

        if (
            card.has_special_type(
                SpecialType.NEO
            )
            and action.evolution_source is not None
            and not self._has_evolution_source(
                player,
                card,
                action.evolution_source,
            )
        ):
            return False

        if action.play_method == PlayMethod.G_ZERO:
            return self._validate_g_zero_play(
                action,
                player,
                card,
            )

        if not self._has_valid_play_permission(
            action,
            player,
            card,
        ):
            return False

        if action.ignore_cost:
            return True

        alternative_cost = getattr(
            action,
            "alternative_cost",
            None,
        )
        if alternative_cost is not None:
            return alternative_cost.can_pay(
                player,
                card,
            )

        if isinstance(card, TwinPactCard):
            return self._can_play_face(
                player,
                card.creature_face,
                card,
            )

        return player.can_play(card, self.context)

    def _has_evolution_source(
        self,
        player,
        card,
        source,
    ):

        if source is not None:
            sources = (
                source
                if isinstance(source, list)
                else [source]
            )
            ability = self._evolution_ability(card)
            if (
                ability is None
                or len(sources) != ability.source_count
                or len(set(id(source) for source in sources))
                != len(sources)
            ):
                return False

            candidates = self._evolution_source_candidates(
                player,
                card,
            )
            return all(
                candidate in candidates
                for candidate in sources
            )

        ability = self._evolution_ability(card)
        if ability is None:
            return False

        return len(
            self._evolution_source_candidates(
                player,
                card,
            )
        ) >= ability.source_count

    def _evolution_source_candidates(
        self,
        player,
        card,
    ):

        ability = self._evolution_ability(card)
        if ability is None:
            return []

        return ability.source_candidates(
            player,
            card,
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

    def _violates_dream_same_name_rule(
        self,
        player,
        card,
    ):

        if not card.has_special_type(
            SpecialType.DREAM
        ):
            return False

        return any(
            candidate is not card
            and not is_card_pending(candidate)
            and not is_seal_card(candidate)
            and not is_ignored_by_seal(candidate)
            and not getattr(
                candidate,
                "is_evolution_source",
                False,
            )
            and candidate.has_special_type(
                SpecialType.DREAM
            )
            and candidate.name == card.name
            for candidate in player.battle_zone.cards
        )

    def validate_spell(
        self,
        action,
    ):

        player = action.player

        spell = action.spell

        if self._is_spell_cast_prevented(
            player,
            spell,
        ):
            return False

        if action.play_method == PlayMethod.G_ZERO:
            return self._validate_g_zero_play(
                action,
                player,
                spell,
            )

        if not self._has_valid_play_permission(
            action,
            player,
            spell,
        ):
            return False

        if action.ignore_cost:
            return True

        cost_override = getattr(action, "cost_override", None)
        if cost_override is not None:
            civs = getattr(
                action,
                "cost_override_civilizations",
                getattr(spell, "civilizations", 0),
            )
            return player.can_pay_cost(cost_override, civs)

        if isinstance(spell, TwinPactCard):
            return self._can_play_face(
                player,
                spell.spell_face,
                spell,
            )

        return player.can_play(
            spell,
            self.context,
        )

    def _validate_g_zero_play(
        self,
        action,
        player,
        card,
    ):
        if self.context.state.step != GameStep.MAIN:
            return False

        if self.context.state.current_player is not player:
            return False

        if not self._has_g_zero_play_permission(
            action,
            player,
            card,
        ):
            return False

        ability = getattr(
            action,
            "g_zero_ability",
            None,
        )
        if ability is None:
            ability = self._g_zero_ability_for_action(
                action
            )

        if ability is None:
            return False

        return ability.can_use(
            self.context.controller,
            player,
            card,
        )

    def _has_g_zero_play_permission(
        self,
        action,
        player,
        card,
    ):
        if getattr(
            card,
            "owner",
            None,
        ) is not player:
            return False

        zone = getattr(
            card,
            "zone",
            None,
        )
        if zone == ZoneType.HAND:
            return card in player.hand.cards

        if getattr(
            card,
            "owner",
            None,
        ) is not player:
            return False

        if zone is None:
            return False

        if card not in player.get_zone(zone).cards:
            return False

        permissions = self._action_play_permissions(
            action
        )
        if not permissions:
            return False

        return self._has_valid_play_permission(
            action,
            player,
            card,
        )

    def _has_valid_play_permission(
        self,
        action,
        player,
        card,
    ):
        permissions = self._action_play_permissions(
            action
        )
        if not permissions:
            return True

        return any(
            self._permission_allows(
                permission,
                player,
                card,
            )
            for permission in permissions
        )

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

    def _g_zero_ability_for_action(
        self,
        action,
    ):
        for ability in self._action_abilities(
            action
        ):
            if isinstance(
                ability,
                GZeroAbility,
            ):
                return ability

        return None

    def _action_abilities(
        self,
        action,
    ):
        if isinstance(
            action,
            SummonAction,
        ):
            card = action.card
            if isinstance(
                card,
                TwinPactCard,
            ) and card.creature_face is not None:
                return getattr(
                    card.creature_face,
                    "abilities",
                    [],
                )

            return getattr(
                card,
                "abilities",
                [],
            )

        if isinstance(
            action,
            CastSpellAction,
        ):
            card = action.spell
            if isinstance(
                card,
                TwinPactCard,
            ) and card.spell_face is not None:
                return getattr(
                    card.spell_face,
                    "abilities",
                    [],
                )

            return getattr(
                card,
                "abilities",
                [],
            )

        return []

    def _executed_card(
        self,
        action,
    ):
        # 「カードを実行（プレイ）する」アクションが対象とするカードを返す。
        # 攻撃などプレイ以外のアクションは None（実行ロックの対象外）。
        if isinstance(action, CastSpellAction):
            return getattr(action, "spell", None)

        if isinstance(
            action,
            (SummonAction, UseCardAction),
        ):
            return getattr(action, "card", None)

        return None

    def _is_card_execution_prevented(
        self,
        player,
        card,
    ):
        # コスト指定の実行ロック（CostExecutionLockEffect）を対象プレイヤー側に
        # 登録された一覧から参照する。
        for lock in getattr(player, "execution_locks", []):
            if lock.prevents_execution(card):
                return True

        return False

    def _is_spell_cast_prevented(
        self,
        player,
        spell,
    ):

        for opponent_card in self._opponent_battle_cards(
            player,
        ):
            for ability in getattr(
                opponent_card,
                "abilities",
                [],
            ):
                if (
                    hasattr(
                        ability,
                        "prevents_spell_cast",
                    )
                    and ability.prevents_spell_cast(
                        opponent_card,
                        player,
                        spell,
                    )
                ):
                    return True

        return False

    def _opponent_battle_cards(
        self,
        player,
    ):

        return [
            card
            for candidate in self.context.state.players
            for card in candidate.battle_zone.cards
            if (
                not is_card_pending(card)
                and not is_seal_card(card)
                and not is_ignored_by_seal(card)
            )
        ]

    def _can_play_face(
        self,
        player,
        face,
        spending_card=None,
    ):

        if face is None:
            return False

        return player.can_pay_cost(
            face.cost,
            face.civilizations,
            spending_card=spending_card,
        )

    def validate_attack(
        self,
        action,
    ):

        attacker = (
            action.attacker
        )

        target = (
            action.target
        )

        validator = (
            self.context.attack_validator
        )

        if not validator.can_attack(
            attacker
        ):

            return False

        return validator.can_attack_target(
            attacker,
            target,
        )

    def validate_finish_attack_step(
        self,
        action,
    ):
        return not self._has_mandatory_attacker(
            action.player,
        )

    def _has_mandatory_attacker(
        self,
        player,
    ):
        for attacker in player.battle_zone.cards:
            if is_card_pending(attacker):
                continue

            if is_seal_card(attacker) or is_ignored_by_seal(attacker):
                continue

            if not self.context.attack_validator.can_attack(
                attacker
            ):
                continue

            targets = self.context.query.get_attack_targets(
                attacker
            )
            if not targets:
                continue

            if self._is_attack_required(
                attacker,
            ):
                return True

        return False

    def _is_attack_required(
        self,
        attacker,
    ):
        # 相手のカードによる強制（例: オピオンの「相手のクリーチャーは可能なら攻撃する」）に加え、
        # 攻撃クリーチャー自身に付与された強制（例: スペース・チャージで「可能なら攻撃する」を
        # 与えられた場合）も判定する。後者はその能力の持ち主＝攻撃クリーチャー自身。
        holders = list(
            self._opponent_battle_cards(attacker.owner)
        )
        holders.append(attacker)

        for holder in holders:
            for ability in getattr(
                holder,
                "abilities",
                [],
            ):
                if (
                    hasattr(
                        ability,
                        "requires_attack",
                    )
                    and ability.requires_attack(
                        holder,
                        attacker,
                    )
                ):
                    return True

        return False
