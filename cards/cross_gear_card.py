"""クロスギア。ジェネレートで単体でバトルゾーンに出し、コストを再度払ってクリーチャーにクロスする。"""

from abilities.base.activated_ability import ActivatedAbility
from actions.activate_ability_action import ActivateAbilityAction
from actions.use_card_action import UseCardAction
from cards.card import Card, CardType
from cards.creature_card import CreatureCard
from core.pending_cards import (
    begin_pending,
    end_pending,
    is_card_pending,
)
from core.seal_utils import is_ignored_by_seal
from events.card_executed_event import CardExecutedEvent
from ui.card_display import format_card_name
from zones.zone_type import ZoneType


class CrossGearCard(Card):

    def __init__(
        self,
        name,
        cost,
        civilizations,
        card_types=None,
        special_types=None,
        name_ja=None,
        effect_name_ja=None,
        effect_texts_ja=None,
        game=None,
    ):
        super().__init__(
            name=name,
            cost=cost,
            civilizations=civilizations,
            card_types=card_types or (CardType.CROSS_GEAR,),
            special_types=special_types,
            name_ja=name_ja,
            effect_name_ja=effect_name_ja,
            effect_texts_ja=effect_texts_ja,
        )

        # クロス中のクリーチャー（未クロスなら None）。
        # クロスギアはあくまで独立したオブジェクトであり、
        # クリーチャーに含まれるカードとしては扱わない。
        self.crossed_to = None

        self.abilities.append(
            CrossGearCrossAbility(
                owner_card=self,
                game=game,
            )
        )

    def can_exist_in_battle_alone(
        self,
    ):
        return True

    # --- ジェネレート（手札 → バトルゾーンに単体で出す） ---

    def can_use(
        self,
        game,
        player,
        ignore_cost=False,
    ):
        if self.owner is not player:
            return False

        if getattr(self, "zone", None) != ZoneType.HAND:
            return False

        if is_card_pending(self):
            return False

        if not ignore_cost and not player.can_play(self):
            return False

        return True

    def use(
        self,
        game,
        player,
        ignore_cost=False,
    ):
        if not self.can_use(
            game,
            player,
            ignore_cost=ignore_cost,
        ):
            return False

        if not ignore_cost:
            if not player.tap_mana(
                self._current_cost(player, game),
                spending_card=self,
                choice_manager=(
                    game.choice_manager
                ),
            ):
                return False

        from_zone = (
            getattr(self, "zone", None)
            or ZoneType.HAND
        )
        pending_started = begin_pending(
            self,
            reason="generate_cross_gear",
        )

        try:
            moved = game.card_mover.move(
                card=self,
                owner=player,
                from_zone=from_zone,
                to_zone=ZoneType.BATTLE,
                reason="generate_cross_gear",
            )
            if moved:
                self.crossed_to = None
                self.summoning_sick = False
                game.event_manager.publish(
                    CardExecutedEvent(
                        player=player,
                        card=self,
                        from_zone=from_zone,
                        ignore_cost=ignore_cost,
                    )
                )
                return True

            return False
        finally:
            if pending_started and is_card_pending(self):
                end_pending(self)

    def play_without_cost(
        self,
        game,
        player,
    ):
        return self.use(
            game,
            player,
            ignore_cost=True,
        )

    def get_available_actions(
        self,
        game,
        player,
    ):
        if self.can_use(game, player):
            return [
                UseCardAction(
                    player,
                    self,
                )
            ]

        return []

    # --- クロス（バトルゾーンの自分のクリーチャー1体に装備する） ---

    def can_cross(
        self,
        game,
        player,
        ignore_cost=False,
    ):
        if self.owner is not player:
            return False

        if getattr(self, "zone", None) != ZoneType.BATTLE:
            return False

        if is_card_pending(self):
            return False

        if not self.cross_targets(player):
            return False

        if not ignore_cost and not player.can_play(self):
            return False

        return True

    def cross(
        self,
        game,
        player,
        target=None,
        ignore_cost=False,
    ):
        if not self.can_cross(
            game,
            player,
            ignore_cost=ignore_cost,
        ):
            return False

        targets = self.cross_targets(player)

        if target is None:
            target = game.target_selector.select(
                player,
                targets,
                prompt=(
                    "Choose a creature to cross "
                    f"{format_card_name(self)} onto"
                ),
            )

        if target is None or target not in targets:
            return False

        if not ignore_cost:
            if not player.tap_mana(
                self._current_cost(player, game),
                spending_card=self,
                choice_manager=(
                    game.choice_manager
                ),
            ):
                return False

        # 再クロス時は元のクリーチャーから外れ、新しいクリーチャーに付け替える。
        self.set_crossed_to(target)
        print(
            f"{player.name} crossed "
            f"{format_card_name(self)} onto "
            f"{format_card_name(target)}"
        )
        return True

    def cross_targets(
        self,
        player,
    ):
        return [
            card
            for card in player.battle_zone.cards
            if card is not self
            and not is_card_pending(card)
            and not is_ignored_by_seal(card)
            and isinstance(card, CreatureCard)
            and card.has_card_type(CardType.CREATURE)
        ]

    def set_crossed_to(
        self,
        creature,
    ):
        """クロス先を更新し、外れる/付くタイミングのフックを能力へ通知する。"""

        previous = self.crossed_to
        if previous is creature:
            return

        if previous is not None:
            self._notify_cross_hook("on_uncross", previous)

        self.crossed_to = creature

        if creature is not None:
            self._notify_cross_hook("on_cross", creature)

    def _notify_cross_hook(
        self,
        hook_name,
        creature,
    ):
        for ability in self.abilities:
            hook = getattr(ability, hook_name, None)
            if hook is not None:
                hook(creature)

    def reset_battle_state(
        self,
    ):
        # クロスギアがバトルゾーンを離れる時は、クロスを解除して
        # クロス先へ付与した能力を取り除く。
        self.tapped = False
        self.set_crossed_to(None)

    def detach_if_invalid(
        self,
    ):
        """クロス先が不適正（離れた・クリーチャーでなくなった）なら外す。"""

        creature = self.crossed_to
        if creature is None:
            return False

        if self._cross_still_valid(creature):
            return False

        self.set_crossed_to(None)
        return True

    def _cross_still_valid(
        self,
        creature,
    ):
        owner = getattr(self, "owner", None)
        if owner is None:
            return False

        if creature not in owner.battle_zone.cards:
            return False

        if getattr(creature, "zone", None) != ZoneType.BATTLE:
            return False

        if not creature.has_card_type(CardType.CREATURE):
            return False

        return True

    def _current_cost(
        self,
        player,
        game,
    ):
        try:
            return self.get_current_cost(
                player=player,
                game=game,
            )
        except TypeError:
            return self.get_current_cost()


class CrossGearCrossAbility(ActivatedAbility):
    """バトルゾーンのクロスギアをクリーチャーにクロスする起動型アクションを生成する。"""

    def __init__(
        self,
        owner_card,
        game=None,
    ):
        super().__init__()
        self.owner_card = owner_card
        self.game = game

    def can_activate(
        self,
        player,
    ):
        return self.owner_card.can_cross(
            self.game,
            player,
        )

    def activate(
        self,
        action,
    ):
        return self.owner_card.cross(
            self.game,
            action.player,
        )

    def get_activate_actions(
        self,
        player,
        source_card,
    ):
        if not self.can_activate(player):
            return []

        return [
            ActivateAbilityAction(
                player,
                self,
                source_card,
            )
        ]


def gears_crossed_onto(
    creature,
):
    """指定クリーチャーにクロスされているクロスギアの一覧を返す。"""

    owner = getattr(creature, "owner", None)
    if owner is None:
        return []

    return [
        card
        for card in owner.battle_zone.cards
        if getattr(card, "crossed_to", None) is creature
    ]
