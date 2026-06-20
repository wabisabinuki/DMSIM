"""Public effect exports.

Internal modules are grouped by responsibility, but callers can import common
effect classes directly from this package. Exports are loaded lazily so package
initialization does not pull in cards and create circular imports.
"""

from importlib import import_module


_EXPORTS = {
    "AddHandToShieldEffect": "effects.zones.add_hand_to_shield_effect",
    "AddDeckToShieldEffect": "effects.zones.add_deck_to_shield_effect",
    "AddPowerModifierEffect": "effects.modifiers.add_power_modifier_effect",
    "AddShieldToHandEffect": "effects.zones.add_shield_to_hand_effect",
    "BaseEffect": "effects.base.base_effect",
    "BounceCardEffect": "effects.zones.bounce_card_effect",
    "BounceEffect": "effects.zones.bounce_effect",
    "BreakShieldEffect": "effects.zones.break_shield_effect",
    "ConditionalEffect": "effects.composition.conditional_effect",
    "ContinuousPowerModifierEffect": "effects.modifiers.continuous_power_modifier_effect",
    "CountEffect": "effects.composition.count_effect",
    "DestroyEffect": "effects.zones.dectroy_effect",
    "DiscardEffect": "effects.zones.discard_effect",
    "DrawEffect": "effects.zones.draw_effect",
    "DurationEffect": "effects.base.duration_effect",
    "EnchantEffect": "effects.base.enchant_effect",
    "EffectContext": "effects.effect_context",
    "EffectFactory": "effects.effect_factory",
    "ExecuteCardFromHandEffect": "effects.zones.execute_card_from_hand_effect",
    "ExecuteCardFromZoneEffect": "effects.zones.execute_card_from_zone_effect",
    "ForEachEffect": "effects.composition.for_each_stored_effect",
    "ForEachStoredEffect": "effects.composition.for_each_stored_effect",
    "LookEffect": "effects.composition.look_effect",
    "LookTopChooseToHandEffect": "effects.zones.look_top_choose_to_hand_effect",
    "MillEffect": "effects.zones.mill_effect",
    "MoveCardEffect": "effects.zones.move_card_effect",
    "PackagedEffect": "effects.composition.packaged_effect",
    "PutCreatureFromZoneEffect": "effects.zones.put_creature_from_zone_effect",
    "ReleaseHyperModeEffect": "effects.combat.release_hyper_mode_effect",
    "RevealCardsEffect": "effects.composition.reveal_cards_effect",
    "RevealEffect": "effects.composition.reveal_effect",
    "RevealStoredCardEffect": "effects.zones.reveal_stored_card_effect",
    "ReturnFromGraveyardEffect": "effects.zones.return_from_graveyard_effect",
    "ScopedTemporaryJustDiverEffect": "effects.combat.scoped_temporary_just_diver_effect",
    "SelectThenEffect": "effects.composition.select_then_effect",
    "StoreCardFromZoneEffect": "effects.zones.store_card_from_zone_effect",
    "TemporaryAttackPermissionEffect": "effects.combat.temporary_attack_permission_effect",
    "TemporaryAbilityEffect": "effects.combat.temporary_ability_effect",
    "TemporaryCombatRestrictionEffect": "effects.combat.temporary_combat_restriction_effect",
    "TemporaryJustDiverEffect": "effects.combat.temporary_just_diver_effect",
    "TapEffect": "effects.combat.tap_effect",
    "TemporaryTurnStartFreezeEffect": "effects.combat.temporary_turn_start_freeze_effect",
    "TemporaryUntapLockEffect": "effects.combat.temporary_untap_lock_effect",
    "TimedPowerModifierEffect": "effects.modifiers.timed_power_modifier_effect",
    "TimedPowerMultiplierEffect": "effects.modifiers.timed_power_multiplier_effect",
    "UntapEffect": "effects.combat.untap_effect",
    "UseCardEffect": "effects.zones.use_card_effect",
    "build_effects": "effects.registry",
    "creature_cost": "effects.composition.card_predicates",
    "has_civilization": "effects.composition.card_predicates",
    "is_creature_card": "effects.composition.card_predicates",
    "matches_card_filter": "effects.composition.card_predicates",
}

__all__ = sorted(_EXPORTS)


def __getattr__(name):
    if name not in _EXPORTS:
        raise AttributeError(f"module 'effects' has no attribute {name!r}")

    module = import_module(_EXPORTS[name])
    value = getattr(module, name)
    globals()[name] = value
    return value
