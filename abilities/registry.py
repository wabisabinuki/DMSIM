"""Ability ID registry used by card definitions.

New reusable ability words should be registered here so card creation does not
grow a long conditional chain.
"""

from abilities.keywords.blocker_ability import BlockerAbility
from abilities.keywords.breaker_ability import (
    WBreakerAbility,
    TBreakerAbility,
    QBreakerAbility,
    WorldBreakerAbility,
)
from abilities.keywords.power_attacker_ability import (
    build_power_attacker_ability,
)
from abilities.keywords.powered_blocker_ability import (
    build_powered_blocker_ability,
)
from abilities.keywords.battle_power_ability import (
    build_battle_power_ability,
)
from abilities.keywords.battle_or_deck_face_up_infinite_power_ability import (
    build_battle_or_deck_face_up_infinite_power_ability,
)
from abilities.keywords.must_attack_ability import (
    build_must_attack_ability,
)
from abilities.keywords.powered_breaker_ability import PoweredBreakerAbility
from abilities.keywords.evolution_ability import build_evolution_ability
from abilities.keywords.escape_ability import EscapeAbility
from abilities.keywords.final_revolution_ability import (
    build_final_revolution_ability,
    build_extreme_final_revolution_ability,
)
from abilities.keywords.just_diver_ability import JustDiverAbility
from abilities.keywords.g_zero_ability import build_g_zero_ability
from abilities.keywords.g_strike_ability import GStrikeAbility
from abilities.keywords.mach_fighter_ability import MachFighterAbility
from abilities.keywords.ninja_strike_ability import NinjaStrikeAbility
from abilities.keywords.revolution_change_ability import (
    build_revolution_change_ability,
)
from abilities.keywords.revolution_zero_ability import (
    build_revolution_zero_ability,
)
from abilities.keywords.shield_trigger_ability import (
    ConditionalShieldTriggerAbility,
    ShieldTriggerAbility,
)
from abilities.keywords.shield_force_ability import (
    ShieldForceAbility,
    build_shield_force_granted_abilities,
)
from abilities.keywords.shield_saver_ability import ShieldSaverAbility
from abilities.keywords.saber_ability import SaberAbility
from abilities.keywords.attack_chance_ability import (
    build_attack_chance_ability,
)
from abilities.keywords.recycle_ability import (
    build_recycle_ability,
)
from abilities.keywords.slayer_ability import SlayerAbility
from abilities.keywords.guardman_ability import GuardmanAbility
from abilities.keywords.super_guardman_ability import SuperGuardmanAbility
from abilities.keywords.speed_attacker import SpeedAttackerAbility
from abilities.auras.power_per_card_in_zone_ability import (
    build_power_per_card_in_zone_ability,
)
from abilities.auras.power_buff_ability import (
    build_power_buff_ability,
)
from abilities.traits.mana_number_ability import (
    build_mana_number_ability,
)
from abilities.traits.mana_all_civilizations_ability import (
    build_mana_all_civilizations_ability,
)
from abilities.replacements.packaged_replacement_ability import (
    PackagedReplacementAbility,
)
from abilities.replacements.break_this_shield_instead_ability import (
    BreakThisShieldInsteadAbility,
)
from abilities.replacements.eternal_omega_ability import (
    EternalOmegaAbility,
)
from abilities.replacements.super_dimension_redirect_ability import (
    SuperDimensionRedirectAbility,
)
from abilities.traits.cannot_cast_spells_ability import CannotCastSpellsAbility
from abilities.traits.element_entry_lock_ability import (
    ElementEntryLockAbility,
)
from abilities.traits.creature_entry_lock_ability import (
    CreatureEntryLockAbility,
)
from abilities.traits.enter_turn_attack_lock_ability import (
    EnterTurnAttackLockAbility,
)
from abilities.traits.attack_player_lock_ability import (
    AttackPlayerLockAbility,
)
from abilities.traits.alternative_summon_cost_ability import (
    build_alternative_summon_cost_ability,
)
from abilities.traits.attack_lure_ability import (
    AttackLureAbility,
)
from abilities.traits.attack_untapped_ability import (
    AttackUntappedAbility,
)
from abilities.traits.conditional_attack_forbid_ability import (
    ConditionalAttackForbidAbility,
)
from abilities.traits.ignore_own_attack_forbid_ability import (
    IgnoreOwnAttackForbidAbility,
)
from abilities.traits.d_switch_ability import build_d_switch_ability
from abilities.traits.opponent_attack_mandatory_ability import (
    OpponentAttackMandatoryAbility,
)
from abilities.traits.opponent_creature_choice_replacement_ability import (
    OpponentCreatureChoiceReplacementAbility,
)
from abilities.traits.play_from_zone_ability import (
    build_play_from_zone_ability,
)
from abilities.traits.separation_lock_ability import SeparationLockAbility
from abilities.traits.scoped_grant_ability import ScopedGrantAbility
from abilities.traits.graveyard_summon_ability import (
    build_graveyard_summon_ability,
)
from abilities.traits.look_top_deck_ability import LookTopDeckDuringTurnAbility
from abilities.traits.summon_top_deck_creature_ability import (
    build_summon_top_deck_creature_ability,
)
from abilities.traits.soulshift_ability import SoulshiftAbility
from abilities.traits.sympathy_ability import SympathyAbility
from abilities.traits.tap_to_play_ability import TapToPlayAbility
from abilities.traits.unblockable_ability import UnblockableAbility
from abilities.traits.untouchable_ability import UntouchableAbility
from abilities.triggers.draw_on_turn_end import DrawOnTurnEndAbility
from abilities.triggers.draw_on_turn_start import DrawOnTurnStartAbility
from abilities.triggers.generic_triggered_ability import GenericTriggeredAbility
from abilities.triggers.packaged_on_summon import PackagedOnSummonAbility
from abilities.triggers.shield_breaker_ability import ShieldBreakerAbility
from abilities.triggers.z_rush_ability import ZRushAbility
from abilities.cross_gear.cross_gear_abilities import (
    CrossGrantAbility,
    CrossLeaveReplacementAbility,
    CrossOnAllyEnterAbility,
    CrossOnCrossedAttackAbility,
)
from cards.card import Civilization


