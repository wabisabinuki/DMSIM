"""Effect ID registry used by JSON card definitions."""

from effects.composition.conditional_effect import ConditionalEffect
from effects.composition.packaged_effect import PackagedEffect
from effects.composition.select_then_effect import SelectThenEffect
from effects.modifiers.add_power_modifier_effect import AddPowerModifierEffect
from effects.modifiers.timed_power_multiplier_effect import TimedPowerMultiplierEffect
from effects.combat.temporary_combat_restriction_effect import (
    TemporaryCombatRestrictionEffect,
)
from effects.combat.temporary_ability_effect import TemporaryAbilityEffect
from effects.combat.release_hyper_mode_effect import ReleaseHyperModeEffect
from effects.combat.scoped_temporary_just_diver_effect import (
    ScopedTemporaryJustDiverEffect,
)
from effects.combat.tap_effect import TapEffect
from effects.combat.untap_effect import UntapEffect
from effects.combat.temporary_turn_start_freeze_effect import (
    TemporaryTurnStartFreezeEffect,
)
from effects.combat.temporary_untap_lock_effect import (
    TemporaryUntapLockEffect,
)
from effects.cross_gear.cross_gear_effects import (
    OpponentTapsOwnCreatureEffect,
)
from core.effect_argument_resolver import parse_duration_spec
from effects.zones.bounce_effect import BounceEffect
from effects.zones.bounce_card_effect import BounceCardEffect
from effects.zones.add_deck_to_shield_effect import AddDeckToShieldEffect
from effects.zones.add_hand_to_shield_effect import AddHandToShieldEffect
from effects.zones.add_shield_to_hand_effect import AddShieldToHandEffect
from effects.zones.break_shield_effect import BreakShieldEffect
from effects.zones.charger_effect import ChargerEffect
from effects.zones.discard_effect import DiscardEffect
from effects.zones.discard_hand_then_draw_effect import DiscardHandThenDrawEffect
from effects.zones.draw_effect import DrawEffect
from effects.zones.execute_card_from_hand_effect import ExecuteCardFromHandEffect
from effects.zones.execute_card_from_zone_effect import ExecuteCardFromZoneEffect
from effects.zones.look_top_choose_to_hand_effect import LookTopChooseToHandEffect
from effects.zones.look_top_put_creature_to_battle_effect import (
    LookTopPutCreatureToBattleEffect,
)
from effects.composition.count_effect import CountEffect
from effects.composition.count_matching_effect import CountMatchingEffect
from effects.composition.destroy_multiple_effect import DestroyMultipleEffect
from effects.composition.for_each_stored_effect import (
    ForEachEffect,
    ForEachStoredEffect,
)
from effects.composition.gather_matching_effect import GatherMatchingEffect
from effects.composition.look_top_choose_distinct_types_to_hand_effect import (
    LookTopChooseDistinctTypesToHandEffect,
)
from effects.composition.look_top_same_cost_creatures_to_battle_effect import (
    LookTopSameCostCreaturesToBattleEffect,
)
from effects.composition.opponent_choose_own_creature_or_shield_to_mana_effect import (
    OpponentChooseOwnCreatureOrShieldToManaEffect,
)
from effects.composition.look_effect import LookEffect
from effects.composition.repeat_effect import RepeatEffect
from effects.composition.reveal_cards_effect import RevealCardsEffect
from effects.composition.reveal_effect import RevealEffect
from effects.composition.select_n_effect import SelectNEffect
from effects.composition.select_within_total_cost_effect import (
    SelectWithinTotalCostEffect,
)
from effects.composition.select_within_total_power_effect import (
    SelectWithinTotalPowerEffect,
)
from effects.turns.grant_extra_turn_effect import GrantExtraTurnEffect
from effects.zones.mill_effect import MillEffect
from effects.zones.move_card_effect import MoveCardEffect
from effects.zones.put_creature_from_zone_effect import PutCreatureFromZoneEffect
from effects.zones.reveal_stored_card_effect import RevealStoredCardEffect
from effects.zones.return_from_graveyard_effect import ReturnFromGraveyardEffect
from effects.zones.store_card_from_zone_effect import StoreCardFromZoneEffect
from effects.composition.choose_n_effects import ChooseNEffectsEffect
from effects.composition.once_per_turn_effect import OncePerTurnEffect
from effects.composition.mark_final_revolution_used_effect import (
    MarkFinalRevolutionUsedEffect,
)
from effects.composition.look_then_distribute_effect import (
    LookThenDistributeEffect,
)
from effects.composition.summon_within_total_cost_effect import (
    SummonWithinTotalCostEffect,
)
from effects.composition.revive_within_total_cost_sealed_effect import (
    ReviveWithinTotalCostSealedEffect,
)
from effects.composition.cost_execution_lock_effect import (
    CostExecutionLockEffect,
)
from effects.composition.extreme_protection_effects import (
    OpponentEffectSeparationGuard,
    PreventLossEffect,
)
from effects.zones.move_deck_top_effect import MoveDeckTopEffect
from effects.zones.put_creature_from_multi_zone_effect import PutCreatureFromMultiZoneEffect
from effects.combat.battle_two_creatures_effect import BattleTwoCreaturesEffect
from effects.combat.wins_all_battles_effect import WinsAllBattlesEffect
from effects.zones.seal_effect import AttachSealEffect
from effects.combat.power_gachinko_judge_effect import (
    PowerGachinkoJudgeEffect,
)
from effects.fields.flip_d2_field_effect import FlipD2FieldEffect


