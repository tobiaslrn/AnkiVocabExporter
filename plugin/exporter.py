import os
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple
from .models import ExportResult, ExportSettings
from aqt import mw


class VocabularyExporter:
    cards_query_learning = "is:learn"
    cards_query_fresh = "is:review -is:learn prop:ivl>=1 prop:ivl<=7"
    cards_query_young = "is:review -is:learn prop:ivl>=8 prop:ivl<=20"
    cards_query_mature = "is:review -is:learn prop:ivl>=21 prop:ivl<=89"
    cards_query_mastered = "is:review -is:learn prop:ivl>=90"

    def __init__(self, settings: ExportSettings):
        self.settings = settings
        self._new_cards_by_day: Dict[int, List[int]] = {}

    def export(self, export_dir: str, output_path: Optional[str] = None) -> ExportResult:
        try:
            self._load_new_cards_if_needed()
            return self._perform_export(export_dir, output_path)
        except Exception as e:
            return ExportResult(success=False, error_message=str(e))

    def _load_new_cards_if_needed(self) -> None:
        if self.settings.predictive_days > 0 and self.settings.grouping == "status":
            self._new_cards_by_day = get_new_cards_by_day(self.settings.deck, self.settings.predictive_days)

    def _perform_export(self, export_dir: str, output_path: Optional[str]) -> ExportResult:
        total_cards = 0
        files_created: List[str] = []
        last_output_path = output_path or ""

        days_to_export = self._get_days_to_export()

        for day_offset in days_to_export:
            sections = self._build_sections_for_day(day_offset)

            if day_offset > 0 and not sections:
                continue

            if day_offset == 0 and not sections and self.settings.grouping == "status":
                return ExportResult(success=False, error_message="Please select at least one status to include.")

            target_date = date.today() + timedelta(days=day_offset)
            day_output_path = self._get_output_path_for_day(export_dir, output_path, target_date, day_offset)
            last_output_path = day_output_path

            write_markdown(day_output_path, sections, self.settings.fields)

            total_cards += sum(len(rows) for _, rows in sections)
            files_created.append(os.path.basename(day_output_path))

        return ExportResult(
            success=True,
            total_cards=total_cards,
            files_created=files_created,
            export_directory=export_dir,
            output_path=last_output_path,
        )

    def _get_days_to_export(self) -> range:
        if self.settings.predictive_days > 0:
            return range(self.settings.predictive_days + 1)
        return range(1)

    def _get_output_path_for_day(
        self, export_dir: str, output_path: Optional[str], target_date: date, day_offset: int
    ) -> str:
        ext = ".md"

        if self.settings.predictive_days > 0:
            if day_offset == 0:
                filename = f"vocab_{target_date.isoformat()}{ext}"
            else:
                filename = f"vocab_pred_{target_date.isoformat()}{ext}"
            return os.path.join(export_dir, filename)

        return output_path or os.path.join(export_dir, f"vocab_{target_date.isoformat()}{ext}")

    def _build_sections_for_day(self, day_offset: int) -> List[Tuple[str, List[Dict[str, str]]]]:
        if self.settings.grouping == "none":
            if day_offset == 0:
                return self._build_all_cards_section()
            return []
        else:
            return self._build_grouped_sections(day_offset)

    def _build_all_cards_section(self) -> List[Tuple[str, List[Dict[str, str]]]]:
        query = build_query(self.settings.deck, "")
        card_ids = sort_cards_by_first_review(fetch_cards(query))
        rows = [extract_row(cid, self.settings.fields) for cid in card_ids]
        return [("All Cards", rows)]

    def _build_grouped_sections(self, day_offset: int) -> List[Tuple[str, List[Dict[str, str]]]]:
        sections: List[Tuple[str, List[Dict[str, str]]]] = []
        today_batch = day_offset - 1
        exclude_ids: Set[int] = set()

        if self.settings.include_fresh:
            if self.settings.separate_today:
                today_result = self._build_today_section(day_offset, today_batch)
                if today_result:
                    section_name, rows, today_ids = today_result
                    sections.append((section_name, rows))
                    exclude_ids = today_ids

            sections.append(self._build_fresh_section(today_batch, exclude_ids))

        status_configs = [
            (self.settings.include_young, self.cards_query_young, "Young"),
            (self.settings.include_mature, self.cards_query_mature, "Mature"),
            (self.settings.include_mastered, self.cards_query_mastered, "Mastered"),
        ]

        for include, query_filter, section_name in status_configs:
            if include:
                sections.append(self._build_status_section(query_filter, section_name))

        return sections

    def _build_today_section(
        self, day_offset: int, today_batch: int
    ) -> Optional[Tuple[str, List[Dict[str, str]], Set[int]]]:
        if day_offset == 0:
            today_card_ids = get_cards_first_reviewed_today(self.settings.deck)
            rows = [extract_row(cid, self.settings.fields) for cid in today_card_ids]
            if rows:
                return ("Added Today", rows, set(today_card_ids))
        elif today_batch >= 0 and today_batch in self._new_cards_by_day:
            today_card_ids = self._new_cards_by_day[today_batch]
            rows = [extract_row(cid, self.settings.fields) for cid in today_card_ids]
            if rows:
                return ("Added Today", rows, set(today_card_ids))
        return None

    def _build_fresh_section(self, today_batch: int, exclude_ids: Set[int]) -> Tuple[str, List[Dict[str, str]]]:
        fresh_rows: List[Dict[str, str]] = []

        learning_query = build_query(self.settings.deck, self.cards_query_learning)
        learning_ids = sort_cards_by_first_review(fetch_cards(learning_query))
        learning_ids = [cid for cid in learning_ids if cid not in exclude_ids]
        fresh_rows.extend(extract_row(cid, self.settings.fields) for cid in learning_ids)

        for batch in range(today_batch):
            if batch in self._new_cards_by_day:
                new_card_ids = [cid for cid in self._new_cards_by_day[batch] if cid not in exclude_ids]
                fresh_rows.extend(extract_row(cid, self.settings.fields) for cid in new_card_ids)

        fresh_query = build_query(self.settings.deck, self.cards_query_fresh)
        fresh_ids = sort_cards_by_first_review(fetch_cards(fresh_query))
        fresh_ids = [cid for cid in fresh_ids if cid not in exclude_ids]
        fresh_rows.extend(extract_row(cid, self.settings.fields) for cid in fresh_ids)

        return ("Fresh", fresh_rows)

    def _build_status_section(self, query_filter: str, section_name: str) -> Tuple[str, List[Dict[str, str]]]:
        query = build_query(self.settings.deck, query_filter)
        card_ids = sort_cards_by_first_review(fetch_cards(query))
        rows = [extract_row(cid, self.settings.fields) for cid in card_ids]
        return (section_name, rows)


