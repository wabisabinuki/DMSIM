"""
現在のゲーム状態に基づいて、アクティブプレイヤーが実行可能なすべてのアクションの一覧を生成するジェネレータ。
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

from actions.use_card_action import (
    UseCardAction
)

from actions.play_method import (
    PlayMethod,
)

from actions.proceed_to_attack_step_action import (
    ProceedToAttackStepAction,
)

from actions.finish_attack_step_action import (
    FinishAttackStepAction,
)

from cards.creature_card import (
    CreatureCard
)

from cards.castle_card import (
    CastleCard
)

from cards.cross_gear_card import (
    CrossGearCard
)

from cards.field_card import (
    FieldCard
)

from cards.spell_card import (
    SpellCard
)

from cards.twin_pact_card import (
    TwinPactCard
)

from abilities.keywords.g_zero_ability import (
    GZeroAbility,
)

from core.pending_cards import is_card_pending
from core.seal_utils import is_ignored_by_seal, is_seal_card

class ActionGenerator:

    def __init__(
        self,
        context,
        action_validator=None,
    ):

        self.context = context

        self.validator = (
            action_validator
            or context.action_validator
        )

    def get_main_step_actions(
        self,
        player,
    ):

        candidate_actions = []

        for card in player.hand.cards:
            if is_card_pending(card):
                continue

            if isinstance(
                card,
                CreatureCard,
            ):

                candidate_actions.append(
                    SummonAction(
                        player,
                        card,
                    )
                )

            elif isinstance(
                card,
                SpellCard,
            ):

                candidate_actions.append(
                    CastSpellAction(
                        player,
                        card,
                    )
                )

            elif isinstance(
                card,
                (CastleCard, CrossGearCard, FieldCard),
            ):

                candidate_actions.append(
                    UseCardAction(
                        player,
                        card,
                    )
                )

            elif isinstance(
                card,
                TwinPactCard,
            ):
                # ツインパクトカードは両方の面のアクションを追加
                if card.creature_face:
                    candidate_actions.append(
                        SummonAction(
                            player,
                            card,
                        )
                    )
                if card.spell_face:
                    candidate_actions.append(
                        CastSpellAction(
                            player,
                            card,
                        )
                    )

        for card in self._alternative_summon_cards(
            player
        ):
            for ability in getattr(
                card,
                "abilities",
                [],
            ):
                get_actions = getattr(
                    ability,
                    "get_alternative_summon_actions",
                    None,
                )
                if get_actions is None:
                    continue
                candidate_actions.extend(
                    get_actions(
                        player,
                        card,
                    )
                )

        candidate_actions.extend(
            self._play_permission_actions(
                player
            )
        )

        candidate_actions = self._with_g_zero_actions(
            player,
            candidate_actions,
        )

        candidate_actions.extend(
            self._activated_ability_actions(
                player
            )
        )

        candidate_actions.append(
            ProceedToAttackStepAction(
                player
            )
        )

        return self._filter_legal(
            candidate_actions
        )

    def get_attack_step_actions(
        self,
        player,
    ):

        candidate_actions = []

        for creature in (
            player.battle_zone.cards
        ):

            if is_card_pending(creature):
                continue

            if is_seal_card(creature) or is_ignored_by_seal(creature):
                continue

            # TwinPactCardもクリーチャーとして攻撃可能
            if not isinstance(
                creature,
                (CreatureCard, TwinPactCard),
            ):
                continue

            # TwinPactCardの場合、クリーチャー面として使用されているか確認
            if isinstance(creature, TwinPactCard):
                if not creature.selected_face or not isinstance(creature.selected_face, CreatureCard):
                    continue

            targets = (
                self.context
                .query
                .get_attack_targets(
                    creature
                )
            )

            for target in targets:

                candidate_actions.append(
                    AttackAction(
                        player,
                        creature,
                        target,
                    )
                )

        candidate_actions.append(
            FinishAttackStepAction(
                player
            )
        )

        candidate_actions.extend(
            self._activated_ability_actions(
                player
            )
        )

        return self._filter_legal(
            candidate_actions
        )

    def get_player_actions(
        self,
        player,
    ):
        """
        後方互換。現在の step に応じた合法手を返す。
        """

        step = self.context.state.step

        from core.game_step import GameStep

        if step == GameStep.ATTACK:
            return self.get_attack_step_actions(
                player
            )

        return self.get_main_step_actions(
            player
        )

    def _filter_legal(
        self,
        candidate_actions,
    ):

        legal_actions = []

        for action in candidate_actions:

            if self.validator.validate(
                action
            ):

                legal_actions.append(
                    action
                )

        return legal_actions

    def _alternative_summon_cards(
        self,
        player,
    ):

        cards = []
        for zone in (
            player.deck,
            player.hand,
            player.battle_zone,
            player.graveyard,
            player.mana_zone,
            player.shield_zone,
        ):
            cards.extend(
                card
                for card in zone.cards
                if (
                    not is_card_pending(card)
                    and not is_seal_card(card)
                    and not is_ignored_by_seal(card)
                )
            )

        return cards

    def _activated_ability_cards(
        self,
        player,
    ):
        cards = []
        for zone in (
            player.hand,
            player.battle_zone,
            player.graveyard,
            player.mana_zone,
            player.shield_zone,
        ):
            cards.extend(
                card
                for card in zone.cards
                if (
                    not is_card_pending(card)
                    and not is_seal_card(card)
                    and not is_ignored_by_seal(card)
                )
            )

        return cards

    def _activated_ability_actions(
        self,
        player,
    ):
        actions = []

        for card in self._activated_ability_cards(
            player
        ):
            for ability in getattr(
                card,
                "abilities",
                [],
            ):
                get_actions = getattr(
                    ability,
                    "get_activate_actions",
                    None,
                )
                if get_actions is None:
                    continue

                actions.extend(
                    get_actions(
                        player,
                        card,
                    )
                )

        return actions

    def _merge_play_permission_actions(
        self,
        actions,
    ):
        merged = []
        by_key = {}

        for action in actions:
            key = self._play_permission_action_key(
                action
            )
            existing = by_key.get(key)
            if existing is None:
                by_key[key] = action
                merged.append(action)
                continue

            self._extend_play_permissions(
                existing,
                getattr(
                    action,
                    "play_permissions",
                    (),
                ),
            )

        return merged

    def _play_permission_action_key(
        self,
        action,
    ):
        if isinstance(
            action,
            SummonAction,
        ):
            return (
                "summon",
                id(action.card),
                getattr(action.card, "zone", None),
                action.play_method,
                id(getattr(action, "alternative_cost", None)),
                _source_key(action.evolution_source),
            )

        if isinstance(
            action,
            CastSpellAction,
        ):
            return (
                "cast",
                id(action.spell),
                getattr(action.spell, "zone", None),
                action.play_method,
            )

        return (
            action.__class__,
            id(action),
        )

    def _extend_play_permissions(
        self,
        action,
        permissions,
    ):
        current = getattr(
            action,
            "play_permissions",
            None,
        )
        if current is None:
            current = []
            action.play_permissions = current

        seen = {
            id(permission)
            for permission in current
        }
        for permission in permissions:
            if permission is None:
                continue
            key = id(permission)
            if key in seen:
                continue
            seen.add(key)
            current.append(permission)

        action.play_permission = (
            current[0]
            if current
            else getattr(action, "play_permission", None)
        )

    def _play_permission_actions(
        self,
        player,
    ):
        actions = []

        for card in self._activated_ability_cards(
            player
        ):
            for ability in getattr(
                card,
                "abilities",
                [],
            ):
                get_actions = getattr(
                    ability,
                    "get_play_actions",
                    None,
                )
                if get_actions is None:
                    continue

                actions.extend(
                    get_actions(
                        player,
                        card,
                    )
                )

        return self._merge_play_permission_actions(
            actions
        )

    def _with_g_zero_actions(
        self,
        player,
        candidate_actions,
    ):
        actions = list(candidate_actions)

        for action in candidate_actions:
            g_zero_action = self._g_zero_action(
                player,
                action,
            )
            if g_zero_action is not None:
                actions.append(g_zero_action)

        return actions

    def _g_zero_action(
        self,
        player,
        action,
    ):
        if getattr(
            action,
            "ignore_cost",
            False,
        ):
            return None

        if getattr(
            action,
            "alternative_cost",
            None,
        ) is not None:
            return None

        ability = self._g_zero_ability_for_action(
            action
        )
        if ability is None:
            return None

        card = self._action_card(action)
        if not ability.can_use(
            self.context.controller,
            player,
            card,
        ):
            return None

        if isinstance(
            action,
            SummonAction,
        ):
            return SummonAction(
                player,
                action.card,
                evolution_source=action.evolution_source,
                play_method=PlayMethod.G_ZERO,
                play_permission=getattr(
                    action,
                    "play_permission",
                    None,
                ),
                play_permissions=getattr(
                    action,
                    "play_permissions",
                    None,
                ),
                g_zero_ability=ability,
            )

        if isinstance(
            action,
            CastSpellAction,
        ):
            return CastSpellAction(
                player,
                action.spell,
                play_method=PlayMethod.G_ZERO,
                play_permission=getattr(
                    action,
                    "play_permission",
                    None,
                ),
                play_permissions=getattr(
                    action,
                    "play_permissions",
                    None,
                ),
                g_zero_ability=ability,
            )

        return None

    def _g_zero_ability_for_action(
        self,
        action,
    ):
        for ability in self._action_abilities(action):
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
        card = self._action_card(action)
        if card is None:
            return []

        if isinstance(
            card,
            TwinPactCard,
        ):
            if isinstance(
                action,
                SummonAction,
            ) and card.creature_face is not None:
                return getattr(
                    card.creature_face,
                    "abilities",
                    [],
                )

            if isinstance(
                action,
                CastSpellAction,
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

    def _action_card(
        self,
        action,
    ):
        if isinstance(
            action,
            SummonAction,
        ):
            return action.card

        if isinstance(
            action,
            CastSpellAction,
        ):
            return action.spell

        return None


def _source_key(
    source,
):
    if isinstance(
        source,
        list,
    ):
        return tuple(
            id(item)
            for item in source
        )

    return id(source)
