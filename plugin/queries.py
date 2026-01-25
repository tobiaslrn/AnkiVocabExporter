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


def fetch_cards(query: str) -> List[int]:
    return mw.col.find_cards(query)


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
