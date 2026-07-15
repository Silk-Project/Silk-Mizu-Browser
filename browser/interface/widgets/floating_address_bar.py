from PySide6.QtWidgets import QWidget, QLineEdit, QHBoxLayout
from PySide6.QtCore import Qt, Signal, QUrl
from PySide6.QtGui import QKeyEvent
from interface.widgets.better_webengine import BetterWebEngine

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
        self.hide()
        if self.browser:
            self.browser.setFocus()
