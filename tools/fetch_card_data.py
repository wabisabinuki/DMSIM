import argparse
import html
import json
import re
import sys
import time
import urllib.request
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DETAIL_URL = "https://dm.takaratomy.co.jp/card/detail/?id={official_id}"
PRODUCT_URL = "https://dm.takaratomy.co.jp/product/{slug}/"
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; DMSIM-card-data-fetcher/1.0)"
    ),
}

FIELD_CLASSES = {
    "card_type": "type",
    "civilization": "civil",
    "rarity": "rarelity",
    "power": "power",
    "cost": "cost",
    "race": "race",
}

CIVILIZATION_JA_EN = {
    "光": "light",
    "水": "water",
    "闇": "darkness",
    "火": "fire",
    "自然": "nature",
    "ゼロ": "zero",
    "無色": "zero",
}

KIND_JA_EN = {
    "クリーチャー": "creature",
    "進化クリーチャー": "creature",
    "呪文": "spell",
    "G城": "castle",
    "Ｇ城": "castle",
    "フィールド": "field",
    "D2フィールド": "field",
    "Ｄ2フィールド": "field",
}

SPECIAL_TYPES_BY_CARD_TYPE = {
    "G城": ["galaxy"],
    "Ｇ城": ["galaxy"],
    "進化クリーチャー": ["evolution"],
    "D2フィールド": ["d2"],
    "Ｄ2フィールド": ["d2"],
}

EMPTY_ABILITIES = {
    "keyword": [],
    "static": [],
    "triggered": [],
    "activated": [],
    "replacement": [],
}

FULLWIDTH_DIGITS = str.maketrans(
    "０１２３４５６７８９",
    "0123456789",
)


class CardDetailParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.card_names = []
        self.packnames = []
        self.fields = {
            name: []
            for name in FIELD_CLASSES
        }
        self.skills = []

        self._card_name_depth = 0
        self._card_name_parts = None
        self._packname_depth = 0
        self._packname_parts = None
        self._field_name = None
        self._field_depth = 0
        self._field_parts = None
        self._skills_depth = 0
        self._skill_li_depth = 0
        self._skill_parts = None

    @property
    def card_name(self):
        if not self.card_names:
            return ""
        return self.card_names[0]

    @property
    def packname(self):
        if not self.packnames:
            return ""
        return self.packnames[0]

    def handle_starttag(self, tag, attrs):
        classes = _classes(attrs)

        if tag == "br" and self._skill_li_depth:
            self._flush_skill_parts()
            return

        if self._card_name_depth:
            self._card_name_depth += 1
        if self._packname_depth:
            self._packname_depth += 1
        if self._field_depth:
            self._field_depth += 1
        if self._skills_depth:
            self._skills_depth += 1
        if self._skill_li_depth:
            self._skill_li_depth += 1

        if tag == "h3" and "card-name" in classes:
            self._card_name_depth = 1
            self._card_name_parts = []
            self._packname_parts = []

        if (
            self._card_name_depth
            and tag == "span"
            and "packname" in classes
        ):
            self._packname_depth = 1

        if tag == "td" and not self._field_depth:
            for field_name, class_name in FIELD_CLASSES.items():
                if class_name in classes:
                    self._field_name = field_name
                    self._field_depth = 1
                    self._field_parts = []
                    break

        if (
            tag == "td"
            and "skills" in classes
            and not self._skills_depth
        ):
            self._skills_depth = 1

        if self._skills_depth and tag == "li" and not self._skill_li_depth:
            self._skill_li_depth = 1
            self._skill_parts = []

    def handle_startendtag(self, tag, attrs):
        if tag == "br" and self._skill_li_depth:
            self._flush_skill_parts()
            return
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if self._skill_li_depth:
            self._skill_li_depth -= 1
            if self._skill_li_depth == 0:
                self._flush_skill_parts()
                self._skill_parts = None

        if self._skills_depth:
            self._skills_depth -= 1

        if self._field_depth:
            self._field_depth -= 1
            if self._field_depth == 0:
                self.fields[self._field_name].append(
                    clean_text("".join(self._field_parts or []))
                )
                self._field_name = None
                self._field_parts = None

        if self._packname_depth:
            self._packname_depth -= 1

        if self._card_name_depth:
            self._card_name_depth -= 1
            if self._card_name_depth == 0:
                self.card_names.append(
                    clean_text("".join(self._card_name_parts or []))
                )
                self.packnames.append(
                    clean_text("".join(self._packname_parts or []))
                )
                self._card_name_parts = None
                self._packname_parts = None

    def handle_data(self, data):
        if self._card_name_depth:
            if self._packname_depth:
                self._packname_parts.append(data)
            else:
                self._card_name_parts.append(data)

        if self._field_name:
            self._field_parts.append(data)

        if self._skill_li_depth and self._skill_parts is not None:
            self._skill_parts.append(data)

    def _flush_skill_parts(self):
        skill = clean_text("".join(self._skill_parts or []))
        if skill:
            self.skills.append(skill)
        self._skill_parts = []

    def details(self):
        return {
            "name_ja": self.card_name,
            "packname": self.packname,
            "skills": [
                skill
                for skill in unique_in_order(self.skills)
                if not is_parenthetical_only(skill)
            ],
            "field_values": {
                name: list(values)
                for name, values in self.fields.items()
            },
            **{
                name: values[0] if values else ""
                for name, values in self.fields.items()
            },
        }


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Fetch Duel Masters official card facts and emit DMSIM JSON "
            "skeletons."
        )
    )
    parser.add_argument(
        "set_name",
        help="Set file stem, for example DM26-RP1.",
    )
    parser.add_argument(
        "cards",
        nargs="*",
        help=(
            "Card numbers, numeric ranges, or official id suffixes, such as "
            "53, 1-10, or OR001."
        ),
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Fetch all card ids listed on the product page.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Merge fetched entries into data/impl_cards and metadata.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help=(
            "With --write, replace existing entries instead of skipping "
            "duplicate card ids."
        ),
    )
    args = parser.parse_args()

    if args.all and args.cards:
        parser.error("Specify card numbers or --all, not both.")
    if not args.all and not args.cards:
        parser.error("Specify at least one card number or --all.")
    if args.overwrite and not args.write:
        parser.error("--overwrite requires --write.")

    warnings = []
    set_name = args.set_name
    slug = official_slug(set_name)

    if args.all:
        product_html = fetch_url(PRODUCT_URL.format(slug=slug))
        official_ids = collect_product_official_ids(product_html, slug)
        if not official_ids:
            raise SystemExit(f"No card detail ids found for {slug}.")
        time.sleep(1)
    else:
        official_ids = unique_in_order(
            official_id_from_arg(slug, card)
            for card in expand_card_args(args.cards, parser)
        )

    impl_cards = {}
    metadata_cards = {}
    for index, official_id in enumerate(official_ids):
        if index:
            time.sleep(1)

        details = fetch_card_detail(official_id)
        entry = build_card_entries(
            set_name,
            slug,
            official_id,
            details,
            warnings,
        )
        if entry is None:
            continue

        card_id, impl_entry, metadata_entry = entry
        impl_cards[card_id] = impl_entry
        metadata_cards[card_id] = metadata_entry

    for warning in warnings:
        print(f"WARNING: {warning}", file=sys.stderr)

    if args.write:
        write_entries(
            set_name,
            impl_cards,
            metadata_cards,
            overwrite=args.overwrite,
        )
        return

    print(
        json.dumps(
            {
                "impl_cards": {
                    "cards": impl_cards,
                },
                "impl_card_metadata": {
                    "cards": metadata_cards,
                },
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def fetch_card_detail(official_id):
    source = fetch_url(
        DETAIL_URL.format(
            official_id=official_id,
        )
    )
    parser = CardDetailParser()
    parser.feed(source)
    parser.close()
    return parser.details()


def fetch_url(url):
    request = urllib.request.Request(
        url,
        headers=REQUEST_HEADERS,
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def build_card_entries(set_name, slug, official_id, details, warnings):
    name_ja = details["name_ja"]
    if not name_ja:
        warnings.append(f"{official_id}: card-name is empty; skipped")
        return None

    rarity = details["rarity"]
    pack_number = pack_number_from_packname(details["packname"])
    if not rarity or not pack_number:
        warnings.append(
            f"{official_id}: missing rarity or pack number; skipped"
        )
        return None

    pack_set = pack_set_from_packname(details["packname"])
    if pack_set and official_slug(pack_set) != slug:
        warnings.append(
            f"{official_id}: pack set {pack_set!r} does not match {set_name!r}"
        )

    card_id = f"{set_name.lower()}.{rarity}.{pack_number}"
    kind = KIND_JA_EN.get(details["card_type"])
    if kind is None:
        warnings.append(
            f"{card_id}: unsupported card type {details['card_type']!r}; skipped"
        )
        return None

    handled_multiple_fields = set()

    cost = parse_int(details["cost"])
    if cost is None:
        warnings.append(
            f"{card_id}: unsupported cost {details['cost']!r}; skipped"
        )
        return None

    civilizations = parse_civilizations(
        details["civilization"],
        warnings,
        card_id,
    )
    if not civilizations:
        warnings.append(
            f"{card_id}: no supported civilizations found; skipped"
        )
        return None

    race_ja = split_race(details["race"])
    metadata_entry = {
        "name_ja": name_ja,
        "effect_name_ja": "",
    }
    if race_ja:
        metadata_entry["race_ja"] = race_ja

    metadata_entry["effect_texts_ja"] = details["skills"]

    special_types = SPECIAL_TYPES_BY_CARD_TYPE.get(details["card_type"])
    power = None
    hyper_power = None

    if kind == "creature":
        power, hyper_power = parse_power_values(details, warnings, card_id)
        if has_multiple_field_values(details, "power"):
            handled_multiple_fields.add("power")
        if power is None:
            warnings.append(
                f"{card_id}: unsupported power {details['power']!r}; skipped"
            )
            return None
        if hyper_power is not None:
            special_types = ["hyper_mode"]

    impl_entry = build_impl_entry(
        kind=kind,
        cost=cost,
        civilizations=civilizations,
        power=power,
        special_types=special_types,
        hyper_power=hyper_power,
    )

    warn_on_multiple_field_values(
        details,
        warnings,
        official_id,
        handled_multiple_fields,
    )

    return card_id, impl_entry, metadata_entry


def collect_product_official_ids(source, slug):
    source = html.unescape(source)
    pattern = re.compile(
        r"detail/\?id=("
        + re.escape(slug)
        + r"-[A-Za-z0-9]+)",
        re.IGNORECASE,
    )
    official_ids = []
    seen = set()
    for match in pattern.finditer(source):
        official_id = match.group(1)
        key = official_id.lower()
        if key in seen:
            continue
        seen.add(key)
        official_ids.append(official_id)
    return official_ids


def build_impl_entry(
    kind,
    cost,
    civilizations,
    power=None,
    special_types=None,
    hyper_power=None,
):
    entry = {
        "kind": kind,
    }

    if special_types:
        entry["special_types"] = list(special_types)

    entry["cost"] = cost
    entry["civilizations"] = civilizations

    if kind == "creature":
        entry["power"] = power
        if hyper_power is not None:
            entry["hyper_power"] = hyper_power

    entry["abilities"] = empty_abilities()

    if kind == "spell":
        entry["effects"] = []

    return entry


def write_entries(set_name, impl_cards, metadata_cards, overwrite=False):
    impl_path = ROOT / "data" / "impl_cards" / f"{set_name}.json"
    metadata_path = ROOT / "data" / "impl_card_metadata" / f"{set_name}.json"

    impl_result = merge_entries(impl_path, impl_cards, overwrite=overwrite)
    metadata_result = merge_entries(
        metadata_path,
        metadata_cards,
        overwrite=overwrite,
    )

    print(
        f"{impl_path}: added {impl_result['added']}, "
        f"overwritten {impl_result['overwritten']}, "
        f"skipped {impl_result['skipped']}"
    )
    print(
        f"{metadata_path}: added {metadata_result['added']}, "
        f"overwritten {metadata_result['overwritten']}, "
        f"skipped {metadata_result['skipped']}"
    )


def merge_entries(path, entries, overwrite=False):
    payload = load_cards_payload(path)
    cards = payload["cards"]
    result = {
        "added": 0,
        "overwritten": 0,
        "skipped": 0,
    }

    for card_id, entry in entries.items():
        if card_id in cards:
            if not overwrite:
                print(
                    f"WARNING: {path}: {card_id} already exists; skipped",
                    file=sys.stderr,
                )
                result["skipped"] += 1
                continue
            cards[card_id] = entry
            result["overwritten"] += 1
        else:
            cards[card_id] = entry
            result["added"] += 1

    if result["added"] or result["overwritten"]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    return result


def load_cards_payload(path):
    if not path.exists():
        return {
            "cards": {},
        }

    with path.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    if not isinstance(payload, dict):
        raise ValueError(f"{path}: payload must be an object")

    cards = payload.setdefault("cards", {})
    if not isinstance(cards, dict):
        raise ValueError(f"{path}: cards must be an object")

    return payload


def official_slug(set_name):
    return re.sub(r"[-_\s]", "", set_name).lower()


def official_id_from_arg(slug, card_arg):
    value = card_arg.strip()
    if value.lower().startswith(f"{slug}-"):
        return value
    if value.isdigit():
        return f"{slug}-{int(value):03d}"
    return f"{slug}-{value.upper()}"


def expand_card_args(card_args, parser):
    expanded = []
    for card_arg in card_args:
        value = card_arg.strip()
        match = re.fullmatch(
            r"([A-Za-z]*)(\d+)-([A-Za-z]*)(\d+)",
            value,
        )
        if match is None:
            expanded.append(value)
            continue

        prefix_start, num_start, prefix_end, num_end = match.groups()
        prefix = resolve_range_prefix(prefix_start, prefix_end, value, parser)

        start, end = int(num_start), int(num_end)
        if start > end:
            parser.error(f"Invalid card range {value!r}: start exceeds end.")

        if prefix:
            width = max(len(num_start), len(num_end))
            expanded.extend(
                f"{prefix}{number:0{width}d}"
                for number in range(start, end + 1)
            )
        else:
            expanded.extend(
                str(number)
                for number in range(start, end + 1)
            )
    return expanded


def resolve_range_prefix(prefix_start, prefix_end, value, parser):
    if prefix_start and prefix_end:
        if prefix_start.upper() != prefix_end.upper():
            parser.error(
                f"Invalid card range {value!r}: prefixes "
                f"{prefix_start!r} and {prefix_end!r} differ."
            )
        return prefix_start.upper()
    return (prefix_start or prefix_end).upper()


def pack_set_from_packname(packname):
    parts = packname_parts(packname)
    if len(parts) < 2:
        return ""
    return parts[0]


def pack_number_from_packname(packname):
    parts = packname_parts(packname)
    if len(parts) < 2:
        return ""
    return parts[-1]


def packname_parts(packname):
    cleaned = clean_text(packname).strip("()")
    return cleaned.split()


def clean_text(value):
    return re.sub(
        r"\s+",
        " ",
        value.replace("\u3000", " "),
    ).strip().translate(FULLWIDTH_DIGITS)


OPEN_PARENS = "（("
CLOSE_PARENS = {"（": "）", "(": ")"}


def is_parenthetical_only(value):
    """かっこで丸ごと囲まれているだけのルール説明かどうかを判定する。

    （…）や(…)で全体が単一の括弧に包まれているテキストを True とする。
    括弧をテキストの一部として含むだけの効果説明（先頭が括弧でない、
    あるいは複数の括弧に分かれている）は False。
    """
    text = clean_text(value)
    if not text or text[0] not in OPEN_PARENS:
        return False

    close = CLOSE_PARENS[text[0]]
    depth = 0
    for index, char in enumerate(text):
        if char in OPEN_PARENS and CLOSE_PARENS[char] == close:
            depth += 1
        elif char == close:
            depth -= 1
            if depth == 0:
                # 最初に開いた括弧が末尾で閉じれば「丸ごと括弧」
                return index == len(text) - 1
    return False


def parse_int(value):
    cleaned = clean_text(value)
    if not re.fullmatch(r"\d+", cleaned):
        return None
    return int(cleaned)


def parse_power(value):
    return parse_int(clean_text(value).rstrip("+＋"))


def is_variable_power(value):
    return clean_text(value).endswith(("+", "＋"))


def parse_civilizations(value, warnings, card_id):
    civilizations = []
    for item in split_terms(value):
        civilization = CIVILIZATION_JA_EN.get(item)
        if civilization is None:
            warnings.append(f"{card_id}: unknown civilization {item!r}")
            continue
        civilizations.append(civilization)
    return civilizations


def split_race(value):
    return split_terms(value)


def split_terms(value):
    return [
        item
        for item in (
            clean_text(part)
            for part in re.split(r"[／/]", value)
        )
        if item and item != "-"
    ]


def parse_power_values(details, warnings, card_id):
    values = unique_in_order(
        details.get("field_values", {}).get(
            "power",
            [details["power"]],
        )
    )
    powers = [
        parse_power(value)
        for value in values
    ]

    if not powers or powers[0] is None:
        return None, None

    if is_variable_power(values[0]):
        warnings.append(
            f"{card_id}: power {values[0]!r} は可変パワー(+表記); "
            f"基礎値 {powers[0]} を採用。パワーアタッカー等の能力は手動で実装すること"
        )

    if len(powers) < 2:
        return powers[0], None

    if powers[1] is None:
        warnings.append(
            f"{card_id}: unsupported hyper power {values[1]!r}; "
            "left hyper_power unset"
        )
        return powers[0], None

    if has_hyper_mode_marker(details):
        if len(powers) > 2:
            warnings.append(
                f"{card_id}: more than two power values {values!r}; "
                "using the first two"
            )
        return powers[0], powers[1]

    warnings.append(
        f"{card_id}: multiple power values {values!r} without "
        "ハイパー化/Zラッシュ marker; left hyper_power unset"
    )
    return powers[0], None


def has_hyper_mode_marker(details):
    text = "\n".join(details.get("skills", []))
    return "ハイパー化" in text or "Zラッシュ" in text


def has_multiple_field_values(details, field_name):
    values = details.get("field_values", {}).get(field_name, [])
    return len(unique_in_order(values)) > 1


def warn_on_multiple_field_values(
    details,
    warnings,
    official_id,
    handled_fields=None,
):
    handled_fields = handled_fields or set()
    field_values = details.get("field_values", {})
    for field_name, values in field_values.items():
        if field_name in handled_fields:
            continue
        unique_values = unique_in_order(values)
        if len(unique_values) <= 1:
            continue
        if field_name == "power":
            warnings.append(
                f"{official_id}: multiple power values {unique_values!r}; "
                "using the first and leaving hyper_power/manual fields unset"
            )
            continue
        warnings.append(
            f"{official_id}: multiple {field_name} values {unique_values!r}; "
            "using the first"
        )


def unique_in_order(values):
    unique_values = []
    seen = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        unique_values.append(value)
    return unique_values


def empty_abilities():
    return {
        key: list(value)
        for key, value in EMPTY_ABILITIES.items()
    }


def _classes(attrs):
    for name, value in attrs:
        if name == "class" and value:
            return set(value.split())
    return set()


if __name__ == "__main__":
    main()
