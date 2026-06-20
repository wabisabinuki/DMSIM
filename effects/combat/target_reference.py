"""Helpers for resolving effect targets from package context."""

from core.pending_cards import is_card_pending


def resolve_target_reference(
    target,
    package_context,
):
    if isinstance(
        target,
        dict,
    ):
        if set(target) == {"ref"}:
            target = package_context.get(
                target["ref"]
            )
        elif target.get("from") == "stored":
            target = package_context.get(
                target["key"]
            )

    if is_card_pending(target):
        return None

    return target