def build_effects(
    specs,
    game,
    player,
    source_card=None,
):
    effects = []

    for spec in specs:
        spec = _normalize_effect_spec(spec)
        if source_card is not None:
            spec = {
                **spec,
                "source_card": source_card,
            }

        effect_id = spec["id"]

        if effect_id not in EFFECT_BUILDERS:
            raise ValueError(f"Unknown effect id: {effect_id}")

        effect = EFFECT_BUILDERS[effect_id](
            spec,
            game,
            player,
        )
        if effect is not None:
            if (
                spec.get("label")
                and not getattr(effect, "label", None)
            ):
                effect.label = spec["label"]

            effect.package_connector = spec.get(
                "connector",
                spec.get(
                    "package_connector",
                    "after",
                ),
            )
            effects.append(effect)

    return effects


# 同じ概念を表す「共通キー」を正規化（alias → canonical）するための対応表。
# どの effect_id でも同じキーで書けるようにするため、build_effects の入口で
# canonical キーが未設定のときだけ alias の値をコピーする。既存 alias は残すので
# alias を直接読む既存 builder とも互換。canonical が既にあれば上書きしない
# （= 既存の `spec.get(canonical, spec.get(alias))` と同じ優先順位）。
COMMON_KEY_ALIASES = {
    "effect_id": "id",
    "count": "amount",
    "up_to": "max_amount",
    "player": "target_player",
    "source_zone": "from_zone",
    "destination_zone": "to_zone",
    "shield_destination": "shield_placement",
    "stack_on": "shield_stack_on",
    "tap": "tapped",
    "chooser": "selector",
    "package_connector": "connector",
    "position": "from",
}


def _normalize_effect_spec(spec):
    normalized = dict(spec)
    for alias, canonical in COMMON_KEY_ALIASES.items():
        if alias in normalized and canonical not in normalized:
            normalized[canonical] = normalized[alias]
    return normalized


def _draw(spec, game, player):
    return DrawEffect(
        player=player,
        amount=spec.get("amount", 1),
        game=game,
        min_amount=spec.get("min_amount"),
        max_amount=spec.get(
            "max_amount",
            spec.get("up_to"),
        ),
        prompt=spec.get("prompt"),
        optional=spec.get("optional", False),
    )


def _discard(spec, game, player):
    return DiscardEffect(
        player=player,
        amount=spec.get("amount", 1),
        game=game,
        optional=spec.get("optional", False),
        store_as=spec.get("store_as"),
        target_player=spec.get("target_player", "self"),
    )


def _discard_hand_then_draw(spec, game, player):
    return DiscardHandThenDrawEffect(
        player=player,
        draw_amount=spec.get("draw_amount", 3),
        game=game,
        optional=spec.get("optional", True),
        prompt=spec.get("prompt", "Discard your entire hand and draw?"),
    )


def _break_shield(spec, game, player):
    chooser_player = None
    selector = spec.get("selector", spec.get("chooser"))
    if selector == "opponent":
        chooser_player = game.query.get_opponent(player)
    elif selector in (
        None,
        "self",
        "controller",
        "owner",
    ):
        chooser_player = None
    else:
        raise ValueError(f"Unknown break_shield selector: {selector}")

    return BreakShieldEffect(
        player=player,
        game=game,
        amount=spec.get("amount", 1),
        target=spec.get("target", "opponent_shields"),
        optional=spec.get("optional", True),
        chooser_player=chooser_player,
    )


def _creature_break_shield(spec, game, player):
    # クリーチャーが発生源となってシールドをブレイクする汎用効果。
    # breaker（=ブレイクする主体）と exclude（候補から外すカード）を ref で渡す。
    return BreakShieldEffect(
        player=player,
        game=game,
        amount=spec.get("amount", 1),
        target=spec.get("target", "own_shields"),
        optional=spec.get("optional", True),
        breaker=spec.get("breaker", spec.get("card")),
        exclude=spec.get("exclude"),
        prompt=spec.get("prompt", "Choose a shield to break"),
    )


def _add_shield_to_hand(spec, game, player):
    return AddShieldToHandEffect(
        player=player,
        game=game,
        target=spec.get("target", "own_shields"),
        amount=spec.get("amount", spec.get("count", 1)),
        optional=spec.get("optional", True),
        exclude_face_up=spec.get("exclude_face_up", False),
        disable_s_trigger=spec.get("disable_s_trigger", True),
    )


def _add_deck_to_shield(spec, game, player):
    return AddDeckToShieldEffect(
        player=player,
        game=game,
        amount=spec.get("amount", 1),
        optional=spec.get("optional", False),
        face_options=spec.get("face_options"),
        shield_placement=spec.get(
            "shield_placement",
            spec.get("shield_destination", "new"),
        ),
        shield_stack_on=spec.get(
            "shield_stack_on",
            spec.get("stack_on"),
        ),
        store_as=spec.get("store_as"),
    )


