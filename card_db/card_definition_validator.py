"""Validation for structured card ability definitions."""

from dataclasses import dataclass
import re

from abilities.v2.event_map import EVENT_TYPES, event_name
from abilities.v2.spec_schema import (
    COMPOSITE_TRIGGER_KEYS,
    EVENT_KEYS,
    REPLACEMENT_ATTEMPT_KEYS,
    TARGET_KEYS,
    TARGET_FROM_KEYS,
    TIMING_KEYS,
    TRIGGER_KEYS,
    TRIGGER_SUBJECTS,
    composite_sub_triggers,
    is_composite_trigger,
)
from abilities.v2.timing_matcher import STEP_NAMES, ZONE_NAMES
from core.card_filter_evaluator import CARD_FILTER_FIELDS
from core.condition_registry import CONDITION_TYPES, condition_validator_name
from core.dsl_compare import COMPARISON_OPERATORS, SYMBOL_OPERATOR_ALIASES
from core.zone_filter_evaluator import ZONE_FILTER_FIELDS
from effects.composition.card_predicates import CARD_TYPE_NAMES


EFFECT_TYPES_WITH_CHILDREN = (
    "effects",
    "then",
    "else",
    "default",
    "alternative",
    "alternative_effects",
)

IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

_KNOWN_KEYWORD_IDS = None


def _known_keyword_ids():
    """登録済みキーワード ID 集合（registry を遅延 import してキャッシュ）。

    `abilities.registry` は多数の ability クラスを import するため、循環 import を
    避けて呼び出し時に1度だけ取り込む。`ABILITY_METADATA`（reminder 等のメタのみ
    保持する keyword）も含めて漏れを防ぐ。
    """

    global _KNOWN_KEYWORD_IDS
    if _KNOWN_KEYWORD_IDS is None:
        from abilities.registry import ABILITY_BUILDERS, ABILITY_METADATA

        _KNOWN_KEYWORD_IDS = frozenset(ABILITY_BUILDERS) | frozenset(
            ABILITY_METADATA
        )
    return _KNOWN_KEYWORD_IDS

CARD_TYPE_KEYS = frozenset(("card_type", "card_types"))
ZONE_ALIAS_FIXES = {
    "battle_zone": "battle",
    "grave": "graveyard",
    "hand_zone": "hand",
    "mana_zone": "mana",
    "shield_zone": "shield",
    "shields": "shield",
}
ZONE_KEYS = frozenset(
    (
        "active_zone",
        "active_zones",
        "from",
        "from_zone",
        "source_zone",
        "to",
        "to_zone",
        "destination_zone",
        "zone",
        "zones",
        "allow_from_zone",
        "allow_from_zones",
        "block_from_zones",
    )
)
VALID_CARD_TYPE_VALUES = frozenset(
    {
        *CARD_TYPE_NAMES,
        "any",
        "element",
        "non_creature",
    }
)
OPTIONAL_AWARE_EFFECT_IDS = frozenset(
    (
        "add_deck_to_shield",
        "add_hand_to_shield",
        "add_shield_to_hand",
        "battle_two_creatures",
        "break_shield",
        "creature_break_shield",
        "discard",
        "discard_hand_then_draw",
        "destroy_creature",
        "draw",
        "execute_card_from_hand",
        "execute_card_from_zone",
        "look_top_choose_distinct_types_to_hand",
        "look_top_choose_to_hand",
        "look_top_put_creature_to_battle",
        "look_top_same_cost_creatures_to_battle",
        "mill",
        "move_card",
        "move_deck_top",
        "opponent_choose_own_creature_or_shield_to_mana",
        "power_gachinko_judge",
        "put_creature_from_multi_zone",
        "put_creature_from_zone",
        "reveal_cards",
        "return_from_graveyard",
        "select",
        "select_n",
        "select_within_total_cost",
        "select_then",
        "select_within_total_power",
        "shield_plus",
        "store_card_from_zone",
        "tap",
        "untap",
    )
)
OPTIONAL_AWARE_V2_TYPES = frozenset(
    (
        "draw",
        "discard",
        "execute",
        "move",
        "select",
    )
)
DEPENDENCY_REQUIRED_KEYS = {
    "count": ("source", "count_key"),
    "count_matching": ("source", "store_as"),
    "for_each": ("source",),
    "for_each_stored": ("source",),
    "gather_matching": ("store_as",),
    "if_stored_card_matches": ("key",),
    "repeat": ("count_key",),
    "select_n": ("count_key", "store_as"),
    "select_within_total_cost": ("max_total_cost", "store_as"),
    "select_within_total_power": ("max_total_power", "store_as"),
}


@dataclass(frozen=True)
class ValidationWarning:
    card_id: str
    card_name: str
    code: str
    path: str
    message: str
    possible_fix: str

    def format(
        self,
    ):
        return (
            f"{self.code}: "
            f"card_id={self.card_id}; "
            f"card_name={self.card_name}; "
            f"path={self.path}; "
            f"message={self.message}; "
            f"possible_fix={self.possible_fix}"
        )

REPLACEMENT_COST_VALIDATORS = {
    "pay_mana": "_validate_pay_mana_replacement_cost",
    "move_cards": "_validate_move_cards_replacement_cost",
}