CIVILIZATION_BITS = {
    "fire": Civilization.FIRE,
    "water": Civilization.WATER,
    "nature": Civilization.NATURE,
    "light": Civilization.LIGHT,
    "darkness": Civilization.DARKNESS,
}


def _simple(cls):
    return lambda spec, card, game: cls()


def _with_card_and_game(cls):
    return lambda spec, card, game: cls(card, game)


def _breaker(cls):
    return lambda spec, card, game: cls(
        active_if=spec.get("active_if")
    )


def _blocker(spec, card, game):
    return BlockerAbility(
        active_if=spec.get("active_if"),
    )


def _world_breaker(spec, card, game):
    return WorldBreakerAbility(
        game=game,
        active_if=spec.get("active_if"),
    )


def _opponent_attack_mandatory(spec, card, game):
    return OpponentAttackMandatoryAbility(
        active_if=spec.get("active_if"),
        scope=spec.get(
            "scope",
            "opponent_creatures",
        ),
    )


def _attack_lure(spec, card, game):
    return AttackLureAbility(
        active_if=spec.get("active_if"),
        scope=spec.get(
            "scope",
            "opponent_creatures",
        ),
    )


def _opponent_creature_choice_replacement(spec, card, game):
    return OpponentCreatureChoiceReplacementAbility(
        owner_card=card,
        game=game,
        affected_player=spec.get(
            "affected_player",
            "opponent",
        ),
        active_if=spec.get("active_if"),
    )


def _eternal_omega(spec, card, game):
    return EternalOmegaAbility(
        owner_card=card,
        game=game,
        label=spec.get("label"),
    )


def _super_dimension_redirect(spec, card, game):
    return SuperDimensionRedirectAbility(
        owner_card=card,
        game=game,
        label=spec.get("label"),
    )


def _separation_lock(spec, card, game):
    return SeparationLockAbility(
        owner_card=card,
        active_if=spec.get("active_if"),
        scope=spec.get(
            "scope",
            "own_creatures",
        ),
    )