def _shield_plus(spec, game, player):
    return AddDeckToShieldEffect(
        player=player,
        game=game,
        amount=spec.get("amount", 1),
        optional=spec.get("optional", True),
        face_options=("face_down",),
        shield_placement="choose_slot",
    )


def _add_hand_to_shield(spec, game, player):
    return AddHandToShieldEffect(
        player=player,
        game=game,
        optional=spec.get("optional", True),
        face_options=spec.get("face_options"),
        shield_placement=spec.get(
            "shield_placement",
            spec.get("shield_destination", "new"),
        ),
    )


def _flip_d2_field(spec, game, player):
    return FlipD2FieldEffect(
        game=game,
        player=player,
        prompt=spec.get("prompt"),
    )


def _packaged(spec, game, player):
    return PackagedEffect(
        build_effects(
            spec.get("effects", []),
            game,
            player,
            source_card=spec.get("source_card"),
        ),
        label=spec.get("label"),
    )


def _look_top_choose_to_hand(spec, game, player):
    return LookTopChooseToHandEffect(
        player=player,
        amount=spec["amount"],
        game=game,
        store_as=spec.get("store_as"),
        optional=spec.get("optional", True),
        filter_spec=_filter_spec(spec),
        prompt=spec.get("prompt"),
    )


def _look_top_put_creature_to_battle(spec, game, player):
    return LookTopPutCreatureToBattleEffect(
        player=player,
        amount=spec.get("amount", spec.get("count", 1)),
        game=game,
        store_as=spec.get("store_as"),
        optional=spec.get("optional", True),
        filter_spec=_filter_spec(spec),
        prompt=spec.get("prompt"),
        summoning_sick=spec.get("summoning_sick", True),
    )


def _look_top_choose_distinct_types_to_hand(spec, game, player):
    return LookTopChooseDistinctTypesToHandEffect(
        player=player,
        amount=spec["amount"],
        game=game,
        optional=spec.get("optional", True),
        prompt=spec.get("prompt"),
    )


def _look_top_same_cost_creatures_to_battle(spec, game, player):
    return LookTopSameCostCreaturesToBattleEffect(
        game=game,
        player=player,
        amount=spec.get("amount", spec.get("count", 3)),
        source_card=spec.get("source_card"),
    )


def _look(spec, game, player):
    return LookEffect(
        game=game,
        player=player,
        zone=spec["zone"],
        amount=spec.get("amount", spec.get("count", 1)),
        target_player=spec.get(
            "target_player",
            spec.get("player", "self"),
        ),
        position=spec.get("from", spec.get("position", "top")),
        store_key=_store_key(spec),
    )


def _execute_card_from_hand(spec, game, player):
    return ExecuteCardFromHandEffect(
        player=player,
        game=game,
        card_type=spec.get("type", "element"),
        max_cost=spec.get("max_cost"),
        filter_spec=_filter_spec(spec),
        optional=spec.get("optional", True),
        prompt=spec.get("prompt"),
        ignore_cost=_ignore_cost(spec),
    )


def _execute_card_from_zone(spec, game, player):
    return ExecuteCardFromZoneEffect(
        player=player,
        game=game,
        from_zone=spec.get(
            "from_zone",
            spec.get("source_zone", "hand"),
        ),
        card_type=spec.get(
            "type",
            spec.get("card_type", "element"),
        ),
        filter_spec=_filter_spec(spec),
        optional=spec.get("optional", True),
        prompt=spec.get("prompt"),
        ignore_cost=_ignore_cost(spec),
        target_player=spec.get(
            "target_player",
            spec.get("player", "self"),
        ),
        selection=spec.get("selection"),
        max_cost=spec.get("max_cost"),
        store_as=spec.get("store_as"),
    )


def _mill(spec, game, player):
    return MillEffect(
        player=player,
        game=game,
        target=spec.get("target", "opponent_deck"),
        amount=spec.get("amount", 1),
        optional=spec.get("optional", False),
    )



def _count_matching(spec, game, player):
    return CountMatchingEffect(
        game=game,
        player=player,
        source=spec["source"],
        filter_spec=spec.get("filter", {}),
        store_as=spec["store_as"],
    )


def _count(spec, game, player):
    return CountEffect(
        game=game,
        player=player,
        source=spec.get("source"),
        condition=spec.get(
            "condition",
            spec.get("filter", {}),
        ),
        count_key=spec.get("count_key", spec.get("store_as")),
        store_key=_store_key(spec),
        zone=spec.get("zone"),
        target_player=spec.get(
            "target_player",
            spec.get("player", "self"),
        ),
    )


def _repeat(spec, game, player):
    inner_effects = build_effects(
        spec.get("effects", []),
        game,
        player,
        source_card=spec.get("source_card"),
    )
    return RepeatEffect(
        effects=inner_effects,
        count_key=spec["count_key"],
    )


