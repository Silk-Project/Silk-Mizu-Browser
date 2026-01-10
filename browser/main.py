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
    QSpinBox,
    QDialog,
    QLabel,
    QDialogButtonBox,
    QProgressBar,
    QListWidget,
    QTabWidget
)
from PyQt6.QtCore import Qt, QUrl, QSize
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings
from PyQt6.QtGui import QPixmap, QAction, QKeySequence
import qtawesome as qta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config", "settings.json")
BOOKMARKS_PATH = os.path.join(SCRIPT_DIR, "config", "bookmarks.json")
VERSION_NUMBER = "0.2.4"
SEARCH_ENGINE_SEARCH_QUERIES = {
    "Google":"https://www.google.com/search?q=",
    "DuckDuckGo":"https://duckduckgo.com/?q=",
    "Brave":"https://search.brave.com/search?q=",
    "Ecosia":"https://www.ecosia.org/search?method=index&q=",
    "Yahoo":"https://search.yahoo.com/search?p="
}

current_settings = {}
default_settings = {
    "start_page_url":"https://silk-project.github.io/",
    "search_engine":"Google",
    "javascript_enabled":True,
    "default_font_size":16
}

current_bookmarks = {}
default_bookmarks = {
    "Google":"https://google.com/",
    "Wikipedia":"https://wikipedia.org/"
}

# Load settings.json
if os.path.exists(CONFIG_PATH):
    with open(CONFIG_PATH, "r") as f:
        d = json.load(f)

        try:
            for setting, value in d.items():
                current_settings[setting] = value
            print(current_settings)
        except KeyError:
            current_settings = default_settings
            print("Failed to load settings.json. Using default settings.")
        
else:
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(default_settings, f, indent=4)
    current_settings = default_settings

# Load bookmarks.json
if os.path.exists(BOOKMARKS_PATH):
    with open(BOOKMARKS_PATH, "r") as f:
        d = json.load(f)

        try:
            for name, url in d.items():
                current_bookmarks[name] = url
            print(current_bookmarks)
        except KeyError:
            current_bookmarks = default_bookmarks
            print("Failed to load bookmarks.json. Using default bookmarks.")
else:
    os.makedirs(os.path.dirname(BOOKMARKS_PATH), exist_ok=True)
    with open(BOOKMARKS_PATH, "w") as f:
        json.dump(default_bookmarks, f, indent=4)
    current_bookmarks = default_bookmarks

class WebEngine():
    def __init__(self, window, url_bar, prevbtn, nextbtn, reloadbtn, page_progress, zoom_label):
        self.window = window
        self.url_bar = url_bar
        self.prevbtn = prevbtn
        self.nextbtn = nextbtn
        self.reloadbtn = reloadbtn
        self.page_progress = page_progress
        self.zoom_label = zoom_label

        self.page_is_loading = False

        self.init_engine()
    
    def init_engine(self):
        self.load_page(current_settings["start_page_url"])
        self.update_nav_btn_status()
    
    def load_page(self, url):
        # Load URL if valid, else use the default search engine
        processed_url = QUrl.fromUserInput(url).toString()
        if self.valid_url(processed_url) or self.valid_url(url):
            self.window.setUrl(QUrl(processed_url))
        else:
            # Get url for search engine
            search_url = SEARCH_ENGINE_SEARCH_QUERIES.get(current_settings["search_engine"]) + url
            self.window.setUrl(QUrl(search_url))
        
        self.page_is_loading = True
        self.update_url_bar()
        self.update_nav_btn_status()
    
    def get_page_load_status(self):
        return self.page_is_loading
    
    def reload_page(self):
        self.page_is_loading = True
        self.window.reload()
        self.update_nav_btn_status()
    
    def stop_page_load(self):
        self.page_is_loading = False
        self.window.stop()
        self.update_nav_btn_status()
          
    def update_url_bar(self):
        url = self.window.url().toString()
        self.url_bar.setText(url)
        self.update_nav_btn_status()
    
    def update_nav_btn_status(self):
        # Activate / Deactivate Back and Forward Buttons
        self.prevbtn.setEnabled(self.window.history().canGoBack())
        self.nextbtn.setEnabled(self.window.history().canGoForward())

        # Update reload / stop button
        if self.page_is_loading:
            self.reloadbtn.setIcon(qta.icon("ei.remove"))
        else:
            self.reloadbtn.setIcon(qta.icon("fa6s.arrow-rotate-right"))
    
    def page_load_finished(self):
        self.page_is_loading = False
        self.page_progress.setValue(0)
        self.update_nav_btn_status()
    
    def update_page_progress(self, prog):
        self.page_progress.setValue(prog)
    
    def valid_url(self, url):
        # Regex for standard http/https URLs and file paths
        regex = re.compile(
            r'^(?:(?:http|ftp)s?|file)://'  # file
            r'(?:'
                r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' # domain
                r'localhost|' # localhost
                r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # or ip
            r'|' # OR 
                r'/[^\s]+' # Absolute path for file:/// schemes
            r')'
            r'(?::\d+)?' # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)

        return re.match(regex, url) is not None
    
    def back_page(self):
        self.window.history().back()

    def next_page(self):
        self.window.history().forward()

    def update_zoom_label(self):
        zoom_string = str(round(self.window.zoomFactor() * 100)) + "%"
        self.zoom_label.setText(zoom_string)
    
    def scale_page_up(self):
        zoom_factor = self.window.zoomFactor()
        self.window.setZoomFactor(zoom_factor + 0.1)
        self.update_zoom_label()

    def scale_page_down(self):
        zoom_factor = self.window.zoomFactor()
        self.window.setZoomFactor(zoom_factor - 0.1)
        self.update_zoom_label()
    
    def scale_page_reset(self):
        self.window.setZoomFactor(1)
        self.update_zoom_label()
    
    def update_engine(self):
        settings = self.window.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled,
                             current_settings["javascript_enabled"])
        settings.setFontSize(QWebEngineSettings.FontSize.DefaultFontSize,
                             current_settings["default_font_size"])

