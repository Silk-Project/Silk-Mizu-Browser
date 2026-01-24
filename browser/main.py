import sys
import os
import json
import re
import copy
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
    QTabWidget,
    QRadioButton,
    QButtonGroup,
    QMessageBox,
    QSizePolicy,
    QTextEdit,
)
from PyQt6.QtCore import Qt, QUrl, QSize, pyqtSlot, pyqtSignal, QThreadPool, QRunnable, QObject
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings
from PyQt6.QtGui import QPixmap, QAction, QKeySequence, QIcon
import qtawesome as qta
import qdarktheme
import darkdetect
import ollama

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config", "settings.json")
BOOKMARKS_PATH = os.path.join(SCRIPT_DIR, "config", "bookmarks.json")
START_PAGE_PATH = os.path.join(SCRIPT_DIR, "assets", "Silk-Start", "start", "v1.1.1", "seperate", "index.html")
AI_SYSPROMPT_PATH = os.path.join(SCRIPT_DIR, "config", "sysprompt.txt")
VERSION_NUMBER = "0.2.5"
SEARCH_ENGINE_SEARCH_QUERIES = {
    "Google":"https://www.google.com/search?q=",
    "DuckDuckGo":"https://duckduckgo.com/?q=",
    "Brave":"https://search.brave.com/search?q=",
    "Ecosia":"https://www.ecosia.org/search?method=index&q=",
    "Yahoo":"https://search.yahoo.com/search?p="
}

current_settings = {}
default_settings = {
    "start_page_url":START_PAGE_PATH,
    "search_engine":"Google",
    "theme":"Dark",
    "bottom_bar_visible":False,
    "go_button_visible":False,
    "javascript_enabled":True,
    "default_font_size":16,
    "scrollbars_enabled":True,
    "ai_summarization_enabled":False
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

# Load AI system prompt
with open(AI_SYSPROMPT_PATH, 'r') as f:
    ai_system_prompt = f.read()

class BetterWebEngine(QWebEngineView):
    def __init__(self, parent):
        super().__init__(parent)
        self.page_is_loading = False
        self.init_engine()
        self.update_engine_config()
    
    def init_engine(self):
        self.load_page(current_settings["start_page_url"])

    def load_page(self, url):
        # Load URL if valid, else use the default search engine
        processed_url = QUrl.fromUserInput(url).toString()
        if self.valid_url(processed_url) or self.valid_url(url):
            self.setUrl(QUrl(processed_url))
        else:
            # Get url for search engine
            search_url = SEARCH_ENGINE_SEARCH_QUERIES.get(current_settings["search_engine"]) + url
            self.setUrl(QUrl(search_url))
        
        self.page_is_loading = True
    
    def reload_page(self):
        self.page_is_loading = True
        self.reload()
    
    def stop_page(self):
        self.page_is_loading = False
        self.stop()
    
    def page_load_finished(self):
        self.page_is_loading = False
    
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
    
    def scale_page_up(self):
        zoom_factor = self.zoomFactor()
        self.setZoomFactor(zoom_factor + 0.1)

    def scale_page_down(self):
        zoom_factor = self.zoomFactor()
        self.setZoomFactor(zoom_factor - 0.1)

    def scale_page_reset(self):
        self.setZoomFactor(1)
    
    def update_engine_config(self):
        settings = self.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled,
                             current_settings["javascript_enabled"])
        settings.setFontSize(QWebEngineSettings.FontSize.DefaultFontSize,
                             current_settings["default_font_size"])
        settings.setAttribute(QWebEngineSettings.WebAttribute.ShowScrollBars,
                                current_settings["scrollbars_enabled"])