def _select_n(spec, game, player):
    return SelectNEffect(
        player=player,
        game=game,
        count_key=spec["count_key"],
        candidates=spec.get("candidates", "opponent_creatures"),
        filter_spec=spec.get("filter", {}),
        store_as=spec["store_as"],
        optional=spec.get("optional", True),
        prompt=spec.get("prompt"),
    )


def _select_within_total_power(spec, game, player):
    return SelectWithinTotalPowerEffect(
        player=player,
        game=game,
        candidates=spec.get("candidates", "opponent_creatures"),
        filter_spec=spec.get("filter", {}),
        store_as=spec["store_as"],
        max_total_power=spec["max_total_power"],
        optional=spec.get("optional", True),
        prompt=spec.get("prompt"),
    )


def _select_within_total_cost(spec, game, player):
    return SelectWithinTotalCostEffect(
        player=player,
        game=game,
        candidates=spec.get("candidates", "opponent_creatures"),
        filter_spec=spec.get("filter", {}),
        store_as=spec["store_as"],
        max_total_cost=spec["max_total_cost"],
        optional=spec.get("optional", True),
        prompt=spec.get("prompt"),
    )


def _for_each_stored(spec, game, player):
    return ForEachStoredEffect(
        game=game,
        player=player,
        source=spec["source"],
        effect_spec=spec.get("effect", {}),
    )


def _for_each(spec, game, player):
    return ForEachEffect(
        game=game,
        player=player,
        source=spec.get("source"),
        store_key=_store_key(spec),
        effect_spec=spec.get("effect", {}),
    )


def _destroy_multiple(spec, game, player):
    return DestroyMultipleEffect(
        game=game,
        player=player,
        source=spec.get("source"),
        cards=spec.get("cards", spec.get("target")),
        source_card=spec.get("source_card"),
    )


def _gather_matching(spec, game, player):
    return GatherMatchingEffect(
        game=game,
        player=player,
        candidates=spec.get("candidates", "opponent_creatures"),
        filter_spec=spec.get("filter", {}),
        store_as=spec["store_as"],
        source_card=spec.get("source_card"),
    )


def _return_from_graveyard(spec, game, player):
    return ReturnFromGraveyardEffect(
        game=game,
        target=spec.get("target", "self"),
        tapped=spec.get(
            "tapped",
            spec.get("tap", False),
        ),
        optional=spec.get("optional", True),
    )


def _move_card(spec, game, player):
    return MoveCardEffect(
        player=player,
        game=game,
        from_zone=spec.get(
            "from_zone",
            spec.get("source_zone"),
        ),
        to_zone=spec.get(
            "to_zone",
            spec.get("destination_zone"),
        ),
        amount=spec.get("amount", 1),
        min_amount=spec.get("min_amount"),
        max_amount=spec.get(
            "max_amount",
            spec.get("up_to"),
        ),
        target_player=spec.get(
            "target_player",
            spec.get("player", "self"),
        ),
        filter_spec=_filter_spec(spec),
        selection=spec.get("selection"),
        optional=spec.get("optional", True),
        prompt=spec.get("prompt"),
        tapped=spec.get("tapped"),
        face_options=spec.get("face_options"),
        shield_face=spec.get("shield_face"),
        destination_position=spec.get("destination_position"),
        store_as=spec.get("store_as"),
        reason=spec.get("reason"),
        evolution_mode=spec.get("evolution_mode", "stack"),
        shield_placement=spec.get(
            "shield_placement",
            spec.get("shield_destination", "new"),
        ),
    )


def _store_card_from_zone(spec, game, player):
    return StoreCardFromZoneEffect(
        player=player,
        game=game,
        from_zone=spec.get(
            "from_zone",
            spec.get("source_zone"),
        ),
        target_player=spec.get(
            "target_player",
            spec.get("player", "self"),
        ),
        filter_spec=_filter_spec(spec),
        selection=spec.get("selection"),
        optional=spec.get("optional", False),
        prompt=spec.get("prompt"),
        store_as=spec["store_as"],
    )


def _put_creature_from_zone(spec, game, player):
    return PutCreatureFromZoneEffect(
        player=player,
        game=game,
        from_zone=spec.get(
            "from_zone",
            spec.get("source_zone"),
        ),
        amount=spec.get("amount", 1),
        target_player=spec.get(
            "target_player",
            spec.get("player", "self"),
        ),
        filter_spec=_filter_spec(spec),
        selection=spec.get("selection"),
        optional=spec.get("optional", True),
        prompt=spec.get("prompt"),
        tapped=spec.get("tapped", False),
        store_as=spec.get("store_as"),
        reason=spec.get("reason"),
        summoning_sick=spec.get(
            "summoning_sick",
            True,
        ),
    )


def _reveal_stored_card(spec, game, player):
    return RevealStoredCardEffect(
        key=spec["key"],
    )


def _reveal(spec, game, player):
    return RevealEffect(
        game=game,
        player=player,
        source=spec.get("source"),
        store_key=_store_key(spec),
        reveal_to=spec.get("to"),
    )


