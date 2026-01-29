import os
from datetime import date, timedelta
from aqt import mw
from aqt.qt import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)
from aqt.utils import showInfo, showWarning
from .config import get_config, save_config
from .queries import (
    build_query,
    extract_row,
    fetch_cards,
    get_deck_names,
    get_fields_for_deck,
    get_new_cards_by_day,
    sort_cards_by_first_review,
)
from .writers import write_json, write_markdown


class ExportDialog(QDialog):
    def __init__(self, parent=None, preselect_deck: str = None):
        super().__init__(parent)
        self.preselect_deck = preselect_deck
        self.setWindowTitle("Export Vocabulary")
        self.setMinimumWidth(450)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        self.config = get_config()

        deck_layout = QHBoxLayout()
        deck_layout.addWidget(QLabel("Deck:"))
        self.deck_combo = QComboBox()
        self.deck_combo.addItem("All Decks", None)
        for deck_name in get_deck_names():
            self.deck_combo.addItem(deck_name, deck_name)

        if self.preselect_deck:
            index = self.deck_combo.findText(self.preselect_deck)
            if index >= 0:
                self.deck_combo.setCurrentIndex(index)

        deck_layout.addWidget(self.deck_combo)
        layout.addLayout(deck_layout)

        layout.addWidget(QLabel("Select fields to export:"))
        self.fields_list = QListWidget()
        self.fields_list.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.fields_list.setMaximumHeight(150)

        self.saved_fields = self.config.get("fields", [])
        if isinstance(self.saved_fields, str):
            self.saved_fields = [f.strip() for f in self.saved_fields.split(",") if f.strip()]

        layout.addWidget(self.fields_list)

        self.deck_combo.currentIndexChanged.connect(self.update_fields_list)
        self.update_fields_list()

        group_layout = QHBoxLayout()
        group_layout.addWidget(QLabel("Group by:"))
        self.group_combo = QComboBox()
        self.group_combo.addItem("No grouping (all in one)", "none")
        self.group_combo.addItem("Learning status", "status")

        saved_grouping = self.config.get("grouping", "status")
        index = self.group_combo.findData(saved_grouping)
        if index >= 0:
            self.group_combo.setCurrentIndex(index)

        group_layout.addWidget(self.group_combo)
        group_layout.addStretch()
        layout.addLayout(group_layout)

        self.status_layout = QHBoxLayout()
        self.status_layout.addWidget(QLabel("Include:"))
        self.learning_cb = QCheckBox("Learning")
        self.learning_cb.setChecked(self.config.get("include_learning", True))
        self.fresh_cb = QCheckBox("Fresh (1-7d)")
        self.fresh_cb.setChecked(self.config.get("include_fresh", True))
        self.young_cb = QCheckBox("Young (8-20d)")
        self.young_cb.setChecked(self.config.get("include_young", True))
        self.mature_cb = QCheckBox("Mature (21-89d)")
        self.mature_cb.setChecked(self.config.get("include_mature", True))
        self.mastered_cb = QCheckBox("Mastered (90d+)")
        self.mastered_cb.setChecked(self.config.get("include_mastered", True))
        self.status_layout.addWidget(self.learning_cb)
        self.status_layout.addWidget(self.fresh_cb)
        self.status_layout.addWidget(self.young_cb)
        self.status_layout.addWidget(self.mature_cb)
        self.status_layout.addWidget(self.mastered_cb)
        layout.addLayout(self.status_layout)

        self.predictive_layout = QHBoxLayout()
        self.predictive_layout.addWidget(QLabel("Include new cards for next:"))
        self.predictive_spin = QSpinBox()
        self.predictive_spin.setRange(0, 30)
        self.predictive_spin.setValue(self.config.get("predictive_days", 0))
        self.predictive_spin.setSuffix(" days")
        self.predictive_spin.setToolTip(
            "Generate separate files with predicted new cards for future days.\n"
            "Uses deck's 'new cards per day' setting to predict which cards will appear."
        )
        self.predictive_layout.addWidget(self.predictive_spin)
        self.predictive_layout.addStretch()
        layout.addLayout(self.predictive_layout)

        self.group_combo.currentIndexChanged.connect(self.update_status_visibility)
        self.update_status_visibility()

        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("Format:"))
        self.format_combo = QComboBox()
        self.format_combo.addItem("JSON", "json")
        self.format_combo.addItem("Markdown", "markdown")

        saved_format = self.config.get("format", "json")
        index = self.format_combo.findData(saved_format)
        if index >= 0:
            self.format_combo.setCurrentIndex(index)

        format_layout.addWidget(self.format_combo)
        format_layout.addStretch()
        layout.addLayout(format_layout)

        button_layout = QHBoxLayout()
        self.export_btn = QPushButton("Export")
        self.export_btn.clicked.connect(self.do_export)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_btn)
        button_layout.addWidget(self.export_btn)
        layout.addLayout(button_layout)

    def update_status_visibility(self):
        show_status = self.group_combo.currentData() == "status"
        self.learning_cb.setVisible(show_status)
        self.fresh_cb.setVisible(show_status)
        self.young_cb.setVisible(show_status)
        self.mature_cb.setVisible(show_status)
        self.mastered_cb.setVisible(show_status)

        for i in range(self.status_layout.count()):
            widget = self.status_layout.itemAt(i).widget()
            if widget:
                widget.setVisible(show_status)

        for i in range(self.predictive_layout.count()):
            widget = self.predictive_layout.itemAt(i).widget()
            if widget:
                widget.setVisible(show_status)

    def update_fields_list(self):
        currently_selected = [item.text() for item in self.fields_list.selectedItems()]

        deck_name = self.deck_combo.currentData()
        available_fields = get_fields_for_deck(deck_name)

        self.fields_list.clear()
        for field_name in available_fields:
            item = QListWidgetItem(field_name)
            self.fields_list.addItem(item)
            if field_name in currently_selected or field_name in self.saved_fields:
                item.setSelected(True)

    def _get_export_settings(self):
        return {
            "deck": self.deck_combo.currentData(),
            "export_format": self.format_combo.currentData(),
            "grouping": self.group_combo.currentData(),
            "requested_fields": [item.text() for item in self.fields_list.selectedItems()],
        }

    def _get_file_extension_and_filter(self, export_format):
        if export_format == "json":
            return ".json", "JSON Files (*.json);;All Files (*)"
        return ".md", "Markdown Files (*.md);;All Files (*)"

    def _prompt_for_export_path(self, predictive_days, ext, file_filter):
        last_dir = self.config.get("last_export_dir", "")

        if predictive_days > 0:
            export_dir = QFileDialog.getExistingDirectory(self, "Select Export Directory", last_dir)
            if not export_dir:
                return None, None
            return export_dir, None
        else:
            default_filename = f"vocab_{date.today().isoformat()}{ext}"
            default_path = os.path.join(last_dir, default_filename) if last_dir else default_filename
            output_path, _ = QFileDialog.getSaveFileName(self, "Save Vocabulary Export", default_path, file_filter)
            if not output_path:
                return None, None
            return os.path.dirname(output_path), output_path

    def _build_all_cards_section(self, deck, requested_fields):
        all_query = build_query(deck, "")
        all_ids = sort_cards_by_first_review(fetch_cards(all_query))
        all_rows = [extract_row(cid, requested_fields) for cid in all_ids]
        return [("All Cards", all_rows)]

    def _build_status_section(self, deck, requested_fields, query_filter, section_name):
        query = build_query(deck, query_filter)
        card_ids = sort_cards_by_first_review(fetch_cards(query))
        rows = [extract_row(cid, requested_fields) for cid in card_ids]
        return (section_name, rows)

    def _build_learning_section(self, deck, requested_fields, today_batch, new_cards_by_day):
        learning_query = build_query(deck, "is:learn")
        learning_ids = sort_cards_by_first_review(fetch_cards(learning_query))
        learning_rows = [extract_row(cid, requested_fields) for cid in learning_ids]

        for batch in range(today_batch):
            if batch in new_cards_by_day:
                new_card_ids = new_cards_by_day[batch]
                new_rows = [extract_row(cid, requested_fields) for cid in new_card_ids]
                learning_rows.extend(new_rows)

        return ("Learning", learning_rows)

    def _build_today_section(self, requested_fields, today_batch, new_cards_by_day):
        if today_batch >= 0 and today_batch in new_cards_by_day:
            today_card_ids = new_cards_by_day[today_batch]
            today_rows = [extract_row(cid, requested_fields) for cid in today_card_ids]
            if today_rows:
                return ("Added Today", today_rows)
        return None

    def _build_grouped_sections(self, deck, requested_fields, day_offset, new_cards_by_day):
        sections = []
        today_batch = day_offset - 1

        if self.learning_cb.isChecked():
            today_section = self._build_today_section(requested_fields, today_batch, new_cards_by_day)
            if today_section:
                sections.append(today_section)
            sections.append(self._build_learning_section(deck, requested_fields, today_batch, new_cards_by_day))

        status_configs = [
            (self.fresh_cb, "is:review -is:learn prop:ivl>=1 prop:ivl<=7", "Fresh"),
            (self.young_cb, "is:review -is:learn prop:ivl>=8 prop:ivl<=20", "Young"),
            (self.mature_cb, "is:review -is:learn prop:ivl>=21 prop:ivl<=89", "Mature"),
            (self.mastered_cb, "is:review -is:learn prop:ivl>=90", "Mastered"),
        ]

        for checkbox, query_filter, section_name in status_configs:
            if checkbox.isChecked():
                sections.append(self._build_status_section(deck, requested_fields, query_filter, section_name))

        return sections

    def _build_sections_for_day(self, deck, requested_fields, grouping, day_offset, new_cards_by_day):
        if grouping == "none":
            if day_offset == 0:
                return self._build_all_cards_section(deck, requested_fields)
            return []
        else:
            return self._build_grouped_sections(deck, requested_fields, day_offset, new_cards_by_day)

    def _get_output_path_for_day(self, export_dir, output_path, target_date, day_offset, predictive_days, ext):
        if predictive_days > 0:
            if day_offset == 0:
                day_filename = f"vocab_{target_date.isoformat()}{ext}"
            else:
                day_filename = f"vocab_pred_{target_date.isoformat()}{ext}"
            return os.path.join(export_dir, day_filename)
        return output_path

    def _write_export_file(self, output_path, sections, requested_fields, export_format):
        if export_format == "json":
            write_json(output_path, sections, requested_fields)
        else:
            write_markdown(output_path, sections, requested_fields)

    def _save_export_config(self, requested_fields, grouping, export_format, predictive_days, export_dir):
        self.config["fields"] = requested_fields
        self.config["grouping"] = grouping
        self.config["format"] = export_format
        self.config["include_learning"] = self.learning_cb.isChecked()
        self.config["include_fresh"] = self.fresh_cb.isChecked()
        self.config["include_young"] = self.young_cb.isChecked()
        self.config["include_mature"] = self.mature_cb.isChecked()
        self.config["include_mastered"] = self.mastered_cb.isChecked()
        self.config["predictive_days"] = predictive_days
        self.config["last_export_dir"] = export_dir
        save_config(self.config)

    def _show_export_success(self, total_cards, files_created, export_dir, output_path, predictive_days):
        if predictive_days > 0:
            showInfo(
                f"Successfully exported {total_cards} cards to {len(files_created)} files:\n"
                f"{', '.join(files_created)}\n\nDirectory: {export_dir}"
            )
        else:
            showInfo(f"Successfully exported {total_cards} cards to:\n{output_path}")

    def do_export(self):
        selected_items = self.fields_list.selectedItems()
        if not selected_items:
            showWarning("Please select at least one field.")
            return

        settings = self._get_export_settings()
        deck = settings["deck"]
        export_format = settings["export_format"]
        grouping = settings["grouping"]
        requested_fields = settings["requested_fields"]
        predictive_days = self.predictive_spin.value() if grouping == "status" else 0

        ext, file_filter = self._get_file_extension_and_filter(export_format)
        export_dir, output_path = self._prompt_for_export_path(predictive_days, ext, file_filter)
        if export_dir is None:
            return

        new_cards_by_day = {}
        if predictive_days > 0 and grouping == "status":
            new_cards_by_day = get_new_cards_by_day(deck, predictive_days)

        try:
            total_cards = 0
            files_created = []
            days_to_export = range(predictive_days + 1) if predictive_days > 0 else [0]
            last_output_path = output_path

            for day_offset in days_to_export:
                target_date = date.today() + timedelta(days=day_offset)
                sections = self._build_sections_for_day(deck, requested_fields, grouping, day_offset, new_cards_by_day)

                if day_offset > 0 and not sections:
                    continue

                if day_offset == 0 and not sections and grouping == "status":
                    showWarning("Please select at least one status to include.")
                    return

                day_output_path = self._get_output_path_for_day(
                    export_dir,
                    output_path,
                    target_date,
                    day_offset,
                    predictive_days,
                    ext,
                )
                last_output_path = day_output_path

                self._write_export_file(day_output_path, sections, requested_fields, export_format)

                total_cards += sum(len(rows) for _, rows in sections)
                files_created.append(os.path.basename(day_output_path))

            self._save_export_config(requested_fields, grouping, export_format, predictive_days, export_dir)
            self._show_export_success(
                total_cards,
                files_created,
                export_dir,
                last_output_path,
                predictive_days,
            )
            self.accept()
        except Exception as e:
            showWarning(f"Error exporting vocabulary:\n{str(e)}")


def show_export_dialog(deck_name: str = None):
    dialog = ExportDialog(mw, preselect_deck=deck_name)
    dialog.exec()