class ManageBookmarksDialog(QDialog):
    def __init__(self, parent, passed_bookmarks):
        super().__init__(parent)
        self.setWindowTitle("Manage Bookmarks")
        self.setFixedSize(400, 300)

        # Temporary copy of bookmarks for editing
        self.temp_bookmarks = []
        for name, url in passed_bookmarks.items():
            self.temp_bookmarks.append({'name':name, 'url':url})

        self.init_ui()

        # Select first item if exists
        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)
    
    def init_ui(self):
        self.setWindowTitle("Manage Bookmarks")
        self.setFixedSize(400, 300)

        layout = QVBoxLayout(self)
        content_layout = QHBoxLayout()

        # Title
        title_label = QLabel("Manage Bookmarks")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; padding: 20px")
        layout.addWidget(title_label)

        # Left side: Bookmark list
        self.list_widget = QListWidget()
        for b in self.temp_bookmarks:
            self.list_widget.addItem(b['name'])

        self.list_widget.currentRowChanged.connect(self.load_bookmark_to_inputs)
        content_layout.addWidget(self.list_widget, 1)

        # Right side: Bookmark actions
        action_layout = QVBoxLayout()

        add_btn = QPushButton("Add New")
        add_btn.setIcon(qta.icon("fa6s.plus"))
        add_btn.setIconSize(QSize(16, 16))
        add_btn.clicked.connect(self.add_bookmark)
        action_layout.addWidget(add_btn)

        delete_btn = QPushButton("Delete")
        delete_btn.setIcon(qta.icon("fa6s.minus"))
        delete_btn.setIconSize(QSize(16, 16))
        delete_btn.clicked.connect(self.delete_bookmark)
        action_layout.addWidget(delete_btn)

        action_layout.addStretch(1)

        # Middle: Live editor of selected bookmark
        edit_layout = QFormLayout()
        edit_layout.setContentsMargins(0, 5, 0, 5)

        self.name_lineedit = QLineEdit()
        self.name_lineedit.textEdited.connect(self.sync_data_live)
        edit_layout.addRow("Bookmark Name: ", self.name_lineedit)

        self.url_lineedit = QLineEdit()
        self.url_lineedit.textEdited.connect(self.sync_data_live)
        edit_layout.addRow("Bookmark URL: ", self.url_lineedit)

        # Save / Cancel buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        # Assemble layouts
        content_layout.addLayout(action_layout, 0)

        layout.addLayout(content_layout)
        layout.addLayout(edit_layout)
        layout.addWidget(button_box)
        self.setLayout(layout)
    
    def load_bookmark_to_inputs(self, row):
        """Switches the editor to show the data for the selected row."""
        # Block signals so setting the text doesn't trigger sync_data_live
        self.name_lineedit.blockSignals(True)
        self.url_lineedit.blockSignals(True)
        
        if row >= 0:
            bm = self.temp_bookmarks[row]
            self.name_lineedit.setText(bm['name'])
            self.url_lineedit.setText(bm['url'])
            self.name_lineedit.setEnabled(True)
            self.url_lineedit.setEnabled(True)
        else:
            self.name_lineedit.clear()
            self.url_lineedit.clear()
            self.name_lineedit.setEnabled(False)
            self.url_lineedit.setEnabled(False)
            
        self.name_lineedit.blockSignals(False)
        self.url_lineedit.blockSignals(False)

    def sync_data_live(self):
        """Updates the internal list and the Sidebar List UI as the user types."""
        row = self.list_widget.currentRow()
        if row >= 0:
            new_name = self.name_lineedit.text()
            new_url = self.url_lineedit.text()
            
            # Update the temporary data list
            self.temp_bookmarks[row]['name'] = new_name
            self.temp_bookmarks[row]['url'] = new_url
            
            # Update the list item text live so the user sees the rename
            self.list_widget.item(row).setText(new_name if new_name else "Untitled")

    def add_bookmark(self):
        new_bm = {"name": "New Bookmark", "url": "https://"}
        self.temp_bookmarks.append(new_bm)
        self.list_widget.addItem(new_bm['name'])
        self.list_widget.setCurrentRow(self.list_widget.count() - 1)

    def delete_bookmark(self):
        row = self.list_widget.currentRow()
        if row >= 0:
            self.temp_bookmarks.pop(row)
            self.list_widget.takeItem(row)

class BrowserWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Window configuration
        self.setWindowTitle("Silk Mizu")
        self.setMinimumSize(480, 360)
        self.resize(960, 720)
        self.layout = QGridLayout()

        # Initialize whole UI
        self.init_menu_bar()
        self.init_control_ui()
        self.init_web_engine()

        # Add main widget
        widget = QWidget()
        widget.setLayout(self.layout)
        self.setCentralWidget(widget)
    
    def init_menu_bar(self):
        # Add menu bar
        menu_bar = self.menuBar()

        fileMenu = menu_bar.addMenu("&File")
        editMenu = menu_bar.addMenu("&Edit")
        viewMenu = menu_bar.addMenu("&View")
        bookmarkMenu = menu_bar.addMenu("&Bookmarks")
        helpMenu = menu_bar.addMenu("&Help")

        # File Menu
        settingsAction = fileMenu.addAction("Program Settings")
        settingsAction.triggered.connect(self.settings_dialog)
        settingsAction.setShortcut(QKeySequence("Ctrl + s"))
        fileMenu.addAction(settingsAction)

        exitAction = fileMenu.addAction("Quit")
        exitAction.triggered.connect(sys.exit)
        exitAction.setShortcut(QKeySequence("Ctrl + q"))
        fileMenu.addAction(exitAction)

        # Edit Menu
        backAction = editMenu.addAction("Back")
        backAction.triggered.connect(self.request_back_page)
        backAction.setShortcut("Alt + left")
        editMenu.addAction(backAction)

        nextAction = editMenu.addAction("Next")
        nextAction.triggered.connect(self.request_next_page)
        nextAction.setShortcut(QKeySequence("Alt + right"))
        editMenu.addAction(nextAction)

        # View Menu
        scaleUpAction = viewMenu.addAction("Increase page zoom by 10%")
        scaleUpAction.triggered.connect(self.request_scale_page_up)
        scaleUpAction.setShortcut(QKeySequence("Ctrl + +"))
        viewMenu.addAction(scaleUpAction)

        scaleDownAction = viewMenu.addAction("Decrease page zoom by 10%")
        scaleDownAction.triggered.connect(self.request_scale_page_down)
        scaleDownAction.setShortcut(QKeySequence("Ctrl + -"))
        viewMenu.addAction(scaleDownAction)

        scaleDefaultAction = viewMenu.addAction("Set page zoom to 100%")
        scaleDefaultAction.triggered.connect(self.request_scale_page_reset)
        viewMenu.addAction(scaleDefaultAction)

        # Bookmarks Menu
        manageBookmarksAction = bookmarkMenu.addAction("Manage bookmarks")
        manageBookmarksAction.triggered.connect(self.manage_bookmarks_dialog)
        manageBookmarksAction.setShortcut(QKeySequence("Ctrl + shift + o"))
        bookmarkMenu.addAction(manageBookmarksAction)

        addPageToBookmarksAction = bookmarkMenu.addAction("Add current page to bookmarks")
        addPageToBookmarksAction.triggered.connect(self.add_current_to_bookmarks_dialog)
        addPageToBookmarksAction.setShortcut(QKeySequence("Ctrl + d"))
        bookmarkMenu.addAction(addPageToBookmarksAction)

        # Help Menu
        documentationAction = QAction("Project Page", self)
        documentationAction.triggered.connect(lambda: self.web_engine.load_page("https://github.com/FlipArtYT/Silk-Mizu-Browser/"))
        helpMenu.addAction(documentationAction)

        aboutAction = helpMenu.addAction("About")
        aboutAction.triggered.connect(self.about_dialog)
        helpMenu.addAction(aboutAction)

    def init_control_ui(self):
        # Add main controls
        controls_layout = QHBoxLayout()
        bottom_bar_layout = QHBoxLayout()
        self.layout.addLayout(controls_layout, 0, 0)
        self.layout.addLayout(bottom_bar_layout, 3, 0)

        # Browser main controls
        self.prev_page_btn = QPushButton()
        self.prev_page_btn.setIcon(qta.icon("fa6s.arrow-left"))
        self.prev_page_btn.setProperty("class", "navbtns")
        self.prev_page_btn.setStyleSheet("padding: 10px;")
        self.prev_page_btn.clicked.connect(self.request_back_page)
        controls_layout.addWidget(self.prev_page_btn)

        self.next_page_btn = QPushButton()
        self.next_page_btn.setIcon(qta.icon("fa6s.arrow-right"))
        self.next_page_btn.setProperty("class", "navbtns")
        self.next_page_btn.setStyleSheet("padding: 10px;")
        self.next_page_btn.clicked.connect(self.request_next_page)
        controls_layout.addWidget(self.next_page_btn)

        self.reload_page_btn = QPushButton()
        self.reload_page_btn.setIcon(qta.icon("fa6s.arrow-rotate-right"))
        self.reload_page_btn.setProperty("class", "navbtns")
        self.reload_page_btn.setStyleSheet("padding: 10px;")
        self.reload_page_btn.clicked.connect(self.request_reload_stop_page)
        controls_layout.addWidget(self.reload_page_btn)

        self.url_bar = QLineEdit()
        self.url_bar.setObjectName("url_bar")
        self.url_bar.setStyleSheet("padding: 10px;")
        self.url_bar.clearFocus()
        self.url_bar.returnPressed.connect(self.request_load_page_from_urlbar)
        controls_layout.addWidget(self.url_bar)

        self.load_btn = QPushButton("Go")
        self.load_btn.setIcon(qta.icon("mdi.arrow-right-bold-box"))
        self.load_btn.setProperty("class", "navbtns")
        self.load_btn.setStyleSheet("padding: 10px;")
        self.load_btn.clicked.connect(self.request_load_page_from_urlbar)
        controls_layout.addWidget(self.load_btn)

        self.add_to_bookmarks_btn = QPushButton()
        self.add_to_bookmarks_btn.setIcon(qta.icon("fa5s.star"))
        self.add_to_bookmarks_btn.setProperty("class", "navbtns")
        self.add_to_bookmarks_btn.setStyleSheet("padding: 10px;")
        self.add_to_bookmarks_btn.clicked.connect(self.add_current_to_bookmarks_dialog)
        controls_layout.addWidget(self.add_to_bookmarks_btn)

        self.settings_btn = QPushButton()
        self.settings_btn.setIcon(qta.icon("fa5s.cog"))
        self.settings_btn.setProperty("class", "navbtns")
        self.settings_btn.setStyleSheet("padding: 10px;")
        self.settings_btn.clicked.connect(self.settings_dialog)
        controls_layout.addWidget(self.settings_btn)

        # Bookmark bar
        self.init_bookmark_bar()

        # Bottom bar
        self.page_progressbar = QProgressBar()
        self.page_progressbar.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.page_progressbar.setFixedWidth(200)
        self.page_progressbar.setValue(0)
        bottom_bar_layout.addWidget(self.page_progressbar)

        bottom_bar_layout.addStretch(1)

        self.scale_down_btn = QPushButton()
        self.scale_down_btn.setIcon(qta.icon("ph.magnifying-glass-minus"))
        self.scale_down_btn.setProperty("class", "navbtns")
        self.scale_down_btn.setStyleSheet("padding: 5px")
        self.scale_down_btn.clicked.connect(self.request_scale_page_down)
        bottom_bar_layout.addWidget(self.scale_down_btn)

        self.zoom_factor_label = QLabel("100%")
        bottom_bar_layout.addWidget(self.zoom_factor_label)

        self.scale_up_btn = QPushButton()
        self.scale_up_btn.setIcon(qta.icon("ph.magnifying-glass-plus"))
        self.scale_up_btn.setProperty("class", "navbtns")
        self.scale_up_btn.setStyleSheet("padding: 5px")
        self.scale_up_btn.clicked.connect(self.request_scale_page_up)
        bottom_bar_layout.addWidget(self.scale_up_btn)

    def init_bookmark_bar(self):
        # Bookmark bar
        bookmarks_layout = QHBoxLayout()
        self.layout.addLayout(bookmarks_layout, 1, 0)

        # Clear existing bookmarks
        for i in reversed(range(bookmarks_layout.count())):
            widget_to_remove = bookmarks_layout.itemAt(i).widget()
            if widget_to_remove is not None:
                widget_to_remove.setParent(None)

        bookmark_map = {}

        for name, url in current_bookmarks.items():
            bookmark_btn = QPushButton(name)
            bookmark_btn.setStyleSheet("padding: 5px;")
            bookmark_btn.clicked.connect(lambda checked, url=url: self.request_load_page(url))
            bookmark_map[name] = bookmark_btn
            bookmarks_layout.addWidget(bookmark_btn)

        bookmarks_layout.addStretch(1)

        print("Bookmark bar initialized with bookmarks:", bookmark_map.keys())
    
    def init_web_engine(self):
        # Web Engine
        self.web_widget = QWebEngineView()
        self.web_engine = WebEngine(self.web_widget,
                                    self.url_bar,
                                    self.prev_page_btn,
                                    self.next_page_btn,
                                    self.reload_page_btn,
                                    self.page_progressbar,
                                    self.zoom_factor_label)
        self.web_widget.urlChanged.connect(self.web_engine.update_url_bar)
        self.web_widget.loadProgress.connect(self.web_engine.update_page_progress)
        self.web_widget.loadFinished.connect(self.web_engine.page_load_finished)
        self.layout.addWidget(self.web_widget, 2, 0)

    def request_load_page_from_urlbar(self):
        url = self.url_bar.text()
        self.web_engine.load_page(url)
    
    def request_load_page(self, url):
        self.web_engine.load_page(url)
    
    def request_reload_stop_page(self):
        if self.web_engine.page_is_loading:
            self.web_engine.stop_page_load()
        else:
            self.web_engine.reload_page()
    
    def request_back_page(self):
        self.web_engine.back_page()

    def request_next_page(self):
        self.web_engine.next_page()
    
    def request_scale_page_up(self):
        self.web_engine.scale_page_up()
    
    def request_scale_page_down(self):
        self.web_engine.scale_page_down()
    
    def request_scale_page_reset(self):
        self.web_engine.scale_page_reset()

    def add_current_to_bookmarks_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Add to Bookmarks")
        dlg.setFixedSize(340, 220)

        layout = QGridLayout()
        form_layout = QFormLayout()

        title_label = QLabel("Add Current Page to Bookmarks")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; padding: 20px")
        form_layout.addRow(title_label)

        name_lineedit = QLineEdit()
        name_lineedit.setText(self.web_widget.title())
        name_lineedit.setMinimumWidth(200)
        form_layout.addRow("Bookmark name: ", name_lineedit)

        url_lineedit = QLineEdit()
        url_lineedit.setText(self.web_widget.url().toString())
        url_lineedit.setMinimumWidth(200)
        form_layout.addRow("Bookmark URL: ", url_lineedit)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(dlg.accept)
        button_box.rejected.connect(dlg.reject)

        layout.addLayout(form_layout, 0, 0, 0, 2)
        layout.addWidget(button_box, 1, 1)

        dlg.setLayout(layout)

        if dlg.exec():
            bookmark_name = name_lineedit.text()
            bookmark_url = url_lineedit.text()

            current_bookmarks[bookmark_name] = bookmark_url

            with open(CONFIG_PATH, "w") as f:
                json.dump(current_settings, f, indent=4)
            
            self.init_bookmark_bar()
    
    def manage_bookmarks_dialog(self):
        global current_bookmarks
        dlg = ManageBookmarksDialog(self, current_bookmarks)

        if dlg.exec():
            updated_bookmarks = {b['name']: b['url'] for b in dlg.temp_bookmarks}
        
            current_bookmarks = updated_bookmarks
        
            # Save to file
            with open(BOOKMARKS_PATH, "w") as f:
                json.dump(updated_bookmarks, f, indent=4)
        
            self.init_bookmark_bar()
    
    def settings_dialog(self):
        global current_settings

        dlg = QDialog(self)
        dlg.setWindowTitle("Settings")
        dlg.setFixedSize(480, 360)

        layout = QGridLayout()

        # Settings tab widget
        tabs = QTabWidget()

        # General Tab
        general_settings = QWidget()
        general_settings_layout = QFormLayout()
        general_settings.setLayout(general_settings_layout)

        title_label = QLabel("Browser Settings")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; padding-top: 20px; padding-bottom: 10px;")
        layout.addWidget(title_label, 0, 0)

        start_page_lineedit = QLineEdit()
        start_page_lineedit.setText(current_settings["start_page_url"])
        start_page_lineedit.setMinimumWidth(200)
        general_settings_layout.addRow("Start page: ", start_page_lineedit)

        search_engine_combobox = QComboBox()
        search_engine_combobox.addItems(["Google", "DuckDuckGo", "Brave", "Ecosia", "Yahoo"])
        search_engine_combobox.setCurrentText(current_settings["search_engine"])
        general_settings_layout.addRow("Search engine: ", search_engine_combobox)

        # Display settings
        display_settings = QWidget()
        display_settings_layout = QFormLayout()
        display_settings.setLayout(display_settings_layout)

        font_size_spinbox = QSpinBox()
        font_size_spinbox.setRange(10, 80)
        font_size_spinbox.setValue(current_settings["default_font_size"])
        display_settings_layout.addRow("Default font size: ", font_size_spinbox)

        theme_combobox = QComboBox()
        theme_combobox.addItems(["Light", "Dark", "System Default"])
        theme_combobox.setCurrentText("System Default")
        display_settings_layout.addRow("Theme: ", theme_combobox)

        # Engine tab settings
        engine_settings = QWidget()
        engine_settings_layout = QFormLayout()
        engine_settings.setLayout(engine_settings_layout)

        javascript_checkbox = QCheckBox()
        javascript_checkbox.setChecked(current_settings["javascript_enabled"])
        engine_settings_layout.addRow("Javascript enabled: ", javascript_checkbox)

        # Add widgets to tab widget
        tabs.addTab(general_settings, "General")
        tabs.addTab(display_settings, "Display")
        tabs.addTab(engine_settings, "Engine")

        # Add Ok and Cancel buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(dlg.accept)
        button_box.rejected.connect(dlg.reject)

        layout.addWidget(tabs, 1, 0)
        layout.addWidget(button_box, 2, 0, alignment=Qt.AlignmentFlag.AlignRight)

        dlg.setLayout(layout)

        if dlg.exec():
            start_page = start_page_lineedit.text()
            search_engine = search_engine_combobox.currentText()
            javascript_enabled = javascript_checkbox.isChecked()
            default_font_size = font_size_spinbox.value()

            updated_settings = {
                "start_page_url":start_page,
                "search_engine":search_engine,
                "javascript_enabled":javascript_enabled,
                "default_font_size":default_font_size
            }

            current_settings = updated_settings

            self.update_web_engine()

            with open(CONFIG_PATH, "w") as f:
                json.dump(updated_settings, f, indent=4)
    
    def update_web_engine(self):
        self.web_engine.update_engine()
        
    def about_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("About")
        dlg_layout = QVBoxLayout()
        dlg.setFixedSize(240, 300)

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
        about_label = QLabel(f"Version: {VERSION_NUMBER}\nSilk Project 2025-26")
        about_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        button_box.setContentsMargins(0, 8, 0, 8)
        button_box.accepted.connect(dlg.accept)

        dlg_layout.addWidget(logoLabel, alignment=Qt.AlignmentFlag.AlignCenter)
        dlg_layout.addWidget(about_title)
        dlg_layout.addWidget(about_description)
        dlg_layout.addWidget(about_label)
        dlg_layout.addWidget(button_box, alignment=Qt.AlignmentFlag.AlignCenter)
        dlg.setLayout(dlg_layout)
        
        dlg.exec()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("Silk Mizu")
    app.setStyleSheet("""
.navbtns {
    background-color: #333;
    border: 1px solid #444;
    border-radius: 3px;
}
                      
.navbtns:hover {
    background-color: #393939;
}

.navbtns:pressed {
    background-color: #353535;
}
                      
QLineEdit {
    background-color: #333;
    border: 1px solid #444;
    border-radius: 3px;
}
""")
    app.setStyle("breeze")
    window = BrowserWindow()
    window.show()
    sys.exit(app.exec())