def _grant_extra_turn(spec, game, player):
    return GrantExtraTurnEffect(
        game=game,
        player=player,
        target_player=spec.get(
            "target_player",
            spec.get("player", "self"),
        ),
    )


def _reveal_cards(spec, game, player):
    if spec.get("to") is not None or spec.get("reveal_to") is not None:
        raise ValueError("reveal_cards is public; do not set to/reveal_to")

    source = {
        "source": spec.get("source", "zone"),
        "zone": spec.get(
            "zone",
            spec.get("from_zone", spec.get("source_zone", "deck")),
        ),
        "player": spec.get(
            "target_player",
            spec.get("player", "self"),
        ),
        "amount": spec.get("amount", spec.get("count", 1)),
        "from": spec.get(
            "from",
            spec.get("position", spec.get("selection", "top")),
        ),
    }
    return RevealCardsEffect(
        game=game,
        player=player,
        source=source,
        store_as=spec.get("store_as"),
        as_list=spec.get("as_list", False),
        optional=spec.get("optional", False),
        prompt=spec.get("prompt"),
    )


def _if_stored_card_matches(spec, game, player):
    return ConditionalEffect(
        key=spec["key"],
        condition=spec.get("condition", {}),
        effects=build_effects(
            spec.get("effects", []),
            game,
            player,
            source_card=spec.get("source_card"),
        ),
    )


def _select_then(spec, game, player):
    # "effect"（単発）または "effects"（同じ対象へ順番に適用するリスト）。
    return SelectThenEffect(
        player=player,
        game=game,
        candidates=spec["candidates"],
        filter_spec=spec.get("filter", {}),
        effect_spec=spec.get("effect", spec.get("effects")),
        prompt=spec.get("prompt", "Choose a target"),
        optional=spec.get("optional", True),
        store_as=spec.get("store_as"),
    )


def _destroy_creature(spec, game, player):
    target = spec.get(
        "target",
        "creatures",
    )

    if target == "own_other_creatures":
        candidates = "own_other_creatures"
        prompt = "Choose one of your other creatures to destroy"
    elif target == "own_creatures":
        candidates = "own_creatures"
        prompt = "Choose one of your creatures to destroy"
    elif target == "opponent_creatures":
        candidates = "opponent_creatures"
        prompt = "Choose an opponent creature to destroy"
    else:
        candidates = "creatures"
        prompt = "Choose a creature to destroy"

    return SelectThenEffect(
        player=player,
        game=game,
        candidates=candidates,
        filter_spec={
            "type": "creature",
        },
        effect_spec={
            "id": "destroy",
        },
        prompt=spec.get(
            "prompt",
            prompt,
        ),
        optional=spec.get("optional", True),
        store_as=spec.get("store_as"),
    )


def _bounce_opponent_creature(spec, game, player):
    target = _select_opponent_creature(
        game,
        player,
        spec.get("prompt", "Choose a creature to target"),
    )
    if target is None:
        return None

    return BounceEffect(
        target=target,
        game=game,
    )


def _bounce_own_creature(spec, game, player):
    target = _select_own_creature(
        game,
        player,
        spec.get("prompt", "Choose your creature to target"),
    )
    if target is None:
        return None

    return BounceEffect(
        target=target,
        game=game,
    )


def _bounce_opponent_battle_card(spec, game, player):
    target = _select_opponent_battle_card(
        game,
        player,
        spec.get(
            "prompt",
            "Choose a battle-zone card to target",
        ),
    )
    if target is None:
        return None

    return BounceCardEffect(
        target=target,
        game=game,
    )


def _bounce_own_battle_card(spec, game, player):
    target = _select_own_battle_card(
        game,
        player,
        spec.get(
            "prompt",
            "Choose your battle-zone card to target",
        ),
    )
    if target is None:
        return None

    return BounceCardEffect(
        target=target,
        game=game,
    )


def _power_modifier_opponent_creature(spec, game, player):
    target = _select_opponent_creature(
        game,
        player,
        spec.get("prompt", "Choose a creature to target"),
    )
    if target is None:
        return None

    return AddPowerModifierEffect(
        target=target,
        amount=spec["amount"],
    )


def _power_modifier_self(spec, game, player):
    return AddPowerModifierEffect(
        target=spec["source_card"],
        amount=spec["amount"],
    )


def _multiply_power(spec, game, player):
    target_spec = spec.get("target")
    return TimedPowerMultiplierEffect(
        source_card=spec.get("source_card"),
        target_card=None if target_spec is not None else spec.get("source_card"),
        target_spec=target_spec,
        player=player,
        factor=spec.get("factor", 2),
        game=game,
    )


def _temporary_combat_restriction(spec, game, player):
    return TemporaryCombatRestrictionEffect(
        game=game,
        source_card=spec.get("source_card"),
        scope=spec.get("scope", "opponent_creatures"),
        target_card=spec.get("target_card"),
        restrictions=spec.get("restrictions", []),
        duration_type=_duration_type(
            spec.get("duration")
        ),
    )


