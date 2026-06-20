"""Shield Force keyword and granted SF abilities."""

from abilities.base.continuous_ability import ContinuousAbility
from abilities.traits.scoped_grant_ability import ScopedGrantAbility
from core.pending_cards import is_card_pending
from zones.zone_type import ZoneType


class ShieldForceAbility(ContinuousAbility):

    def __init__(
        self,
        owner_card,
        game,
        optional=True,
        effects=None,
        label=None,
    ):
        super().__init__()
        self.owner_card = owner_card
        self.game = game
        self.optional = optional
        self.effects = effects or []
        self.label = label
        self.selected_shield = None
        self.selected_shield_zcc = None

    def prepare_to_enter_battle(
        self,
        player,
    ):
        visible_shields = getattr(
            player.shield_zone,
            "visible_shields",
            None,
        )
        shields = (
            visible_shields()
            if visible_shields is not None
            else list(player.shield_zone.cards)
        )
        if not shields:
            return

        shield = (
            self.game.target_selector.select(
                player,
                shields,
                prompt=(
                    "Choose Shield Force shield "
                    f"for {self.owner_card.name}"
                ),
                can_skip=self.optional,
            )
        )
        if shield is None:
            return

        self.selected_shield = shield
        self.selected_shield_zcc = shield.zone_change_counter

    def is_grant_active(
        self,
    ):
        shield = self.selected_shield
        return (
            self.owner_card.zone == ZoneType.BATTLE
            and shield is not None
            and not is_card_pending(shield)
            and shield.zone == ZoneType.SHIELD
            and shield.zone_change_counter == self.selected_shield_zcc
        )


def build_shield_force_granted_abilities(
    owner_card,
    shield_force,
    effects,
):
    abilities = []

    for effect in effects:
        effect_id = effect.get(
            "effect_id",
            effect.get("id"),
        )
        if effect_id != "grant_ability":
            continue

        ability = dict(effect.get("ability", {}))
        if "id" not in ability and "ability_id" in ability:
            ability["id"] = ability["ability_id"]
        if ability.get("id") == "sf_ability":
            ability["id"] = "separation_lock"
            ability["ability_id"] = "separation_lock"

        if "id" not in ability:
            raise ValueError(
                f"Shield Force grant requires ability_id: {effect}"
            )

        abilities.append(
            ScopedGrantAbility(
                owner_card=owner_card,
                game=shield_force.game,
                ability=ability,
                scope=effect.get("scope", "self"),
                active_if=shield_force,
                optional=effect.get(
                    "optional",
                    ability.get("optional", True),
                ),
            )
        )

    return abilities
