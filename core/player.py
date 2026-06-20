"""
プレイヤーを表現するクラス。手札、マナ、シールド、バトルゾーン、墓地、デッキなどの各領域を保持します。
"""

# core/player.py

from core.protocols import ZoneContext

from zones.shield_zone import ShieldZone
from zones.zone import Zone
from zones.zone_type import ZoneType

from actions.end_turn_action import (
    EndTurnAction
)

from core.pending_cards import (
    first_visible_card,
    is_card_pending,
)
from core.seal_utils import is_ignored_by_seal, is_seal_card
from core.mana_payment import (
    auto_select_mana,
    can_pay_with_mana,
    card_civilizations,
    is_valid_payment,
    normalize_selections,
)


class Player:
    def __init__(self, name):
        self.name = name

        self.deck = Zone("Deck")
        self.hand = Zone("Hand")
        self.mana_zone = Zone("Mana")
        self.battle_zone = Zone("Battle")
        self.shield_zone = ShieldZone("Shield")
        self.graveyard = Zone("Graveyard")
        # 超次元ゾーン。通常は使わないが、特定カード（ゾロ・ア・スタート等）が
        # クリーチャーを一時的に置く領域として使用する。
        self.super_dimension = Zone("SuperDimension")

        self.has_charged_mana = False

    def draw(
        self,
        game: ZoneContext,
        count=1,
    ):

        state = getattr(game, "state", None)

        for _ in range(count):

            card = first_visible_card(
                self.deck.cards
            )

            if card is None:

                if state is not None:
                    lost = state.declare_loss(
                        self,
                        reason="deck_out",
                    )
                    if not lost:
                        return False

                print(
                    f"{self.name} loses by deck out"
                )

                return False

            game.card_mover.move(
                card=card,
                owner=self,
                from_zone=ZoneType.DECK,
                to_zone=ZoneType.HAND,
                reason="draw",
            )

            print(
                f"{self.name} drew "
                f"{card.name}"
            )

            if (
                state is not None
                and not self.deck.cards
            ):
                state.declare_loss(
                    self,
                    reason="deck_out",
                )
                if state.game_over:
                    return False

        return True

    def charge_mana(
        self,
        game: ZoneContext,
        card,
    ):

        if card.is_multicolored():

            card.tapped = True

        else:

            card.tapped = False

        game.card_mover.move(
            card=card,
            owner=self,
            from_zone=ZoneType.HAND,
            to_zone=ZoneType.MANA,
            reason="mana_charge",
        )

        self.has_charged_mana = True

        print(
            f"{self.name} charged "
            f"{card.name} to mana"
        )

    def untap_mana(self):
        for card in self.mana_zone.cards:
            card.untap(
                player=self,
                turn_start=True,
            )

    def mana_value(self, card):
        """カードの「マナの数字」（タップ時に生み出すマナの量）を返す。

        通常は1だが、バトルゾーンの常在型能力（ManaNumberAbility など）が
        値を上書きしている場合はその最大値を採用する。
        """

        value = 1

        for creature in self.battle_zone.cards:
            if (
                is_card_pending(creature)
                or is_seal_card(creature)
                or is_ignored_by_seal(creature)
            ):
                continue

            for ability in getattr(creature, "abilities", ()):
                getter = getattr(ability, "mana_value_for", None)
                if getter is None:
                    continue

                override = getter(card, self)
                if override is not None and override > value:
                    value = override

        return value

    def mana_civilizations(self, card):
        """カードがマナとして提供できる文明ビットを返す。

        通常はカード本来の文明だが、バトルゾーンの常在型能力
        （ManaAllCivilizationsAbility など）が文明を追加している場合は、それを
        OR で重ねて反映する（``card.civilizations`` 自体は書き換えない）。
        """

        civilizations = card_civilizations(card)

        for creature in self.battle_zone.cards:
            if (
                is_card_pending(creature)
                or is_seal_card(creature)
                or is_ignored_by_seal(creature)
            ):
                continue

            for ability in getattr(creature, "abilities", ()):
                getter = getattr(ability, "mana_civilizations_for", None)
                if getter is None:
                    continue

                override = getter(card, self)
                if override is not None:
                    civilizations |= override

        return civilizations

    def available_mana(self):
        return sum(
            self.mana_value(card)
            for card in self.mana_zone.cards
            if (
                not card.tapped
                and not is_card_pending(card)
            )
        )

    def _tappable_mana(self, spending_card=None):
        return [
            card
            for card in self.mana_zone.cards
            if (
                not card.tapped
                and (
                    not is_card_pending(card)
                    or card is spending_card
                )
            )
        ]

    def tap_mana(
        self,
        amount,
        spending_card=None,
        required_civilizations=None,
        choice_manager=None,
    ):
        if required_civilizations is None:
            required_civilizations = (
                self._play_civilizations(spending_card)
            )

        tappable = self._tappable_mana(
            spending_card
        )

        selected = None
        select_mana = getattr(
            choice_manager,
            "select_mana_to_pay",
            None,
        )
        if select_mana is not None:
            selected = select_mana(
                player=self,
                amount=amount,
                required_civilizations=required_civilizations,
                tappable_mana=tappable,
                mana_value=self.mana_value,
                mana_civilizations=self.mana_civilizations,
                spending_card=spending_card,
            )
            if selected is not None:
                selected = normalize_selections(
                    selected
                )
                if not is_valid_payment(
                    selected,
                    amount,
                    required_civilizations,
                    tappable,
                    self.mana_value,
                    self.mana_civilizations,
                ):
                    selected = None
        else:
            selected = self._select_mana_payment(
                amount,
                required_civilizations,
                tappable,
            )

        if selected is None:
            return False

        for selection in selected:
            selection.card.tapped = True

        return True

    def can_pay_cost(
        self,
        cost,
        required_civilizations=0,
        spending_card=None,
    ):
        return can_pay_with_mana(
            cost,
            required_civilizations,
            self._tappable_mana(spending_card),
            self.mana_value,
            self.mana_civilizations,
        )

    def _select_mana_payment(
        self,
        cost,
        required_civilizations,
        tappable,
    ):
        return auto_select_mana(
            cost,
            required_civilizations,
            tappable,
            self.mana_value,
            self.mana_civilizations,
        )

    def _select_mana_to_pay(
        self,
        cost,
        required_civilizations,
        tappable,
    ):
        """支払いに使うマナカードの一覧を返す（不可能なら None）。

        まず必要文明をそれぞれ別々のカードで賄い（文明数は軽減されない）、
        その後マナの数字の合計が ``cost`` 以上になるまでカードを足していく。
        """

        selected = self._select_mana_payment(
            cost,
            required_civilizations,
            tappable,
        )
        if selected is None:
            return None

        return [
            selection.card
            for selection in selected
        ]

    def get_zone(self, zone_type):

        mapping = {
            ZoneType.DECK: self.deck,
            ZoneType.HAND: self.hand,
            ZoneType.MANA: self.mana_zone,
            ZoneType.BATTLE: self.battle_zone,
            ZoneType.SHIELD: self.shield_zone,
            ZoneType.GRAVEYARD: self.graveyard,
            ZoneType.SUPER_DIMENSION: self.super_dimension,
        }

        return mapping[zone_type]
    
    def has_civilization(self, civilization):

        for card in self.mana_zone.cards:

            if is_card_pending(card):
                continue

            if self.mana_civilizations(card) & civilization:
                return True

        return False
    
    def can_play(self, card, game=None):
        cost = self._play_cost(card, game)

        return self.can_pay_cost(
            cost,
            self._play_civilizations(card),
            spending_card=card,
        )

    def _play_cost(self, card, game=None):
        get_current_cost = getattr(
            card,
            "get_current_cost",
            None,
        )
        if get_current_cost is None:
            return card.cost

        try:
            return get_current_cost(
                player=self,
                game=game,
            )
        except TypeError:
            try:
                return get_current_cost(
                    player=self,
                )
            except TypeError:
                return get_current_cost()

    def _play_civilizations(
        self,
        card,
    ):
        if card is None:
            return 0

        selected_face = getattr(
            card,
            "selected_face",
            None,
        )
        if selected_face is not None:
            return getattr(
                selected_face,
                "civilizations",
                0,
            )

        return getattr(
            card,
            "civilizations",
            0,
        ) or 0
    
    def can_generate_civilizations(
        self,
        mana_civilizations,
        required_civilizations,
    ):

        required_bits = []

        # 必要文明を分解
        for i in range(5):

            bit = 1 << i

            if required_civilizations & bit:
                required_bits.append(bit)

        used = [False] * len(mana_civilizations)

        def dfs(index):

            # 全文明満たした
            if index == len(required_bits):
                return True

            required = required_bits[index]

            for i, mana in enumerate(mana_civilizations):

                if used[i]:
                    continue

                # このマナが文明生成可能
                if mana & required:

                    used[i] = True

                    if dfs(index + 1):
                        return True

                    used[i] = False

            return False

        return dfs(0)
    
    def get_available_actions(
        self,
        game_controller,
    ):

        return (
            game_controller
            .action_generator
            .get_player_actions(
                self
            )
        )
