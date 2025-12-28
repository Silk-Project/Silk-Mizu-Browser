import sys
import os
import json
import re
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QFormLayout,
    QPushButton,
    QLineEdit,
    QComboBox,
    QCheckBox,
    QDialog,
    QLabel,
    QDialogButtonBox
)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtGui import QPixmap, QIcon, QAction

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config", "settings.json")
VERSION_NUMBER = "0.0.1"
SEARCH_ENGINE_SEARCH_QUERIES = {
    "Google":"https://www.google.com/search?q=",
    "DuckDuckGo":"https://duckduckgo.com/?q="
}
start_page = "https://silk-project.github.io/"
search_engine = "Google"
default_settings = {
    "start_page_url":"https://silk-project.github.io/",
    "search_engine":"Google"
}

# Load settings.json
if os.path.exists(CONFIG_PATH):
    with open(CONFIG_PATH, "r") as f:
        d = json.load(f)

        if d["start_page_url"] and d["search_engine"]:
            start_page = d["start_page_url"]
            search_engine = d["search_engine"]
        else:
            print("Failed to load settings.json.")
        
else:
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(default_settings, f, indent=4)

class WebEngine():
    def __init__(self, window, url_bar, prevbtn, nextbtn):
        self.window = window
        self.url_bar = url_bar
        self.prevbtn = prevbtn
        self.nextbtn = nextbtn

        self.init_engine()
    
    def init_engine(self):
        self.load_page(start_page)
        self.update_nav_btn_status()
    
    def load_page(self, url):
        # Load URL if valid, else use the default search engine
        if self.valid_url(url):
            self.window.setUrl(QUrl(url))
        else:
            # Get url for search engine
            search_url = SEARCH_ENGINE_SEARCH_QUERIES.get(search_engine) + url
            self.window.setUrl(QUrl(search_url))
        
        self.update_url_bar()
        self.update_nav_btn_status()
          
    def update_url_bar(self):
        url = self.window.url().toString()
        self.url_bar.setText(url)
        self.update_nav_btn_status()
    
    def update_nav_btn_status(self):
        # Activate / Deactivate Back and Forward Buttons
        self.prevbtn.setEnabled(True if self.window.history().canGoBack() == True else False)
        self.nextbtn.setEnabled(True if self.window.history().canGoForward() == True else False)
    
    def valid_url(self, url):
        # Regex for standard http/https URLs
        regex = re.compile(
            r'^(?:http|ftp)s?://' # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' # domain...
            r'localhost|' # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
            r'(?::\d+)?' # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)

        return re.match(regex, url) is not None
    
    def back_page(self):
        self.window.history().back()

    def next_page(self):
        self.window.history().forward()

class BrowserWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Silk Mizu")
        self.setMinimumSize(960, 720)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        controls_layout = QHBoxLayout()
        layout.addLayout(controls_layout)

        # Browser main controls
        self.prev_page_btn = QPushButton("<")
        self.prev_page_btn.setStyleSheet("padding: 10px;")
        self.prev_page_btn.clicked.connect(self.request_back_page)
        controls_layout.addWidget(self.prev_page_btn)

        self.next_page_btn = QPushButton(">")
        self.next_page_btn.setStyleSheet("padding: 10px;")
        self.next_page_btn.clicked.connect(self.request_next_page)
        controls_layout.addWidget(self.next_page_btn)

        self.url_bar = QLineEdit()
        self.url_bar.setStyleSheet("padding: 10px;")
        self.url_bar.clearFocus()
        self.url_bar.returnPressed.connect(self.request_load_page)
        controls_layout.addWidget(self.url_bar)

        self.load_btn = QPushButton("Load")
        self.load_btn.setStyleSheet("padding: 10px;")
        self.load_btn.clicked.connect(self.request_load_page)
        controls_layout.addWidget(self.load_btn)

        # Web Engine
        self.web_widget = QWebEngineView()
        self.web_engine = WebEngine(self.web_widget, self.url_bar, self.prev_page_btn, self.next_page_btn)
        self.web_widget.urlChanged.connect(self.web_engine.update_url_bar)
        layout.addWidget(self.web_widget)

        # Add menu bar
        menu_bar = self.menuBar()

        fileMenu = menu_bar.addMenu("&File")
        editMenu = menu_bar.addMenu("&Edit")
        settingsMenu = menu_bar.addMenu("&Settings")
        helpMenu = menu_bar.addMenu("&Help")

        # File Menu
        # Edit Menu
        # Settings Menu
        settingsAction = settingsMenu.addAction("Program Settings")
        settingsAction.triggered.connect(self.settings_dialog)
        settingsMenu.addAction(settingsAction)

        # Help Menu
        aboutAction = helpMenu.addAction("About")
        aboutAction.triggered.connect(self.about_dialog)
        helpMenu.addAction(aboutAction)

        # Add main widget
        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)

    def request_load_page(self):
        url = self.url_bar.text()
        self.web_engine.load_page(url)
    
    def request_back_page(self):
        self.web_engine.back_page()

    def request_next_page(self):
        self.web_engine.next_page()
    
    def settings_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Settings")
        dlg.setFixedSize(480, 360)

        layout = QGridLayout()
        settings_layout = QFormLayout()

        start_page_lineedit = QLineEdit()
        start_page_lineedit.setText(start_page)
        start_page_lineedit.setMinimumWidth(200)
        settings_layout.addRow("Start Page: ", start_page_lineedit)

        search_engine_combobox = QComboBox()
        search_engine_combobox.addItems(["Google", "DuckDuckGo"])
        search_engine_combobox.setCurrentText(search_engine)
        settings_layout.addRow("Search Engine: ", search_engine_combobox)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(dlg.accept)
        button_box.rejected.connect(dlg.reject)

        layout.addLayout(settings_layout, 0, 0)
        layout.addWidget(button_box, 1, 1)

        dlg.setLayout(layout)

        if dlg.exec():
            settings = {
                "start_page_url":start_page_lineedit.text(),
                "search_engine":search_engine_combobox.currentText()
            }

            with open(CONFIG_PATH, "w") as f:
                json.dump(settings, f, indent=4)
        
    def about_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("About")
        dlg_layout = QVBoxLayout()
        dlg.setFixedSize(240, 270)

        logoLabel = QLabel(self)
        logoLabel.setFixedSize(150, 150)
        logoLabel.setScaledContents(True)
        logo_path = os.path.join(SCRIPT_DIR, "assets", "mizu.png")
        
        if os.path.exists(logo_path):
            logoLabel.setPixmap(QPixmap(logo_path))

        about_title = QLabel("Silk Mizu")
        about_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        about_title.setStyleSheet("font-size: 20px; font-weight: bold;")
        about_description = QLabel("A simple PyQT6 browser for Silk and Linux devices.")
        about_description.setWordWrap(True)
        about_description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        about_label = QLabel(f"Version: {VERSION_NUMBER}\nSilk Project 2025")
        about_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        dlg_layout.addWidget(logoLabel, alignment=Qt.AlignmentFlag.AlignCenter)
        dlg_layout.addWidget(about_title)
        dlg_layout.addWidget(about_description)
        dlg_layout.addWidget(about_label)
        dlg.setLayout(dlg_layout)
        dlg.exec()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("Silk Mizu")
    app.setStyle("breeze")
    window = BrowserWindow()
    window.show()
    sys.exit(app.exec())