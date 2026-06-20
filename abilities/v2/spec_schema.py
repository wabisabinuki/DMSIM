"""Shared keys and aliases for v2 ability JSON specs."""


def ability_id(spec, default):
    """Return the author-facing identifier for a structured ability spec."""

    return spec.get(
        "ability_id",
        spec.get("id", default),
    )


EVENT_KEYS = (
    "event",
    "type",
)

TRIGGER_EVENT_FIELDS = (
    "card",
    "shield_card",
    "attacker",
    "target",
    "blocker",
)

TRIGGER_SUBJECTS = frozenset(
    (
        "self",
        "any",
        "any_card",
        "controller",
        "own",
        "opponent",
    )
)

TRIGGER_KEYS = frozenset(
    EVENT_KEYS
    + (
        "subject",
        "attacker",
        "target",
        "player",
        "card",
        "filter",
        "from_zone",
        "to_zone",
        "reason",
    )
)

# Composite ("DSL") trigger support: a trigger may combine several leaf
# triggers with a boolean operator instead of describing a single event.
COMPOSITE_TRIGGER_TYPES = frozenset(
    (
        "or",
        "and",
        "not",
    )
)

# Keys that hold the sub-trigger(s) of a composite trigger.
COMPOSITE_TRIGGER_LIST_KEYS = (
    "triggers",
    "conditions",
    "any",
    "all",
)

COMPOSITE_TRIGGER_SINGLE_KEYS = (
    "trigger",
    "condition",
)

COMPOSITE_TRIGGER_KEYS = frozenset(
    ("type",)
    + COMPOSITE_TRIGGER_LIST_KEYS
    + COMPOSITE_TRIGGER_SINGLE_KEYS
)


def is_composite_trigger(trigger):
    """Return True when ``trigger`` is a boolean composition of triggers."""

    if not isinstance(trigger, dict):
        return False

    trigger_type = trigger.get("type")
    return (
        isinstance(trigger_type, str)
        and trigger_type in COMPOSITE_TRIGGER_TYPES
    )


def composite_sub_triggers(trigger):
    """Return the list of sub-triggers held by a composite trigger."""

    for key in COMPOSITE_TRIGGER_LIST_KEYS:
        if key in trigger:
            value = trigger[key]
            return list(value) if isinstance(value, list) else [value]

    for key in COMPOSITE_TRIGGER_SINGLE_KEYS:
        if key in trigger:
            return [trigger[key]]

    return []

TIMING_KEYS = frozenset(
    (
        "active_zone",
        "active_zones",
        "step",
    )
)

REPLACEMENT_ATTEMPT_KEYS = frozenset(
    EVENT_KEYS
    + (
        "breaker",
        "card",
        "card_filter",
        "from_zone",
        "to_zone",
    )
)

TARGET_KEYS = frozenset(
    (
        "id",
        "chooser",
        "from",
        "filter",
        "min",
        "max",
        "optional",
        "prompt",
    )
)

TARGET_FROM_KEYS = frozenset(
    (
        "player",
        "zone",
    )
)

ABILITY_GROUP_ALIASES = {
    "keyword": (
        "keyword",
    ),
    "static": (
        "static",
    ),
    "triggered": (
        "triggered",
    ),
    "activated": (
        "activated",
    ),
    "replacement": (
        "replacement",
    ),
}