def get_cards_first_reviewed_today(deck_name: str) -> List[int]:
    today_start = int(datetime.combine(date.today(), datetime.min.time()).timestamp()) * 1000
    deck_id = mw.col.decks.id_for_name(deck_name)

    query = """
        SELECT DISTINCT r.cid 
        FROM revlog r
        JOIN cards c ON r.cid = c.id
        WHERE c.did = ? AND r.id >= ?
        AND r.id = (SELECT MIN(id) FROM revlog WHERE cid = r.cid)
    """
    result = mw.col.db.list(query, deck_id, today_start)

    return result


def get_note_type_fields(note_type_name: str = None) -> List[str]:
    fields = set()
    for model in mw.col.models.all():
        if note_type_name is None or model["name"] == note_type_name:
            for fld in model["flds"]:
                fields.add(fld["name"])
    return sorted(fields)


def build_query(deck: str, extra: str) -> str:
    return "-is:new " + extra + f' deck:"{deck}"'


def get_new_cards_per_day(deck_name: str) -> int:
    deck_id = mw.col.decks.id_for_name(deck_name)
    conf = mw.col.decks.config_dict_for_deck_id(deck_id)
    return conf.get("new", {}).get("perDay", 5)


def get_new_cards_by_day(deck_name: str, days_ahead: int) -> Dict[int, List[int]]:
    query = f'is:new deck:"{deck_name}"'
    card_ids = mw.col.find_cards(query)

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


def escape_csv(value: str) -> str:
    value = value.replace("\n", " ")
    if any(ch in value for ch in [",", '"', "\n"]):
        value = '"' + value.replace('"', '""') + '"'
    return value


def write_markdown(path: str, sections: List[Tuple[str, List[Dict[str, str]]]], fieldnames: List[str]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for idx, (title, rows) in enumerate(sections):
            if idx > 0:
                f.write("\n\n")
            f.write(f"## {title}\n\n")
            if rows:
                f.write(",".join(fieldnames) + "\n")
                for row in rows:
                    values = [escape_csv(str(row.get(name, ""))) for name in fieldnames]
                    f.write(",".join(values) + "\n")