REPLACE_ACTION_VALIDATORS = {
    "move_event_card": "_validate_move_event_card_action",
    "put_attempt_shield_on_bottom": "_validate_move_event_card_action",
    "draw": "_validate_draw_action",
}

STRUCTURED_SPEC_VALIDATORS = {
    "trigger": "_validate_trigger_spec",
    "timing": "_validate_timing_spec",
    "attempt": "_validate_attempt_spec",
}


class CardDefinitionValidator:
    """Validate condition/filter/ref/target DSL shapes early."""

    def __init__(
        self,
        allow_legacy=True,
    ):
        self.allow_legacy = allow_legacy

    def validate_card(
        self,
        card,
        label=None,
    ):
        label = label or card.get("id", "<unknown>")
        errors = []
        errors.extend(
            self._validate_card_type_fields(
                card,
                label,
            )
        )
        errors.extend(
            self.validate_abilities(
                card.get("abilities"),
                f"{label}.abilities",
            )
        )
        return _dedupe(errors)

    def validate_card_warnings(
        self,
        card,
        label=None,
        card_id=None,
        card_name=None,
    ):
        label = label or card.get("id", "<unknown>")
        card_id = card_id or card.get("id", label)
        card_name = card_name or _card_name(card)
        warnings = []
        warnings.extend(
            self._warn_effects(
                card.get("effects", []),
                f"{label}.effects",
                card_id,
                card_name,
            )
        )
        warnings.extend(
            self._warn_effects(
                card.get("replacement_effects", []),
                f"{label}.replacement_effects",
                card_id,
                card_name,
            )
        )
        warnings.extend(
            self._validate_ability_warnings(
                card.get("abilities"),
                f"{label}.abilities",
                card_id,
                card_name,
            )
        )
        return warnings

    def validate_abilities(
        self,
        abilities,
        path="abilities",
    ):
        if abilities is None:
            return []

        if isinstance(abilities, list):
            return self._validate_legacy_ability_list(
                abilities,
                path,
            )

        if not isinstance(abilities, dict):
            return [
                f"{path}: abilities must be a list or object"
            ]

        errors = []
        for index, spec in enumerate(_as_list(abilities.get("static"))):
            if self._is_structured_static(spec):
                errors.extend(
                    self._validate_structured_ability(
                        spec,
                        f"{path}.static[{index}]",
                    )
                )

        for index, spec in enumerate(_as_list(abilities.get("triggered"))):
            if isinstance(spec, dict) and "trigger" in spec:
                errors.extend(
                    self._validate_structured_ability(
                        spec,
                        f"{path}.triggered[{index}]",
                    )
                )
            elif not self.allow_legacy:
                errors.append(
                    f"{path}.triggered[{index}]: legacy trigger is not allowed"
                )

        for index, spec in enumerate(_as_list(abilities.get("activated"))):
            errors.extend(
                self._validate_structured_ability(
                    spec,
                    f"{path}.activated[{index}]",
                )
            )

        for index, spec in enumerate(_as_list(abilities.get("replacement"))):
            if isinstance(spec, dict) and "attempt" in spec:
                errors.extend(
                    self._validate_structured_ability(
                        spec,
                        f"{path}.replacement[{index}]",
                    )
                )
            elif not self.allow_legacy:
                errors.append(
                    f"{path}.replacement[{index}]: legacy replacement is not allowed"
                )

        return errors

    def _validate_ability_warnings(
        self,
        abilities,
        path,
        card_id,
        card_name,
    ):
        if abilities is None:
            return []

        warnings = []
        warnings.extend(
            self._warn_unknown_keywords(
                abilities,
                path,
                card_id,
                card_name,
            )
        )
        for group in (
            "static",
            "triggered",
            "activated",
            "replacement",
        ):
            for index, spec in enumerate(_as_list(abilities.get(group))):
                if not isinstance(spec, dict):
                    continue
                spec_path = f"{path}.{group}[{index}]"
                warnings.extend(
                    self._warn_zone_aliases(
                        spec,
                        spec_path,
                        card_id,
                        card_name,
                    )
                )
                warnings.extend(
                    self._warn_effects(
                        spec.get("effects", []),
                        f"{spec_path}.effects",
                        card_id,
                        card_name,
                    )
                )

                replace_with = spec.get("replace_with")
                if isinstance(replace_with, dict):
                    warnings.extend(
                        self._warn_effects(
                            replace_with.get("effects", []),
                            f"{spec_path}.replace_with.effects",
                            card_id,
                            card_name,
                        )
                    )
                    warnings.extend(
                        self._warn_zone_aliases(
                            replace_with.get("actions", []),
                            f"{spec_path}.replace_with.actions",
                            card_id,
                            card_name,
                        )
                    )

                after_batch = spec.get(
                    "after_replacement_batch",
                    spec.get("after_replacements"),
                )
                if isinstance(after_batch, dict):
                    warnings.extend(
                        self._warn_effects(
                            after_batch.get("effects", []),
                            f"{spec_path}.after_replacement_batch.effects",
                            card_id,
                            card_name,
                        )
                    )

        return warnings

    def _validate_legacy_ability_list(
        self,
        abilities,
        path,
    ):
        if self.allow_legacy:
            return []

        errors = []
        for index, item in enumerate(abilities):
            if isinstance(item, str):
                errors.append(
                    f"{path}[{index}]: only keyword strings are allowed"
                )
        return errors

    def _validate_structured_ability(
        self,
        spec,
        path,
    ):
        if not isinstance(spec, dict):
            return [
                f"{path}: ability must be an object"
            ]

        errors = []
        for key, validator_name in STRUCTURED_SPEC_VALIDATORS.items():
            if key in spec:
                errors.extend(
                    getattr(self, validator_name)(
                        spec[key],
                        f"{path}.{key}",
                    )
                )

        errors.extend(
            self._validate_condition(
                spec.get("active_if"),
                f"{path}.active_if",
            )
        )
        errors.extend(
            self._validate_condition(
                spec.get("condition"),
                f"{path}.condition",
            )
        )
        errors.extend(
            self._validate_targets(
                spec.get("targets", []),
                f"{path}.targets",
            )
        )
        errors.extend(
            self._validate_effects(
                spec.get("effects", []),
                f"{path}.effects",
            )
        )
        errors.extend(
            self._validate_replacement_costs(
                spec.get("costs", []),
                f"{path}.costs",
            )
        )

        replace_with = spec.get("replace_with")
        if isinstance(replace_with, dict):
            errors.extend(
                self._validate_effects(
                    replace_with.get("effects", []),
                    f"{path}.replace_with.effects",
                )
            )
            errors.extend(
                self._validate_replace_actions(
                    replace_with.get("actions", []),
                    f"{path}.replace_with.actions",
                )
            )

        after_batch = spec.get(
            "after_replacement_batch",
            spec.get("after_replacements"),
        )
        if isinstance(after_batch, dict):
            errors.extend(
                self._validate_effects(
                    after_batch.get("effects", []),
                    f"{path}.after_replacement_batch.effects",
                )
            )

        return errors

    def _validate_trigger_spec(
        self,
        trigger,
        path,
    ):
        # 複合トリガー（or / and / not）は triggers 等のサブトリガーを持ち、
        # 各サブトリガーを再帰的に検証する（v2 パーサと同じ扱い）。
        if is_composite_trigger(trigger):
            return self._validate_composite_trigger_spec(
                trigger,
                path,
            )

        errors = self._validate_event_spec(
            trigger,
            path,
            TRIGGER_KEYS,
        )
        if errors:
            return errors

        subject = trigger.get("subject")
        if subject is not None and subject not in TRIGGER_SUBJECTS:
            errors.append(
                f"{path}.subject: unknown trigger subject {subject!r}"
            )

        for key in (
            "attacker",
            "card",
        ):
            if key in trigger:
                errors.extend(
                    self._validate_card_ref_value(
                        trigger[key],
                        f"{path}.{key}",
                    )
                )

        if "player" in trigger:
            errors.extend(
                self._validate_player_ref_value(
                    trigger["player"],
                    f"{path}.player",
                )
            )

        if "filter" in trigger:
            errors.extend(
                self._validate_card_filter(
                    trigger["filter"],
                    f"{path}.filter",
                )
            )

        for key in (
            "from_zone",
            "to_zone",
            "reason",
        ):
            if key in trigger:
                errors.extend(
                    self._validate_comparison_expression(
                        trigger[key],
                        f"{path}.{key}",
                    )
                )

        return errors

    def _validate_composite_trigger_spec(
        self,
        trigger,
        path,
    ):
        errors = self._validate_key_set(
            trigger,
            path,
            COMPOSITE_TRIGGER_KEYS,
        )
        if errors:
            return errors

        sub_triggers = composite_sub_triggers(trigger)
        if not sub_triggers:
            return [
                f"{path}: composite trigger requires sub-triggers"
            ]

        for index, sub in enumerate(sub_triggers):
            errors.extend(
                self._validate_trigger_spec(
                    sub,
                    f"{path}.triggers[{index}]",
                )
            )

        return errors

    def _validate_timing_spec(
        self,
        timing,
        path,
    ):
        errors = self._validate_key_set(
            timing,
            path,
            TIMING_KEYS,
        )
        if errors:
            return errors

        for key in (
            "active_zone",
            "active_zones",
        ):
            if key in timing:
                errors.extend(
                    self._validate_zone_names(
                        timing[key],
                        f"{path}.{key}",
                    )
                )

        if "step" in timing and timing["step"] not in STEP_NAMES:
            errors.append(
                f"{path}.step: unknown step {timing['step']!r}"
            )

        return errors

    def _validate_zone_names(
        self,
        value,
        path,
    ):
        if value == "any":
            return []

        errors = []
        for item in _as_list(value):
            if item not in ZONE_NAMES:
                errors.append(
                    f"{path}: unknown zone {item!r}"
                )

        return errors

    def _validate_attempt_spec(
        self,
        attempt,
        path,
    ):
        errors = self._validate_event_spec(
            attempt,
            path,
            REPLACEMENT_ATTEMPT_KEYS,
        )
        if errors:
            return errors

        breaker = attempt.get("breaker")
        if breaker is not None:
            errors.extend(
                self._validate_card_ref_value(
                    breaker,
                    f"{path}.breaker",
                )
            )

        if "card" in attempt:
            errors.extend(
                self._validate_card_ref_value(
                    attempt["card"],
                    f"{path}.card",
                )
            )

        if "card_filter" in attempt:
            errors.extend(
                self._validate_card_filter(
                    attempt["card_filter"],
                    f"{path}.card_filter",
                )
            )

        for key in (
            "from_zone",
            "to_zone",
        ):
            if key in attempt:
                errors.extend(
                    self._validate_comparison_expression(
                        attempt[key],
                        f"{path}.{key}",
                    )
                )

        return errors

    def _validate_event_spec(
        self,
        spec,
        path,
        allowed_keys,
    ):
        errors = self._validate_key_set(
            spec,
            path,
            allowed_keys,
        )
        if errors:
            return errors

        value = _first_present(
            spec,
            EVENT_KEYS,
        )
        if value is None:
            return [
                f"{path}.event: event is required"
            ]

        for item in _as_list(value):
            resolved = event_name(item)
            if resolved not in EVENT_TYPES:
                errors.append(
                    f"{path}.event: unknown event {item!r}"
                )

        return errors

    def _validate_key_set(
        self,
        spec,
        path,
        allowed_keys,
    ):
        if not isinstance(spec, dict):
            return [
                f"{path}: must be an object"
            ]

        unknown = set(spec) - set(allowed_keys)
        if not unknown:
            return []

        return [
            f"{path}.{sorted(unknown)[0]}: unknown key"
        ]

    def _validate_condition(
        self,
        condition,
        path,
    ):
        if condition is None:
            return []

        if isinstance(condition, str):
            return [
                f"{path}: condition must be an object, not a string"
            ]

        if not isinstance(condition, dict):
            return [
                f"{path}: condition must be an object"
            ]

        condition_type = condition.get("type")
        if condition_type not in CONDITION_TYPES:
            return [
                f"{path}.type: unknown condition type {condition_type!r}"
            ]

        validator_name = condition_validator_name(condition_type)
        if validator_name is None:
            return []

        return getattr(self, validator_name)(
            condition,
            path,
        )

    def _validate_logical_condition(
        self,
        condition,
        path,
    ):
        items = condition.get(
            "conditions",
            condition.get("all", condition.get("any", [])),
        )
        errors = []
        if not isinstance(items, list):
            errors.append(
                f"{path}.conditions: must be a list"
            )

        for index, item in enumerate(_as_list(items)):
            errors.extend(
                self._validate_condition(
                    item,
                    f"{path}.conditions[{index}]",
                )
            )

        return errors

    def _validate_not_condition(
        self,
        condition,
        path,
    ):
        return self._validate_condition(
            condition.get("condition"),
            f"{path}.condition",
        )

    def _validate_card_filter_condition(
        self,
        condition,
        path,
    ):
        return self._validate_card_filter(
            condition.get("filter", {}),
            f"{path}.filter",
        )

    def _validate_event_zone_change_condition(
        self,
        condition,
        path,
    ):
        errors = self._validate_card_filter(
            condition.get("card_filter", {}),
            f"{path}.card_filter",
        )
        for key in (
            "from_zone",
            "to_zone",
            "reason",
            "from_shield_face_up",
        ):
            if key not in condition:
                continue
            errors.extend(
                self._validate_comparison_expression(
                    condition[key],
                    f"{path}.{key}",
                )
            )

        return errors

    def _validate_source_zone_condition(
        self,
        condition,
        path,
    ):
        return self._validate_comparison_expression(
            condition.get("zone"),
            f"{path}.zone",
        )

    def _validate_card_count_condition(
        self,
        condition,
        path,
    ):
        errors = []
        errors.extend(
            self._validate_card_filter(
                condition.get("filter", {}),
                f"{path}.filter",
            )
        )
        errors.extend(
            self._validate_condition_operator(
                condition,
                path,
            )
        )
        errors.extend(
            self._validate_ref_value(
                condition.get("value", condition.get("count", 0)),
                f"{path}.value",
            )
        )

        if "cards" in condition:
            errors.extend(
                self._validate_ref_value(
                    condition["cards"],
                    f"{path}.cards",
                )
            )
        elif (
            "zone" not in condition
            and not isinstance(condition.get("from"), dict)
        ):
            errors.append(
                f"{path}.from: must be an object when cards is omitted"
            )

        return errors

    def _validate_battle_result_condition(
        self,
        condition,
        path,
    ):
        errors = []
        for key in (
            "winner",
            "loser",
        ):
            if key in condition:
                errors.extend(
                    self._validate_ref_value(
                        condition[key],
                        f"{path}.{key}",
                    )
                )

        for key in (
            "winner_filter",
            "loser_filter",
        ):
            if key in condition:
                errors.extend(
                    self._validate_card_filter(
                        condition[key],
                        f"{path}.{key}",
                    )
                )

        return errors

    def _validate_choice_history_condition(
        self,
        condition,
        path,
    ):
        errors = []
        if "card" in condition:
            errors.extend(
                self._validate_ref_value(
                    condition["card"],
                    f"{path}.card",
                )
            )
        if "filter" in condition:
            errors.extend(
                self._validate_card_filter(
                    condition["filter"],
                    f"{path}.filter",
                )
            )
        if "prompt" in condition:
            errors.extend(
                self._validate_comparison_expression(
                    condition["prompt"],
                    f"{path}.prompt",
                )
            )

        return errors

    def _validate_player_zone_count_condition(
        self,
        condition,
        path,
    ):
        errors = self._validate_condition_operator(
            condition,
            path,
        )
        errors.extend(
            self._validate_ref_value(
                condition.get("value"),
                f"{path}.value",
            )
        )
        return errors

    def _validate_condition_operator(
        self,
        condition,
        path,
    ):
        operator = condition.get(
            "op",
            condition.get("operator", "eq"),
        )
        if self._is_condition_operator(operator):
            return []

        return [
            f"{path}.op: unknown comparison operator {operator!r}"
        ]

    def _validate_targets(
        self,
        targets,
        path,
    ):
        errors = []
        for index, target in enumerate(_as_list(targets)):
            target_path = f"{path}[{index}]"
            if not isinstance(target, dict):
                errors.append(
                    f"{target_path}: target must be an object"
                )
                continue

            errors.extend(
                self._validate_key_set(
                    target,
                    target_path,
                    TARGET_KEYS,
                )
            )

            if not isinstance(target.get("id"), str):
                errors.append(
                    f"{target_path}.id: target id must be a string"
                )

            if not isinstance(target.get("from"), dict):
                errors.append(
                    f"{target_path}.from: must be an object"
                )
            else:
                errors.extend(
                    self._validate_key_set(
                        target["from"],
                        f"{target_path}.from",
                        TARGET_FROM_KEYS,
                    )
                )

            errors.extend(
                self._validate_card_filter(
                    target.get("filter", {}),
                    f"{target_path}.filter",
                )
            )

        return errors

    def _validate_effects(
        self,
        effects,
        path,
    ):
        errors = []
        for index, effect in enumerate(_as_list(effects)):
            effect_path = f"{path}[{index}]"
            if not isinstance(effect, dict):
                errors.append(
                    f"{effect_path}: effect must be an object"
                )
                continue

            if "type" in effect:
                for key in ("target", "card", "cards"):
                    if key not in effect:
                        continue
                    value = effect[key]
                    if isinstance(value, str) and value not in (
                        "self",
                        "source",
                        "source_card",
                    ):
                        errors.append(
                            f"{effect_path}.{key}: string references must use {{\"ref\": ...}}"
                        )
                    else:
                        errors.extend(
                            self._validate_ref_value(
                                value,
                                f"{effect_path}.{key}",
                            )
                        )

            if "filter" in effect:
                errors.extend(
                    self._validate_card_filter(
                        effect["filter"],
                        f"{effect_path}.filter",
                    )
                )

            for key in (
                "amount",
                "value",
                "count",
            ):
                if key in effect:
                    errors.extend(
                        self._validate_ref_value(
                            effect[key],
                            f"{effect_path}.{key}",
                        )
                    )

            for key in EFFECT_TYPES_WITH_CHILDREN:
                errors.extend(
                    self._validate_effects(
                        effect.get(key, []),
                        f"{effect_path}.{key}",
                    )
                )

            for choice_index, choice in enumerate(
                _as_list(effect.get("choices"))
            ):
                if isinstance(choice, dict):
                    errors.extend(
                        self._validate_effects(
                            choice.get("effects", []),
                            f"{effect_path}.choices[{choice_index}].effects",
                        )
                    )

        return errors

    def _validate_replacement_costs(
        self,
        costs,
        path,
    ):
        errors = []
        for index, cost in enumerate(_as_list(costs)):
            cost_path = f"{path}[{index}]"
            if not isinstance(cost, dict):
                errors.append(
                    f"{cost_path}: cost must be an object"
                )
                continue

            cost_type = cost.get("type")
            validator_name = REPLACEMENT_COST_VALIDATORS.get(cost_type)
            if validator_name is None:
                errors.append(
                    f"{cost_path}.type: unknown replacement cost {cost_type!r}"
                )
                continue

            errors.extend(
                getattr(self, validator_name)(
                    cost,
                    cost_path,
                )
            )

        return errors

    def _validate_pay_mana_replacement_cost(
        self,
        cost,
        path,
    ):
        if "amount" not in cost:
            return []

        return self._validate_ref_value(
            cost["amount"],
            f"{path}.amount",
        )

    def _validate_move_cards_replacement_cost(
        self,
        cost,
        path,
    ):
        errors = self._validate_pay_mana_replacement_cost(
            cost,
            path,
        )
        if not isinstance(cost.get("from"), dict):
            errors.append(
                f"{path}.from: must be an object"
            )
        for key in (
            "to",
            "to_zone",
        ):
            if key in cost:
                errors.extend(
                    self._validate_ref_value(
                        cost[key],
                        f"{path}.{key}",
                    )
                )

        return errors

    def _validate_replace_actions(
        self,
        actions,
        path,
    ):
        errors = []
        for index, action in enumerate(_as_list(actions)):
            action_path = f"{path}[{index}]"
            if not isinstance(action, dict):
                errors.append(
                    f"{action_path}: action must be an object"
                )
                continue

            action_type = action.get("type")
            validator_name = REPLACE_ACTION_VALIDATORS.get(action_type)
            if validator_name is None:
                errors.append(
                    f"{action_path}.type: unknown replacement action {action_type!r}"
                )
                continue

            errors.extend(
                getattr(self, validator_name)(
                    action,
                    action_path,
                )
            )

        return errors

    def _validate_move_event_card_action(
        self,
        action,
        path,
    ):
        errors = []
        for key in (
            "card",
            "from_zone",
            "to",
            "to_zone",
        ):
            if key in action:
                errors.extend(
                    self._validate_ref_value(
                        action[key],
                        f"{path}.{key}",
                    )
                )

        return errors

    def _validate_draw_action(
        self,
        action,
        path,
    ):
        errors = []
        if "amount" in action:
            errors.extend(
                self._validate_ref_value(
                    action["amount"],
                    f"{path}.amount",
                )
            )

        return errors

    def _validate_card_filter(
        self,
        filter_spec,
        path,
    ):
        if filter_spec is None:
            return []

        if not isinstance(filter_spec, dict):
            return [
                f"{path}: filter must be an object"
            ]

        errors = []
        for key, value in filter_spec.items():
            if key in ("and", "or"):
                if not isinstance(value, list):
                    errors.append(
                        f"{path}.{key}: must be a list"
                    )
                    continue
                for index, item in enumerate(value):
                    errors.extend(
                        self._validate_card_filter(
                            item,
                            f"{path}.{key}[{index}]",
                        )
                    )
                continue

            if key == "not":
                errors.extend(
                    self._validate_card_filter(
                        value,
                        f"{path}.not",
                    )
                )
                continue

            if key in (
                "max_cost",
                "min_cost",
                "cost_less_than",
                "cost_lt",
            ):
                # select 系効果が解釈する動的なコスト境界フィルタ。値は固定値の
                # ほか stored 参照（{"from": "stored", ...}）も取り得るため、
                # 汎用比較式としての検証は行わない。
                continue

            if key == "civilizations_all_in_mana_zone":
                # legacy フィルタ（card_predicates）が解釈する関係述語。
                # 「カードの全文明がプレイヤーのマナゾーンにある」かを表し、
                # 値はプレイヤー参照（"self" 等）。DSL の単純比較には載らない。
                continue

            if key in (
                "card_type",
                "type",
                "types",
                "card_types",
            ):
                errors.extend(
                    self._validate_card_type_values(
                        value,
                        f"{path}.{key}",
                    )
                )

            if key not in CARD_FILTER_FIELDS:
                errors.append(
                    f"{path}.{key}: unknown filter key"
                )
                continue

            errors.extend(
                self._validate_comparison_expression(
                    value,
                    f"{path}.{key}",
                )
            )

        return errors

    def _validate_card_type_fields(
        self,
        value,
        path,
    ):
        errors = []
        if isinstance(value, dict):
            for key, item in value.items():
                item_path = f"{path}.{key}"
                if key in CARD_TYPE_KEYS:
                    errors.extend(
                        self._validate_card_type_values(
                            item,
                            item_path,
                        )
                    )
                errors.extend(
                    self._validate_card_type_fields(
                        item,
                        item_path,
                    )
                )
            return errors

        if isinstance(value, list):
            for index, item in enumerate(value):
                errors.extend(
                    self._validate_card_type_fields(
                        item,
                        f"{path}[{index}]",
                    )
                )

        return errors

    def _validate_card_type_values(
        self,
        value,
        path,
    ):
        errors = []
        for value_path, item in _iter_scalar_values(value, path):
            if isinstance(item, dict):
                continue

            if not isinstance(item, str):
                errors.append(
                    f"{value_path}: E_UNKNOWN_CARD_TYPE: card_type value must be a string"
                )
                continue

            key = item.lower()
            if key not in VALID_CARD_TYPE_VALUES:
                errors.append(
                    f"{value_path}: E_UNKNOWN_CARD_TYPE: unknown card_type {item!r} "
                    f"(possible fix: use one of {', '.join(sorted(VALID_CARD_TYPE_VALUES))})"
                )

        return errors

    def _warn_effects(
        self,
        effects,
        path,
        card_id,
        card_name,
    ):
        effect_list = _as_list(effects)
        warnings = []

        for index, effect in enumerate(effect_list):
            effect_path = f"{path}[{index}]"
            if not isinstance(effect, dict):
                continue

            warnings.extend(
                self._warn_zone_aliases(
                    effect,
                    effect_path,
                    card_id,
                    card_name,
                )
            )
            warnings.extend(
                self._warn_missing_dependency_keys(
                    effect,
                    effect_path,
                    card_id,
                    card_name,
                )
            )
            warnings.extend(
                self._warn_ignored_optional(
                    effect,
                    effect_path,
                    card_id,
                    card_name,
                )
            )

            for child_key in EFFECT_TYPES_WITH_CHILDREN:
                warnings.extend(
                    self._warn_effects(
                        effect.get(child_key, []),
                        f"{effect_path}.{child_key}",
                        card_id,
                        card_name,
                    )
                )

            for choice_index, choice in enumerate(
                _as_list(effect.get("choices"))
            ):
                if not isinstance(choice, dict):
                    continue
                choice_path = f"{effect_path}.choices[{choice_index}]"
                warnings.extend(
                    self._warn_effects(
                        choice.get("effects", []),
                        f"{choice_path}.effects",
                        card_id,
                        card_name,
                    )
                )

        return warnings

    def _warn_missing_dependency_keys(
        self,
        effect,
        path,
        card_id,
        card_name,
    ):
        effect_id = _effect_id(effect)
        required = DEPENDENCY_REQUIRED_KEYS.get(effect_id)
        if not required:
            return []

        warnings = []
        for key in required:
            if key in effect:
                continue
            warnings.append(
                self._warning(
                    card_id,
                    card_name,
                    "W_MISSING_DEPENDENCY_KEY",
                    path,
                    (
                        f"{effect_id!r} usually needs {key!r} to connect "
                        "stored values between effects"
                    ),
                    f'add "{key}" or confirm this effect intentionally has no dependency',
                )
            )
        return warnings

    def _warn_ignored_optional(
        self,
        effect,
        path,
        card_id,
        card_name,
    ):
        warnings = []
        for key in ("may", "is_optional"):
            if key in effect:
                warnings.append(
                    self._warning(
                        card_id,
                        card_name,
                        "W_IGNORED_OPTIONAL",
                        f"{path}.{key}",
                        f"{key!r} is not a standard effect optional flag",
                        'use "optional" or an effect-specific amount bound',
                    )
                )

        if "optional" not in effect:
            return warnings

        effect_id = _effect_id(effect)
        effect_type = effect.get("type")
        if (
            effect_id in OPTIONAL_AWARE_EFFECT_IDS
            or effect_type in OPTIONAL_AWARE_V2_TYPES
        ):
            return warnings

        warnings.append(
            self._warning(
                card_id,
                card_name,
                "W_IGNORED_OPTIONAL",
                f"{path}.optional",
                (
                    "optional is present, but this effect type is not known "
                    "to read it"
                ),
                (
                    "move the optional choice to a select/move/execute effect, "
                    "or add implementation support if this effect should be optional"
                ),
            )
        )
        return warnings

    def _warn_unknown_keywords(
        self,
        abilities,
        path,
        card_id,
        card_name,
    ):
        if not isinstance(abilities, dict):
            return []

        known = _known_keyword_ids()
        warnings = []
        for index, entry in enumerate(_as_list(abilities.get("keyword"))):
            if isinstance(entry, str):
                keyword_id = entry
            elif isinstance(entry, dict):
                keyword_id = entry.get("ability_id") or entry.get("id")
            else:
                continue

            if not keyword_id or keyword_id in known:
                continue

            warnings.append(
                self._warning(
                    card_id,
                    card_name,
                    "W_UNKNOWN_KEYWORD",
                    f"{path}.keyword[{index}]",
                    (
                        f"unknown keyword id {keyword_id!r} is not registered; "
                        "the ability will raise at runtime when built"
                    ),
                    (
                        "register it in abilities/registry.py "
                        "(ABILITY_BUILDERS) or fix the spelling"
                    ),
                )
            )
        return warnings

    def _warn_zone_aliases(
        self,
        value,
        path,
        card_id,
        card_name,
    ):
        warnings = []
        if isinstance(value, dict):
            for key, item in value.items():
                item_path = f"{path}.{key}"
                if key in ZONE_KEYS:
                    warnings.extend(
                        self._warn_zone_alias_value(
                            item,
                            item_path,
                            card_id,
                            card_name,
                        )
                    )
                warnings.extend(
                    self._warn_zone_aliases(
                        item,
                        item_path,
                        card_id,
                        card_name,
                    )
                )
        elif isinstance(value, list):
            for index, item in enumerate(value):
                warnings.extend(
                    self._warn_zone_aliases(
                        item,
                        f"{path}[{index}]",
                        card_id,
                        card_name,
                    )
                )

        return warnings

    def _warn_zone_alias_value(
        self,
        value,
        path,
        card_id,
        card_name,
    ):
        warnings = []
        for value_path, item in _iter_scalar_values(value, path):
            if not isinstance(item, str):
                continue
            canonical = ZONE_ALIAS_FIXES.get(item.lower())
            if canonical is None:
                continue
            warnings.append(
                self._warning(
                    card_id,
                    card_name,
                    "W_ZONE_ALIAS",
                    value_path,
                    f"zone alias {item!r} is accepted but inconsistent",
                    f"use canonical zone name {canonical!r}",
                )
            )
        return warnings

    def _warning(
        self,
        card_id,
        card_name,
        code,
        path,
        message,
        possible_fix,
    ):
        return ValidationWarning(
            card_id=card_id,
            card_name=card_name,
            code=code,
            path=path,
            message=message,
            possible_fix=possible_fix,
        )

    def _validate_zone_filter(
        self,
        filter_spec,
        path,
    ):
        if not isinstance(filter_spec, dict):
            return [
                f"{path}: zone filter must be an object"
            ]

        errors = []
        for key, value in filter_spec.items():
            if key not in ZONE_FILTER_FIELDS:
                errors.append(
                    f"{path}.{key}: unknown zone filter key"
                )
                continue
            errors.extend(
                self._validate_comparison_expression(
                    value,
                    f"{path}.{key}",
                )
            )
        return errors

    def _validate_comparison_expression(
        self,
        value,
        path,
    ):
        if isinstance(value, dict) and set(value) == {"ref"}:
            return self._validate_ref_value(value, path)

        if isinstance(value, dict):
            errors = []
            for operator, expected in value.items():
                if operator not in COMPARISON_OPERATORS:
                    errors.append(
                        f"{path}.{operator}: unknown comparison operator"
                    )
                    continue
                errors.extend(
                    self._validate_ref_value(
                        expected,
                        f"{path}.{operator}",
                    )
                )
            return errors

        return []

    def _validate_ref_value(
        self,
        value,
        path,
    ):
        if isinstance(value, dict):
            if "ref" in value:
                if set(value) != {"ref"}:
                    return [
                        f"{path}: ref object must contain only ref"
                    ]
                return self._validate_ref_path(
                    value["ref"],
                    f"{path}.ref",
                )

            errors = []
            for key, item in value.items():
                errors.extend(
                    self._validate_ref_value(
                        item,
                        f"{path}.{key}",
                    )
                )
            return errors

        if isinstance(value, list):
            errors = []
            for index, item in enumerate(value):
                errors.extend(
                    self._validate_ref_value(
                        item,
                        f"{path}[{index}]",
                    )
                )
            return errors

        return []

    def _validate_card_ref_value(
        self,
        value,
        path,
    ):
        if isinstance(value, str):
            if value in (
                "self",
                "source",
                "source_card",
            ):
                return []
            return [
                f"{path}: string references must use {{\"ref\": ...}}"
            ]

        return self._validate_ref_value(
            value,
            path,
        )

    def _validate_player_ref_value(
        self,
        value,
        path,
    ):
        if isinstance(value, str):
            if value in (
                "controller",
                "self",
                "owner",
                "opponent",
            ):
                return []
            return [
                f"{path}: string references must use {{\"ref\": ...}}"
            ]

        return self._validate_ref_value(
            value,
            path,
        )

    def _validate_ref_path(
        self,
        ref,
        path,
    ):
        if not isinstance(ref, str):
            return [
                f"{path}: ref must be a string"
            ]

        parts = ref.split(".")
        if not parts or not all(parts):
            return [
                f"{path}: invalid ref path {ref!r}"
            ]

        if len(parts) == 1:
            if IDENTIFIER_RE.match(parts[0]):
                return []
            return [
                f"{path}: invalid stored ref {ref!r}"
            ]

        root = parts[0]
        if root in ("controller", "opponent"):
            if len(parts) == 3 and parts[1] == "zone_count":
                return []
            # バトルゾーンのクリーチャー数（RefResolver._part_creature_count）。
            if len(parts) == 2 and parts[1] == "creature_count":
                return []
            return [
                f"{path}: invalid player ref {ref!r}"
            ]

        if root == "source":
            if parts[1] in (
                "cost",
                "power",
                "controller",
                "owner",
                "zone",
            ):
                return []
            return [
                f"{path}: invalid source ref {ref!r}"
            ]

        if root == "source_info":
            if parts[1] in (
                "card_id",
                "instance_id",
                "object_id",
                "name",
                "name_ja",
                "effect_name_ja",
                "owner",
                "controller",
                "zone",
                "zone_change_counter",
                "zcc",
                "cost",
                "power",
                "civilization",
                "civilizations",
                "race",
                "races",
                "race_ja",
                "races_ja",
                "card_type",
                "card_types",
                "types",
                "special_types",
                "tapped",
                "shield_face_up",
                "deck_face_up",
                "is_evolution",
                "is_evolution_source",
                "contained_card_count",
                "contained_count",
                "contained_cards",
                "contained_card_snapshots",
                "abilities",
                "ability_id",
                "ability_ids",
                "ability_types",
            ):
                return []
            return [
                f"{path}: invalid source_info ref {ref!r}"
            ]

        if root == "event":
            if parts[1] in (
                "attacker",
                "blocker",
                "card",
                "defender",
                "moved_card",
                "target",
                "player",
                "owner",
                "target_player",
                "shield_card",
                "winner",
                "loser",
                "prompt",
                "evolution_sources",
            ):
                return []
            return [
                f"{path}: invalid event ref {ref!r}"
            ]

        if root == "effect_context":
            if all(
                IDENTIFIER_RE.match(part)
                for part in parts[1:]
            ):
                return []
            return [
                f"{path}: invalid effect_context ref {ref!r}"
            ]

        if root == "replacement":
            if parts[1] == "count":
                return []
            return [
                f"{path}: invalid replacement ref {ref!r}"
            ]

        return [
            f"{path}: unknown ref root {root!r}"
        ]

    def _is_condition_operator(
        self,
        operator,
    ):
        return (
            operator in COMPARISON_OPERATORS
            or operator in SYMBOL_OPERATOR_ALIASES
        )

    def _is_structured_static(
        self,
        spec,
    ):
        return isinstance(spec, dict) and "type" in spec


def _as_list(
    value,
):
    if value is None:
        return []

    if isinstance(value, list):
        return value

    return [value]


def _first_present(
    spec,
    keys,
):
    for key in keys:
        if key in spec:
            return spec[key]

    return None


def _dedupe(
    items,
):
    seen = set()
    result = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def _card_name(
    card,
):
    return (
        card.get("name_ja")
        or card.get("id", "<unknown>")
    )


def _effect_id(
    effect,
):
    return effect.get(
        "effect_id",
        effect.get("id", effect.get("type")),
    )


def _iter_scalar_values(
    value,
    path,
):
    if isinstance(value, list):
        for index, item in enumerate(value):
            yield from _iter_scalar_values(
                item,
                f"{path}[{index}]",
            )
        return

    if isinstance(value, dict):
        if set(value) == {"ref"}:
            yield path, value
            return

        for key, item in value.items():
            yield from _iter_scalar_values(
                item,
                f"{path}.{key}",
            )
        return

    yield path, value
