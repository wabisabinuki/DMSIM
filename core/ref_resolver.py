"""Resolve explicit ``{"ref": "..."}`` values for ability DSL evaluators."""

from core.card_snapshot import EffectSource
from core.pending_cards import visible_cards
from core.seal_utils import is_ignored_by_seal
from effects.zones.zone_effect_utils import parse_zone


class RefResolver:
    """Resolve approved dynamic references without using Python eval."""

    EVENT_ALIASES = {
        "moved_card": "card",
    }

    ROOT_RESOLVERS = {
        "controller": "_root_controller",
        "self": "_root_controller",
        "owner": "_root_controller",
        "opponent": "_root_opponent",
        "source": "_root_source",
        "event": "_root_event",
        "effect_context": "_root_effect_context",
        "source_info": "_root_source_info",
    }

    PART_RESOLVERS = {
        "count": "_part_count",
        "cost": "_part_cost",
        "power": "_part_power",
        "controller": "_part_controller",
        "owner": "_part_owner",
        "zone": "_part_zone",
        "state": "_part_state",
        "creature_count": "_part_creature_count",
    }

    def __init__(
        self,
        game,
    ):
        self.game = game

    def resolve(
        self,
        value,
        context=None,
    ):
        context = context or {}

        if isinstance(value, dict) and set(value) == {"ref"}:
            return self.resolve_ref(
                value["ref"],
                context,
            )

        if isinstance(value, dict) and value.get("from") == "source_info":
            property_name = value.get(
                "property",
                value.get("field"),
            )
            if property_name is None:
                return self._root_source_info(
                    context
                )
            return self.resolve_ref(
                f"source_info.{property_name}",
                context,
            )

        return value

    def resolve_ref(
        self,
        ref,
        context=None,
    ):
        if not isinstance(ref, str):
            raise ValueError(
                f"ref must be a string: {ref!r}"
            )

        context = context or {}
        package_context = context.get("package_context") or {}
        if ref in package_context:
            return package_context.get(ref)

        effect_context = context.get("effect_context")
        effect_value = self._effect_context_get(
            effect_context,
            ref,
            missing=None,
        )
        if effect_value is not None:
            return effect_value

        parts = ref.split(".")
        if not parts or not all(parts):
            raise ValueError(
                f"Invalid ref path: {ref}"
            )

        current = self._resolve_root(
            parts[0],
            context,
        )
        index = 1
        while index < len(parts):
            part = parts[index]

            if part == "zone_count":
                if index + 1 >= len(parts):
                    raise ValueError(
                        f"zone_count ref requires a zone: {ref}"
                    )
                current = self._zone_count(
                    current,
                    parts[index + 1],
                )
                index += 2
                continue

            current = self._resolve_part(
                current,
                part,
                context,
                full_ref=ref,
            )
            index += 1

        return current

    def _resolve_root(
        self,
        root,
        context,
    ):
        handler_name = self.ROOT_RESOLVERS.get(root)
        if handler_name is not None:
            return getattr(self, handler_name)(context)

        package_context = context.get("package_context") or {}
        if root in package_context:
            return package_context[root]

        if root in context:
            return context[root]

        effect_value = self._effect_context_get(
            context.get("effect_context"),
            root,
            missing=None,
        )
        if effect_value is not None:
            return effect_value

        raise ValueError(
            f"Unknown ref root: {root}"
        )

    def _resolve_part(
        self,
        current,
        part,
        context,
        full_ref,
    ):
        if current is None:
            return None

        if self._is_source_info_value(current):
            return current.get_property(part)

        handler_name = self.PART_RESOLVERS.get(part)
        if handler_name is not None:
            return getattr(self, handler_name)(
                current,
                context,
            )

        if isinstance(current, dict):
            if part not in current:
                raise ValueError(
                    f"Unknown ref path: {full_ref}"
                )
            return current[part]

        effect_value = self._effect_context_get(
            current,
            part,
            missing=None,
        )
        if effect_value is not None:
            return effect_value

        if self._looks_like_event(current):
            attr = self.EVENT_ALIASES.get(
                part,
                part,
            )
            return getattr(
                current,
                attr,
                None,
            )

        raise ValueError(
            f"Unknown ref path: {full_ref}"
        )

    def _root_controller(
        self,
        context,
    ):
        return self._controller(context)

    def _root_opponent(
        self,
        context,
    ):
        return self._opponent(
            self._controller(context)
        )

    def _root_source(
        self,
        context,
    ):
        return context.get("source_card")

    def _root_source_info(
        self,
        context,
    ):
        source_info = context.get("source_info")
        if source_info is not None:
            return source_info

        package_context = context.get("package_context") or {}
        source_info = package_context.get("source_info")
        if source_info is not None:
            return source_info

        effect_context = context.get("effect_context")
        source_info = self._effect_context_get(
            effect_context,
            "source_info",
            missing=None,
        )
        if source_info is not None:
            return source_info

        source_card = context.get("source_card")
        if source_card is None:
            return None

        return EffectSource(
            source_card,
            game=self.game,
            player=self._controller(context),
        )

    def _root_event(
        self,
        context,
    ):
        return context.get("event")

    def _root_effect_context(
        self,
        context,
    ):
        return context.get("effect_context")

    def _part_count(
        self,
        current,
        context,
    ):
        return self._count(current)

    def _part_cost(
        self,
        current,
        context,
    ):
        source_info = self._source_info_for_card(
            current,
            context,
        )
        if source_info is not None:
            return source_info.get_property("cost")

        return self._card_cost(current, context)

    def _part_power(
        self,
        current,
        context,
    ):
        source_info = self._source_info_for_card(
            current,
            context,
        )
        if source_info is not None:
            return source_info.get_property("power")

        return self._card_power(current)

    def _part_controller(
        self,
        current,
        context,
    ):
        if self._is_source_info_value(current):
            return current.get_property("controller")

        return getattr(
            current,
            "owner",
            None,
        )

    def _part_owner(
        self,
        current,
        context,
    ):
        if self._is_source_info_value(current):
            return current.get_property("owner")

        return getattr(
            current,
            "owner",
            None,
        )

    def _part_creature_count(
        self,
        current,
        context,
    ):
        if current is None:
            return 0

        query = getattr(self.game, "query", None)
        if query is None:
            return 0

        return len(query.get_creatures(controller=current))

    def _part_zone(
        self,
        current,
        context,
    ):
        if self._is_source_info_value(current):
            return current.get_property("zone")

        return self._zone_name(
            getattr(current, "zone", current)
        )

    def _part_state(
        self,
        current,
        context,
    ):
        return current

    def _controller(
        self,
        context,
    ):
        if context.get("controller") is not None:
            return context["controller"]

        if context.get("player") is not None:
            return context["player"]

        source_card = context.get("source_card")
        return getattr(
            source_card,
            "owner",
            None,
        )

    def _opponent(
        self,
        player,
    ):
        if player is None:
            return None

        query = getattr(
            self.game,
            "query",
            None,
        )
        if query is not None:
            return query.get_opponent(player)

        state = getattr(
            self.game,
            "state",
            None,
        )
        players = getattr(
            state,
            "players",
            (),
        )
        for candidate in players:
            if candidate is not player:
                return candidate

        return None

    def _zone_count(
        self,
        player,
        zone,
    ):
        if player is None:
            return 0

        zone_type = parse_zone(zone)
        player_zone = player.get_zone(zone_type)
        shield_count = getattr(
            player_zone,
            "shield_count",
            None,
        )
        if shield_count is not None:
            return shield_count()

        return len(
            [
                card
                for card in visible_cards(
                    player_zone.cards
                )
                if not is_ignored_by_seal(card)
            ]
        )

    def _count(
        self,
        value,
    ):
        if value is None:
            return 0

        if hasattr(value, "cards"):
            shield_count = getattr(
                value,
                "shield_count",
                None,
            )
            if shield_count is not None:
                return shield_count()

            return len(
                [
                    card
                    for card in visible_cards(value.cards)
                    if not is_ignored_by_seal(card)
                ]
            )

        try:
            return len(value)
        except TypeError:
            raise ValueError(
                f"Cannot count value: {value!r}"
            )

    def _card_cost(
        self,
        card,
        context,
    ):
        get_current_cost = getattr(
            card,
            "get_current_cost",
            None,
        )
        if get_current_cost is not None:
            for kwargs in (
                {
                    "player": self._controller(context),
                    "game": self.game,
                },
                {
                    "player": self._controller(context),
                },
                {},
            ):
                try:
                    return get_current_cost(**kwargs)
                except TypeError:
                    continue
                except ValueError:
                    break

        return getattr(
            card,
            "cost",
            None,
        )

    def _card_power(
        self,
        card,
    ):
        get_current_power = getattr(
            card,
            "get_current_power",
            None,
        )
        if get_current_power is not None:
            return get_current_power()

        return getattr(
            card,
            "base_power",
            0,
        )

    def _zone_name(
        self,
        zone,
    ):
        if zone is None:
            return None

        parsed = parse_zone(zone)
        return parsed.name.lower()

    def _effect_context_get(
        self,
        effect_context,
        key,
        missing=None,
    ):
        if effect_context is None:
            return missing

        getter = getattr(
            effect_context,
            "get",
            None,
        )
        if getter is not None:
            return getter(
                key,
                missing,
            )

        if isinstance(effect_context, dict):
            return effect_context.get(
                key,
                missing,
            )

        return missing

    def _looks_like_event(
        self,
        value,
    ):
        return any(
            hasattr(value, field)
            for field in (
                "attacker",
                "blocker",
                "card",
                "target",
                "player",
                "owner",
            )
        )

    def _is_source_info_value(
        self,
        value,
    ):
        return hasattr(
            value,
            "get_property",
        ) and (
            hasattr(value, "snapshot")
            or value.__class__.__name__ == "CardInfoSnapshot"
        )

    def _source_info_for_card(
        self,
        card,
        context,
    ):
        source_info = context.get("source_info")
        if source_info is None:
            package_context = context.get("package_context") or {}
            source_info = package_context.get("source_info")

        if source_info is None:
            return None

        live_card = getattr(
            source_info,
            "live_card",
            None,
        )
        if live_card is card:
            return source_info

        return None