class ManageBookmarksDialog(QDialog):
    def __init__(self, parent, passed_bookmarks):
        super().__init__(parent)
        self.setWindowTitle("Manage Bookmarks")
        self.setFixedSize(400, 300)

        # Temporary copy of bookmarks for editing
        self.temp_bookmarks = []
        for name, url in passed_bookmarks.items():
            self.temp_bookmarks.append({'name':name, 'url':url})
        
        # Create a deep copy of the original bookmarks to compare it to the new ones
        self.bookmarks_reference = copy.deepcopy(self.temp_bookmarks)

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
        icon_color = self.parent().get_contrast_color_from_theme()
        action_layout = QVBoxLayout()

        add_btn = QPushButton("Add New")
        add_btn.setIcon(qta.icon("fa6s.plus", color=icon_color))
        add_btn.setIconSize(QSize(16, 16))
        add_btn.clicked.connect(self.add_bookmark)
        action_layout.addWidget(add_btn)

        delete_btn = QPushButton("Delete")
        delete_btn.setIcon(qta.icon("fa6s.minus", color=icon_color))
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
        # Block signals so setting the text doesn't trigger sync_data_live
        self.name_lineedit.blockSignals(True)
        self.url_lineedit.blockSignals(True)
        
        if row >= 0 and row < len(self.temp_bookmarks):
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

class InstallerSignals(QObject):
    installation_complete = pyqtSignal()

class InstallWorker(QRunnable):
    def __init__(self, model_name):
        super().__init__()
        self.model_name = model_name
        self.signals = InstallerSignals()
    
    @pyqtSlot()
    def run(self):
        print(f"Installing model: {self.model_name}...")
        ollama.pull(self.model_name)
        print("Model installation complete.")
        self.signals.installation_complete.emit()

class WorkerSignals(QObject):
    chunk_received = pyqtSignal(str)
    finished = pyqtSignal()

class AI_SummarizationWorker(QRunnable):
    def __init__(self, text):
        super().__init__()
        self.text = text
        self.signals = WorkerSignals()
    
    @pyqtSlot()
    def run(self):
        print("Summarizing page content...")
        stream = ollama.chat(
            model='lfm2.5-thinking:1.2b',
            messages=[
                {"role": "system", "content": ai_system_prompt},
                {"role": "user", "content": self.text},
            ],
            stream=True,
        )

        for chunk in stream:
            content = chunk['message']['content']
            self.signals.chunk_received.emit(content)
        
        self.signals.finished.emit()

