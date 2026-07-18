import re
from PySide6.QtWidgets import QWidget, QLineEdit, QHBoxLayout, QListWidget, QListWidgetItem
from PySide6.QtCore import Qt, Signal, QUrl, QPoint
from PySide6.QtGui import QKeyEvent
from interface.widgets.better_webengine import BetterWebEngine
from services.history_mgr import HistoryEntryData

class HistoryPopup(QListWidget):
    entrySelected = Signal(str)

    def __init__(self, entries: list[HistoryEntryData], parent=None):
        super().__init__(parent)

        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFixedHeight(min(len(entries) * 36 + 8, 300))
        self.setStyleSheet(
            "QListWidget { background: #202124; border: 1px solid #414242; border-radius: 8px; }"
            "QListWidget::item { padding: 10px 25px; color: #ddd; border-radius: 8px;}"
            "QListWidget::item:hover { background: #3a3a3a; }"
        )

        for entry in entries:
            self.addItem(QListWidgetItem(entry.url))

        self.itemClicked.connect(self._on_clicked)

    def _on_clicked(self, item: QListWidgetItem):
        self.entrySelected.emit(item.text())
        self.close()

class FloatingAddressBarInput(QLineEdit):
    escape_pressed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("https://")
        self.setStyleSheet(
            "padding: 10px 14px;"
            "font-size: 15px;"
            "background: transparent;"
            "border: none;"
        )

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Escape:
            self.escape_pressed.emit()
        elif event.key() == Qt.Key.Key_Backspace and self.hasSelectedText():
            sel_start = self.selectionStart()
            typed = self.text()[:sel_start]
            new_text = typed[:-1] if typed else ""

            self.blockSignals(True)
            self.setText(new_text)
            self.setCursorPosition(len(new_text))
            self.blockSignals(False)
            
            self.textChanged.emit(new_text)
        else:
            super().keyPressEvent(event)

class FloatingAddressBar(QWidget):
    def __init__(self, controller, parent=None):
        super().__init__(parent)

        self.controller = controller
        self.browser: BetterWebEngine = None

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setStyleSheet("border-radius: 8px; border: 1px solid #414242;")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        self.url_input = FloatingAddressBarInput()
        self.url_input.textChanged.connect(self._filter)
        self.url_input.returnPressed.connect(self._on_return_pressed)
        self.url_input.escape_pressed.connect(self.hide_bar)

        layout.addWidget(self.url_input)

        self.setFixedHeight(52)
        self.hide()

        controller.currentBrowserChanged.connect(self._set_browser)

        # Sync initial browser
        initial_browser = controller.current_browser()
        if initial_browser:
            self._set_browser(initial_browser)

    def _set_browser(self, browser):
        if self.browser:
            try:
                self.browser.urlChanged.disconnect(self._on_url_changed)
            except RuntimeError:
                pass

        self.browser = browser
        self.browser.urlChanged.connect(self._on_url_changed)
    
    def _display_menu(self, entries: list[HistoryEntryData]):
        if not entries or not self.isVisible():
            return

        if hasattr(self, '_menu') and self._menu:
            self._menu.close()

        popup = HistoryPopup(entries=entries, parent=self)
        popup.setFixedWidth(self.url_input.width())

        bottom_pos = self.url_input.mapToGlobal(QPoint(0, self.url_input.height() + 10))
        popup.move(bottom_pos)
        popup.show()

        popup.entrySelected.connect(self._on_history_entry_selected)

        self._menu = popup
    
    def _autocomplete(self, user_url: str, autocomp: str):
        end_pos = len(autocomp) - len(user_url)

        self.url_input.textChanged.disconnect(self._filter)
        self.url_input.setText(autocomp)
        self.url_input.textChanged.connect(self._filter)

        self.url_input.setCursorPosition(len(user_url))
        self.url_input.setSelection(len(user_url), end_pos)

    def _filter(self, user_url: str):
        if not user_url or not self.browser:
            return

        history = self.controller.history.get_history()
        matching: list[HistoryEntryData] = []
        autocomp = None

        for entry in history:
            url = entry.url
            if not url:
                continue
            domain = re.sub(r"^https?://", "", url)

            url_exists = False
                
            for match in matching:
                if match.url == url:
                    url_exists = True
                    continue

            if url.startswith(user_url):
                if not url_exists:
                    matching.append(entry)

                if autocomp is None:
                    autocomp = url

            elif domain.startswith(user_url):
                if not url_exists:
                    matching.append(entry)

                if autocomp is None:
                    autocomp = domain

        if autocomp is not None and autocomp != user_url:
            self._autocomplete(user_url, autocomp)

        self._display_menu(matching)
    
    def _on_history_entry_selected(self, url: str):
        if self.browser:
            self.hide_bar()
            self.browser.load_page(url)

    def _on_url_changed(self, url: QUrl):
        if not self.url_input.hasFocus():
            self.url_input.setText(url.toString())

    def _on_return_pressed(self):
        url = self.url_input.text().strip()
        if not url or not self.browser:
            self.hide_bar()
            return

        self.browser.load_page(url)
        self.hide_bar()

    def show_bar(self):
        if self.browser:
            current_url = self.browser.url().toString()
            self.url_input.setText(current_url)
            self.url_input.selectAll()

        self.show()
        self.raise_()
        self.url_input.setFocus()

        # Center in the parent
        if self.parent():
            parent_width = self.parent().width()
            parent_height = self.parent().height()
            bar_width = min(600, parent_width - 80)
            self.setFixedWidth(bar_width)
            x = (parent_width - bar_width) // 2
            y = (parent_height - self.height()) // 3
            self.move(x, y)

    def hide_bar(self):
        if hasattr(self, '_menu') and self._menu:
            self._menu.close()
            self._menu = None
        self.hide()
        if self.browser:
            self.browser.setFocus()
