"""
呪文を唱えるアクションを実行するハンドラ。呪文効果を解決キューに追加し、使用後に墓地に送ります。
"""

from core.action_handlers.base_action_handler import (
    BaseActionHandler
)

from zones.zone_type import (
    ZoneType
)

from events.spell_cast_event import (
    SpellCastEvent
)

from ui.trigger_debug import log_spell_effects

from cards.twin_pact_card import (
    TwinPactCard
)

from ui.card_display import format_card_name
from core.pending_cards import (
    begin_pending,
    end_pending,
)
from core.play_history import record_play


class CastSpellActionHandler(
    BaseActionHandler
):

    def process(
        self,
        action,
    ):

        player = action.player

        spell = action.spell

        if isinstance(spell, TwinPactCard):
            spell.select_spell_face()

        from_zone = (
            getattr(
                spell,
                "zone",
                None,
            )
            or ZoneType.HAND
        )

        play_permission = getattr(action, "play_permission", None)

        begin_pending(
            spell,
            reason="cast_spell",
        )

        try:
            # コスト支払い
            if not action.ignore_cost:
                cost_override = getattr(action, "cost_override", None)
                if cost_override is not None:
                    # リサイクルなど独自コストを持つ能力
                    cost_civs = getattr(action, "cost_override_civilizations", None)
                    tap_kwargs = dict(
                        spending_card=spell,
                        choice_manager=(
                            self.game_controller
                            .choice_manager
                        ),
                    )
                    if cost_civs is not None:
                        tap_kwargs["required_civilizations"] = cost_civs
                    if not player.tap_mana(cost_override, **tap_kwargs):
                        return
                else:
                    if not player.can_play(
                        spell,
                        self.game_controller,
                    ):
                        return

                    try:
                        play_cost = spell.get_current_cost(
                            player=player,
                            game=self.game_controller,
                        )
                    except TypeError:
                        try:
                            play_cost = spell.get_current_cost(
                                player=player,
                            )
                        except TypeError:
                            play_cost = spell.get_current_cost()

                    if not player.tap_mana(
                        play_cost,
                        spending_card=spell,
                        choice_manager=(
                            self.game_controller
                            .choice_manager
                        ),
                    ):
                        return

            print(
                f"{player.name} "
                f"casts "
                f"{format_card_name(spell)}"
            )

            self.game_controller.event_manager.publish(
                SpellCastEvent(
                    player,
                    spell,
                    from_zone=from_zone,
                    ignore_cost=action.ignore_cost,
                    play_method=action.play_method,
                )
            )

            effects = (
                spell.create_effects(
                    self.game_controller,
                    player,
                )
            )

            log_spell_effects(
                spell,
                effects,
            )

            package_context = {}
            for effect in effects:

                effect.source_card = spell
                effect.package_context = package_context

                self.game_controller\
                    .effect_resolver\
                    .add_effect(
                        effect,
                        controller=player,
                        is_shield_trigger=(
                            self.game_controller
                            .context
                            .resolving_shield_trigger
                        ),
                    )

            self.game_controller\
                .effect_resolver\
                .resolve_specific_effects(
                    self.game_controller,
                    effects,
                )

            if play_permission is not None:
                mark_used = getattr(play_permission, "mark_used", None)
                if mark_used is not None:
                    mark_used(player, spell)

            if getattr(spell, "charger_to_mana", False):
                to_zone = ZoneType.MANA
            else:
                to_zone = getattr(
                    play_permission,
                    "cast_destination",
                    ZoneType.GRAVEYARD,
                )

            self.game_controller\
                .card_mover.move(
                    card=spell,
                    owner=player,
                    from_zone=from_zone,
                    to_zone=to_zone,
                    reason="cast_spell",
                )
            spell.charger_to_mana = False

            record_play(
                self.game_controller,
                player,
                spell,
                "cast_spell",
                from_zone,
                action,
            )
        finally:
            spell.charger_to_mana = False
            end_pending(spell)