def _cannot_cast_spells(spec, card, game):
    cost_comparison = spec.get("cost_comparison")
    cost_limit = spec.get("cost_limit")
    max_cost = spec.get("max_cost")
    exact_cost = spec.get("exact_cost")

    if cost_limit is not None:
        if cost_comparison in (
            None,
            "at_most",
            "less_than_or_equal",
        ):
            max_cost = cost_limit
        elif cost_comparison in (
            "exact",
            "equal",
        ):
            exact_cost = cost_limit
        else:
            raise ValueError(
                f"Unknown cannot_cast_spells cost_comparison: {cost_comparison}"
            )

    return CannotCastSpellsAbility(
        affected_player=spec.get(
            "affected_player",
            "opponent",
        ),
        active_if=spec.get("active_if"),
        max_cost=max_cost,
        exact_cost=exact_cost,
        civilizations=_civilization_bits(
            spec.get(
                "civilizations",
                spec.get("civilization"),
            )
        ),
    )


def _element_entry_lock(spec, card, game):
    return ElementEntryLockAbility(
        owner_card=card,
        affected_player=spec.get("affected_player", "opponent"),
        allow_from_zone=spec.get("allow_from_zone"),
        allow_reason=spec.get("allow_reason"),
        allow_reasons=spec.get("allow_reasons"),
    )


def _creature_entry_lock(spec, card, game):
    allow_from_zones = spec.get("allow_from_zones")
    if allow_from_zones is None and "allow_from_zone" in spec:
        allow_from_zones = spec.get("allow_from_zone")

    return CreatureEntryLockAbility(
        owner_card=card,
        affected_player=spec.get("affected_player", "opponent"),
        allow_from_zones=allow_from_zones,
        block_from_zones=spec.get("block_from_zones"),
        allow_reasons=spec.get("allow_reasons"),
    )


def _enter_turn_attack_lock(spec, card, game):
    return EnterTurnAttackLockAbility(
        game=game,
        active_if=spec.get("active_if"),
        scope=spec.get("scope", "opponent_creatures"),
        filter_spec=spec.get("filter"),
    )


def _attack_player_lock(spec, card, game):
    return AttackPlayerLockAbility(
        game=game,
        active_if=spec.get("active_if"),
        scope=spec.get("scope", "self"),
        filter_spec=spec.get("filter"),
    )


def _tap_to_play(spec, card, game):
    return TapToPlayAbility(
        owner_card=card,
        affected_player=spec.get(
            "affected_player",
            "opponent",
        ),
        zones=spec.get("zones"),
        active_if=spec.get("active_if"),
        tap_required=spec.get(
            "tap_required",
            True,
        ),
        optional=spec.get(
            "optional",
            False,
        ),
        prompt=spec.get("prompt"),
        game=game,
    )


def _sympathy(spec, card, game):
    return SympathyAbility(
        owner_card=card,
        scope=spec.get("scope", "own_creature"),
    )


def _soulshift(spec, card, game):
    return SoulshiftAbility(
        owner_card=card,
        min_cost=spec.get("min_cost", 1),
    )


def _shield_saver(spec, card, game):
    return ShieldSaverAbility(
        owner_card=card,
        game=game,
        optional=spec.get("optional", True),
    )


def _saber(spec, card, game):
    filter_spec = spec.get("filter")
    if filter_spec is None and "race_ja" in spec:
        filter_spec = {
            "race_ja": spec["race_ja"],
        }

    return SaberAbility(
        owner_card=card,
        game=game,
        filter_spec=filter_spec,
        optional=spec.get("optional", True),
    )


def _break_this_shield_instead(spec, card, game):
    return BreakThisShieldInsteadAbility(
        owner_card=card,
        game=game,
        optional=spec.get("optional", True),
        prompt=spec.get("prompt"),
    )


def _grant_ability(spec, card, game):
    ability = _normalize_spec(
        spec.get("ability", {})
    )
    if not isinstance(ability, dict) or "id" not in ability:
        raise ValueError(
            f"grant_ability requires ability_id: {spec}"
        )

    return ScopedGrantAbility(
        owner_card=card,
        game=game,
        ability=ability,
        scope=spec.get("scope", "own_creatures"),
        active_if=spec.get("active_if"),
        active_zone=spec.get("active_zone", "battle"),
        optional=spec.get(
            "optional",
            ability.get("optional", True),
        ),
        filter_spec=spec.get("filter"),
        exclude_source=spec.get("exclude_source", False),
    )


def _enchant_ability(spec, card, game):
    return _grant_ability(
        spec,
        card,
        game,
    )


