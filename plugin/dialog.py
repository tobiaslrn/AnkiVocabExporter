"""Dialog UI for the vocabulary export plugin."""

import os
from datetime import date
from typing import List, Optional

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
from .exporter import VocabularyExporter
from .models import ExportSettings


class ExportDialog(QDialog):
    def __init__(self, parent=None, preselect_deck: Optional[str] = None):
        super().__init__(parent)
        self._preselect_deck = preselect_deck
        self._config = get_config()
        self._saved_fields: list[str] = []

        self._setup_window()
        self._create_widgets()
        self._setup_layout()
        self._connect_signals()
        self._apply_saved_config()

    def _setup_window(self) -> None:
        self.setWindowTitle("Export Vocabulary")
        self.setMinimumWidth(500)

    def _create_widgets(self) -> None:
        self._deck_label = QLabel("Deck:")
        self._deck_combo = QComboBox()
        self._deck_combo.addItem("All Decks", None)
        for deck_name in self.get_deck_names():
            self._deck_combo.addItem(deck_name, deck_name)

        self._fields_label = QLabel("Select fields to export:")
        self._fields_list = QListWidget()
        self._fields_list.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self._fields_list.setMaximumHeight(200)

        self._group_label = QLabel("Group by:")
        self._group_combo = QComboBox()
        self._group_combo.addItem("No grouping (all in one)", "none")
        self._group_combo.addItem("Learning status", "status")

        self._status_label = QLabel("Include:")
        self._fresh_cb = QCheckBox("Fresh (1-7d)")
        self._young_cb = QCheckBox("Young (8-20d)")
        self._mature_cb = QCheckBox("Mature (21-89d)")
        self._mastered_cb = QCheckBox("Mastered (90d+)")

        self._separate_today_cb = QCheckBox("Separate 'Added Today' section")

        self._predictive_label = QLabel("Include new cards for next:")
        self._predictive_spin = QSpinBox()
        self._predictive_spin.setRange(0, 30)
        self._predictive_spin.setSuffix(" days")

        self._export_btn = QPushButton("Export")
        self._cancel_btn = QPushButton("Cancel")

    def _setup_layout(self) -> None:
        layout = QVBoxLayout(self)

        # Deck row
        deck_layout = QHBoxLayout()
        deck_layout.addWidget(self._deck_label)
        deck_layout.addWidget(self._deck_combo)
        layout.addLayout(deck_layout)

        # Fields section
        layout.addWidget(self._fields_label)
        layout.addWidget(self._fields_list)

        # Group by row
        group_layout = QHBoxLayout()
        group_layout.addWidget(self._group_label)
        group_layout.addWidget(self._group_combo)
        group_layout.addStretch()
        layout.addLayout(group_layout)

        # Status checkboxes row
        self._status_layout = QHBoxLayout()
        self._status_layout.addWidget(self._status_label)
        self._status_layout.addWidget(self._fresh_cb)
        self._status_layout.addWidget(self._young_cb)
        self._status_layout.addWidget(self._mature_cb)
        self._status_layout.addWidget(self._mastered_cb)
        layout.addLayout(self._status_layout)

        # Today section row
        self._today_layout = QHBoxLayout()
        self._today_layout.addWidget(self._separate_today_cb)
        self._today_layout.addStretch()
        layout.addLayout(self._today_layout)

        # Predictive row
        self._predictive_layout = QHBoxLayout()
        self._predictive_layout.addWidget(self._predictive_label)
        self._predictive_layout.addWidget(self._predictive_spin)
        self._predictive_layout.addStretch()
        layout.addLayout(self._predictive_layout)

        # Buttons row
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self._cancel_btn)
        button_layout.addWidget(self._export_btn)
        layout.addLayout(button_layout)

    def _connect_signals(self) -> None:
        self._deck_combo.currentIndexChanged.connect(self._on_deck_changed)
        self._group_combo.currentIndexChanged.connect(self._on_grouping_changed)
        self._export_btn.clicked.connect(self._on_export_clicked)
        self._cancel_btn.clicked.connect(self.reject)

    def _apply_saved_config(self) -> None:
        if self._preselect_deck:
            index = self._deck_combo.findText(self._preselect_deck)
            if index >= 0:
                self._deck_combo.setCurrentIndex(index)

        saved_fields = self._config.get("fields", [])
        if isinstance(saved_fields, str):
            saved_fields = [f.strip() for f in saved_fields.split(",") if f.strip()]
        self._saved_fields = saved_fields

        self._update_fields_list()

        saved_grouping = self._config.get("grouping", "status")
        index = self._group_combo.findData(saved_grouping)
        if index >= 0:
            self._group_combo.setCurrentIndex(index)

        self._fresh_cb.setChecked(self._config.get("include_fresh", True))
        self._young_cb.setChecked(self._config.get("include_young", True))
        self._mature_cb.setChecked(self._config.get("include_mature", True))
        self._mastered_cb.setChecked(self._config.get("include_mastered", True))
        self._separate_today_cb.setChecked(self._config.get("separate_today", True))
        self._predictive_spin.setValue(self._config.get("predictive_days", 0))

        self._update_status_visibility()

    def _on_deck_changed(self) -> None:
        self._update_fields_list()

    def _on_grouping_changed(self) -> None:
        self._update_status_visibility()

    def _update_fields_list(self) -> None:
        currently_selected = [item.text() for item in self._fields_list.selectedItems()]

        deck_name = self._deck_combo.currentData()
        available_fields = self.get_fields_for_deck(deck_name)

        self._fields_list.clear()
        for field_name in available_fields:
            item = QListWidgetItem(field_name)
            self._fields_list.addItem(item)
            if field_name in currently_selected or field_name in self._saved_fields:
                item.setSelected(True)

    def _update_status_visibility(self) -> None:
        show_status = self._group_combo.currentData() == "status"

        for i in range(self._status_layout.count()):
            widget = self._status_layout.itemAt(i).widget()
            if widget:
                widget.setVisible(show_status)

        for i in range(self._today_layout.count()):
            widget = self._today_layout.itemAt(i).widget()
            if widget:
                widget.setVisible(show_status)

        for i in range(self._predictive_layout.count()):
            widget = self._predictive_layout.itemAt(i).widget()
            if widget:
                widget.setVisible(show_status)

    def _get_export_settings(self) -> ExportSettings:
        grouping = self._group_combo.currentData()
        predictive_days = self._predictive_spin.value() if grouping == "status" else 0

        return ExportSettings(
            deck=self._deck_combo.currentData(),
            fields=[item.text() for item in self._fields_list.selectedItems()],
            grouping=grouping,
            include_fresh=self._fresh_cb.isChecked(),
            include_young=self._young_cb.isChecked(),
            include_mature=self._mature_cb.isChecked(),
            include_mastered=self._mastered_cb.isChecked(),
            separate_today=self._separate_today_cb.isChecked(),
            predictive_days=predictive_days,
        )

    def _prompt_for_export_path(self, predictive_days: int) -> tuple[Optional[str], Optional[str]]:
        last_dir = self._config.get("last_export_dir", "")
        ext = ".md"
        file_filter = "Markdown Files (*.md);;All Files (*)"

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

    def _save_config_from_settings(self, settings: ExportSettings, export_dir: str) -> None:
        self._config["fields"] = settings.fields
        self._config["grouping"] = settings.grouping
        self._config["include_fresh"] = settings.include_fresh
        self._config["include_young"] = settings.include_young
        self._config["include_mature"] = settings.include_mature
        self._config["include_mastered"] = settings.include_mastered
        self._config["separate_today"] = settings.separate_today
        self._config["predictive_days"] = settings.predictive_days
        self._config["last_export_dir"] = export_dir
        save_config(self._config)

    def _on_export_clicked(self) -> None:
        if not self._fields_list.selectedItems():
            showWarning("Please select at least one field.")
            return

        settings = self._get_export_settings()

        export_dir, output_path = self._prompt_for_export_path(settings.predictive_days)
        if export_dir is None:
            return

        exporter = VocabularyExporter(settings)
        result = exporter.export(export_dir, output_path)

        if not result.success:
            showWarning(result.error_message or "Export failed.")
            return

        self._save_config_from_settings(settings, export_dir)
        self._show_success_message(result)
        self.accept()

    def _show_success_message(self, result) -> None:
        if len(result.files_created) > 1:
            showInfo(
                f"Successfully exported {result.total_cards} cards to {len(result.files_created)} files:\n- "
                f"{'\n- '.join(result.files_created)}\n\nDirectory: {result.export_directory}"
            )
        else:
            showInfo(f"Successfully exported {result.total_cards} cards to:\n{result.output_path}")

    @staticmethod
    def get_deck_names() -> List[str]:
        return sorted(mw.col.decks.all_names())

    @staticmethod
    def get_fields_for_deck(deck_name: str) -> List[str]:
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


def show_export_dialog(deck_name: Optional[str] = None) -> None:
    dialog = ExportDialog(mw, preselect_deck=deck_name)
    dialog.exec()
