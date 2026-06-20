"""Manage Duel Masters seal attachments and automatic unsealing."""

from cards.card import CardType
from cards.creature_card import CreatureCard
from cards.twin_pact_card import TwinPactCard
from core.battle_display_labels import clear_battle_display_label
from core.pending_cards import first_visible_card, is_card_pending
from core.seal_utils import is_ignored_by_seal, is_seal_card
from zones.zone_type import ZoneType


class SealManager:

    def __init__(
        self,
        context,
    ):
        self.context = context

    def attach_seal(
        self,
        target_card,
        player=None,
    ):
        if not self._can_receive_seal(target_card):
            return False

        player = player or getattr(
            target_card,
            "owner",
            None,
        )
        if player is None:
            return False

        seal_card = first_visible_card(
            player.deck.cards
        )
        if seal_card is None:
            return False

        self._prepare_as_seal(
            seal_card,
            target_card,
        )
        moved = self.context.card_mover.move(
            card=seal_card,
            owner=player,
            from_zone=ZoneType.DECK,
            to_zone=ZoneType.BATTLE,
            reason="seal_attach",
        )

        if (
            moved
            and getattr(
                seal_card,
                "zone",
                None,
            )
            == ZoneType.BATTLE
            and seal_card in getattr(
                target_card,
                "seals",
                (),
            )
        ):
            return True

        self._restore_from_seal(
            seal_card,
        )
        return False

    def attach_seals(
        self,
        targets,
        amount=1,
        player=None,
    ):
        targets = [
            target
            for target in _as_list(targets)
            if self._can_receive_seal(target)
        ]
        if not targets:
            return []

        amount = int(amount)
        attached = []
        pending = []
        for target in targets:
            pending.extend(
                [target] * amount
            )

        while pending:
            target = self._choose_next_attach_target(
                pending,
                player,
            )
            if target is None:
                break

            pending.remove(target)
            if self.attach_seal(
                target,
                player=player
                or getattr(
                    target,
                    "owner",
                    None,
                ),
            ):
                attached.append(target)

        return attached

    def finalize_seal_attachment(
        self,
        seal_card,
    ):
        if not is_seal_card(seal_card):
            return False

        if getattr(
            seal_card,
            "zone",
            None,
        ) != ZoneType.BATTLE:
            return False

        target = getattr(
            seal_card,
            "sealed_target",
            None,
        )
        if target is None:
            return False

        seals = getattr(
            target,
            "seals",
            None,
        )
        if seals is None:
            seals = []
            target.seals = seals

        if seal_card not in seals:
            seals.append(seal_card)

        if self._target_is_creature(target):
            self._mark_ignored_tree(target)

        return True

    def handle_card_entered_battle(
        self,
        card,
        owner,
    ):
        if is_seal_card(card):
            return False

        if not self._is_command_element(card):
            return False

        candidates = self._unseal_candidates(
            owner,
            getattr(
                card,
                "civilizations",
                0,
            ),
        )
        if not candidates:
            return False

        target = self._choose_unseal_target(
            owner,
            candidates,
        )
        if target is None:
            return False

        return self.remove_one_seal(
            target,
            reason="seal_removed_by_command",
        )

    def remove_one_seal(
        self,
        target_card,
        reason="seal_removed",
    ):
        seals = getattr(
            target_card,
            "seals",
            [],
        )
        if not seals:
            return False

        seal_card = seals[-1]
        return self.move_seal_to_graveyard(
            seal_card,
            reason=reason,
        )

    def move_seal_to_graveyard(
        self,
        seal_card,
        reason="seal_removed",
    ):
        if not is_seal_card(seal_card):
            return False

        if getattr(
            seal_card,
            "zone",
            None,
        ) != ZoneType.BATTLE:
            self._detach_seal_relation(
                seal_card,
            )
            self._restore_from_seal(
                seal_card,
            )
            return False

        owner = getattr(
            seal_card,
            "owner",
            None,
        )
        if owner is None:
            return False

        moved = self.context.card_mover.move(
            card=seal_card,
            owner=owner,
            from_zone=ZoneType.BATTLE,
            to_zone=ZoneType.GRAVEYARD,
            reason=reason,
            apply_replacements=False,
        )
        return bool(moved)

    def before_zone_change_event(
        self,
        event,
    ):
        event.from_seal = bool(
            is_seal_card(event.card)
            and event.from_zone == ZoneType.BATTLE
        )
        event.sealed_target = getattr(
            event.card,
            "sealed_target",
            None,
        )

    def after_zone_change_event(
        self,
        event,
    ):
        if not getattr(
            event,
            "from_seal",
            False,
        ):
            return

        self._detach_seal_relation(
            event.card,
        )
        self._restore_from_seal(
            event.card,
        )

    def apply_orphaned_seals(
        self,
    ):
        moved_any = False

        for player in self.context.state.players:
            for card in player.battle_zone.cards[:]:
                if not is_seal_card(card):
                    continue

                target = getattr(
                    card,
                    "sealed_target",
                    None,
                )
                if (
                    target is not None
                    and getattr(
                        target,
                        "zone",
                        None,
                    )
                    == ZoneType.BATTLE
                    and target in player.battle_zone.cards
                ):
                    continue

                moved = self.move_seal_to_graveyard(
                    card,
                    reason="orphaned_seal",
                )
                moved_any = moved_any or bool(moved)

        return moved_any

    def _prepare_as_seal(
        self,
        card,
        target,
    ):
        if is_seal_card(card):
            return

        state = {
            "cost": getattr(
                card,
                "cost",
                None,
            ),
            "civilizations": getattr(
                card,
                "civilizations",
                0,
            ),
            "card_types": getattr(
                card,
                "card_types",
                (),
            ),
            "race": getattr(
                card,
                "race",
                None,
            ),
            "race_ja": getattr(
                card,
                "race_ja",
                None,
            ),
            "abilities": list(
                getattr(
                    card,
                    "abilities",
                    (),
                )
            ),
            "selected_face": getattr(
                card,
                "selected_face",
                None,
            ),
        }
        card._seal_original_state = state

        # 能力の購読(subscribe)は解除しない。ゲーム開始時に全カードが
        # 一度だけ登録され、以後は解除されない設計のため、ここで
        # unregister すると封印解除後（墓地など）の能力が二度と働かなく
        # なってしまう。封印中の能力は can_trigger / register_abilities /
        # has_ability の is_seal_card ガードによって休止する。
        card.is_seal = True
        card.sealed_target = target
        card.is_ignored_by_seal = False
        card.face_down = True
        try:
            card.cost = 0
        except AttributeError:
            pass
        card.civilizations = 0
        card.card_types = ()
        card.race = ()
        card.race_ja = ()
        card.abilities = []

        clear_face = getattr(
            card,
            "clear_selected_face",
            None,
        )
        if clear_face is not None:
            clear_face()

        # 封印化したカードに残った表示用識別子（A/B/C…）を消し、
        # 元カード名に基づくラベルが盤面に漏れないようにする。
        clear_battle_display_label(card)

    def _restore_from_seal(
        self,
        card,
    ):
        state = getattr(
            card,
            "_seal_original_state",
            None,
        )
        if state is None:
            return

        card.is_seal = False
        card.sealed_target = None
        card.face_down = False

        try:
            card.cost = state["cost"]
        except AttributeError:
            pass
        card.civilizations = state["civilizations"]
        card.card_types = state["card_types"]
        card.race = state["race"]
        card.race_ja = state["race_ja"]
        card.abilities = state["abilities"]

        if isinstance(card, TwinPactCard):
            selected = state.get("selected_face")
            if selected is card.creature_face:
                card.select_creature_face()
            elif selected is card.spell_face:
                card.select_spell_face()
            else:
                card.clear_selected_face()

        if hasattr(
            card,
            "_seal_original_state",
        ):
            delattr(
                card,
                "_seal_original_state",
            )

    def _detach_seal_relation(
        self,
        seal_card,
    ):
        target = getattr(
            seal_card,
            "sealed_target",
            None,
        )
        if target is None:
            return

        seals = getattr(
            target,
            "seals",
            [],
        )
        if seal_card in seals:
            seals.remove(seal_card)

        if not seals:
            self._clear_ignored_tree(target)

    def _mark_ignored_tree(
        self,
        card,
    ):
        card.is_ignored_by_seal = True
        for source in getattr(
            card,
            "evolution_sources",
            (),
        ):
            self._mark_ignored_tree(source)

    def _clear_ignored_tree(
        self,
        card,
    ):
        card.is_ignored_by_seal = False
        for source in getattr(
            card,
            "evolution_sources",
            (),
        ):
            self._clear_ignored_tree(source)

    def _can_receive_seal(
        self,
        target_card,
    ):
        return (
            target_card is not None
            and getattr(
                target_card,
                "zone",
                None,
            )
            == ZoneType.BATTLE
            and not is_card_pending(target_card)
            and not is_seal_card(target_card)
        )

    def _target_is_creature(
        self,
        card,
    ):
        if isinstance(
            card,
            CreatureCard,
        ):
            return True

        return (
            isinstance(
                card,
                TwinPactCard,
            )
            and isinstance(
                getattr(
                    card,
                    "selected_face",
                    None,
                ),
                CreatureCard,
            )
        )

    def _is_command_element(
        self,
        card,
    ):
        if is_ignored_by_seal(card):
            return False

        if not getattr(
            card,
            "is_element",
            False,
        ):
            return False

        if not (
            set(
                getattr(
                    card,
                    "card_types",
                    (),
                )
            )
            & {
                card_type
                for card_type in CardType
                if card_type != CardType.SPELL
            }
        ):
            return False

        races = list(
            _as_list(
                getattr(
                    card,
                    "race_ja",
                    (),
                )
            )
        )
        creature_face = getattr(
            card,
            "creature_face",
            None,
        )
        if creature_face is not None:
            races.extend(
                _as_list(
                    getattr(
                        creature_face,
                        "race_ja",
                        (),
                    )
                )
            )

        return any(
            "コマンド" in str(race)
            for race in races
        )

    def _unseal_candidates(
        self,
        owner,
        command_civilizations,
    ):
        return [
            card
            for card in owner.battle_zone.cards
            if self._target_is_creature(card)
            and not is_card_pending(card)
            and getattr(
                card,
                "seals",
                None,
            )
            and (
                getattr(
                    card,
                    "civilizations",
                    0,
                )
                & command_civilizations
            )
        ]

    def _choose_unseal_target(
        self,
        player,
        candidates,
    ):
        if len(candidates) == 1:
            return candidates[0]

        return self.context.choice_manager.select(
            player,
            candidates,
            prompt="封印を外すクリーチャーを選んでください",
        )

    def _choose_next_attach_target(
        self,
        pending,
        player,
    ):
        unique = []
        for target in pending:
            if target not in unique:
                unique.append(target)

        if len(unique) == 1:
            return unique[0]

        chooser = player or getattr(
            unique[0],
            "owner",
            None,
        )
        if chooser is None:
            return unique[0]

        return self.context.choice_manager.select(
            chooser,
            unique,
            prompt="封印を付けるカードを選んでください",
        )


def _as_list(
    value,
):
    if value is None:
        return []

    if isinstance(
        value,
        (list, tuple, set),
    ):
        return list(value)

    return [
        value,
    ]
