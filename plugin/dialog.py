import os
from datetime import date
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
        self.fields_list.setSelectionMode(
            QAbstractItemView.SelectionMode.MultiSelection
        )
        self.fields_list.setMaximumHeight(150)

        self.saved_fields = self.config.get("fields", [])
        if isinstance(self.saved_fields, str):
            self.saved_fields = [
                f.strip() for f in self.saved_fields.split(",") if f.strip()
            ]

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

    def do_export(self):
        selected_items = self.fields_list.selectedItems()
        if not selected_items:
            showWarning("Please select at least one field.")
            return

        requested_fields = [item.text() for item in selected_items]

        deck = self.deck_combo.currentData()

        export_format = self.format_combo.currentData()
        if export_format == "json":
            default_filename = f"vocab_{date.today().isoformat()}.json"
            file_filter = "JSON Files (*.json);;All Files (*)"
        else:
            default_filename = f"vocab_{date.today().isoformat()}.md"
            file_filter = "Markdown Files (*.md);;All Files (*)"

        last_dir = self.config.get("last_export_dir", "")
        if last_dir:
            default_path = os.path.join(last_dir, default_filename)
        else:
            default_path = default_filename

        output_path, _ = QFileDialog.getSaveFileName(
            self, "Save Vocabulary Export", default_path, file_filter
        )

        if not output_path:
            return

        sections = []
        grouping = self.group_combo.currentData()

        if grouping == "none":
            all_query = build_query(deck, "")
            all_ids = sort_cards_by_first_review(fetch_cards(all_query))
            all_rows = [extract_row(cid, requested_fields) for cid in all_ids]
            sections.append(("All Cards", all_rows))
        else:
            if self.learning_cb.isChecked():
                learning_query = build_query(deck, "is:learn")
                learning_ids = sort_cards_by_first_review(fetch_cards(learning_query))
                learning_rows = [
                    extract_row(cid, requested_fields) for cid in learning_ids
                ]
                sections.append(("Learning", learning_rows))

            if self.fresh_cb.isChecked():
                fresh_query = build_query(
                    deck, "is:review -is:learn prop:ivl>=1 prop:ivl<=7"
                )
                fresh_ids = sort_cards_by_first_review(fetch_cards(fresh_query))
                fresh_rows = [extract_row(cid, requested_fields) for cid in fresh_ids]
                sections.append(("Fresh", fresh_rows))

            if self.young_cb.isChecked():
                young_query = build_query(
                    deck, "is:review -is:learn prop:ivl>=8 prop:ivl<=20"
                )
                young_ids = sort_cards_by_first_review(fetch_cards(young_query))
                young_rows = [extract_row(cid, requested_fields) for cid in young_ids]
                sections.append(("Young", young_rows))

            if self.mature_cb.isChecked():
                mature_query = build_query(
                    deck, "is:review -is:learn prop:ivl>=21 prop:ivl<=89"
                )
                mature_ids = sort_cards_by_first_review(fetch_cards(mature_query))
                mature_rows = [extract_row(cid, requested_fields) for cid in mature_ids]
                sections.append(("Mature", mature_rows))

            if self.mastered_cb.isChecked():
                mastered_query = build_query(deck, "is:review -is:learn prop:ivl>=90")
                mastered_ids = sort_cards_by_first_review(fetch_cards(mastered_query))
                mastered_rows = [
                    extract_row(cid, requested_fields) for cid in mastered_ids
                ]
                sections.append(("Mastered", mastered_rows))

            if not sections:
                showWarning("Please select at least one status to include.")
                return

        try:
            if export_format == "json":
                write_json(output_path, sections, requested_fields)
            else:
                write_markdown(output_path, sections, requested_fields)

            total_cards = sum(len(rows) for _, rows in sections)

            self.config["fields"] = requested_fields
            self.config["grouping"] = self.group_combo.currentData()
            self.config["format"] = export_format
            self.config["include_learning"] = self.learning_cb.isChecked()
            self.config["include_fresh"] = self.fresh_cb.isChecked()
            self.config["include_young"] = self.young_cb.isChecked()
            self.config["include_mature"] = self.mature_cb.isChecked()
            self.config["include_mastered"] = self.mastered_cb.isChecked()
            self.config["last_export_dir"] = os.path.dirname(output_path)
            save_config(self.config)

            showInfo(f"Successfully exported {total_cards} cards to:\n{output_path}")
            self.accept()
        except Exception as e:
            showWarning(f"Error exporting vocabulary:\n{str(e)}")


def show_export_dialog(deck_name: str = None):
    dialog = ExportDialog(mw, preselect_deck=deck_name)
    dialog.exec()