def _ninja_strike(spec, card, game):
    mana_count = spec.get(
        "mana_count",
        spec.get("count", spec.get("n")),
    )
    if mana_count is None:
        raise ValueError("ninja_strike requires mana_count")

    return NinjaStrikeAbility(
        owner_card=card,
        game=game,
        mana_count=mana_count,
        civilizations=None,
        keyword_name="ninja_strike",
        optional=spec.get("optional", True),
    )


def _ura_ninja_strike(spec, card, game):
    mana_count = spec.get(
        "mana_count",
        spec.get("count", spec.get("n")),
    )
    if mana_count is None:
        raise ValueError("ura_ninja_strike requires mana_count")

    civilizations = _civilization_bits(
        spec.get(
            "civilizations",
            spec.get("civilization"),
        )
    )
    if civilizations is None:
        raise ValueError("ura_ninja_strike requires civilization")

    return NinjaStrikeAbility(
        owner_card=card,
        game=game,
        mana_count=mana_count,
        civilizations=civilizations,
        keyword_name="ura_ninja_strike",
        optional=spec.get("optional", True),
    )


def _civilization_bits(
    values,
):
    if values is None:
        return None

    if isinstance(values, str):
        values = [
            values,
        ]

    bits = 0
    for value in values:
        key = str(value).lower()
        if key not in CIVILIZATION_BITS:
            raise ValueError(
                f"Unknown civilization: {value}"
            )
        bits |= CIVILIZATION_BITS[key]

    return bits


def _ability_bundle(*ability_ids):
    def build(spec, card, game):
        return [
            create_ability(
                ability_id,
                card,
                game,
            )
            for ability_id in ability_ids
        ]

    return build


def _packaged_on_summon(spec, card, game):
    return PackagedOnSummonAbility(
        card,
        game,
        spec.get("effects", []),
        label=spec.get("label"),
    )


def _packaged_on_enter_battle(spec, card, game):
    return _packaged_on_summon(
        spec,
        card,
        game,
    )


def _shield_breaker(spec, card, game):
    return ShieldBreakerAbility(
        card,
        game,
        spec.get("effects", []),
        label=spec.get("label"),
    )


def _shield_force(spec, card, game):
    shield_force = ShieldForceAbility(
        owner_card=card,
        game=game,
        optional=spec.get("optional", True),
        effects=spec.get("effects", []),
        label=spec.get("label"),
    )
    return [
        shield_force,
        *build_shield_force_granted_abilities(
            card,
            shield_force,
            spec.get("effects", []),
        ),
    ]


def _generic_triggered(spec, card, game):
    return GenericTriggeredAbility(
        owner_card=card,
        game=game,
        event=spec["event"],
        condition=spec.get("condition", "self"),
        effects=spec.get("effects", []),
        label=spec.get("label"),
        resolution=spec.get("resolution", "packaged"),
        active_if=spec.get("active_if"),
        active_zones=spec.get("active_zones"),
        ignore_source_continuity=spec.get(
            "ignore_source_continuity",
            False,
        ),
    )


def _replacement_package(spec, card, game):
    return PackagedReplacementAbility(
        owner_card=card,
        game=game,
        event=spec["event"],
        condition=spec.get(
            "condition",
            "breaker_self",
        ),
        replace_effects=spec.get("replace", []),
        finalize_effects=spec.get("finalize", []),
        active_if=spec.get("active_if"),
        cancel_event=spec.get("cancel_event", True),
    )


def _cross_grant(spec, card, game):
    return CrossGrantAbility(
        owner_card=card,
        game=game,
        ability_ids=spec.get(
            "abilities",
            spec.get("ability_ids", []),
        ),
    )


def _cross_on_ally_enter(spec, card, game):
    return CrossOnAllyEnterAbility(
        owner_card=card,
        game=game,
        cross=spec.get("cross"),
        effects=spec.get("effects", []),
        label=spec.get("label"),
    )


def _cross_on_crossed_attack_recross(spec, card, game):
    return CrossOnCrossedAttackAbility(
        owner_card=card,
        game=game,
        label=spec.get("label"),
    )


def _cross_leave_saver(spec, card, game):
    return CrossLeaveReplacementAbility(
        owner_card=card,
        game=game,
        optional=spec.get("optional", True),
    )


def _bolmeteus_shield_burn(spec, card, game):
    package_spec = {
        "event": "shield_break_attempt",
        "condition": "breaker_self",
        "active_if": spec.get("active_if"),
        "replace": [
            {
                "id": "put_attempt_shield_on_bottom",
            }
        ],
        "finalize": [
            {
                "id": "draw_each_player",
                "amount": "replacement_count",
            }
        ],
    }
    return _replacement_package(
        package_spec,
        card,
        game,
    )


