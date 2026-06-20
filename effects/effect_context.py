"""Shared store for effect results in v2 JSON-authored effect chains."""


class EffectContext:
    """Resolve ``{"ref": "name"}`` values against a package context."""

    def __init__(
        self,
        values=None,
    ):
        self.values = values if values is not None else {}

    @classmethod
    def from_package_context(
        cls,
        package_context,
    ):
        context = package_context.get("__effect_context__")
        if context is None:
            context = cls(package_context)
            package_context["__effect_context__"] = context
        return context

    def store(
        self,
        name,
        value,
    ):
        self.values[name] = value
        return value

    def get(
        self,
        name,
        default=None,
    ):
        return self.values.get(
            name,
            default,
        )

    def resolve(
        self,
        value,
    ):
        if isinstance(
            value,
            dict,
        ):
            if set(value) == {"ref"}:
                return self.get(value["ref"])

            return {
                key: self.resolve(item)
                for key, item in value.items()
            }

        if isinstance(
            value,
            list,
        ):
            return [
                self.resolve(item)
                for item in value
            ]

        return value


def ref_to_stored_spec(
    value,
):
    """Translate v2 refs into the legacy stored-value marker where possible."""

    if isinstance(
        value,
        dict,
    ):
        if set(value) == {"ref"}:
            if (
                isinstance(value["ref"], str)
                and (
                    value["ref"] == "source_info"
                    or value["ref"].startswith("source_info.")
                )
            ):
                return value

            return {
                "from": "stored",
                "key": value["ref"],
            }

        return {
            key: ref_to_stored_spec(item)
            for key, item in value.items()
        }

    if isinstance(
        value,
        list,
    ):
        return [
            ref_to_stored_spec(item)
            for item in value
        ]

    return value
