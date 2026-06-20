"""Factory for the structured v2 ability JSON shape."""

from abilities.base.static_ability import StaticAbility
from abilities.registry import create_ability
from abilities.traits.self_summon_cost_modifier_ability import (
    SelfSummonCostModifierAbility,
)
from abilities.traits.summon_cost_reduction_ability import (
    SummonCostReductionAbility,
)
from abilities.v2.json_activated_ability import JsonActivatedAbility
from abilities.v2.json_replacement_ability import JsonReplacementAbility
from abilities.v2.json_triggered_ability import JsonTriggeredAbility
from card_db.v2_ability_parser import V2AbilityParser


class V2AbilityFactory:
    """Build abilities from the final grouped ability structure."""

    GROUP_CREATORS = (
        ("keyword", "_create_keyword_abilities"),
        ("static", "_create_static_ability"),
        ("triggered", "_create_triggered_ability"),
        ("activated", "_create_activated_ability"),
        ("replacement", "_create_replacement_ability"),
    )

    STATIC_BUILDERS = {
        "break_modifier": "_break_modifier_to_registry_spec",
        "attack_rule": "_attack_rule_to_registry_spec",
        "block_rule": "_block_rule_to_registry_spec",
        "target_rule": "_target_rule_to_registry_spec",
        "cost_payment_rule": "_cost_payment_rule_to_registry_spec",
        "enter_battle_rule": "_enter_battle_rule_to_registry_spec",
        "summon_rule": "_summon_rule_to_registry_spec",
        "cast_rule": "_cast_rule_to_registry_spec",
        "grant_rule": "_grant_rule_to_registry_spec",
        "mana_rule": "_mana_rule_to_registry_spec",
        "power_modifier": "_power_modifier_to_registry_spec",
        "choice_replacement": "_choice_replacement_to_registry_spec",
        "cross_rule": "_cross_rule_to_registry_spec",
    }

    NATIVE_STATIC_TYPES = frozenset(
        (
            "cost_modifier",
        )
    )

    # 構造化 summon_rule.kind -> 対応する registry ability id
    SUMMON_RULE_IDS = {
        "from_graveyard": "graveyard_summon",
        "from_zone": "play_from_zone",
        "from_mana": "play_from_zone",
        "top_of_deck": "summon_top_deck_creature",
        "g_zero": "g_zero",
    }

    # registry へ橋渡しする triggered / replacement の構造化型。
    # spec["type"] -> rule.kind -> registry ability id。
    TRIGGERED_BRIDGE_IDS = {
        "cross_trigger": {
            "on_ally_enter": "cross_on_ally_enter",
            "on_crossed_attack_recross": "cross_on_crossed_attack_recross",
        },
    }

    REPLACEMENT_BRIDGE_IDS = {
        "cross_replacement": {
            "leave_saver": "cross_leave_saver",
        },
        "shield_break_redirect": {
            "break_this_shield_instead": "break_this_shield_instead",
        },
    }

    COST_PAYMENT_RULE_COST_APPLIERS = {
        "pay_mana": "_apply_alt_pay_mana_cost_to_registry",
        "destroy": "_apply_destroy_cost_to_registry",
        "sacrifice": "_apply_destroy_cost_to_registry",
    }

    def __init__(
        self,
        game=None,
    ):
        self.game = game
        self.parser = V2AbilityParser()

    def create_many(
        self,
        ability_group,
        source,
    ):
        parsed = self.parser.parse_group(
            ability_group
        )
        abilities = []

        for group, creator_name in self.GROUP_CREATORS:
            creator = getattr(self, creator_name)
            for spec in parsed[group]:
                abilities.extend(
                    creator(
                        spec,
                        source,
                    )
                )

        return abilities

    def _create_keyword_abilities(
        self,
        spec,
        source,
    ):
        return self._create_registry_ability(
            self._keyword_to_registry_spec(spec),
            source,
        )

    def _create_activated_ability(
        self,
        spec,
        source,
    ):
        return [
            JsonActivatedAbility(
                source,
                self.game,
                spec,
            )
        ]

    def _create_static_ability(
        self,
        spec,
        source,
    ):
        if self._is_summon_cost_reduction(spec):
            return [
                SummonCostReductionAbility(
                    source,
                    self.game,
                    spec,
                )
            ]

        if self._is_self_cost_modifier(spec):
            return [
                SelfSummonCostModifierAbility(
                    source,
                    self.game,
                    spec,
                )
            ]

        registry_spec = self._static_to_registry_spec(
            spec
        )
        if registry_spec is None:
            return [
                StaticAbility(
                    source,
                    self.game,
                    spec,
                )
            ]

        return self._create_registry_ability(
            registry_spec,
            source,
        )

    def _is_summon_cost_reduction(
        self,
        spec,
    ):
        # 「自分のクリーチャー（=自身以外も含む集合）の召喚コストを軽減する」形。
        # applies_to.card == "self" の自己コスト修飾は
        # SelfSummonCostModifierAbility が担う。
        if spec.get("type") != "cost_modifier":
            return False

        applies_to = spec.get("applies_to", {})
        return applies_to.get("card") != "self"

    def _is_self_cost_modifier(
        self,
        spec,
    ):
        if spec.get("type") != "cost_modifier":
            return False

        applies_to = spec.get("applies_to", {})
        return applies_to.get("card") == "self"

    def _create_triggered_ability(
        self,
        spec,
        source,
    ):
        bridged = self._bridge_to_registry_spec(
            spec,
            self.TRIGGERED_BRIDGE_IDS,
        )
        if bridged is not None:
            return self._create_registry_ability(
                bridged,
                source,
            )

        return [
            JsonTriggeredAbility(
                source,
                self.game,
                spec,
            )
        ]

    def _create_replacement_ability(
        self,
        spec,
        source,
    ):
        bridged = self._bridge_to_registry_spec(
            spec,
            self.REPLACEMENT_BRIDGE_IDS,
        )
        if bridged is not None:
            return self._create_registry_ability(
                bridged,
                source,
            )

        # キーワードと同様、attempt を持たない ability_id 指定の置換能力は
        # registry 実装へ橋渡しする。
        if "attempt" not in spec and (
            spec.get("ability_id") or spec.get("id")
        ):
            return self._create_registry_ability(
                spec,
                source,
            )

        return [
            JsonReplacementAbility(
                source,
                self.game,
                spec,
            )
        ]

    def _create_registry_ability(
        self,
        spec,
        source,
    ):
        ability_or_list = create_ability(
            spec,
            source,
            self.game,
        )

        if isinstance(
            ability_or_list,
            list,
        ):
            return ability_or_list

        return [
            ability_or_list,
        ]

    def _keyword_to_registry_spec(
        self,
        spec,
    ):
        if isinstance(
            spec,
            str,
        ):
            return spec

        if "id" in spec:
            return spec

        if "ability_id" in spec:
            return {
                "id": spec["ability_id"],
                **{
                    key: value
                    for key, value in spec.items()
                    if key not in (
                        "ability_id",
                        "keyword",
                        "name",
                        "type",
                    )
                },
            }

        keyword_id = spec.get(
            "keyword",
            spec.get("name"),
        )
        if keyword_id is None:
            raise ValueError(
                f"keyword ability requires ability_id: {spec}"
            )

        return {
            "id": keyword_id,
            **{
                key: value
                for key, value in spec.items()
                if key not in (
                    "keyword",
                    "name",
                    "type",
                )
            },
        }

    def _static_to_registry_spec(
        self,
        spec,
    ):
        spec_type = spec.get("type")
        builder_name = self.STATIC_BUILDERS.get(spec_type)
        if builder_name is not None:
            return getattr(self, builder_name)(
                spec
            )

        if spec_type in self.NATIVE_STATIC_TYPES:
            return None

        raise ValueError(
            f"Unknown v2 static ability type: {spec_type}"
        )

    def _break_modifier_to_registry_spec(
        self,
        spec,
    ):
        value = spec.get(
            "modifier",
            {},
        ).get(
            "value",
            spec.get("value"),
        )
        ability_id = {
            2: "double_breaker",
            3: "triple_breaker",
            4: "q_breaker",
            "world": "world_breaker",
        }.get(value)

        if ability_id is None:
            return None

        return {
            "id": ability_id,
            **self._active_if_field(spec),
        }

    def _attack_rule_to_registry_spec(
        self,
        spec,
    ):
        rule = spec.get("rule", {})
        kind = rule.get("kind")

        if kind == "cannot_be_blocked":
            registry_spec = {
                "id": "unblockable",
                **self._active_if_field(spec),
            }
            if "blocker_condition" in rule:
                registry_spec["condition"] = rule["blocker_condition"]
            return registry_spec

        if kind == "opponent_attack_mandatory":
            return {
                "id": "opponent_attack_mandatory",
                "scope": rule.get(
                    "scope",
                    "opponent_creatures",
                ),
                **self._active_if_field(spec),
            }

        if kind == "must_attack_this":
            # 「相手のクリーチャーが攻撃するなら、可能ならこのクリーチャーを攻撃する」
            return {
                "id": "attack_lure",
                "scope": rule.get(
                    "scope",
                    "opponent_creatures",
                ),
                **self._active_if_field(spec),
            }

        if kind == "cannot_attack_on_enter_turn":
            registry_spec = {
                "id": "enter_turn_attack_lock",
                **self._active_if_field(spec),
            }
            self._copy_present_keys(
                registry_spec,
                rule,
                {
                    "scope": "scope",
                    "filter": "filter",
                },
            )
            return registry_spec

        if kind == "can_attack_untapped":
            return {
                "id": "attack_untapped",
                **self._active_if_field(spec),
            }

        if kind == "cannot_attack_unless":
            return {
                "id": "conditional_attack_forbid",
                "condition": rule.get("condition"),
            }

        if kind == "cannot_attack_player":
            registry_spec = {
                "id": "attack_player_lock",
                **self._active_if_field(spec),
            }
            self._copy_present_keys(
                registry_spec,
                rule,
                {
                    "scope": "scope",
                    "filter": "filter",
                },
            )
            return registry_spec

        return None

    def _block_rule_to_registry_spec(
        self,
        spec,
    ):
        rule = spec.get("rule", {})
        if rule.get("kind") in (
            "blocker",
            "can_block",
        ):
            return {
                "id": "blocker",
                **self._active_if_field(spec),
            }

        return None

    def _target_rule_to_registry_spec(
        self,
        spec,
    ):
        rule = spec.get("rule", {})
        if rule.get("kind") == "cannot_be_chosen_by_opponent":
            return {
                "id": "untouchable",
                **self._active_if_field(spec),
            }

        return None

    def _cost_payment_rule_to_registry_spec(
        self,
        spec,
    ):
        rule = spec.get("rule", {})
        if rule.get("kind") != "alternative_payment":
            return None

        registry_spec = {
            "id": "alternative_summon_cost",
            **self._active_if_field(spec),
        }
        applies_to = spec.get("applies_to", {})
        if applies_to.get("from_zone"):
            registry_spec["active_zone"] = applies_to["from_zone"]

        condition = spec.get("condition")
        if (
            isinstance(condition, dict)
            and condition.get("type") == "player_zone_count"
        ):
            registry_spec["requirements"] = [
                {
                    "id": "min_shields",
                    "count": condition.get(
                        "value",
                        condition.get("count"),
                    ),
                }
            ]

        for cost in rule.get("costs", []):
            applier_name = self.COST_PAYMENT_RULE_COST_APPLIERS.get(
                cost.get("type")
            )
            if applier_name is not None:
                getattr(self, applier_name)(
                    registry_spec,
                    cost,
                )

        return registry_spec

    def _apply_alt_pay_mana_cost_to_registry(
        self,
        registry_spec,
        cost,
    ):
        registry_spec["cost"] = cost.get("amount")
        registry_spec["civilizations"] = cost.get(
            "civilizations"
        )

    def _apply_destroy_cost_to_registry(
        self,
        registry_spec,
        cost,
    ):
        registry_spec.setdefault(
            "additional_costs",
            [],
        ).append(
            {
                "id": "destroy_own_creature",
                "prompt": cost.get(
                    "prompt",
                    "Choose one of your creatures to destroy",
                ),
            }
        )

    def _enter_battle_rule_to_registry_spec(
        self,
        spec,
    ):
        rule = spec.get("rule", {})
        kind = rule.get("kind")
        applies_to = spec.get("applies_to", {})

        if kind in (
            "cannot_enter_except_from",
            "hand_only",
            "only_from_zone",
        ):
            registry_spec = {
                "id": "element_entry_lock",
                "affected_player": applies_to.get(
                    "player",
                    rule.get("affected_player", "opponent"),
                ),
                **self._active_if_field(spec),
            }
            self._copy_present_keys(
                registry_spec,
                rule,
                {
                    "from_zone": "allow_from_zone",
                    "allow_from_zone": "allow_from_zone",
                    "allow_reason": "allow_reason",
                    "allow_reasons": "allow_reasons",
                },
            )
            return registry_spec

        if kind == "creature_only":
            registry_spec = {
                "id": "creature_entry_lock",
                "affected_player": applies_to.get(
                    "player",
                    rule.get("affected_player", "opponent"),
                ),
                **self._active_if_field(spec),
            }
            self._copy_present_keys(
                registry_spec,
                rule,
                {
                    "allow_from_zones": "allow_from_zones",
                    "block_from_zones": "block_from_zones",
                    "allow_reasons": "allow_reasons",
                },
            )
            return registry_spec

        if kind == "enters_tapped":
            registry_spec = {
                "id": "tap_to_play",
                "affected_player": applies_to.get(
                    "player",
                    rule.get("affected_player", "opponent"),
                ),
                **self._active_if_field(spec),
            }
            self._copy_present_keys(
                registry_spec,
                rule,
                {
                    "zones": "zones",
                    "tap_required": "tap_required",
                    "optional": "optional",
                    "prompt": "prompt",
                },
            )
            return registry_spec

        return None

    def _summon_rule_to_registry_spec(
        self,
        spec,
    ):
        rule = spec.get("rule", {})
        kind = rule.get("kind")
        registry_id = self.SUMMON_RULE_IDS.get(kind)
        if registry_id is None:
            raise ValueError(
                f"Unknown v2 summon_rule kind: {kind}"
            )

        registry_spec = {
            "id": registry_id,
            **self._active_if_field(spec),
        }
        for key, value in rule.items():
            if key != "kind":
                registry_spec[key] = value

        return registry_spec

    def _cast_rule_to_registry_spec(
        self,
        spec,
    ):
        rule = spec.get("rule", {})
        if rule.get("kind") != "cannot_cast":
            return None

        registry_spec = {
            "id": "cannot_cast_spells",
            **self._active_if_field(spec),
        }
        self._copy_present_keys(
            registry_spec,
            rule,
            {
                "affected_player": "affected_player",
                "max_cost": "max_cost",
                "cost_limit": "cost_limit",
                "cost_comparison": "cost_comparison",
                "exact_cost": "exact_cost",
                "civilizations": "civilizations",
                "civilization": "civilization",
            },
        )
        return registry_spec

    def _grant_rule_to_registry_spec(
        self,
        spec,
    ):
        rule = spec.get("rule", {})
        registry_spec = {
            "id": "grant_ability",
            **self._active_if_field(spec),
        }
        self._copy_present_keys(
            registry_spec,
            rule,
            {
                "scope": "scope",
                "ability": "ability",
                "optional": "optional",
                "active_zone": "active_zone",
                "filter": "filter",
                "exclude_source": "exclude_source",
            },
        )
        # hyper_mode 以外の条件（例: G城の shield_face_up）は dict のまま
        # active_if として渡す（active_if_matches が ConditionEvaluator で評価）。
        condition = spec.get("condition")
        if (
            "active_if" not in registry_spec
            and isinstance(condition, dict)
        ):
            registry_spec["active_if"] = condition

        return registry_spec

    def _mana_rule_to_registry_spec(
        self,
        spec,
    ):
        rule = spec.get("rule", {})

        if rule.get("kind") == "all_civilizations":
            return {
                "id": "mana_all_civilizations",
                **self._active_if_field(spec),
            }

        registry_spec = {
            "id": "mana_number",
            **self._active_if_field(spec),
        }
        self._copy_present_keys(
            registry_spec,
            rule,
            {
                "value": "value",
                "min_card_types": "min_card_types",
            },
        )
        return registry_spec

    def _power_modifier_to_registry_spec(
        self,
        spec,
    ):
        rule = spec.get("rule", {})
        if rule.get("kind") != "per_card_in_zone":
            return None

        registry_spec = {
            "id": "power_per_card_in_zone",
            **self._active_if_field(spec),
        }
        self._copy_present_keys(
            registry_spec,
            rule,
            {
                "amount": "amount",
                "zone": "zone",
            },
        )
        return registry_spec

    def _choice_replacement_to_registry_spec(
        self,
        spec,
    ):
        registry_spec = {
            "id": "opponent_creature_choice_replacement",
        }
        applies_to = spec.get("applies_to", {})
        if "player" in applies_to:
            registry_spec["affected_player"] = applies_to["player"]

        condition = spec.get("condition")
        if condition is not None:
            registry_spec["active_if"] = condition

        return registry_spec

    def _cross_rule_to_registry_spec(
        self,
        spec,
    ):
        rule = spec.get("rule", {})
        if rule.get("kind") != "grant":
            return None

        registry_spec = {
            "id": "cross_grant",
            **self._active_if_field(spec),
        }
        self._copy_present_keys(
            registry_spec,
            rule,
            {
                "abilities": "abilities",
                "ability_ids": "ability_ids",
            },
        )
        return registry_spec

    def _bridge_to_registry_spec(
        self,
        spec,
        bridge_ids,
    ):
        if not isinstance(spec, dict):
            return None

        kind_map = bridge_ids.get(spec.get("type"))
        if kind_map is None:
            return None

        rule = spec.get("rule", {})
        kind = rule.get("kind")
        registry_id = kind_map.get(kind)
        if registry_id is None:
            raise ValueError(
                f"Unknown bridged ability kind: {spec.get('type')}/{kind}"
            )

        registry_spec = {
            "id": registry_id,
        }
        if "label" in spec:
            registry_spec["label"] = spec["label"]
        registry_spec.update(
            self._active_if_field(spec)
        )
        for key, value in rule.items():
            if key != "kind":
                registry_spec[key] = value

        return registry_spec

    def _copy_present_keys(
        self,
        dst,
        src,
        mapping,
    ):
        for src_key, dst_key in mapping.items():
            if src_key in src:
                dst[dst_key] = src[src_key]

    def _active_if_field(
        self,
        spec,
    ):
        active_if = self._condition_to_active_if(
            spec.get("condition")
        )
        if active_if is None:
            return {}

        return {
            "active_if": active_if,
        }

    def _condition_to_active_if(
        self,
        condition,
    ):
        if not isinstance(
            condition,
            dict,
        ):
            return None

        if (
            condition.get("type") in (
                "card_state",
                "source_has_state",
            )
            and condition.get("card", "self") == "self"
            and condition.get("state") == "hyper_mode"
            and condition.get("value", True)
        ):
            return "hyper_mode"

        if condition.get("type") == "not":
            return condition

        return None