class AI_Sidebar(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setFixedWidth(300)
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(5, 5, 5, 5)
        self.layout.setSpacing(5)

        self.messages = []

        self.input_controls_layout = QHBoxLayout()

        self.title_label = QLabel("AI Summary")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet("font-size: 18px; font-weight: bold; padding: 20px")
        self.layout.addWidget(self.title_label)

        self.output_textedit = QTextEdit()
        self.output_textedit.setReadOnly(True)
        self.output_textedit.setPlaceholderText("Summarization output will appear here...")
        self.output_textedit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.layout.addWidget(self.output_textedit)

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setIcon(qta.icon("fa6s.trash", color=self.parent().get_contrast_color_from_theme()))
        self.clear_btn.clicked.connect(self.clear_output)
        self.input_controls_layout.addWidget(self.clear_btn)

        self.update_output()

        self.layout.addLayout(self.input_controls_layout)
        self.setLayout(self.layout)
    
    def send_webpage(self, prompt):
        prompt = prompt.strip()
        self.messages.append({"role": "User", "content": f"{prompt[:100]}..."})
        self.update_output()

        # Start AI worker
        worker = AI_SummarizationWorker(prompt)
        worker.signals.chunk_received.connect(self.handle_chunk)
        worker.signals.finished.connect(self.summarization_complete)

        QThreadPool.globalInstance().start(worker)
    
    def clear_output(self):
        self.messages = []
        self.update_output()
    
    def update_output(self):
        self.output_textedit.clear()
        cursor = self.output_textedit.textCursor()
        for msg in self.messages:
            cursor.insertText(f"[{msg['role']}]:\n{msg['content']}\n\n")
    
    def handle_chunk(self, chunk):
        if self.messages and self.messages[-1]['role'] == "AI":
            self.messages[-1]['content'] += chunk
        else:
            self.messages.append({"role": "AI", "content": chunk})
        
        self.update_output()
    
    def summarization_complete(self):
        self.update_output()

class BrowserWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Window configuration
        self.setWindowTitle("Silk Mizu")
        self.setMinimumSize(480, 360)
        self.resize(960, 720)
        self.layout = QGridLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # Initialize whole UI
        self.init_menu_bar()
        self.init_control_ui()
        self.init_ai_sidebar()
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
        self.aiMenu = menu_bar.addMenu("&AI Summarization")
        helpMenu = menu_bar.addMenu("&Help")

        self.aiMenu.setEnabled(current_settings["ai_summarization_enabled"])

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

        # AI Summarization Menu
        toggleAIsidebarAction = self.aiMenu.addAction("Toggle AI Summarization Sidebar")
        toggleAIsidebarAction.triggered.connect(self.toggle_ai_sidebar)
        toggleAIsidebarAction.setShortcut(QKeySequence("Ctrl + b"))
        self.aiMenu.addAction(toggleAIsidebarAction)
        aiSummarizationAction = self.aiMenu.addAction("Summarize current page with AI")
        aiSummarizationAction.triggered.connect(self.summarize_current_page_ai)
        aiSummarizationAction.setShortcut(QKeySequence("Ctrl + m"))
        self.aiMenu.addAction(aiSummarizationAction)

        # Help Menu
        documentationAction = QAction("Project Page", self)
        documentationAction.triggered.connect(lambda: self.web_engine.load_page("https://github.com/FlipArtYT/Silk-Mizu-Browser/"))
        helpMenu.addAction(documentationAction)

        aboutAction = helpMenu.addAction("About")
        aboutAction.triggered.connect(self.about_dialog)
        helpMenu.addAction(aboutAction)

    def init_control_ui(self):
        # Add main control layouts
        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(5, 5, 5, 5)
        controls_layout.setSpacing(5)

        self.bottom_bar = QWidget()
        self.bottom_bar.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self.bottom_bar.setContentsMargins(0, 0, 0, 0)
        self.bottom_bar.setVisible(current_settings["bottom_bar_visible"])
        bottom_bar_layout = QHBoxLayout()
        bottom_bar_layout.setContentsMargins(5, 5, 5, 5)
        bottom_bar_layout.setSpacing(5)

        self.bottom_bar.setLayout(bottom_bar_layout)

        self.layout.addLayout(controls_layout, 0, 0)
        self.layout.addWidget(self.bottom_bar, 3, 0)

        # Browser main controls
        icon_color = self.get_contrast_color_from_theme()

        self.ai_sidebar_btn = QPushButton()
        self.ai_sidebar_btn.setIcon(qta.icon("msc.layout-sidebar-left", color=icon_color))
        self.ai_sidebar_btn.setProperty("class", "navbtns")
        self.ai_sidebar_btn.setStyleSheet("padding: 8px;")
        self.ai_sidebar_btn.setVisible(current_settings["ai_summarization_enabled"])
        self.ai_sidebar_btn.clicked.connect(self.toggle_ai_sidebar)
        controls_layout.addWidget(self.ai_sidebar_btn)

        self.prev_page_btn = QPushButton()
        self.prev_page_btn.setIcon(qta.icon("fa6s.arrow-left", color=icon_color))
        self.prev_page_btn.setProperty("class", "navbtns")
        self.prev_page_btn.setStyleSheet("padding: 8px;")
        self.prev_page_btn.clicked.connect(self.request_back_page)
        controls_layout.addWidget(self.prev_page_btn)

        self.next_page_btn = QPushButton()
        self.next_page_btn.setIcon(qta.icon("fa6s.arrow-right", color=icon_color))
        self.next_page_btn.setProperty("class", "navbtns")
        self.next_page_btn.setStyleSheet("padding: 8px;")
        self.next_page_btn.clicked.connect(self.request_next_page)
        controls_layout.addWidget(self.next_page_btn)

        self.reload_page_btn = QPushButton()
        self.reload_page_btn.setIcon(qta.icon("fa6s.arrow-rotate-right", color=icon_color))
        self.reload_page_btn.setProperty("class", "navbtns")
        self.reload_page_btn.setStyleSheet("padding: 8px;")
        self.reload_page_btn.clicked.connect(self.request_reload_stop_page)
        controls_layout.addWidget(self.reload_page_btn)

        self.url_bar = QLineEdit()
        self.url_bar.setObjectName("url_bar")
        self.url_bar.setStyleSheet("padding: 8px;")
        self.url_bar.clearFocus()
        self.url_bar.returnPressed.connect(self.request_load_page_from_urlbar)
        controls_layout.addWidget(self.url_bar)

        self.load_btn = QPushButton("Go")
        self.load_btn.setIcon(qta.icon("mdi.arrow-right-bold-box", color=icon_color))
        self.load_btn.setProperty("class", "navbtns")
        self.load_btn.setStyleSheet("padding: 8px;")
        self.load_btn.setVisible(current_settings["go_button_visible"])
        self.load_btn.clicked.connect(self.request_load_page_from_urlbar)
        controls_layout.addWidget(self.load_btn)

        self.add_tab_btn = QPushButton()
        self.add_tab_btn.setIcon(qta.icon("fa6s.plus", color=icon_color))
        self.add_tab_btn.setProperty("class", "navbtns")
        self.add_tab_btn.setStyleSheet("padding: 8px;")
        self.add_tab_btn.clicked.connect(self.create_new_tab)
        controls_layout.addWidget(self.add_tab_btn)

        self.ai_summarize_btn = QPushButton()
        self.ai_summarize_btn.setIcon(qta.icon("ph.sparkle-fill", color=icon_color))
        self.ai_summarize_btn.setProperty("class", "navbtns")
        self.ai_summarize_btn.setStyleSheet("padding: 8px;")
        self.ai_summarize_btn.setVisible(current_settings["ai_summarization_enabled"])
        self.ai_summarize_btn.clicked.connect(self.summarize_current_page_ai)
        controls_layout.addWidget(self.ai_summarize_btn)

        self.add_to_bookmarks_btn = QPushButton()
        self.add_to_bookmarks_btn.setIcon(qta.icon("fa5s.bookmark", color=icon_color))
        self.add_to_bookmarks_btn.setProperty("class", "navbtns")
        self.add_to_bookmarks_btn.setStyleSheet("padding: 8px;")
        self.add_to_bookmarks_btn.clicked.connect(self.add_current_to_bookmarks_dialog)
        controls_layout.addWidget(self.add_to_bookmarks_btn)

        self.settings_btn = QPushButton()
        self.settings_btn.setIcon(qta.icon("fa5s.cog", color=icon_color))
        self.settings_btn.setProperty("class", "navbtns")
        self.settings_btn.setStyleSheet("padding: 8px;")
        self.settings_btn.clicked.connect(self.settings_dialog)
        controls_layout.addWidget(self.settings_btn)

        # Bookmark bar
        self.init_bookmark_bar()

        # Bottom bar
        self.page_progressbar = QProgressBar()
        self.page_progressbar.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.page_progressbar.setVisible(False)
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
        if not current_bookmarks:
            return
        
        bookmarks_layout = QHBoxLayout()
        bookmarks_layout.setContentsMargins(5, 0, 5, 5)
        bookmarks_layout.setSpacing(5)
        self.layout.addLayout(bookmarks_layout, 1, 0)

        # Clear existing bookmarks
        for i in reversed(range(bookmarks_layout.count())):
            widget_to_remove = bookmarks_layout.itemAt(i).widget()
            if widget_to_remove is not None:
                widget_to_remove.setParent(None)

        bookmark_map = {}

        for name, url in current_bookmarks.items():
            bookmark_btn = QPushButton(name)
            bookmark_btn.setStyleSheet("padding: 3px;")
            bookmark_btn.clicked.connect(lambda checked, url=url: self.request_load_page(url))
            bookmark_map[name] = bookmark_btn
            bookmarks_layout.addWidget(bookmark_btn)

        bookmarks_layout.addStretch(1)

    def init_ai_sidebar(self):
        # Create middle layout
        self.middle_layout = QHBoxLayout()
        self.middle_layout.setContentsMargins(0, 0, 0, 0)
        self.middle_layout.setSpacing(0)
        self.layout.addLayout(self.middle_layout, 2, 0)

        # AI Sidebar
        self.ai_sidebar = AI_Sidebar(self)
        self.ai_sidebar.setVisible(False)
        self.middle_layout.addWidget(self.ai_sidebar)
    
    def toggle_ai_sidebar(self):
        is_visible = self.ai_sidebar.isVisible()
        self.ai_sidebar.setVisible(not is_visible)
    
    def summarize_current_page_ai(self):
        self.ai_sidebar.setVisible(True)
        current_page = self.web_tabs.currentWidget()
        current_page.page().toPlainText(self.ai_sidebar.send_webpage)

    def init_web_engine(self):
        # Tab bar
        self.tab_list = []
        self.web_tabs = QTabWidget()
        self.web_tabs.setTabsClosable(True)
        self.web_tabs.setTabShape(QTabWidget.TabShape.Rounded)
        self.web_tabs.currentChanged.connect(self.update_tab_info)
        self.web_tabs.tabCloseRequested.connect(self.remove_web_tab)
        self.middle_layout.addWidget(self.web_tabs, 1)
        
        # Add start tab
        self.create_new_tab()

    def update_tab_info(self):
        self.update_urlbar_content()
        self.update_nav_btn_status()
        self.update_tab_titles()
    
    def create_new_tab(self):
        # Web Engine
        new_tab_index = len(self.tab_list)
        self.tab_list.append(BetterWebEngine(self))

        self.tab_list[new_tab_index].loadProgress.connect(self.update_progressbar)
        self.tab_list[new_tab_index].loadFinished.connect(self.page_load_finished)
        self.tab_list[new_tab_index].loadFinished.connect(self.tab_list[new_tab_index].page_load_finished)
        self.tab_list[new_tab_index].loadStarted.connect(self.page_load_started)
        self.tab_list[new_tab_index].urlChanged.connect(self.update_urlbar_content)

        self.web_tabs.addTab(self.tab_list[new_tab_index], "New Tab")
        self.web_tabs.setCurrentIndex(new_tab_index)
        self.update_tab_info()
    
    def update_tab_titles(self):
        for tab_index in range(self.web_tabs.count()):
            web_engine = self.tab_list[tab_index]
            title = web_engine.title() if web_engine.title() else "New Tab"
            self.web_tabs.setTabText(tab_index, f"{" "*3}{title[:10]+"..." if len(title) > 10 else title}{" "*3}")
            self.web_tabs.setTabIcon(tab_index, QIcon(web_engine.icon()))
            self.web_tabs.setIconSize(QSize(16, 16))
            self.web_tabs.setTabToolTip(tab_index, web_engine.title())

    def request_load_page_from_urlbar(self):
        url = self.url_bar.text()
        self.web_tabs.currentWidget().load_page(url)

    def update_urlbar_content(self):
        current_url = self.web_tabs.currentWidget().url().toString()
        self.url_bar.setText(current_url)
    
    def request_load_page(self, url):
        self.web_tabs.currentWidget().load_page(url)
    
    def request_reload_stop_page(self):
        if self.web_tabs.currentWidget().page_is_loading:
            self.web_tabs.currentWidget().stop_page()
        else:
            self.web_tabs.currentWidget().reload_page()
        
        self.update_tab_info()
    
    def request_back_page(self):
        self.web_tabs.currentWidget().history().back()
        self.update_tab_info()

    def request_next_page(self):
        self.web_tabs.currentWidget().history().forward()
        self.update_tab_info()
    
    def update_progressbar(self, prog):
        if self.web_tabs.currentWidget() == self.tab_list[self.web_tabs.currentIndex()]:
            self.page_progressbar.setVisible(True)
            self.page_progressbar.setValue(prog)

    def page_load_finished(self):
        self.web_tabs.currentWidget().page_is_loading = False
        self.page_progressbar.setVisible(False)
        self.update_tab_info()
    
    def page_load_started(self):
        self.update_progressbar(0)
        self.update_tab_info()

    def update_nav_btn_status(self):
        # Enable / Disable back and forward buttons
        self.prev_page_btn.setEnabled(self.web_tabs.currentWidget().history().canGoBack())
        self.next_page_btn.setEnabled(self.web_tabs.currentWidget().history().canGoForward())

        # Update reload / stop button
        if self.web_tabs.currentWidget().page_is_loading:
            self.reload_page_btn.setIcon(qta.icon("ei.remove"))
        else:
            self.reload_page_btn.setIcon(qta.icon("fa6s.arrow-rotate-right"))
    
    def remove_web_tab(self, index):
        tab_amount = self.web_tabs.count()
        if index >= 0 and tab_amount > 1:
            self.web_tabs.removeTab(index)
            del self.tab_list[index]
    
    def request_scale_page_up(self):
        self.web_tabs.currentWidget().scale_page_up()
        zoom_string = str(round(self.web_tabs.currentWidget().zoomFactor() * 100)) + "%"
        self.zoom_factor_label.setText(zoom_string)
    
    def request_scale_page_down(self):
        self.web_tabs.currentWidget().scale_page_down()
        zoom_string = str(round(self.web_tabs.currentWidget().zoomFactor() * 100)) + "%"
        self.zoom_factor_label.setText(zoom_string)
    
    def request_scale_page_reset(self):
        self.web_tabs.currentWidget().scale_page_reset()
        zoom_string = str(round(self.web_tabs.currentWidget().zoomFactor() * 100)) + "%"
        self.zoom_factor_label.setText(zoom_string)

    def get_cur_theme_dark_light(self):
        if current_settings["theme"] != "Automatic":
            return current_settings["theme"].lower()
        else:
            return "dark" if darkdetect.isDark() else "light"
        
    def get_contrast_color_from_theme(self):
        if self.get_cur_theme_dark_light() == "light":
            return "black"
        else:
            return "white"
    
    def update_icon_colors(self):
        icon_color = self.get_contrast_color_from_theme()

        self.prev_page_btn.setIcon(qta.icon("fa6s.arrow-left", color=icon_color))
        self.next_page_btn.setIcon(qta.icon("fa6s.arrow-right", color=icon_color))
        self.reload_page_btn.setIcon(qta.icon("fa6s.arrow-rotate-right", color=icon_color))
        self.load_btn.setIcon(qta.icon("mdi.arrow-right-bold-box", color=icon_color))
        self.add_to_bookmarks_btn.setIcon(qta.icon("fa5s.bookmark", color=icon_color))
        self.settings_btn.setIcon(qta.icon("fa5s.cog", color=icon_color))

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
        name_lineedit.setText(self.web_engine.title())
        name_lineedit.setMinimumWidth(200)
        form_layout.addRow("Bookmark name: ", name_lineedit)

        url_lineedit = QLineEdit()
        url_lineedit.setText(self.web_engine.url().toString())
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
            if dlg.temp_bookmarks == dlg.bookmarks_reference:
                return
            
            QMessageBox.information(self, "Changed bookmarks", "Bookmarks will refresh correctly after the program is restarted.")

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

        start_page_type_group = QButtonGroup()
        start_page_type_group.setExclusive(True)

        start_page_type_radio_button = QRadioButton("Silk Start (local)")
        start_page_type_radio_button.setChecked(current_settings["start_page_url"] == START_PAGE_PATH)
        start_page_type_radio_button.toggled.connect(lambda: self.toggle_url_edit(False, start_page_urledit))
        start_page_type_group.addButton(start_page_type_radio_button)

        start_page_url_radio_button = QRadioButton("URL")
        start_page_url_radio_button.setChecked(current_settings["start_page_url"] != START_PAGE_PATH)
        start_page_url_radio_button.toggled.connect(lambda: self.toggle_url_edit(True, start_page_urledit))
        start_page_type_group.addButton(start_page_url_radio_button)

        start_page_type_layout = QHBoxLayout()
        start_page_type_layout.addWidget(start_page_type_radio_button)
        start_page_type_layout.addWidget(start_page_url_radio_button)
        general_settings_layout.addRow("Start page type: ", start_page_type_layout)

        start_page_urledit = QLineEdit()
        start_page_urledit.setText(current_settings["start_page_url"])
        start_page_urledit.setMinimumWidth(200)
        start_page_urledit.setEnabled(current_settings["start_page_url"] != START_PAGE_PATH)
        general_settings_layout.addRow("Start page URL: ", start_page_urledit)

        search_engine_combobox = QComboBox()
        search_engine_combobox.addItems(["Google", "DuckDuckGo", "Brave", "Ecosia", "Yahoo"])
        search_engine_combobox.setCurrentText(current_settings["search_engine"])
        general_settings_layout.addRow("Search engine: ", search_engine_combobox)

        # Display settings
        display_settings = QWidget()
        display_settings_layout = QFormLayout()
        display_settings.setLayout(display_settings_layout)

        theme_combobox = QComboBox()
        theme_combobox.addItems(["Light", "Dark", "Automatic"])
        theme_combobox.setCurrentText(current_settings["theme"])
        display_settings_layout.addRow("Theme: ", theme_combobox)

        bottom_bar_visability_checkbox = QCheckBox()
        bottom_bar_visability_checkbox.setChecked(current_settings["bottom_bar_visible"])
        display_settings_layout.addRow("Show bottom bar: ", bottom_bar_visability_checkbox)
        
        go_button_visibility_checkbox = QCheckBox()
        go_button_visibility_checkbox.setChecked(current_settings["go_button_visible"])
        display_settings_layout.addRow("Show 'Go' button in URL bar: ", go_button_visibility_checkbox)

        # Engine tab settings
        engine_settings = QWidget()
        engine_settings_layout = QFormLayout()
        engine_settings.setLayout(engine_settings_layout)

        font_size_spinbox = QSpinBox()
        font_size_spinbox.setRange(10, 80)
        font_size_spinbox.setValue(current_settings["default_font_size"])
        engine_settings_layout.addRow("Default font size: ", font_size_spinbox)

        javascript_checkbox = QCheckBox()
        javascript_checkbox.setChecked(current_settings["javascript_enabled"])
        engine_settings_layout.addRow("Javascript enabled: ", javascript_checkbox)

        scrollbars_enabled_checkbox = QCheckBox()
        scrollbars_enabled_checkbox.setChecked(current_settings["scrollbars_enabled"])
        engine_settings_layout.addRow("Scrollbars enabled: ", scrollbars_enabled_checkbox)

        # AI tab settings
        ai_settings = QWidget()
        ai_settings_layout = QFormLayout()
        ai_settings.setLayout(ai_settings_layout)

        raw_models = ollama.list()
        ollama_model_names = [m.model for m in raw_models.models]
        sum_model_installed = 'lfm2.5-thinking:1.2b' in ollama_model_names

        install_model_btn = QPushButton()

        if not sum_model_installed:
            install_model_btn.setText("Install (731MB)")
            install_model_btn.setIcon(qta.icon("fa6s.download"))
        else:
            install_model_btn.setText("Model Installed")
            install_model_btn.setIcon(qta.icon("fa6s.check", color=self.get_contrast_color_from_theme()))

        install_model_btn.setEnabled(not sum_model_installed)
        install_model_btn.setFixedWidth(200)
        install_model_btn.clicked.connect(lambda: self.start_model_installation(install_model_btn))
        ai_settings_layout.addRow("Install AI Page Summarization Model: ", install_model_btn)
        
        ai_checkbox = QCheckBox()
        ai_checkbox.setEnabled(sum_model_installed)
        ai_checkbox.setChecked(current_settings["ai_summarization_enabled"])
        ai_settings_layout.addRow("Enable AI Page Summarization: ", ai_checkbox)

        # Add widgets to tab widget
        tabs.addTab(general_settings, "General")
        tabs.addTab(display_settings, "Display")
        tabs.addTab(engine_settings, "Engine")
        tabs.addTab(ai_settings, "AI Features")

        # Add Ok and Cancel buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(dlg.accept)
        button_box.rejected.connect(dlg.reject)

        layout.addWidget(tabs, 1, 0)
        layout.addWidget(button_box, 2, 0, alignment=Qt.AlignmentFlag.AlignRight)

        dlg.setLayout(layout)

        if dlg.exec():
            start_page = start_page_urledit.text() if start_page_url_radio_button.isChecked() else START_PAGE_PATH
            search_engine = search_engine_combobox.currentText()
            theme = theme_combobox.currentText()
            go_button_visible = go_button_visibility_checkbox.isChecked()
            bottom_bar_visible = bottom_bar_visability_checkbox.isChecked()
            javascript_enabled = javascript_checkbox.isChecked()
            default_font_size = font_size_spinbox.value()
            default_scrollbars_enabled = scrollbars_enabled_checkbox.isChecked()
            summarize_ai_enabled = ai_checkbox.isChecked()

            # Update settings in browser
            if theme == "Light":
                app.setStyleSheet(qdarktheme.load_stylesheet("light"))
            elif theme == "Dark":
                app.setStyleSheet(qdarktheme.load_stylesheet("dark"))
            else:
                system_theme = "Dark" if darkdetect.isDark() else "Light"
                app.setStyleSheet(qdarktheme.load_stylesheet(system_theme.lower()))

            self.bottom_bar.setVisible(bottom_bar_visible)
            self.load_btn.setVisible(go_button_visible)
            self.ai_summarize_btn.setVisible(summarize_ai_enabled)
            self.ai_sidebar_btn.setVisible(summarize_ai_enabled)
            self.aiMenu.setEnabled(summarize_ai_enabled)

            self.update_web_engine()

            # Prepare settings.json
            updated_settings = {
                "start_page_url":start_page,
                "search_engine":search_engine,
                "theme":theme,
                "bottom_bar_visible":bottom_bar_visible,
                "go_button_visible":go_button_visible,
                "javascript_enabled":javascript_enabled,
                "default_font_size":default_font_size,
                "scrollbars_enabled":default_scrollbars_enabled,
                "ai_summarization_enabled":summarize_ai_enabled
            }

            current_settings = updated_settings

            self.update_icon_colors()

            # Write to settings.json
            with open(CONFIG_PATH, "w") as f:
                json.dump(updated_settings, f, indent=4)

    def start_model_installation(self, install_button):
        install_button.setEnabled(False)
        install_button.setText("Installing...")
        animation = qta.Spin(install_button)
        install_button.setIcon(qta.icon("fa6s.spinner", color=self.get_contrast_color_from_theme(), animation=animation))

        self.threadpool = QThreadPool()
        worker = InstallWorker("lfm2.5-thinking:1.2b")
        worker.signals.installation_complete.connect(lambda: self.model_installation_complete(install_button))
        self.threadpool.start(worker)
    
    def model_installation_complete(self, install_button):
        install_button.setText("Model Installed")
        install_button.setIcon(qta.icon("fa6s.check", color=self.get_contrast_color_from_theme()))
        
        QMessageBox.information(self, "Model Installed", "The AI page summarization model has been installed successfully. You can now enable AI page summarization in the settings.")
    
    def toggle_url_edit(self, enable, urledit):
        urledit.setEnabled(enable)
    
    def update_web_engine(self):
        for tab in self.tab_list:
            tab.update_engine_config()
        
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
    app.setApplicationVersion(VERSION_NUMBER)
    app.setOrganizationName("Silk Project")

    # Load theme
    if current_settings["theme"] and current_settings["theme"] != "Automatic":
        app.setStyleSheet(qdarktheme.load_stylesheet(current_settings["theme"].lower()))
    else:
        system_theme = "Dark" if darkdetect.isDark() else "Light"
        app.setStyleSheet(qdarktheme.load_stylesheet(system_theme.lower()))
    
    app.setWindowIcon(QIcon(os.path.join(SCRIPT_DIR, "assets", "mizu.png")))
    app.setStyle("breeze")
    window = BrowserWindow()
    window.show()
    sys.exit(app.exec())