def _shield_go(spec, card, game):
    """シールド・ゴー（SG）キーワード。

    2つの能力を返す:
      1. 誘発: このクリーチャーが破壊された時、自分の墓地から表向きでシールド化する。
      2. 置換: このクリーチャーが表向きでシールドゾーンを離れる時、かわりに墓地に置く。
    """
    from abilities.v2.json_replacement_ability import JsonReplacementAbility

    destroy_to_shield = create_ability(
        {
            "id": "triggered",
            "event": "destroy",
            "condition": "self",
            "active_zones": "any",
            "ignore_source_continuity": True,
            "label": "シールド・ゴー：破壊された時、自分の墓地から表向きでシールド化する",
            "effects": [
                {
                    "effect_id": "move_card",
                    "from_zone": "graveyard",
                    "to_zone": "shield",
                    "selection": "source_card",
                    "shield_face": "face_up",
                    "optional": False,
                }
            ],
        },
        card,
        game,
    )

    leave_shield_to_graveyard = JsonReplacementAbility(
        card,
        game,
        {
            "ability_id": "shield_go_leave_replacement",
            "type": "zone_change",
            "active_zones": ["shield"],
            "attempt": {
                "event": "zone_change_attempt",
                "from_zone": "shield",
                "card": {
                    "ref": "source",
                },
            },
            "condition": {
                "type": "card_state",
                "card": "source",
                "state": "shield_face_up",
                "value": True,
            },
            "replace_with": {
                "to_zone": "graveyard",
            },
        },
    )

    return [
        destroy_to_shield,
        leave_shield_to_graveyard,
    ]


