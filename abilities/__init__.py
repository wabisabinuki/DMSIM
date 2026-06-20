"""Public ability exports.

Internal modules are grouped by responsibility, but callers can import common
ability classes directly from this package. Exports are loaded lazily so package
initialization does not pull in effects/cards and create circular imports.
"""

from importlib import import_module


_EXPORTS = {
    "BaseAbility": "abilities.base.base_ability",
    "ActivatedAbility": "abilities.base.activated_ability",
    "BlockerAbility": "abilities.keywords.blocker_ability",
    "CannotCastSpellsAbility": "abilities.traits.cannot_cast_spells_ability",
    "ContinuousAbility": "abilities.base.continuous_ability",
    "DrawOnTurnEndAbility": "abilities.triggers.draw_on_turn_end",
    "DrawOnTurnStartAbility": "abilities.triggers.draw_on_turn_start",
    "EvolutionAbility": "abilities.keywords.evolution_ability",
    "ElementEntryLockAbility": "abilities.traits.element_entry_lock_ability",
    "EscapeAbility": "abilities.keywords.escape_ability",
    "GenericTriggeredAbility": "abilities.triggers.generic_triggered_ability",
    "GZeroAbility": "abilities.keywords.g_zero_ability",
    "GStrikeAbility": "abilities.keywords.g_strike_ability",
    "GlobalPowerAbility": "abilities.auras.global_power_ability",
    "GraveyardSummonAbility": "abilities.traits.graveyard_summon_ability",
    "JustDiverAbility": "abilities.keywords.just_diver_ability",
    "MachFighterAbility": "abilities.keywords.mach_fighter_ability",
    "NinjaStrikeAbility": "abilities.keywords.ninja_strike_ability",
    "PackagedOnSummonAbility": "abilities.triggers.packaged_on_summon",
    "OpponentAttackMandatoryAbility": "abilities.traits.opponent_attack_mandatory_ability",
    "OpponentCreatureChoiceReplacementAbility": "abilities.traits.opponent_creature_choice_replacement_ability",
    "PlayFromZoneAbility": "abilities.traits.play_from_zone_ability",
    "ReplacementAbility": "abilities.base.replacement_ability",
    "ScopedGrantAbility": "abilities.traits.scoped_grant_ability",
    "SeparationLockAbility": "abilities.traits.separation_lock_ability",
    "ShieldSaverAbility": "abilities.keywords.shield_saver_ability",
    "ShieldTriggerAbility": "abilities.keywords.shield_trigger_ability",
    "SympathyAbility": "abilities.traits.sympathy_ability",
    "ShieldBreakerAbility": "abilities.triggers.shield_breaker_ability",
    "SpeedAttackerAbility": "abilities.keywords.speed_attacker",
    "StaticAbility": "abilities.base.static_ability",
    "TBreakerAbility": "abilities.keywords.breaker_ability",
    "TapToPlayAbility": "abilities.traits.tap_to_play_ability",
    "UnblockableAbility": "abilities.traits.unblockable_ability",
    "UntouchableAbility": "abilities.traits.untouchable_ability",
    "TriggeredAbility": "abilities.base.triggered_ability",
    "WBreakerAbility": "abilities.keywords.breaker_ability",
    "WorldBreakerAbility": "abilities.keywords.breaker_ability",
}

__all__ = sorted(_EXPORTS)


def __getattr__(name):
    if name not in _EXPORTS:
        raise AttributeError(f"module 'abilities' has no attribute {name!r}")

    module = import_module(_EXPORTS[name])
    value = getattr(module, name)
    globals()[name] = value
    return value
