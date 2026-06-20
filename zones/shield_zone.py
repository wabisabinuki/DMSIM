"""Shield zone with slot support.

A shield slot is one shield for counting and breaking, but can contain
multiple physical cards stacked together.
"""

from dataclasses import dataclass, field

from core.pending_cards import is_card_pending
from zones.zone import Zone


@dataclass
class ShieldSlot:
    cards: list = field(default_factory=list)

    @property
    def top_card(self):
        if not self.cards:
            return None

        return self.cards[-1]

    def visible_cards(self):
        return [
            card
            for card in self.cards
            if not is_card_pending(card)
        ]

    def visible_shield_cards(self):
        return [
            card
            for card in self.visible_cards()
            if not _is_active_fortified_castle(card)
        ]

    def visible_top_card(self):
        visible = self.visible_cards()
        if not visible:
            return None

        return visible[-1]

    def visible_shield_card(self):
        visible = self.visible_shield_cards()
        if not visible:
            return None

        return visible[-1]

    def has_fortified_castle(self):
        return any(
            _is_active_fortified_castle(card)
            for card in self.cards
        )

    def active_fortified_castles(self):
        return [
            card
            for card in self.cards
            if _is_active_fortified_castle(card)
        ]


class ShieldZone(Zone):
    """Card zone that groups shield cards into countable slots."""

    def __init__(self, name="Shield"):
        super().__init__(name)
        self.slots = []

    def add(self, card, stack_on=None):
        self._repair_slots()

        if stack_on is None:
            slot = ShieldSlot()
            self.slots.append(slot)
            self.cards.append(card)
        else:
            slot = self.slot_for(stack_on)
            if slot is None:
                raise ValueError(
                    "Cannot stack a shield on a card outside the shield zone"
                )
            insert_at = self._slot_insert_index(slot)
            self.cards.insert(insert_at, card)

        slot.cards.append(card)
        self._mark_card(card, slot)

    def remove(self, card):
        self._repair_slots()

        slot = self.slot_for(card)
        if slot is not None and card in slot.cards:
            slot.cards.remove(card)
            if not slot.cards:
                self.slots.remove(slot)

        self.cards.remove(card)
        self._clear_card(card)

    def remove_slot(self, card):
        self._repair_slots()

        slot = self.slot_for(card)
        if slot is None:
            self.remove(card)
            return [card]

        cards = list(slot.cards)
        for slot_card in cards:
            if slot_card in self.cards:
                self.cards.remove(slot_card)
            self._clear_card(slot_card)

        self.slots.remove(slot)
        return cards

    def remove_cards(self, cards):
        self._repair_slots()

        removed = []
        for card in list(cards):
            if card not in self.cards:
                continue

            slot = self.slot_for(card)
            if slot is not None and card in slot.cards:
                slot.cards.remove(card)
                if not slot.cards:
                    self.slots.remove(slot)

            self.cards.remove(card)
            self._clear_card(card)
            removed.append(card)

        return removed

    def slot_for(self, card):
        self._repair_slots()

        for slot in self.slots:
            if card in slot.cards:
                return slot

        return None

    def slot_cards(self, card):
        slot = self.slot_for(card)
        if slot is None:
            return []

        return list(slot.cards)

    def shield_cards(self, card):
        slot = self.slot_for(card)
        if slot is None:
            return []

        return [
            slot_card
            for slot_card in slot.cards
            if not _is_active_fortified_castle(slot_card)
        ]

    def slot_index(self, card):
        slot = self.slot_for(card)
        if slot is None:
            return None

        return self.slots.index(slot)

    def slot_size(self, card):
        slot = self.slot_for(card)
        if slot is None:
            return 0

        return len(slot.cards)

    def visible_shields(self):
        self._repair_slots()
        shields = []

        for slot in self.slots:
            card = slot.visible_shield_card()
            if card is not None:
                shields.append(card)

        return shields

    def shield_count(self):
        return len(self.visible_shields())

    def fortifiable_shields(self):
        self._repair_slots()
        shields = []

        for slot in self.slots:
            if slot.has_fortified_castle():
                continue

            card = slot.visible_shield_card()
            if card is not None:
                shields.append(card)

        return shields

    def orphaned_fortified_castles(self):
        self._repair_slots()
        castles = []

        for slot in self.slots:
            if slot.visible_shield_cards():
                continue

            castles.extend(
                slot.active_fortified_castles()
            )

        return castles

    def _slot_insert_index(self, slot):
        indexes = [
            self.cards.index(card)
            for card in slot.cards
            if card in self.cards
        ]
        if not indexes:
            return len(self.cards)

        return max(indexes) + 1

    def _repair_slots(self):
        self._release_face_down_fortifications()

        if not self.slots:
            self._create_slots_for_untracked_cards()
            return

        known_ids = set()
        repaired_slots = []

        for slot in self.slots:
            for card in slot.cards:
                if card not in self.cards:
                    self._clear_card(card)

            kept = [
                card
                for card in slot.cards
                if card in self.cards
            ]
            if not kept:
                continue

            slot.cards = kept
            repaired_slots.append(slot)
            for card in kept:
                known_ids.add(id(card))
                self._mark_card(card, slot)

        for card in self.cards:
            if id(card) in known_ids:
                continue

            slot = ShieldSlot([card])
            repaired_slots.append(slot)
            known_ids.add(id(card))
            self._mark_card(card, slot)

        repaired_slots.sort(
            key=lambda slot: min(
                self.cards.index(card)
                for card in slot.cards
                if card in self.cards
            )
        )
        self.slots = repaired_slots

    def _create_slots_for_untracked_cards(self):
        for card in self.cards:
            slot = ShieldSlot([card])
            self.slots.append(slot)
            self._mark_card(card, slot)

    def _mark_card(self, card, slot):
        card.shield_slot = slot

    def _clear_card(self, card):
        if hasattr(card, "shield_slot"):
            card.shield_slot = None
        if hasattr(card, "is_fortified_castle"):
            card.is_fortified_castle = False

    def _release_face_down_fortifications(self):
        for card in self.cards:
            if (
                getattr(
                    card,
                    "is_fortified_castle",
                    False,
                )
                and not getattr(
                    card,
                    "shield_face_up",
                    False,
                )
            ):
                card.is_fortified_castle = False


def _is_active_fortified_castle(card):
    return (
        getattr(
            card,
            "is_fortified_castle",
            False,
        )
        and getattr(
            card,
            "shield_face_up",
            False,
        )
    )