ABILITY_BUILDERS = {
    "blocker": _blocker,
    "shield_go": _shield_go,
    "alternative_summon_cost": (
        lambda spec, card, game: build_alternative_summon_cost_ability(
            spec,
            card,
        )
    ),
    "attack_chance": build_attack_chance_ability,
    "recycle": build_recycle_ability,
    "attack_player_lock": _attack_player_lock,
    "attack_untapped": lambda spec, card, game: AttackUntappedAbility(
        owner_card=card,
        game=game,
        active_if=spec.get("active_if"),
    ),
    "conditional_attack_forbid": (
        lambda spec, card, game: ConditionalAttackForbidAbility(
            owner_card=card,
            game=game,
            condition=spec.get("condition"),
        )
    ),
    "bolmeteus_shield_burn": _bolmeteus_shield_burn,
    "break_this_shield_instead": _break_this_shield_instead,
    "cannot_cast_spells": _cannot_cast_spells,
    "cross_grant": _cross_grant,
    "cross_on_ally_enter": _cross_on_ally_enter,
    "cross_on_crossed_attack_recross": _cross_on_crossed_attack_recross,
    "cross_leave_saver": _cross_leave_saver,
    "d_switch": build_d_switch_ability,
    "double_breaker": _breaker(WBreakerAbility),
    "draw_on_turn_end": _with_card_and_game(DrawOnTurnEndAbility),
    "draw_on_turn_start": _with_card_and_game(DrawOnTurnStartAbility),
    "element_entry_lock": _element_entry_lock,
    "creature_entry_lock": _creature_entry_lock,
    "enter_turn_attack_lock": _enter_turn_attack_lock,
    "enchant_ability": _enchant_ability,
    "evolution": lambda spec, card, game: build_evolution_ability(
        spec,
        card,
    ),
    "final_revolution": build_final_revolution_ability,
    "extreme_final_revolution": build_extreme_final_revolution_ability,
    "g_strike": _with_card_and_game(GStrikeAbility),
    "g_zero": build_g_zero_ability,
    "graveyard_summon": build_graveyard_summon_ability,
    "look_top_of_deck": lambda spec, card, game: LookTopDeckDuringTurnAbility(card),
    "summon_top_deck_creature": build_summon_top_deck_creature_ability,
    "escape": _with_card_and_game(EscapeAbility),
    "eternal_omega": _eternal_omega,
    "super_dimension_redirect": _super_dimension_redirect,
    "hand_evolution": lambda spec, card, game: build_evolution_ability(
        {
            **spec,
            "source_zone": "hand",
        },
        card,
    ),
    "mana_evolution": lambda spec, card, game: build_evolution_ability(
        {
            **spec,
            "source_zone": "mana",
        },
        card,
    ),
    "mach_fighter": _simple(MachFighterAbility),
    "mana_all_civilizations": build_mana_all_civilizations_ability,
    "mana_number": build_mana_number_ability,
    "power_attacker": build_power_attacker_ability,
    "powered_blocker": build_powered_blocker_ability,
    "battle_power": build_battle_power_ability,
    "battle_or_deck_face_up_infinite_power": (
        build_battle_or_deck_face_up_infinite_power_ability
    ),
    "must_attack": build_must_attack_ability,
    "ninja_strike": _ninja_strike,
    "just_diver": _with_card_and_game(JustDiverAbility),
    "grant_ability": _grant_ability,
    "attack_lure": _attack_lure,
    "opponent_attack_mandatory": _opponent_attack_mandatory,
    "opponent_creature_choice_replacement": (
        _opponent_creature_choice_replacement
    ),
    "packaged_on_enter_battle": _packaged_on_enter_battle,
    "packaged_on_summon": _packaged_on_summon,
    "play_from_zone": build_play_from_zone_ability,
    "power_buff": build_power_buff_ability,
    "power_per_card_in_zone": build_power_per_card_in_zone_ability,
    "powered_breaker": lambda spec, card, game: PoweredBreakerAbility(
        active_if=spec.get("active_if")
    ),
    "q_breaker": _breaker(QBreakerAbility),
    "quad_breaker": _breaker(QBreakerAbility),
    "quadruple_breaker": _breaker(QBreakerAbility),
    "quatro_breaker": _breaker(QBreakerAbility),
    "replacement_package": _replacement_package,
    "revolution_change": build_revolution_change_ability,
    "revolution_zero": build_revolution_zero_ability,
    "saber": _saber,
    "shield_trigger": _with_card_and_game(ShieldTriggerAbility),
    "conditional_shield_trigger": lambda spec, card, game: ConditionalShieldTriggerAbility(
        card, game, condition=spec.get("condition")
    ),
    "shield_saver": _shield_saver,
    "shield_breaker": _shield_breaker,
    "shield_force": _shield_force,
    "separation_lock": _separation_lock,
    "slayer": _simple(SlayerAbility),
    "soulshift": _soulshift,
    "guardman": lambda spec, card, game: GuardmanAbility(
        active_if=spec.get("active_if"),
    ),
    "ignore_own_attack_forbid": _simple(IgnoreOwnAttackForbidAbility),
    "super_guardman": lambda spec, card, game: SuperGuardmanAbility(
        owner_card=card,
        game=game,
        active_if=spec.get("active_if"),
    ),
    "speed_attacker": _simple(SpeedAttackerAbility),
    "sympathy": _sympathy,
    "tap_to_play": _tap_to_play,
    "t_breaker": _breaker(TBreakerAbility),
    "triple_breaker": _breaker(TBreakerAbility),
    "triple_breaker_hyper": lambda spec, card, game: TBreakerAbility(
        active_if="hyper_mode"
    ),
    "triggered": _generic_triggered,
    "unblockable": lambda spec, card, game: UnblockableAbility(
        condition=spec.get("condition")
    ),
    "unblockable and untouchable": _ability_bundle(
        "unblockable",
        "untouchable",
    ),
    "untouchable": _simple(UntouchableAbility),
    "ura_ninja_strike": _ura_ninja_strike,
    "w_breaker": _breaker(WBreakerAbility),
    "world_breaker": _world_breaker,
    "z_rush": _with_card_and_game(ZRushAbility),
}


