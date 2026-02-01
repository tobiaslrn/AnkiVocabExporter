from aqt import mw, gui_hooks
from aqt.qt import QAction
from .dialog import show_export_dialog


def setup_menu():
    action = QAction("Export Vocabulary", mw)
    action.triggered.connect(lambda: show_export_dialog())
    mw.form.menuTools.addAction(action)


def on_deck_browser_options_menu(menu, deck_id: int) -> None:
    deck = mw.col.decks.get(deck_id)
    if deck is None:
        return

    deck_name = deck["name"]

    action = menu.addAction("Export Vocabulary")
    action.triggered.connect(lambda: show_export_dialog(deck_name))


gui_hooks.deck_browser_will_show_options_menu.append(on_deck_browser_options_menu)