def _temporary_untouchable(spec, game, player):
    return ScopedTemporaryJustDiverEffect(
        game=game,
        scope=spec.get("scope", "own_creatures"),
        duration_type=_duration_type(
            spec.get(
                "duration",
                "until_start_of_controller_turn",
            )
        ),
    )


def _temporary_ability(spec, game, player):
    return TemporaryAbilityEffect(
        game=game,
        player=player,
        source_card=spec.get("source_card"),
        target=spec.get("target", spec.get("card")),
        scope=spec.get("scope"),
        ability=spec["ability"],
        duration_type=_duration_type(
            spec.get("duration")
        ),
    )


def _tap(spec, game, player):
    target = spec.get("target", spec.get("card"))
    if target == "self":
        target = spec.get("source_card")
    return TapEffect(
        target=target,
        game=game,
        optional=spec.get("optional", False),
        prompt=spec.get("prompt", "tap this creature?"),
    )


def _opponent_taps_own_creature(spec, game, player):
    return OpponentTapsOwnCreatureEffect(
        controller=player,
        game=game,
        label=spec.get("label"),
    )


def _untap(spec, game, player):
    target = spec.get("target", "self")
    if target == "own_other_creatures":
        return SelectThenEffect(
            player=player,
            game=game,
            candidates="own_other_creatures",
            filter_spec=_filter_spec(spec) or {
                "type": "creature",
            },
            effect_spec={
                "id": "untap",
            },
            prompt=spec.get(
                "prompt",
                "Choose one of your other creatures to untap",
            ),
            optional=spec.get("optional", False),
            store_as=spec.get("store_as"),
        )

    if target == "self":
        target = spec["source_card"]

    return UntapEffect(
        target=target,
        game=game,
        player=player,
    )


def _freeze_untap(spec, game, player):
    return TemporaryTurnStartFreezeEffect(
        game=game,
        target=spec["target"],
        duration_type=_duration_type(
            spec.get(
                "duration",
                "until_start_of_controller_turn",
            )
        ),
    )


def _lock_untap(spec, game, player):
    return TemporaryUntapLockEffect(
        game=game,
        target=spec["target"],
        duration_type=_duration_type(
            spec.get(
                "duration",
                "until_start_of_controller_turn",
            )
        ),
    )


def _duration_type(value):
    return parse_duration_spec(value)


def _choose_n_effects(spec, game, player):
    return ChooseNEffectsEffect(
        player=player,
        game=game,
        choice_specs=spec.get("choices", []),
        n=int(spec.get("n", 2)),
        prompt=spec.get("prompt", "効果を選んでください"),
        source_card=spec.get("source_card"),
    )


def _choose_number(spec, game, player):
    # V2 の choose_number を registry 経由でも使えるようにするブリッジ。
    # choose_n_effects など build_effects 系の中で「数字を1つ選ぶ」を表現する。
    from effects.effect_factory import V2ChooseNumberEffect

    return V2ChooseNumberEffect(spec, game, player)


def _select(spec, game, player):
    # V2 の select を registry 経由でも使えるようにするブリッジ。
    # 選んだカードを store_as に保存し、後続の effect が {"ref": ...} で参照する。
    from effects.effect_factory import V2SelectEffect

    return V2SelectEffect(spec, game, player, spec.get("source_card"))


def _put_creature_from_multi_zone(spec, game, player):
    return PutCreatureFromMultiZoneEffect(
        player=player,
        game=game,
        from_zones=spec.get("from_zones", ["hand"]),
        filter_spec=_filter_spec(spec),
        optional=spec.get("optional", False),
        prompt=spec.get("prompt"),
        summoning_sick=spec.get("summoning_sick", True),
    )


def _battle_two_creatures(spec, game, player):
    return BattleTwoCreaturesEffect(
        player=player,
        game=game,
        optional=spec.get("optional", False),
    )


def _charger(spec, game, player):
    return ChargerEffect()


def _wins_all_battles(spec, game, player):
    target = spec.get("target", "self")
    if target in ("self", "source"):
        target = spec.get("source_card")
    return WinsAllBattlesEffect(
        source_card=spec.get("source_card"),
        target_card=target,
        duration_type=_duration_type(
            spec.get("duration", "until_end_of_turn")
        ),
        game=game,
    )


def _attach_seal(spec, game, player):
    return AttachSealEffect(
        player=player,
        game=game,
        target=spec.get("target", spec.get("card", "self")),
        amount=spec.get("amount", spec.get("count", 1)),
        seal_player=spec.get("seal_player"),
    )


def _power_gachinko_judge(spec, game, player):
    return PowerGachinkoJudgeEffect(
        game=game,
        player=player,
        on_win=spec.get("on_win", []),
        on_lose=spec.get("on_lose", []),
        optional=spec.get("optional", False),
        prompt=spec.get("prompt"),
        repeat_until_lose=spec.get("repeat_until_lose", False),
        source_card=spec.get("source_card"),
        store_own_as=spec.get(
            "store_own_as",
            spec.get("store_as"),
        ),
        store_opponent_as=spec.get("store_opponent_as"),
        defer_own_bottom_on_win=spec.get(
            "defer_own_bottom_on_win",
            False,
        ),
    )