ABILITY_METADATA = {
    "z_rush": {
        "keyword_name_ja": "Zラッシュ",
        "reminder_text_ja": (
            "シールドが離れたら、次の自分のターンのはじめまで、"
            "このクリーチャーのハイパーモードを解放する"
        ),
    },
    "ninja_strike": {
        "keyword_name_ja": "ニンジャ・ストライク",
    },
    "ura_ninja_strike": {
        "keyword_name_ja": "ウラ・ニンジャ・ストライク",
    },
    "g_strike": {
        "keyword_name_ja": "G・ストライク",
    },
    "d_switch": {
        "keyword_name_ja": "Dスイッチ",
        "reminder_text_ja": (
            "指定のタイミングで、このD2フィールドをゲーム中で1度上下逆さまに"
            "してもよい。そうしたら、後続の効果を使う"
        ),
    },
    "soulshift": {
        "keyword_name_ja": "ソウルシフト",
        "reminder_text_ja": (
            "このクリーチャーの召喚コストを進化元のコストの数だけ少なくする。"
            "ただしコストは0以下にならない"
        ),
    },
    "shield_go": {
        "keyword_name_ja": "シールド・ゴー",
        "reminder_text_ja": (
            "このクリーチャーが破壊された時、自分の墓地から表向きでシールド化する。"
            "このクリーチャーが表向きでシールドゾーンを離れる時、かわりに墓地に置く"
        ),
    },
    "slayer": {
        "keyword_name_ja": "スレイヤー",
        "reminder_text_ja": (
            "「スレイヤー」を持つクリーチャーがバトルする時、"
            "バトルの後、相手のクリーチャーを破壊する"
        ),
    },
    "guardman": {
        "keyword_name_ja": "ガードマン",
        "reminder_text_ja": (
            "このクリーチャーをタップして、相手クリーチャーの攻撃先を、"
            "自分の他のクリーチャーからこのクリーチャーに変更してもよい"
        ),
    },
    "super_guardman": {
        "keyword_name_ja": "スーパーガードマン",
        "reminder_text_ja": (
            "自分の他のクリーチャーがバトルする時、"
            "かわりにこのクリーチャーをタップしてバトルさせてもよい"
        ),
    },
    "attack_chance": {
        "keyword_name_ja": "アタック・チャンス",
        "reminder_text_ja": (
            "自分の指定のクリーチャーが攻撃する時、"
            "このカードをコストを支払わずに実行してもよい"
        ),
    },
    "recycle": {
        "keyword_name_ja": "リサイクル",
        "reminder_text_ja": (
            "この呪文を自分の墓地からリサイクルコストを支払って唱えてもよい。"
            "こうして唱えた後、墓地のかわりに山札の下に置く"
        ),
    },
    "g_zero": {
        "keyword_name_ja": "G・ゼロ",
    },
    "revolution_change": {
        "keyword_name_ja": "革命チェンジ",
    },
    "eternal_omega": {
        "keyword_name_ja": "エターナル・Ω",
        "reminder_text_ja": (
            "このクリーチャーが離れる時、かわりに手札に戻す"
        ),
    },
    "revolution_zero": {
        "keyword_name_ja": "革命0トリガー",
    },
    "final_revolution": {
        "keyword_name_ja": "ファイナル革命",
        "reminder_text_ja": (
            "このクリーチャーが「革命チェンジ」によって出た時、そのターンに"
            "他の「ファイナル革命」を使っていなければ、その効果を使う"
        ),
    },
    "extreme_final_revolution": {
        "keyword_name_ja": "極限ファイナル革命",
        "reminder_text_ja": (
            "このクリーチャーが出た時、このゲーム中に他の「ファイナル革命」を"
            "使っていなければ、その効果を使う"
        ),
    },
    "graveyard_summon": {
        "keyword_name_ja": "墓地召喚",
    },
}


def create_ability(
    ability_spec,
    card,
    game,
):
    spec = _normalize_spec(ability_spec)
    ability_id = spec["id"]

    if ability_id not in ABILITY_BUILDERS:
        raise ValueError(f"Unknown ability id: {ability_id}")

    ability = ABILITY_BUILDERS[ability_id](
        spec,
        card,
        game,
    )
    _attach_metadata(
        ability,
        ability_id,
    )
    return ability


def _normalize_spec(ability_spec):
    if isinstance(ability_spec, dict):
        spec = dict(ability_spec)
        if "id" not in spec and "ability_id" in spec:
            spec["id"] = spec["ability_id"]
        return spec

    return {
        "id": ability_spec,
    }


def _attach_metadata(
    ability,
    ability_id,
):

    if isinstance(ability, list):
        for item in ability:
            _attach_metadata(
                item,
                getattr(
                    item,
                    "ability_id",
                    ability_id,
                ),
            )
        return

    ability.ability_id = ability_id
    metadata = ABILITY_METADATA.get(
        ability_id,
        {},
    )

    for key, value in metadata.items():
        setattr(
            ability,
            key,
            value,
        )
