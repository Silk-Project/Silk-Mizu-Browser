from PySide6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QPushButton,
    QLineEdit,
)

class AddressBar(QLineEdit):
    def __init__(self, browser, parent=None):
        super().__init__(parent)
        self.browser = browser
        self.setPlaceholderText("https://")
        self.returnPressed.connect(self.on_return_pressed)
        self.browser.signals.update_url_bar_content.connect(lambda url: self.setText(url))

    def on_return_pressed(self):
        url = self.text()
        self.browser.request_load_page(url)

class BackBtn(QPushButton):
    def __init__(self, browser, parent = None):
        super().__init__(parent)

        self.browser = browser
        