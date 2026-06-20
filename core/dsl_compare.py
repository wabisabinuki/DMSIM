"""Comparison helpers for structured JSON ability DSL evaluators."""


COMPARISON_OPERATORS = frozenset(
    (
        "eq",
        "ne",
        "lt",
        "lte",
        "gt",
        "gte",
        "contains",
        "not_contains",
        "in",
        "not_in",
    )
)

SYMBOL_OPERATOR_ALIASES = {
    "==": "eq",
    "=": "eq",
    "!=": "ne",
    "<": "lt",
    "<=": "lte",
    ">": "gt",
    ">=": "gte",
}


def normalize_operator(
    operator,
    allow_symbols=False,
):
    if allow_symbols:
        operator = SYMBOL_OPERATOR_ALIASES.get(
            operator,
            operator,
        )

    if operator not in COMPARISON_OPERATORS:
        raise ValueError(
            f"Unknown comparison operator: {operator}"
        )

    return operator


def compare_values(
    actual,
    operator,
    expected,
    allow_symbols=False,
):
    operator = normalize_operator(
        operator,
        allow_symbols=allow_symbols,
    )
    return COMPARISON_HANDLERS[operator](
        actual,
        expected,
    )


def _equals(
    actual,
    expected,
):
    if _is_collection(actual) and not _is_collection(expected):
        return expected in actual

    if _is_collection(actual) and _is_collection(expected):
        return set(actual) == set(expected)

    return actual == expected


def _contains(
    actual,
    expected,
):
    if actual is None:
        return False

    if _is_collection(expected):
        return all(
            item in actual
            for item in expected
        )

    return expected in actual


def _is_in(
    actual,
    expected,
):
    if expected is None:
        return False

    if _is_collection(actual):
        return any(
            item in expected
            for item in actual
        )

    return actual in expected


def _is_collection(
    value,
):
    return isinstance(
        value,
        (list, tuple, set, frozenset),
    )


COMPARISON_HANDLERS = {
    "eq": _equals,
    "ne": lambda actual, expected: not _equals(actual, expected),
    "lt": lambda actual, expected: actual < expected,
    "lte": lambda actual, expected: actual <= expected,
    "gt": lambda actual, expected: actual > expected,
    "gte": lambda actual, expected: actual >= expected,
    "contains": _contains,
    "not_contains": (
        lambda actual, expected: not _contains(actual, expected)
    ),
    "in": _is_in,
    "not_in": lambda actual, expected: not _is_in(actual, expected),
}