def _opponent_choose_own_creature_or_shield_to_mana(spec, game, player):
    return OpponentChooseOwnCreatureOrShieldToManaEffect(
        game=game,
        player=player,
        optional=spec.get("optional", False),
        tapped=spec.get("tapped", False),
        prompt=spec.get("prompt"),
    )


def _release_hyper_mode(spec, game, player):
    return ReleaseHyperModeEffect(
        game=game,
        scope=spec.get("scope", "own_creatures"),
        controller=player,
    )


def _mark_final_revolution_used(spec, game, player):
    return MarkFinalRevolutionUsedEffect(
        game=game,
        player=player,
    )


def _move_deck_top(spec, game, player):
    return MoveDeckTopEffect(
        game=game,
        player=player,
        amount=spec.get("amount", spec.get("count", 1)),
        to_zone=spec.get("to_zone", spec.get("destination_zone", "mana")),
        optional=spec.get("optional", False),
        tapped=spec.get("tapped"),
        prompt=spec.get("prompt"),
    )


def _summon_within_total_cost(spec, game, player):
    return SummonWithinTotalCostEffect(
        game=game,
        player=player,
        from_zones=spec.get("from_zones", ["hand"]),
        filter_spec=_filter_spec(spec) or {"card_type": "creature"},
        max_count=spec.get("max_count", spec.get("amount", 1)),
        max_total_cost=spec["max_total_cost"],
        summoning_sick=spec.get("summoning_sick", True),
        prompt=spec.get("prompt"),
        source_card=spec.get("source_card"),
        store_as=spec.get("store_as"),
    )


def _revive_within_total_cost_sealed(spec, game, player):
    return ReviveWithinTotalCostSealedEffect(
        game=game,
        player=player,
        from_zones=spec.get("from_zones", ["graveyard"]),
        filter_spec=_filter_spec(spec) or {"card_type": "creature"},
        max_count=spec.get("max_count", spec.get("amount", 1)),
        max_total_cost=spec["max_total_cost"],
        seal_amount=spec.get("seal_amount", 1),
        summoning_sick=spec.get("summoning_sick", True),
        prompt=spec.get("prompt"),
        source_card=spec.get("source_card"),
        store_as=spec.get("store_as"),
    )


def _cost_execution_lock(spec, game, player):
    affected = spec.get("affected_player", "opponent")
    if affected == "opponent":
        affected_player = game.query.get_opponent(player)
    else:
        affected_player = player
    return CostExecutionLockEffect(
        game=game,
        affected_player=affected_player,
        cost=spec.get("cost"),
        duration_type=parse_duration_spec(
            spec.get("duration", "until_start_of_controller_turn")
        ),
        source_card=spec.get("source_card"),
        card_filter=spec.get("card_filter"),
    )


def _prevent_loss(spec, game, player):
    return PreventLossEffect(
        game=game,
        controller=player,
        duration_type=parse_duration_spec(
            spec.get("duration", "until_start_of_controller_turn")
        ),
        source_card=spec.get("source_card"),
    )


def _opponent_effect_separation_guard(spec, game, player):
    return OpponentEffectSeparationGuard(
        game=game,
        controller=player,
        duration_type=parse_duration_spec(
            spec.get("duration", "until_start_of_controller_turn")
        ),
        source_card=spec.get("source_card"),
    )


def _look_then_distribute(spec, game, player):
    return LookThenDistributeEffect(
        game=game,
        player=player,
        amount=spec.get("amount", spec.get("count", 3)),
        buckets=spec.get("buckets", []),
        remainder_zone=spec.get("remainder_zone", "mana"),
        source_card=spec.get("source_card"),
    )


def _once_per_turn_gate(spec, game, player):
    return OncePerTurnEffect(
        game=game,
        key=spec["key"],
        consume=False,
    )


def _once_per_turn_mark(spec, game, player):
    return OncePerTurnEffect(
        game=game,
        key=spec["key"],
        consume=True,
    )


