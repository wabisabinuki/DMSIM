from card_db.database import CardDatabase
from card_db.generic_spell import GenericSpellCard
from card_db.v2_ability_factory import V2AbilityFactory
from cards.card import CardType, Civilization
from cards.castle_card import CastleCard, GalaxyCastleCard
from cards.creature_card import CreatureCard
from cards.cross_gear_card import CrossGearCard
from cards.field_card import FieldCard
from cards.generic_card import GenericCard
from cards.twin_pact_card import TwinPactCard


CIVILIZATIONS = {
    "fire": Civilization.FIRE,
    "water": Civilization.WATER,
    "nature": Civilization.NATURE,
    "light": Civilization.LIGHT,
    "darkness": Civilization.DARKNESS,
    "zero": Civilization.ZERO,
}

SPECIAL_TYPES = {
    "evolution": "evolution",
    "進化": "evolution",
    "dream": "dream",
    "ドリーム": "dream",
    "dream creature": "dream",
    "ドリームクリーチャー": "dream",
    "hyper_mode": "hyper_mode",
    "hyper_mode": "hyper_mode",
    "ハイパーモード": "hyper_mode",
    "neo": "neo",
    "NEO": "neo",
    "galaxy": "galaxy",
    "Galaxy": "galaxy",
    "d2": "d2",
    "G": "galaxy",
    "g": "galaxy",
    "G城": "galaxy",
    "g城": "galaxy",
    "ギャラク城": "galaxy",
    "ギャラクシー": "galaxy",
}

CARD_TYPES = {
    "creature": CardType.CREATURE,
    "クリーチャー": CardType.CREATURE,
    "spell": CardType.SPELL,
    "呪文": CardType.SPELL,
    "cross_gear": CardType.CROSS_GEAR,
    "cross gear": CardType.CROSS_GEAR,
    "クロスギア": CardType.CROSS_GEAR,
    "castle": CardType.CASTLE,
    "城": CardType.CASTLE,
    "weapon": CardType.WEAPON,
    "ウエポン": CardType.WEAPON,
    "fortress": CardType.FORTRESS,
    "フォートレス": CardType.FORTRESS,
    "heartbeat": CardType.HEARTBEAT,
    "鼓動": CardType.HEARTBEAT,
    "field": CardType.FIELD,
    "フィールド": CardType.FIELD,
    "core": CardType.CORE,
    "コア": CardType.CORE,
    "aura": CardType.AURA,
    "オーラ": CardType.AURA,
    "ceremony": CardType.CEREMONY,
    "儀": CardType.CEREMONY,
    "星雲": CardType.CEREMONY,
    "儀(星雲)": CardType.CEREMONY,
    "artifact": CardType.ARTIFACT,
    "土地": CardType.LAND,
    "land": CardType.LAND,
    "rule_plus": CardType.RULE_PLUS,
    "rule plus": CardType.RULE_PLUS,
    "ルール・プラス": CardType.RULE_PLUS,
    "tamaseed": CardType.TAMASEED,
    "タマシード": CardType.TAMASEED,
    "duelist": CardType.DUELIST,
    "デュエリスト": CardType.DUELIST,
    "cell": CardType.CELL,
    "セル": CardType.CELL,
}

CROSS_GEAR_KINDS = {
    "cross_gear",
    "cross gear",
    "クロスギア",
}

FIELD_KINDS = {
    "field",
    "フィールド",
}

GENERIC_KINDS = set(CARD_TYPES) - {
    "creature",
    "クリーチャー",
    "spell",
    "呪文",
} - CROSS_GEAR_KINDS - FIELD_KINDS

GALAXY_CASTLE_KINDS = {
    "galaxy_castle",
    "galaxy castle",
    "g_castle",
    "g castle",
    "g城",
    "G城",
    "ギャラク城",
}


