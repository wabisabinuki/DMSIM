import json
import copy
from pathlib import Path

from card_db.card_definition_validator import CardDefinitionValidator


METADATA_KEYS = (
    "name_ja",
    "effect_name_ja",
    "race_ja",
    "effect_texts_ja",
)

GENERIC_CARD_KINDS = (
    "cross_gear",
    "cross gear",
    "クロスギア",
    "castle",
    "城",
    "galaxy_castle",
    "galaxy castle",
    "g_castle",
    "g castle",
    "g城",
    "G城",
    "ギャラク城",
    "weapon",
    "ウエポン",
    "fortress",
    "フォートレス",
    "heartbeat",
    "鼓動",
    "field",
    "フィールド",
    "core",
    "コア",
    "aura",
    "オーラ",
    "ceremony",
    "儀",
    "星雲",
    "儀(星雲)",
    "artifact",
    "土地",
    "land",
    "rule_plus",
    "rule plus",
    "ルール・プラス",
    "tamaseed",
    "タマシード",
    "duelist",
    "デュエリスト",
    "cell",
    "セル",
)


class CardDatabase:
    """JSONカード定義を読み込み、IDで参照する軽量DB。"""

    def __init__(
        self,
        cards,
        metadata_errors=None,
    ):
        self.cards = cards
        self.metadata_errors = list(
            metadata_errors or ()
        )
        self.by_id = {}

        for card in cards:
            card_id = card["id"]
            if card_id in self.by_id:
                raise ValueError(f"Duplicate card id: {card_id}")
            self.by_id[card_id] = card

    @classmethod
    def load_dir(
        cls,
        directory,
        metadata_directory=None,
    ):
        cards = []
        directory = Path(directory)

        for path in sorted(directory.glob("*.json")):
            cards.extend(
                cls._load_file(path)
            )

        metadata_directory = cls._resolve_metadata_directory(
            directory,
            metadata_directory,
        )
        metadata, metadata_errors = cls._load_metadata_dir(
            metadata_directory
        )
        cards, merge_errors = cls._merge_metadata(
            cards,
            metadata,
        )

        return cls(
            cards,
            metadata_errors=[
                *metadata_errors,
                *merge_errors,
            ],
        )

    @staticmethod
    def _load_file(
        path,
    ):
        with path.open(
            "r",
            encoding="utf-8",
        ) as file:
            payload = json.load(file)

        if isinstance(payload, list):
            return payload

        return CardDatabase._normalize_card_entries(
            payload.get(
                "cards",
                [],
            )
        )

    @staticmethod
    def _normalize_card_entries(
        cards,
    ):
        if isinstance(cards, dict):
            return [
                {
                    "id": card_id,
                    **definition,
                }
                for card_id, definition in cards.items()
            ]
        return cards

    @classmethod
    def _resolve_metadata_directory(
        cls,
        card_directory,
        metadata_directory,
    ):
        if metadata_directory is not None:
            return Path(metadata_directory)

        name = card_directory.name
        if name.endswith("cards"):
            sibling = card_directory.parent / (
                name[: -len("cards")] + "card_metadata"
            )
            if sibling.exists():
                return sibling

        default = card_directory.parent / "card_metadata"
        if default.exists():
            return default

        return None

    @classmethod
    def _load_metadata_dir(
        cls,
        directory,
    ):
        if directory is None:
            return {}, []

        directory = Path(directory)
        if not directory.exists():
            return {}, [
                f"metadata directory not found: {directory}"
            ]

        metadata = {}
        errors = []

        for path in sorted(directory.glob("*.json")):
            entries, file_errors = cls._load_metadata_file(
                path
            )
            errors.extend(file_errors)

            for entry in entries:
                card_id = entry.get("id")
                if not isinstance(card_id, str):
                    errors.append(
                        f"{path}: metadata entry missing string id"
                    )
                    continue
                if card_id in metadata:
                    errors.append(
                        f"{path}: duplicate metadata id: {card_id}"
                    )
                    continue
                metadata[card_id] = entry

        return metadata, errors

    @classmethod
    def _load_metadata_file(
        cls,
        path,
    ):
        with path.open(
            "r",
            encoding="utf-8",
        ) as file:
            payload = json.load(file)

        if isinstance(payload, list):
            return payload, []

        if not isinstance(payload, dict):
            return [], [
                f"{path}: metadata file must be an object or list"
            ]

        if "cards" in payload:
            cards = payload["cards"]
            if isinstance(cards, list):
                return cards, []
            if not isinstance(cards, dict):
                return [], [
                    f"{path}: cards must be a list or object"
                ]
            source = cards
        else:
            source = payload

        entries = []
        errors = []
        for card_id, metadata in source.items():
            if not isinstance(metadata, dict):
                errors.append(
                    f"{path}: metadata for {card_id} must be an object"
                )
                continue
            entries.append(
                {
                    "id": card_id,
                    **metadata,
                }
            )

        return entries, errors

    @classmethod
    def _merge_metadata(
        cls,
        cards,
        metadata,
    ):
        if not metadata:
            return cards, []

        merged_cards = [
            copy.deepcopy(card)
            for card in cards
        ]
        by_id = {
            card["id"]: card
            for card in merged_cards
            if "id" in card
        }
        errors = []

        for card_id, entry in metadata.items():
            card = by_id.get(card_id)
            if card is None:
                errors.append(
                    f"{card_id}: metadata refers to unknown card"
                )
                continue

            cls._apply_metadata(
                card,
                entry,
            )

        return merged_cards, errors

    @classmethod
    def _apply_metadata(
        cls,
        card,
        metadata,
    ):
        for key in METADATA_KEYS:
            if key in metadata:
                card[key] = metadata[key]

        for face_key in ("creature", "spell"):
            face_metadata = metadata.get(face_key)
            if not isinstance(face_metadata, dict):
                continue

            face = card.get(face_key)
            if not isinstance(face, dict):
                continue

            for key in METADATA_KEYS:
                if key in face_metadata:
                    face[key] = face_metadata[key]

    def get(
        self,
        card_id,
    ):
        return self.by_id[
            self.resolve_card_id(card_id)
        ]

    def resolve_card_id(
        self,
        card_reference,
    ):
        if card_reference in self.by_id:
            return card_reference

        raise KeyError(card_reference)

    def all(
        self,
    ):
        return list(self.cards)

    def validate(
        self,
    ):
        errors = list(
            self.metadata_errors
        )

        for card in self.cards:
            errors.extend(
                self._validate_card(card)
            )

        return errors

    def validate_warnings(
        self,
    ):
        warnings = []
        for card in self.cards:
            warnings.extend(
                self._validate_card_warnings(card)
            )

        return warnings

    def _validate_card(
        self,
        card,
        prefix=None,
    ):
        errors = []
        label = prefix or card.get("id", "<unknown>")
        kind = card.get("kind")
        kind_key = str(kind).lower()

        for key in ("id", "kind"):
            if prefix and key == "id":
                continue
            if key not in card:
                errors.append(f"{label}: missing {key}")

        for removed_key in (
            "name",
            "deck_alias",
            "race",
        ):
            if removed_key in card:
                errors.append(
                    f"{label}.{removed_key}: field is no longer supported"
                )

        if "name_ja" not in card:
            errors.append(f"{label}: missing name_ja")

        if "name_ja" in card:
            errors.extend(
                self._validate_optional_string(
                    card["name_ja"],
                    f"{label}.name_ja",
                )
            )

        if "effect_name_ja" in card:
            errors.extend(
                self._validate_optional_string(
                    card["effect_name_ja"],
                    f"{label}.effect_name_ja",
                )
            )

        if kind_key == "creature" or kind == "クリーチャー":
            for key in ("cost", "civilizations", "power", "race_ja"):
                if key not in card:
                    errors.append(f"{label}: missing {key}")
            if "hyper_power" in card and not isinstance(
                card["hyper_power"],
                int,
            ):
                errors.append(f"{label}.hyper_power: must be an integer")
            if "effect_texts_ja" in card:
                errors.extend(
                    self._validate_text_list(
                        card["effect_texts_ja"],
                        f"{label}.effect_texts_ja",
                    )
                )

        elif kind_key == "spell" or kind == "呪文":
            for key in ("cost", "civilizations"):
                if key not in card:
                    errors.append(f"{label}: missing {key}")
            if "effect_texts_ja" in card:
                errors.extend(
                    self._validate_text_list(
                        card["effect_texts_ja"],
                        f"{label}.effect_texts_ja",
                    )
                )

        elif kind_key == "twinpact":
            if "effect_texts_ja" in card:
                errors.extend(
                    self._validate_text_list(
                        card["effect_texts_ja"],
                        f"{label}.effect_texts_ja",
                    )
                )
            creature = card.get("creature")
            spell = card.get("spell")
            if not creature:
                errors.append(f"{label}: missing creature face")
            else:
                errors.extend(
                    self._validate_card(
                        creature,
                        prefix=f"{label}.creature",
                    )
                )
            if not spell:
                errors.append(f"{label}: missing spell face")
            else:
                errors.extend(
                    self._validate_card(
                        spell,
                        prefix=f"{label}.spell",
                    )
                )

        elif (
            kind_key in GENERIC_CARD_KINDS
            or kind in GENERIC_CARD_KINDS
        ):
            for key in ("cost", "civilizations"):
                if key not in card:
                    errors.append(f"{label}: missing {key}")
            if "effect_texts_ja" in card:
                errors.extend(
                    self._validate_text_list(
                        card["effect_texts_ja"],
                        f"{label}.effect_texts_ja",
                    )
                )

        else:
            errors.append(f"{label}: unknown kind {kind!r}")

        errors.extend(
            CardDefinitionValidator(
                allow_legacy=True,
            ).validate_card(
                card,
                label=label,
            )
        )

        return errors

    def _validate_card_warnings(
        self,
        card,
        prefix=None,
        card_id=None,
        card_name=None,
    ):
        label = prefix or card.get("id", "<unknown>")
        card_id = card_id or card.get("id", label)
        card_name = card_name or self._card_display_name(card)

        warnings = CardDefinitionValidator(
            allow_legacy=True,
        ).validate_card_warnings(
            card,
            label=label,
            card_id=card_id,
            card_name=card_name,
        )

        if str(card.get("kind")).lower() == "twinpact":
            for face_key in (
                "creature",
                "spell",
            ):
                face = card.get(face_key)
                if not isinstance(face, dict):
                    continue
                warnings.extend(
                    self._validate_card_warnings(
                        face,
                        prefix=f"{label}.{face_key}",
                        card_id=card_id,
                        card_name=card_name,
                    )
                )

        return warnings

    def _card_display_name(
        self,
        card,
    ):
        return (
            card.get("name_ja")
            or card.get("id", "<unknown>")
        )

    def _validate_optional_string(
        self,
        value,
        label,
    ):
        if isinstance(value, str):
            return []

        return [f"{label}: must be a string"]

    def _validate_text_list(
        self,
        value,
        label,
    ):
        if isinstance(value, str):
            return []

        if not isinstance(value, list):
            return [f"{label}: must be a string or list of strings"]

        errors = []
        for index, item in enumerate(value):
            if not isinstance(item, str):
                errors.append(
                    f"{label}[{index}]: must be a string"
                )

        return errors