EFFECT_BUILDERS = {
    "add_deck_to_shield": _add_deck_to_shield,
    "attach_seal": _attach_seal,
    "power_gachinko_judge": _power_gachinko_judge,
    "add_hand_to_shield": _add_hand_to_shield,
    "add_shield_to_hand": _add_shield_to_hand,
    "break_shield": _break_shield,
    "charger": _charger,
    "creature_break_shield": _creature_break_shield,
    "bounce_own_battle_card": _bounce_own_battle_card,
    "bounce_own_creature": _bounce_own_creature,
    "bounce_opponent_battle_card": _bounce_opponent_battle_card,
    "bounce_opponent_creature": _bounce_opponent_creature,
    "discard": _discard,
    "discard_hand_then_draw": _discard_hand_then_draw,
    "destroy_creature": _destroy_creature,
    "draw": _draw,
    "execute_card_from_hand": _execute_card_from_hand,
    "execute_card_from_zone": _execute_card_from_zone,
    "if_stored_card_matches": _if_stored_card_matches,
    "look": _look,
    "look_top_choose_to_hand": _look_top_choose_to_hand,
    "look_top_put_creature_to_battle": _look_top_put_creature_to_battle,
    "look_top_choose_distinct_types_to_hand": (
        _look_top_choose_distinct_types_to_hand
    ),
    "look_top_same_cost_creatures_to_battle": (
        _look_top_same_cost_creatures_to_battle
    ),
    "count": _count,
    "count_matching": _count_matching,
    "destroy_multiple": _destroy_multiple,
    "for_each": _for_each,
    "for_each_stored": _for_each_stored,
    "gather_matching": _gather_matching,
    "grant_extra_turn": _grant_extra_turn,
    "mill": _mill,
    "move_card": _move_card,
    "repeat": _repeat,
    "release_hyper_mode": _release_hyper_mode,
    "select_n": _select_n,
    "select_within_total_cost": _select_within_total_cost,
    "select_within_total_power": _select_within_total_power,
    "shield_plus": _shield_plus,
    "packaged": _packaged,
    "flip_d2_field": _flip_d2_field,
    "multiply_power": _multiply_power,
    "wins_all_battles": _wins_all_battles,
    "power_modifier_opponent_creature": _power_modifier_opponent_creature,
    "power_modifier_self": _power_modifier_self,
    "put_creature_from_zone": _put_creature_from_zone,
    "reveal": _reveal,
    "reveal_cards": _reveal_cards,
    "reveal_stored_card": _reveal_stored_card,
    "store_card_from_zone": _store_card_from_zone,
    "return_from_graveyard": _return_from_graveyard,
    "select_then": _select_then,
    "freeze_untap": _freeze_untap,
    "lock_untap": _lock_untap,
    "tap": _tap,
    "opponent_taps_own_creature": _opponent_taps_own_creature,
    "untap": _untap,
    "temporary_combat_restriction": _temporary_combat_restriction,
    "temporary_untouchable": _temporary_untouchable,
    "temporary_ability": _temporary_ability,
    "choose_n_effects": _choose_n_effects,
    "choose_number": _choose_number,
    "select": _select,
    "mark_final_revolution_used": _mark_final_revolution_used,
    "move_deck_top": _move_deck_top,
    "opponent_choose_own_creature_or_shield_to_mana": (
        _opponent_choose_own_creature_or_shield_to_mana
    ),
    "summon_within_total_cost": _summon_within_total_cost,
    "revive_within_total_cost_sealed": _revive_within_total_cost_sealed,
    "cost_execution_lock": _cost_execution_lock,
    "prevent_loss": _prevent_loss,
    "opponent_effect_separation_guard": _opponent_effect_separation_guard,
    "look_then_distribute": _look_then_distribute,
    "once_per_turn_gate": _once_per_turn_gate,
    "once_per_turn_mark": _once_per_turn_mark,
    "put_creature_from_multi_zone": _put_creature_from_multi_zone,
    "battle_two_creatures": _battle_two_creatures,
}


def _filter_spec(spec):
    filter_spec = dict(spec.get("filter", {}))
    for key in (
        "card_type",
        "civilization",
        "civilizations",
        "cost",
        "exact_cost",
        "exact_power",
        "max_cost",
        "cost_less_than",
        "cost_lt",
        "has_keyword",
        "is_evolution",
        "max_power",
        "min_cost",
        "min_power",
        "power",
        "race_ja",
        "shield_face_up",
        "special_type",
        "special_types",
        "type",
        "types",
    ):
        if key in spec and key not in filter_spec:
            filter_spec[key] = spec[key]

    return filter_spec


def _store_key(spec):
    return spec.get(
        "store_key",
        spec.get(
            "key",
            spec.get("store_as"),
        ),
    )


def _ignore_cost(spec):
    if "without_cost" in spec:
        return bool(spec["without_cost"])

    if "ignore_cost" in spec:
        return bool(spec["ignore_cost"])

    if "pay_cost" in spec:
        return not bool(spec["pay_cost"])

    cost_mode = spec.get("cost_mode")
    if cost_mode in (
        "free",
        "ignore",
        "without_cost",
    ):
        return True
    if cost_mode in (
        "pay",
        "pay_cost",
        "normal",
    ):
        return False

    return True


def _select_opponent_creature(
    game,
    player,
    prompt,
):
    opponent = game.query.get_opponent(player)

    return game.target_selector.select(
        player,
        options=game.query.get_selectable_creatures(
            source=player,
            controller=opponent,
        ),
        prompt=prompt,
    )


def _select_own_creature(
    game,
    player,
    prompt,
):
    return game.target_selector.select(
        player,
        options=game.query.get_selectable_creatures(
            source=player,
            controller=player,
        ),
        prompt=prompt,
    )


def _select_opponent_battle_card(
    game,
    player,
    prompt,
):
    opponent = game.query.get_opponent(player)

    return game.target_selector.select(
        player,
        options=game.query.get_battle_cards(
            controller=opponent,
        ),
        prompt=prompt,
    )


def _select_own_battle_card(
    game,
    player,
    prompt,
):
    return game.target_selector.select(
        player,
        options=game.query.get_battle_cards(
            controller=player,
        ),
        prompt=prompt,
    )