class CardFactory:
    """CardDatabaseの定義からゲーム内カードインスタンスを作る。"""

    def __init__(
        self,
        database,
    ):
        self.database = database

    @classmethod
    def from_dir(
        cls,
        directory,
        metadata_directory=None,
    ):
        return cls(
            CardDatabase.load_dir(
                directory,
                metadata_directory=metadata_directory,
            )
        )

    def create(
        self,
        card_id,
        game=None,
    ):
        return self.create_from_definition(
            self.database.get(card_id),
            game=game,
        )

    def create_many(
        self,
        entries,
        game=None,
    ):
        cards = []

        for entry in entries:
            card_id = self._entry_card_reference(entry)
            count = entry.get("count", 1)

            for _ in range(count):
                cards.append(
                    self.create(
                        card_id,
                        game=game,
                    )
                )

        return cards

    def create_from_definition(
        self,
        definition,
        game=None,
    ):
        kind = definition["kind"]
        kind_key = str(kind).lower()
        special_types = self._special_types(
            definition.get(
                "special_types",
                (),
            )
        )

        if kind_key == "creature" or kind == "クリーチャー":
            card = CreatureCard(
                name=self._runtime_name(definition),
                cost=definition["cost"],
                civilizations=self._civilizations(
                    definition["civilizations"]
                ),
                power=definition["power"],
                hyper_power=definition.get("hyper_power"),
                special_types=special_types,
                name_ja=definition.get("name_ja"),
                effect_name_ja=definition.get("effect_name_ja"),
                race_ja=definition.get("race_ja"),
                effect_texts_ja=self._text_list(
                    definition.get("effect_texts_ja")
                ),
            )

        elif kind_key == "spell" or kind == "呪文":
            card = GenericSpellCard(
                name=self._runtime_name(definition),
                civilizations=self._civilizations(
                    definition["civilizations"]
                ),
                cost=definition["cost"],
                effect_specs=definition.get("effects", []),
                name_ja=definition.get("name_ja"),
                effect_name_ja=definition.get("effect_name_ja"),
                effect_texts_ja=self._text_list(
                    definition.get("effect_texts_ja")
                ),
            )

        elif kind_key == "twinpact":
            creature_face = self.create_from_definition(
                definition["creature"],
                game=game,
            )
            spell_face = self.create_from_definition(
                definition["spell"],
                game=game,
            )
            card = TwinPactCard(
                name=self._runtime_name(definition),
                creature_face=creature_face,
                spell_face=spell_face,
                name_ja=definition.get("name_ja"),
                effect_name_ja=definition.get("effect_name_ja"),
                effect_texts_ja=self._text_list(
                    definition.get("effect_texts_ja")
                ) if "effect_texts_ja" in definition else None,
            )

        elif kind_key == "castle" or kind == "城":
            castle_cls = (
                GalaxyCastleCard
                if self._is_galaxy_castle(
                    special_types
                )
                else CastleCard
            )
            kwargs = {}
            if castle_cls is GalaxyCastleCard:
                kwargs["game"] = game

            card = castle_cls(
                name=self._runtime_name(definition),
                cost=definition["cost"],
                civilizations=self._civilizations(
                    definition["civilizations"]
                ),
                special_types=special_types,
                name_ja=definition.get("name_ja"),
                effect_name_ja=definition.get("effect_name_ja"),
                effect_texts_ja=self._text_list(
                    definition.get("effect_texts_ja")
                ),
                **kwargs,
            )

        elif kind_key in GALAXY_CASTLE_KINDS or kind in GALAXY_CASTLE_KINDS:
            card = GalaxyCastleCard(
                name=self._runtime_name(definition),
                cost=definition["cost"],
                civilizations=self._civilizations(
                    definition["civilizations"]
                ),
                game=game,
                special_types=(
                    special_types
                    if "galaxy" in special_types
                    else (
                        *special_types,
                        "galaxy",
                    )
                ),
                name_ja=definition.get("name_ja"),
                effect_name_ja=definition.get("effect_name_ja"),
                effect_texts_ja=self._text_list(
                    definition.get("effect_texts_ja")
                ),
            )

        elif kind_key in CROSS_GEAR_KINDS or kind in CROSS_GEAR_KINDS:
            card = CrossGearCard(
                name=self._runtime_name(definition),
                cost=definition["cost"],
                civilizations=self._civilizations(
                    definition["civilizations"]
                ),
                special_types=special_types,
                name_ja=definition.get("name_ja"),
                effect_name_ja=definition.get("effect_name_ja"),
                effect_texts_ja=self._text_list(
                    definition.get("effect_texts_ja")
                ),
                game=game,
            )

        elif kind_key in FIELD_KINDS or kind in FIELD_KINDS:
            card = FieldCard(
                name=self._runtime_name(definition),
                cost=definition["cost"],
                civilizations=self._civilizations(
                    definition["civilizations"]
                ),
                special_types=special_types,
                name_ja=definition.get("name_ja"),
                effect_name_ja=definition.get("effect_name_ja"),
                effect_texts_ja=self._text_list(
                    definition.get("effect_texts_ja")
                ),
                game=game,
            )

        elif kind_key in GENERIC_KINDS or kind in GENERIC_KINDS:
            card = GenericCard(
                name=self._runtime_name(definition),
                cost=definition["cost"],
                civilizations=self._civilizations(
                    definition["civilizations"]
                ),
                card_types=(
                    self._card_type(kind),
                ),
                name_ja=definition.get("name_ja"),
                effect_name_ja=definition.get("effect_name_ja"),
                effect_texts_ja=self._text_list(
                    definition.get("effect_texts_ja")
                ),
            )

        else:
            raise ValueError(f"Unknown card kind: {kind}")

        card.abilities.extend(
            V2AbilityFactory(
                game
            ).create_many(
                definition.get("abilities", {}),
                card,
            )
        )

        return card

    def _entry_card_reference(
        self,
        entry,
    ):
        return entry["id"]

    def _runtime_name(
        self,
        definition,
    ):
        return (
            definition.get("name_ja")
            or definition.get("id")
            or "<unnamed>"
        )

    def _civilizations(
        self,
        names,
    ):
        value = 0

        for name in names:
            key = name.lower()
            if key not in CIVILIZATIONS:
                raise ValueError(f"Unknown civilization: {name}")
            value |= CIVILIZATIONS[key]

        return value

    def _special_types(
        self,
        names,
    ):

        special_types = []

        for name in names:
            key = str(name).lower()
            special_types.append(
                SPECIAL_TYPES.get(
                    key,
                    name,
                )
            )

        return tuple(special_types)

    def _is_galaxy_castle(
        self,
        special_types,
    ):

        return "galaxy" in special_types

    def _card_type(
        self,
        name,
    ):

        key = str(name).lower()
        if key not in CARD_TYPES:
            raise ValueError(f"Unknown card type: {name}")

        return CARD_TYPES[key]

    def _text_list(
        self,
        value,
    ):

        if value is None:
            return ()

        if isinstance(value, str):
            return (value,)

        return tuple(value)
