from typing import Dict, List
from aqt import mw


def get_deck_names() -> List[str]:
    return sorted(mw.col.decks.all_names())


def get_note_type_fields(note_type_name: str = None) -> List[str]:
    fields = set()
    for model in mw.col.models.all():
        if note_type_name is None or model["name"] == note_type_name:
            for fld in model["flds"]:
                fields.add(fld["name"])
    return sorted(fields)


def get_fields_for_deck(deck_name: str = None) -> List[str]:
    if deck_name is None:
        return get_note_type_fields()

    query = f'deck:"{deck_name}"'
    card_ids = mw.col.find_cards(query)

    note_type_ids = set()
    for cid in card_ids:
        card = mw.col.get_card(cid)
        note = card.note()
        note_type_ids.add(note.mid)

    fields = set()
    for model in mw.col.models.all():
        if model["id"] in note_type_ids:
            for fld in model["flds"]:
                fields.add(fld["name"])

    return sorted(fields)


def build_query(deck: str | None, extra: str) -> str:
    parts = ["-is:new", extra]
    if deck:
        parts.append(f'deck:"{deck}"')
    return " ".join(parts)


def get_new_cards_per_day(deck_name: str) -> int:
    """Get the 'new cards per day' limit from deck options."""
    if deck_name is None:
        # For "All Decks", use a reasonable default
        return 5
    deck_id = mw.col.decks.id_for_name(deck_name)
    if deck_id is None:
        return 5
    conf = mw.col.decks.config_dict_for_deck_id(deck_id)
    return conf.get("new", {}).get("perDay", 5)


def get_new_cards_by_day(deck_name: str, days_ahead: int) -> Dict[int, List[int]]:
    if deck_name:
        query = f'is:new deck:"{deck_name}"'
    else:
        query = "is:new"

    card_ids = mw.col.find_cards(query)

    if not card_ids:
        return {}

    # Sort cards by their due position (lower = shown first)
    cards_with_position = []
    for cid in card_ids:
        card = mw.col.get_card(cid)
        cards_with_position.append((cid, card.due))

    cards_with_position.sort(key=lambda x: x[1])
    sorted_card_ids = [cid for cid, _ in cards_with_position]

    new_per_day = get_new_cards_per_day(deck_name)

    result: Dict[int, List[int]] = {}
    for day in range(days_ahead + 1):
        start_idx = day * new_per_day
        end_idx = (day + 1) * new_per_day
        day_cards = sorted_card_ids[start_idx:end_idx]
        if day_cards:
            result[day] = day_cards

    return result


def fetch_cards(query: str) -> List[int]:
    return mw.col.find_cards(query)


def sort_cards_by_first_review(card_ids: List[int]) -> List[int]:
    def get_first_review(cid: int) -> int:
        result = mw.col.db.scalar("SELECT MIN(id) FROM revlog WHERE cid = ?", cid)
        return result if result else 0

    return sorted(card_ids, key=get_first_review, reverse=True)


def extract_row(card_id: int, requested_fields: List[str]) -> Dict[str, str]:
    card = mw.col.get_card(card_id)
    note = card.note()

    field_key_map = {k.lower(): k for k in note.keys()}

    row: Dict[str, str] = {}
    for field in requested_fields:
        key = field_key_map.get(field.lower())
        if key is None:
            row[field] = ""
        else:
            value = note[key]
            row[field] = value if value else ""
    return row
