"""Parser and lightweight validation for the structured ability JSON shape."""

from abilities.v2.event_map import EVENT_TYPES, event_name
from abilities.v2.spec_schema import (
    ABILITY_GROUP_ALIASES,
    COMPOSITE_TRIGGER_KEYS,
    EVENT_KEYS,
    REPLACEMENT_ATTEMPT_KEYS,
    TIMING_KEYS,
    TRIGGER_KEYS,
    composite_sub_triggers,
    is_composite_trigger,
)
from abilities.v2.timing_matcher import STEP_NAMES, ZONE_NAMES
from core.condition_registry import CONDITION_TYPES


STATIC_TYPES = frozenset(
    (
        "attack_rule",
        "block_rule",
        "break_modifier",
        "cast_rule",
        "choice_replacement",
        "cost_modifier",
        "cost_payment_rule",
        "cross_rule",
        "enter_battle_rule",
        "grant_rule",
        "mana_rule",
        "power_modifier",
        "summon_rule",
        "target_rule",
    )
)

EFFECT_TYPES = frozenset(
    (
        "draw",
        "discard",
        "move",
        "destroy",
        "tap",
        "untap",
        "select",
        "choose_number",
        "execute",
        "modify_power",
        "temporary_combat_restriction",
        "battle",
        "if",
        "choice",
        "alternative_effect",
    )
)

NESTED_CONDITION_FIELDS = {
    "not": (
        "condition",
    ),
}

# 構造化された triggered / replacement のうち、registry 実装へ橋渡しする型。
# これらは標準の trigger / attempt キーを持たず、rule.kind で機構を指定する。
TRIGGERED_BRIDGE_TYPES = frozenset(
    (
        "cross_trigger",
    )
)

REPLACEMENT_BRIDGE_TYPES = frozenset(
    (
        "cross_replacement",
        "shield_break_redirect",
    )
)


