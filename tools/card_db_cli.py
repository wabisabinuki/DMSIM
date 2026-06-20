import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from card_db import CardDatabase, CardFactory


DEFAULT_CARD_DIR = Path("data/cards")


def main():
    parser = argparse.ArgumentParser(
        description="Inspect and validate DMSIM JSON card definitions."
    )
    parser.add_argument(
        "--card-dir",
        default=str(DEFAULT_CARD_DIR),
        help="Directory containing card JSON files.",
    )
    parser.add_argument(
        "--metadata-dir",
        default=None,
        help=(
            "Optional directory containing card metadata JSON files. "
            "Defaults to data/card_metadata when it exists."
        ),
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    subparsers.add_parser(
        "validate",
        help="Validate all card definitions.",
    )

    subparsers.add_parser(
        "list",
        help="List all known cards.",
    )

    show_parser = subparsers.add_parser(
        "show",
        help="Show one card definition.",
    )
    show_parser.add_argument("card_id")

    make_parser = subparsers.add_parser(
        "make",
        help="Instantiate one card and print its runtime summary.",
    )
    make_parser.add_argument("card_id")

    deck_parser = subparsers.add_parser(
        "deck",
        help="Validate a deck list against the card database.",
    )
    deck_parser.add_argument("deck_path")

    args = parser.parse_args()
    database = CardDatabase.load_dir(
        args.card_dir,
        metadata_directory=args.metadata_dir,
    )

    if args.command == "validate":
        errors = database.validate()
        warnings = database.validate_warnings()
        for warning in warnings:
            print(f"WARNING: {warning.format()}")
        if errors:
            for error in errors:
                print(f"ERROR: {error}")
            raise SystemExit(1)
        if warnings:
            print(
                f"OK: {len(database.all())} cards "
                f"({len(warnings)} warnings)"
            )
        else:
            print(f"OK: {len(database.all())} cards")

    elif args.command == "list":
        for card in database.all():
            print(
                f"{card['id']}: {card.get('name_ja', card['id'])} "
                f"({card['kind']})"
            )

    elif args.command == "show":
        print(
            json.dumps(
                database.get(args.card_id),
                ensure_ascii=False,
                indent=2,
            )
        )

    elif args.command == "make":
        factory = CardFactory(database)
        card = factory.create(args.card_id)
        ability_names = [
            ability.__class__.__name__
            for ability in getattr(card, "abilities", [])
        ]
        keyword_reminders = [
            {
                "ability_id": ability.ability_id,
                "keyword_name_ja": ability.keyword_name_ja,
                "reminder_text_ja": ability.reminder_text_ja,
            }
            for ability in getattr(card, "abilities", [])
            if hasattr(ability, "reminder_text_ja")
        ]

        print(f"name: {card.name}")
        print(f"name_ja: {getattr(card, 'name_ja', card.name)}")
        print(
            "effect_name_ja: "
            f"{getattr(card, 'effect_name_ja', card.name)}"
        )
        print(f"type: {card.__class__.__name__}")
        print(f"cost: {card.cost}")
        print(f"civilizations: {card.civilizations}")
        if hasattr(card, "race_ja"):
            print(f"race_ja: {card.race_ja}")
        print(
            "effect_texts_ja: "
            f"{list(getattr(card, 'effect_texts_ja', []))}"
        )
        print(f"abilities: {ability_names}")
        print(
            "keyword_reminders_ja: "
            f"{keyword_reminders}"
        )

        if getattr(card, "is_twinpact", False):
            print(f"creature_face: {card.creature_face.name}")
            print(
                "creature_face_name_ja: "
                f"{card.creature_face.name_ja}"
            )
            print(
                "creature_face_effect_name_ja: "
                f"{card.creature_face.effect_name_ja}"
            )
            print(
                "creature_face_race_ja: "
                f"{card.creature_face.race_ja}"
            )
            print(
                "creature_face_effect_texts_ja: "
                f"{list(card.creature_face.effect_texts_ja)}"
            )
            print(
                "creature_face_abilities: "
                f"{[ability.__class__.__name__ for ability in card.creature_face.abilities]}"
            )
            print(f"spell_face: {card.spell_face.name}")
            print(
                "spell_face_name_ja: "
                f"{card.spell_face.name_ja}"
            )
            print(
                "spell_face_effect_name_ja: "
                f"{card.spell_face.effect_name_ja}"
            )
            print(
                "spell_face_effect_texts_ja: "
                f"{list(card.spell_face.effect_texts_ja)}"
            )
            print(
                "spell_face_abilities: "
                f"{[ability.__class__.__name__ for ability in card.spell_face.abilities]}"
            )

    elif args.command == "deck":
        with Path(args.deck_path).open(
            "r",
            encoding="utf-8",
        ) as file:
            deck = json.load(file)

        total = 0
        errors = []

        for entry in deck.get("cards", []):
            card_reference = entry.get("id")
            count = entry.get("count", 0)
            total += count

            if card_reference is None:
                errors.append("Deck entry missing id")
            else:
                try:
                    database.resolve_card_id(card_reference)
                except KeyError:
                    errors.append(
                        f"Unknown card reference: {card_reference}"
                    )
            if count <= 0:
                errors.append(
                    f"{card_reference}: count must be positive"
                )

        if total != 40:
            errors.append(f"Deck must contain 40 cards, got {total}")

        if errors:
            for error in errors:
                print(f"ERROR: {error}")
            raise SystemExit(1)

        print(f"OK: {deck.get('name', '<unnamed>')} has {total} cards")


if __name__ == "__main__":
    main()
