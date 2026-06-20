"""スコープ内のクリーチャーへ能力を付与する継続的な付与能力。

置換効果型の能力（シールド・セイバー等）を、対象クリーチャーが持つ能力として
振る舞わせる。クロス先1体に付与する `CrossGrantAbility` と対になる、
スコープ指定（自分のクリーチャーすべて等）の付与。
"""

from abilities.base.replacement_ability import ReplacementAbility
from abilities.active_condition import active_if_matches
from core.card_filter_evaluator import CardFilterEvaluator
from core.creature_scope import creatures_for_scope
from core.pending_cards import is_card_pending
from effects.zones.zone_effect_utils import parse_zone


class ScopedGrantAbility(ReplacementAbility):

    def __init__(
        self,
        owner_card,
        game,
        ability,
        scope="own_creatures",
        active_if=None,
        active_zone="battle",
        optional=True,
        filter_spec=None,
        exclude_source=False,
    ):
        super().__init__()
        self.owner_card = owner_card
        self.game = game
        self.ability_spec = dict(ability)
        if (
            "id" not in self.ability_spec
            and "ability_id" in self.ability_spec
        ):
            self.ability_spec["id"] = self.ability_spec["ability_id"]
        self.scope = scope
        self.active_if = active_if
        # 付与元がこの領域にある間だけ付与が機能する。
        # 城（シールドゾーンで機能するG城など）は "shield" を指定する。
        self.active_zone = parse_zone(active_zone or "battle")
        self.optional = optional
        self.filter_spec = filter_spec or {}
        self.exclude_source = bool(exclude_source)
        # 継続(非置換)能力の「真の付与」を反映している対象クリーチャーと、
        # それぞれに付与した能力実体の対応表。SBA の reconcile から維持する。
        self._true_grants = {}
        self._is_replacement_grant_cached = None

    def is_grant_active(
        self,
    ):
        if self.owner_card.zone != self.active_zone:
            return False

        if is_card_pending(self.owner_card):
            return False

        # 付与元（この能力を持つカード）が能力無視を受けていれば、
        # 付与能力そのものが無視されるため付与は機能しない。
        if self.owner_card.are_abilities_ignored():
            return False

        if self.active_if is None:
            return True

        if self.active_if == "hyper_mode":
            return active_if_matches(
                self.active_if,
                self.owner_card,
                self.game,
            )

        if isinstance(self.active_if, dict):
            return active_if_matches(
                self.active_if,
                self.owner_card,
                self.game,
            )

        is_grant_active = getattr(
            self.active_if,
            "is_grant_active",
            None,
        )
        if is_grant_active is not None:
            return is_grant_active()

        return bool(self.active_if)

    def granted_abilities(
        self,
    ):
        if not self.is_grant_active():
            return []

        return [
            self._build_granted_ability(
                creature,
                optional=False,
            )
            for creature in self._recipients()
        ]

    def prevents_zone_change(
        self,
        event,
    ):
        return any(
            getattr(
                ability,
                "prevents_zone_change",
                lambda event: False,
            )(event)
            for ability in self.granted_abilities()
        )

    def applies(
        self,
        event,
    ):
        return bool(
            self._replacement_candidates(event)
        )

    def replace(
        self,
        event,
    ):
        candidates = self._replacement_candidates(
            event
        )
        if not candidates:
            return False

        if self.optional:
            proceed = self.game.choice_manager.select(
                self.owner_card.owner,
                [
                    True,
                    False,
                ],
                prompt=self._use_prompt(),
            )
            if not proceed:
                return False

        recipient = self.game.choice_manager.select(
            self.owner_card.owner,
            [
                candidate[0]
                for candidate in candidates
            ],
            prompt=self._choose_prompt(),
            min_count=1,
            max_count=1,
        )
        if recipient is None:
            return False

        for candidate, ability in candidates:
            if candidate is recipient:
                return ability.replace(event)

        return False

    def _replacement_candidates(
        self,
        event,
    ):
        if not self.is_grant_active():
            return []

        candidates = []
        for creature in self._recipients():
            ability = self._build_granted_ability(
                creature,
                optional=False,
            )
            applies = getattr(
                ability,
                "applies",
                None,
            )
            if applies is not None and applies(event):
                candidates.append(
                    (
                        creature,
                        ability,
                    )
                )

        return candidates

    def _recipients(
        self,
    ):
        return [
            creature
            for creature in creatures_for_scope(
                self.game,
                self.scope,
                self.owner_card,
            )
            if not (
                self.exclude_source
                and creature is self.owner_card
            )
            and self._matches_filter(creature)
            # 付与された能力の発生源は対象クリーチャー自身であるため、
            # 対象が能力無視を受けていれば付与された能力も無視される。
            and not self._abilities_ignored(creature)
        ]

    def _matches_filter(
        self,
        creature,
    ):
        if not self.filter_spec:
            return True

        return CardFilterEvaluator(
            self.game
        ).matches(
            creature,
            self.filter_spec,
            {
                "game": self.game,
                "player": self.owner_card.owner,
                "controller": self.owner_card.owner,
                "source_card": self.owner_card,
            },
        )

    def _abilities_ignored(
        self,
        creature,
    ):
        are_abilities_ignored = getattr(
            creature,
            "are_abilities_ignored",
            None,
        )
        return bool(
            are_abilities_ignored is not None
            and are_abilities_ignored()
        )

    def _build_granted_ability(
        self,
        creature,
        optional=None,
    ):
        from abilities.registry import create_ability

        spec = dict(self.ability_spec)
        if optional is not None:
            spec["optional"] = optional

        return create_ability(
            spec,
            creature,
            self.game,
        )

    def reconcile(
        self,
    ):
        """継続(非置換)能力の付与を、対象クリーチャーの abilities へ実体として
        反映・除去する。ブロッカーやスピードアタッカー等の常在型能力は
        `has_ability` で参照されるため、置換効果のように surface するだけでは
        機能しない。SBA から繰り返し呼ばれ、状態が安定したら False を返す。

        置換効果型(シールド・セイバー等)は従来通り surface 方式で扱うため、
        ここでは何もしない。
        """
        if self._is_replacement_grant():
            return False

        desired = (
            set(self._recipients())
            if self.is_grant_active()
            else set()
        )

        changed = False

        for recipient in list(self._true_grants.keys()):
            if recipient not in desired:
                self._remove_true_grant(recipient)
                changed = True

        for recipient in desired:
            if recipient not in self._true_grants:
                self._add_true_grant(recipient)
                changed = True

        return changed

    def has_active_true_grants(
        self,
    ):
        return bool(self._true_grants)

    def _is_replacement_grant(
        self,
    ):
        if self._is_replacement_grant_cached is None:
            from abilities.base.replacement_ability import (
                ReplacementAbility,
            )

            probe = self._build_granted_ability(
                self.owner_card,
                optional=False,
            )
            probes = (
                probe
                if isinstance(probe, list)
                else [probe]
            )
            self._is_replacement_grant_cached = any(
                isinstance(item, ReplacementAbility)
                for item in probes
            )

        return self._is_replacement_grant_cached

    def _add_true_grant(
        self,
        recipient,
    ):
        abilities = self._build_granted_ability(
            recipient,
            optional=False,
        )
        if not isinstance(abilities, list):
            abilities = [abilities]

        registered = []
        for ability in abilities:
            recipient.abilities.append(ability)
            registered.append(
                (
                    ability,
                    self._register_granted_ability(
                        recipient,
                        ability,
                    ),
                )
            )

        self._true_grants[recipient] = registered

    def _remove_true_grant(
        self,
        recipient,
    ):
        for ability, was_registered in self._true_grants.pop(
            recipient,
            [],
        ):
            if was_registered:
                ability.unregister()
            if ability in recipient.abilities:
                recipient.abilities.remove(ability)

    def _register_granted_ability(
        self,
        recipient,
        ability,
    ):
        if not getattr(
            recipient,
            "abilities_registered",
            False,
        ):
            return False

        register = getattr(
            ability,
            "register",
            None,
        )
        if register is None:
            return False

        register(self.game.event_manager)
        return True

    def _ability_name(
        self,
    ):
        return str(
            self.ability_spec.get(
                "id",
                self.ability_spec.get("ability_id", "ability"),
            )
        )

    def _use_prompt(
        self,
    ):
        prompt = self.ability_spec.get("use_prompt")
        if prompt is not None:
            return prompt

        if self._ability_name() == "shield_saver":
            return "Use Shield Saver?"

        return f"Use granted {self._ability_name()}?"

    def _choose_prompt(
        self,
    ):
        prompt = self.ability_spec.get("choose_prompt")
        if prompt is not None:
            return prompt

        if self._ability_name() == "shield_saver":
            return "Choose a creature for Shield Saver"

        return f"Choose a creature with granted {self._ability_name()}"