class V2AbilityParser:
    """Validate and normalize the structured v2 ability-group keys."""

    GROUP_VALIDATORS = {
        "static": "_validate_static",
        "triggered": "_validate_triggered",
        "activated": "_validate_activated",
        "replacement": "_validate_replacement",
    }

    def parse_group(
        self,
        ability_group,
    ):
        if ability_group is None:
            return self._empty_group()

        # 「能力なし」を空リストで表すカード定義は許容する。旧形式の能力リスト
        # （非空リスト）は v2 グループ形式へ移行済みのため拒否する。
        if isinstance(
            ability_group,
            list,
        ):
            if ability_group:
                raise ValueError(
                    "abilities must be a v2 ability group object, "
                    "not a legacy ability list"
                )
            return self._empty_group()

        if not isinstance(
            ability_group,
            dict,
        ):
            raise ValueError(
                "abilities must be a v2 ability group object"
            )

        parsed = self._empty_group()
        for group, aliases in ABILITY_GROUP_ALIASES.items():
            for alias in aliases:
                parsed[group].extend(
                    _as_list(
                        ability_group.get(alias)
                    )
                )

        self._validate_group(parsed)
        return parsed

    def _empty_group(
        self,
    ):
        return {
            "keyword": [],
            "static": [],
            "triggered": [],
            "activated": [],
            "replacement": [],
        }

    def _validate_group(
        self,
        parsed,
    ):
        for group, validator_name in self.GROUP_VALIDATORS.items():
            validator = getattr(self, validator_name)
            for spec in parsed[group]:
                validator(spec)

    def _validate_static(
        self,
        spec,
    ):
        self._require_object(
            spec,
            "static ability",
        )
        spec_type = spec.get("type")
        if spec_type not in STATIC_TYPES:
            raise ValueError(
                f"Unknown v2 static ability type: {spec_type}"
            )
        self._validate_condition(
            spec.get("condition")
        )
        self._validate_condition(
            spec.get("active_if")
        )

    def _validate_triggered(
        self,
        spec,
    ):
        self._require_object(
            spec,
            "triggered ability",
        )
        if spec.get("type") in TRIGGERED_BRIDGE_TYPES:
            self._validate_effects(
                spec.get("rule", {}).get("effects", [])
            )
            return

        if "trigger" not in spec:
            raise ValueError(
                f"triggered ability requires trigger: {spec}"
            )
        self._validate_event_spec(
            spec.get("trigger"),
            "trigger",
            allowed_keys=TRIGGER_KEYS,
            allow_composite=True,
        )
        self._validate_condition(
            spec.get("condition")
        )
        self._validate_condition(
            spec.get("active_if")
        )
        self._validate_bool_key(
            spec,
            "requires_trigger_declaration",
            "triggered ability",
        )
        self._validate_bool_key(
            spec,
            "trigger_declaration_optional",
            "triggered ability",
        )
        self._validate_effects(
            spec.get("effects", [])
        )

    def _validate_activated(
        self,
        spec,
    ):
        self._require_object(
            spec,
            "activated ability",
        )
        if "timing" not in spec:
            raise ValueError(
                f"activated ability requires timing: {spec}"
            )
        self._validate_key_set(
            spec.get("timing"),
            "timing",
            TIMING_KEYS,
        )
        self._validate_timing_values(
            spec.get("timing"),
        )
        self._validate_condition(
            spec.get("condition")
        )
        self._validate_condition(
            spec.get("active_if")
        )
        self._validate_effects(
            spec.get("effects", [])
        )

    def _validate_replacement(
        self,
        spec,
    ):
        self._require_object(
            spec,
            "replacement ability",
        )
        if spec.get("type") in REPLACEMENT_BRIDGE_TYPES:
            return

        # registry 実装の置換能力（キーワードと同様に ability_id で指定し、
        # 宣言的な attempt を持たない）。構造検証は registry 側に委ねる。
        if "attempt" not in spec and (
            "ability_id" in spec or "id" in spec
        ):
            return

        if "attempt" not in spec:
            raise ValueError(
                f"replacement ability requires attempt: {spec}"
            )
        self._validate_event_spec(
            spec.get("attempt"),
            "attempt",
            allowed_keys=REPLACEMENT_ATTEMPT_KEYS,
        )
        self._validate_condition(
            spec.get("condition")
        )
        self._validate_condition(
            spec.get("active_if")
        )

        replace_with = spec.get("replace_with", {})
        if isinstance(
            replace_with,
            dict,
        ):
            self._validate_effects(
                replace_with.get("effects", [])
            )

        after_batch = spec.get(
            "after_replacement_batch",
            spec.get("after_replacements", {}),
        )
        if isinstance(after_batch, dict):
            self._validate_effects(
                after_batch.get("effects", [])
            )

    def _validate_condition(
        self,
        condition,
    ):
        if condition is None:
            return

        if isinstance(condition, str):
            raise ValueError(
                "v2 condition must be an object, not a string"
            )

        if isinstance(
            condition,
            list,
        ):
            for item in condition:
                self._validate_condition(item)
            return

        self._require_object(
            condition,
            "condition",
        )
        condition_type = condition.get("type")
        if condition_type not in CONDITION_TYPES:
            raise ValueError(
                f"Unknown v2 condition type: {condition_type}"
            )

        for key in (
            "conditions",
            "all",
            "any",
        ):
            for item in _as_list(condition.get(key)):
                self._validate_condition(item)

        for key in NESTED_CONDITION_FIELDS.get(condition_type, ()):
            self._validate_condition(
                condition.get(key)
            )

    def _validate_bool_key(
        self,
        spec,
        key,
        label,
    ):

        if key not in spec:
            return

        if isinstance(
            spec[key],
            bool,
        ):
            return

        raise ValueError(
            f"v2 {label} {key} must be a boolean"
        )

    def _validate_effects(
        self,
        effects,
    ):
        for effect in _as_list(effects):
            self._validate_effect(effect)

    def _validate_effect(
        self,
        effect,
    ):
        self._require_object(
            effect,
            "effect",
        )
        if "id" in effect or "effect_id" in effect:
            return

        effect_type = effect.get("type")
        if effect_type not in EFFECT_TYPES:
            raise ValueError(
                f"Unknown v2 effect type: {effect_type}"
            )

        for key in (
            "effects",
            "then",
            "else",
            "default",
            "alternative",
            "alternative_effects",
        ):
            self._validate_effects(
                effect.get(key, [])
            )

        for choice in _as_list(effect.get("choices")):
            if isinstance(
                choice,
                dict,
            ):
                self._validate_effects(
                    choice.get("effects", [])
                )

    def _validate_event_spec(
        self,
        spec,
        label,
        allowed_keys,
        allow_composite=False,
    ):
        self._require_object(
            spec,
            label,
        )
        if allow_composite and is_composite_trigger(spec):
            self._validate_composite_event_spec(
                spec,
                label,
                allowed_keys,
            )
            return

        self._validate_key_set(
            spec,
            label,
            allowed_keys,
        )
        value = _first_present(
            spec,
            EVENT_KEYS,
        )
        if value is None:
            raise ValueError(
                f"v2 {label} event is required"
            )

        for item in _as_list(value):
            if event_name(item) not in EVENT_TYPES:
                raise ValueError(
                    f"Unknown v2 {label} event: {item}"
                )

    def _validate_composite_event_spec(
        self,
        spec,
        label,
        allowed_keys,
    ):
        self._validate_key_set(
            spec,
            label,
            COMPOSITE_TRIGGER_KEYS,
        )
        sub_triggers = composite_sub_triggers(spec)
        if not sub_triggers:
            raise ValueError(
                f"v2 {label} composite requires sub-triggers"
            )

        for sub in sub_triggers:
            self._validate_event_spec(
                sub,
                label,
                allowed_keys,
                allow_composite=True,
            )

    def _validate_key_set(
        self,
        spec,
        label,
        allowed_keys,
    ):
        self._require_object(
            spec,
            label,
        )
        unknown = set(spec) - set(allowed_keys)
        if unknown:
            raise ValueError(
                f"Unknown v2 {label} key: {sorted(unknown)[0]}"
            )

    def _validate_timing_values(
        self,
        timing,
    ):
        for key in (
            "active_zone",
            "active_zones",
        ):
            if key in timing:
                self._validate_zone_names(
                    timing[key]
                )

        if "step" in timing and timing["step"] not in STEP_NAMES:
            raise ValueError(
                f"Unknown v2 timing step: {timing['step']}"
            )

    def _validate_zone_names(
        self,
        value,
    ):
        if value == "any":
            return

        for item in _as_list(value):
            if item not in ZONE_NAMES:
                raise ValueError(
                    f"Unknown v2 timing zone: {item}"
                )

    def _require_object(
        self,
        value,
        label,
    ):
        if not isinstance(
            value,
            dict,
        ):
            raise ValueError(
                f"{label} must be an object: {value}"
            )


def _as_list(
    value,
):
    if value is None:
        return []

    if isinstance(
        value,
        list,
    ):
        return list(value)

    return [value]


def _first_present(
    spec,
    keys,
):
    for key in keys:
        if key in spec:
            return spec[key]

    return None
