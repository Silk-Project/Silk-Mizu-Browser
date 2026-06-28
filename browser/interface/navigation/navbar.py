from PySide6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QPushButton,
    QLineEdit,
)
from PySide6.QtCore import QUrl
from PySide6.QtWebEngineWidgets import QWebEngineView
from interface.widgets.better_webengine import BetterWebEngine

class AddressBar(QLineEdit):
    def __init__(self, controller, parent=None):
        super().__init__(parent)

        self.browser: BetterWebEngine = None
        controller.currentBrowserChanged.connect(self.set_browser)

        self.setPlaceholderText("https://")
        self.returnPressed.connect(self.on_return_pressed)
        
    
    def set_browser(self, browser):
        if self.browser:
            self.browser.urlChanged.disconnect(self.update_url)

        self.browser = browser

        self.browser.urlChanged.connect(self.update_url)

        self.update_url(browser.url())

    def update_url(self, url: QUrl):
        str_url = url.toString()
        self.setText(str_url)

    def on_return_pressed(self):
        if not self.browser:
            return

        url = self.text()
        self.browser.load_page(url)

class BackBtn(QPushButton):
    def __init__(self, controller, parent = None):
        super().__init__(parent)

        self.browser: BetterWebEngine = None
        self.setEnabled(False)
        controller.currentBrowserChanged.connect(self.set_browser)
    
    def set_browser(self, browser):
        if self.browser:
            self.browser.iconChanged.disconnect(self.update_status)
            self.browser.urlChanged.disconnect(self.update_status)

        self.browser = browser

        self.browser.iconChanged.connect(self.update_status)
        self.browser.urlChanged.connect(self.update_status)
        self.clicked.connect(self.go_back)

        self.update_status()
    
    def update_status(self):
        self.setEnabled(self.browser.history().canGoBack())
    
    def go_back(self):
        if self.browser:
            self.browser.back()