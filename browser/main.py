import sys
import os
import json
import re
import copy
import datetime
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
    QFileDialog,
    QMenu,
    QWidgetAction
)
from PyQt6.QtCore import Qt, QUrl, QSize, pyqtSlot, pyqtSignal, QThreadPool, QRunnable, QObject, QDir, QTranslator, QLocale
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings, QWebEngineDownloadRequest
from PyQt6.QtGui import QPixmap, QAction, QKeySequence, QIcon
import qtawesome as qta
import qdarktheme
import darkdetect
import ollama

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config", "settings.json")
BOOKMARKS_PATH = os.path.join(SCRIPT_DIR, "config", "bookmarks.json")
LOGO_PATH = os.path.join(SCRIPT_DIR, "assets", "mizu2.png")
START_PAGE_PATH = os.path.join(SCRIPT_DIR, "assets", "Silk-Start", "start", "v1.1.1", "seperate", "index.html")
AI_SYSPROMPT_PATH = os.path.join(SCRIPT_DIR, "config", "sysprompt.txt")
DOWNLOAD_PATH = os.path.join(SCRIPT_DIR, "Downloads")
SUM_AI_MODEL = {"name":"lfm2.5-thinking:1.2b", "size":"700MB"}
VERSION_NUMBER = "0.2.94"
SEARCH_ENGINE_SEARCH_QUERIES = {
    "Google":"https://www.google.com/search?q=",
    "DuckDuckGo":"https://duckduckgo.com/?q=",
    "Brave":"https://search.brave.com/search?q=",
    "Ecosia":"https://www.ecosia.org/search?method=index&q=",
    "Yahoo":"https://search.yahoo.com/search?p="
}
NAME_TO_LANGUAGE = {
    "English":"en_US",
    "Deutsch":"de_DE"
}
LANGUAGE_TO_NAME = {
    "en_US":"English",
    "de_DE":"Deutsch"
}

current_settings = {}
default_settings = {
    "start_page_url":START_PAGE_PATH,
    "search_engine":"Google",
    "theme":"Dark",
    "bottom_bar_visible":False,
    "go_button_visible":False,
    "download_warnings":True,
    "language":"en_US",
    "javascript_enabled":True,
    "default_font_size":16,
    "scrollbars_enabled":True,
    "ai_summarization_enabled":False
}

current_bookmarks = {}
default_bookmarks = {}

# Disable Chromium debug logs
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-logging"

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

class ThemeManager():
    def __init__(self, applic, theme="dark"):
        self.applic = applic
        self.theme = theme
        self.available_themes = [
            "light",
            "dark",
            "automatic",
            "legacy"
        ]
        self.load_theme(theme)
    
    def load_theme(self, theme_input):
        theme_input = theme_input.strip().lower()

        if theme_input in self.available_themes:
            if theme_input != "automatic" and theme_input != "legacy":
                self.applic.setStyleSheet(qdarktheme.load_stylesheet(theme_input))

            elif theme_input == "automatic":
                system_theme = "dark" if darkdetect.isDark() else "light"
                self.applic.setStyleSheet(qdarktheme.load_stylesheet(system_theme))
            
            elif theme_input == "legacy":
                self.applic.setStyleSheet("")
            
            self.theme = theme_input

        else:
            print("Theme not found")
    
    def get_plain_theme(self):
        if self.theme != "automatic" and self.theme != "legacy":
            return self.theme
        
        else:
            system_theme = "dark" if darkdetect.isDark() else "light"
            return system_theme

class BetterWebEngineSignals(QObject):
    sum_selected_with_ai = pyqtSignal(str)
    sum_page_with_ai = pyqtSignal()

class BetterWebEngine(QWebEngineView):
    def __init__(self, parent):
        super().__init__(parent)
        self.page_is_loading = False
        self.signals = BetterWebEngineSignals()

        self.init_engine()
        self.update_engine_config()
    
    def init_engine(self):
        # Check if start page exists
        if os.path.exists(START_PAGE_PATH):
            self.load_page(current_settings["start_page_url"])
        else:
            self.load_page(SEARCH_ENGINE_SEARCH_QUERIES.get(current_settings["search_engine"]))

    def contextMenuEvent(self, event):
        menu = self.createStandardContextMenu()
        menu.addSeparator()

        sum_selected_with_ai_action = menu.addAction(self.tr("Summarize selected text with AI"))
        sum_selected_with_ai_action.triggered.connect(self.prepare_sum_selected_with_ai)

        sum_page_with_ai_action = menu.addAction(self.tr("Summarize page with AI"))
        sum_page_with_ai_action.triggered.connect(lambda: self.signalssum_page_with_ai.emit())

        menu.exec(event.globalPos())

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

    def prepare_sum_selected_with_ai(self):
        selected_text = self.selectedText().strip()
        
        if selected_text:
            self.signals.sum_selected_with_ai.emit(selected_text)
    
    def update_engine_config(self):
        settings = self.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled,
                             current_settings["javascript_enabled"])
        settings.setFontSize(QWebEngineSettings.FontSize.DefaultFontSize,
                             current_settings["default_font_size"])
        settings.setAttribute(QWebEngineSettings.WebAttribute.ShowScrollBars,
                                current_settings["scrollbars_enabled"])

class DownloadManager(QMenu):
    def __init__(self):
        super().__init__()
        self.downloads = {}  # Store active download objects

    def add_download(self, download: QWebEngineDownloadRequest):
        # Download info
        download_filename = download.suggestedFileName()

        if not os.path.exists(DOWNLOAD_PATH):
            os.makedirs(DOWNLOAD_PATH)

        download.setDownloadDirectory(DOWNLOAD_PATH)
        download.setDownloadFileName(download_filename)
        
        # Create layouts for the menu entry
        layout = QVBoxLayout()
        container = QWidget()

        # Download UI elements
        label = QLabel(f"{self.tr("Downloading:")} {self.short_if_needed(download_filename)}")
        label.setToolTip(download_filename)
        progress = QProgressBar()
        stop_btn = QPushButton()
        stop_btn.setIcon(qta.icon("ei.remove"))
        stop_btn.clicked.connect(lambda: download.cancel())
        
        layout.addWidget(label)

        # Bottom layout (progress bar, button)
        bottom_layout = QHBoxLayout()
        layout.addLayout(bottom_layout)

        bottom_layout.addWidget(progress)
        bottom_layout.addWidget(stop_btn)

        container.setLayout(layout)

        widget_action = QWidgetAction(self)
        widget_action.setDefaultWidget(container)

        self.addAction(widget_action)
        
        # 3. Connect signals to track progress and completion
        download.receivedBytesChanged.connect(
            lambda: self.update_progress(download, progress)
        )
        download.isFinishedChanged.connect(
            lambda: self.download_finished(download, label, progress, stop_btn)
        )
        
        # 4. Start the download
        download.accept()
        self.downloads[download.id()] = download

    def update_progress(self, download, progress_bar):
        if download.totalBytes() > 0:
            percent = int((download.receivedBytes() / download.totalBytes()) * 100)
            progress_bar.setValue(percent)
    
    def short_if_needed(self, download_name):
        if len(download_name) > 15:
            return f"{download_name[:15]}..."
        else:
            return download_name

    def download_finished(self, download, label, progress_bar, stop_btn):
        download_filename = download.suggestedFileName()
        state = download.state()
        stop_btn.setEnabled(False)
    
        if state == QWebEngineDownloadRequest.DownloadState.DownloadCompleted:
            progress_bar.setValue(100)
            label.setText(f"{self.tr("Finished:")} {self.short_if_needed(download_filename)}")
        
        elif state == QWebEngineDownloadRequest.DownloadState.DownloadCancelled:
            label.setText(f"{self.tr("Canceled:")} {self.short_if_needed(download_filename)}")
            progress_bar.setEnabled(False)
        
        elif state == QWebEngineDownloadRequest.DownloadState.DownloadInterrupted:
            label.setText(f"{self.tr("Error:")} {self.short_if_needed(download_filename)}")
            progress_bar.setStyleSheet("QProgressBar::chunk { background-color: red; }")

class ManageBookmarksDialog(QDialog):
    def __init__(self, parent, passed_bookmarks):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Manage Bookmarks"))
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
        title_label = QLabel(self.tr("Manage Bookmarks"))
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

        add_btn = QPushButton(self.tr("Add New"))
        add_btn.setIcon(qta.icon("fa6s.plus", color=icon_color))
        add_btn.setIconSize(QSize(16, 16))
        add_btn.clicked.connect(self.add_bookmark)
        action_layout.addWidget(add_btn)

        delete_btn = QPushButton(self.tr("Delete"))
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
        edit_layout.addRow(self.tr("Bookmark Name: "), self.name_lineedit)

        self.url_lineedit = QLineEdit()
        self.url_lineedit.textEdited.connect(self.sync_data_live)
        edit_layout.addRow(self.tr("Bookmark URL: "), self.url_lineedit)

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
        new_bm = {"name": self.tr("New Bookmark"), "url": "https://"}
        self.temp_bookmarks.append(new_bm)
        self.list_widget.addItem(new_bm['name'])
        self.list_widget.setCurrentRow(self.list_widget.count() - 1)

    def delete_bookmark(self):
        row = self.list_widget.currentRow()
        if row >= 0:
            self.temp_bookmarks.pop(row)
            self.list_widget.takeItem(row)

class InstallWorker(QRunnable):
    installation_complete = pyqtSignal()

    def __init__(self, model_name):
        super().__init__()
        self.model_name = model_name
    
    @pyqtSlot()
    def run(self):
        print(f"Installing model: {self.model_name}...")
        ollama.pull(self.model_name)
        print("Model installation complete.")
        self.installation_complete.emit()

class AI_SummarizationWorkerSignals(QObject):
    chunk_received = pyqtSignal(str)
    finished = pyqtSignal()

class AI_SummarizationWorker(QRunnable):
    def __init__(self, text):
        super().__init__()
        self.text = text
        self.signals = AI_SummarizationWorkerSignals()
    
    @pyqtSlot()
    def run(self):
        print("Summarizing page content...")
        stream = ollama.generate(
            model=SUM_AI_MODEL["name"],
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

        self.title_label = QLabel(self.tr("AI Summary"))
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet("font-size: 18px; font-weight: bold; padding: 20px")
        self.layout.addWidget(self.title_label)

        self.output_textedit = QTextEdit()
        self.output_textedit.setReadOnly(True)
        self.output_textedit.setPlaceholderText(self.tr("Summarization output will appear here..."))
        self.output_textedit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.layout.addWidget(self.output_textedit)

        self.download_chat_btn = QPushButton(self.tr("Download"))
        self.download_chat_btn.setIcon(qta.icon("fa6s.download", color=self.parent().get_contrast_color_from_theme()))
        self.download_chat_btn.clicked.connect(self.download_chat_dlg)
        self.input_controls_layout.addWidget(self.download_chat_btn)

        self.clear_btn = QPushButton(self.tr("Clear"))
        self.clear_btn.setIcon(qta.icon("fa6s.trash", color=self.parent().get_contrast_color_from_theme()))
        self.clear_btn.clicked.connect(self.clear_output)
        self.input_controls_layout.addWidget(self.clear_btn)

        self.update_output()

        self.layout.addLayout(self.input_controls_layout)
        self.setLayout(self.layout)
    
    def send_webpage(self, prompt):
        prompt = prompt.strip()
        self.messages.append({"role": "User", "content": f"[Sum]: {prompt[:400]}..."})
        self.update_output()

        # Start AI worker
        worker = AI_SummarizationWorker(f"Summarize this text the way your system prompt intended to:\"{prompt}\"")
        worker.signals.chunk_received.connect(self.handle_chunk)
        worker.signals.finished.connect(self.summarization_complete)

        QThreadPool.globalInstance().start(worker)
    
    def clear_output(self):
        self.messages = []
        self.update_output()
    
    def update_output(self):
        self.output_textedit.clear()

        formatted_output = ""
        for message in self.messages:
            formatted_output += f"**{message["role"]}:**  {message["content"]}\n\n"
        
        self.output_textedit.setMarkdown(formatted_output)
    
    def handle_chunk(self, chunk):
        if self.messages and self.messages[-1]['role'] == "AI":
            self.messages[-1]['content'] += chunk
        else:
            self.messages.append({"role": "AI", "content": chunk})
        
        self.update_output()
    
    def summarization_complete(self):
        self.update_output()

    def download_chat_dlg(self):
        chat_content = self.output_textedit.toMarkdown()
        time_now = datetime.datetime.now()
        time_formatted = time_now.strftime("%H:%M-%d-%m-%Y")
        file_name = f"chat-{time_formatted}.txt"

        if not chat_content:
            return
        
        dir_name = QFileDialog.getExistingDirectory(self, self.tr("Select a Directory"))
        file_path = os.path.join(dir_name, file_name)

        if os.path.exists(file_path):
            QMessageBox.critical(self, self.tr("Cannot write file", f"The file {file_name} already exists in the selected directory."))
        
        with open(file_path, "w") as f:
            f.write(chat_content)
    
    def retranslate_ui(self):
        self.title_label.setText(self.tr("AI Summary"))
        self.output_textedit.setPlaceholderText(self.tr("Summarization output will appear here..."))
        self.download_chat_btn.setText(self.tr("Download"))
        self.clear_btn.setText(self.tr("Clear"))

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
        self.init_bookmark_bar()
        self.init_ai_sidebar()
        self.init_web_engine()

        # Install translator
        self.translator = QTranslator()
        self.load_language(current_settings["language"])

        # Add main widget
        widget = QWidget()
        widget.setLayout(self.layout)
        self.setCentralWidget(widget)

        if not os.path.exists(START_PAGE_PATH):
            QMessageBox.critical(self, self.tr("Start page not found"), self.tr("The Silk Start submodule was not found. Make sure you follow the cloning instructions carefully."))
    
    def init_menu_bar(self):
        # Add menu bar
        menu_bar = self.menuBar()

        self.fileMenu = menu_bar.addMenu(self.tr("&File"))
        self.editMenu = menu_bar.addMenu(self.tr("&Edit"))
        self.viewMenu = menu_bar.addMenu(self.tr("&View"))
        self.bookmarkMenu = menu_bar.addMenu(self.tr("&Bookmarks"))
        self.aiMenu = menu_bar.addMenu(self.tr("&AI Summarization"))
        self.helpMenu = menu_bar.addMenu(self.tr("&Help"))

        self.aiMenu.setEnabled(current_settings["ai_summarization_enabled"])

        # File Menu
        self.settingsAction = QAction(self.tr("Program Settings"))
        self.settingsAction.triggered.connect(self.settings_dialog)
        self.settingsAction.setShortcut(QKeySequence("Ctrl + ,"))
        self.fileMenu.addAction(self.settingsAction)

        self.exitAction = QAction(self.tr("Quit"), self)
        self.exitAction.triggered.connect(sys.exit)
        self.exitAction.setShortcut(QKeySequence("Ctrl + q"))
        self.fileMenu.addAction(self.exitAction)

        # Edit Menu
        self.createNewTabAction = QAction(self.tr("New Tab"), self)
        self.createNewTabAction.triggered.connect(self.create_new_tab)
        self.createNewTabAction.setShortcut(QKeySequence("Ctrl + t"))
        self.editMenu.addAction(self.createNewTabAction)

        self.backAction = QAction(self.tr("Back"), self)
        self.backAction.triggered.connect(self.request_back_page)
        self.backAction.setShortcut(QKeySequence("Alt + left"))
        self.editMenu.addAction(self.backAction)

        self.nextAction = QAction(self.tr("Next"), self)
        self.nextAction.triggered.connect(self.request_next_page)
        self.nextAction.setShortcut(QKeySequence("Alt + right"))
        self.editMenu.addAction(self.nextAction)

        # View Menu
        self.scaleUpAction = QAction(self.tr("Increase page zoom by 10%"), self)
        self.scaleUpAction.triggered.connect(self.request_scale_page_up)
        self.scaleUpAction.setShortcut(QKeySequence("Ctrl + +"))
        self.viewMenu.addAction(self.scaleUpAction)

        self.scaleDownAction = QAction(self.tr("Decrease page zoom by 10%"), self)
        self.scaleDownAction.triggered.connect(self.request_scale_page_down)
        self.scaleDownAction.setShortcut(QKeySequence("Ctrl + -"))
        self.viewMenu.addAction(self.scaleDownAction)

        self.scaleDefaultAction = QAction(self.tr("Set page zoom to 100%"), self)
        self.scaleDefaultAction.triggered.connect(self.request_scale_page_reset)
        self.viewMenu.addAction(self.scaleDefaultAction)

        # Bookmarks Menu
        self.manageBookmarksAction = QAction(self.tr("Manage bookmarks"), self)
        self.manageBookmarksAction.triggered.connect(self.manage_bookmarks_dialog)
        self.manageBookmarksAction.setShortcut(QKeySequence("Ctrl + shift + o"))
        self.bookmarkMenu.addAction(self.manageBookmarksAction)

        self.addPageToBookmarksAction = QAction(self.tr("Add current page to bookmarks"), self)
        self.addPageToBookmarksAction.triggered.connect(self.add_current_to_bookmarks_dialog)
        self.addPageToBookmarksAction.setShortcut(QKeySequence("Ctrl + d"))
        self.bookmarkMenu.addAction(self.addPageToBookmarksAction)

        # AI Summarization Menu
        self.toggleAIsidebarAction = QAction(self.tr("Toggle AI Summarization Sidebar"), self)
        self.toggleAIsidebarAction.triggered.connect(self.toggle_ai_sidebar)
        self.toggleAIsidebarAction.setShortcut(QKeySequence("Ctrl + b"))
        self.aiMenu.addAction(self.toggleAIsidebarAction)

        self.aiSummarizationAction = QAction(self.tr("Summarize current page with AI"), self)
        self.aiSummarizationAction.triggered.connect(self.summarize_current_page_ai)
        self.aiSummarizationAction.setShortcut(QKeySequence("Ctrl + m"))
        self.aiMenu.addAction(self.aiSummarizationAction)

        # Help Menu
        self.documentationAction = QAction(self.tr("Project Page"), self)
        self.documentationAction.triggered.connect(lambda: self.create_new_tab("https://github.com/Silk-Project/Silk-Mizu-Browser/"))
        self.helpMenu.addAction(self.documentationAction)

        self.aboutAction = QAction(self.tr("About"))
        self.aboutAction.triggered.connect(self.about_dialog)
        self.helpMenu.addAction(self.aboutAction)

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

        # Left side: Basic navigation (Back, Forward page)
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

        # Middle: URL Bar
        self.url_bar = QLineEdit()
        self.url_bar.setObjectName("url_bar")
        self.url_bar.setStyleSheet("padding: 8px;")
        self.url_bar.clearFocus()
        self.url_bar.returnPressed.connect(self.request_load_page_from_urlbar)
        controls_layout.addWidget(self.url_bar)

        # Right: Everything else
        self.load_btn = QPushButton(self.tr("Go"))
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

        self.download_widget = DownloadManager()
        self.downloads_btn = QPushButton()
        self.downloads_btn.setIcon(qta.icon("ei.download", color=icon_color))
        self.downloads_btn.setStyleSheet("padding: 8px;")
        self.downloads_btn.setVisible(False)
        self.downloads_btn.clicked.connect(self.show_download_menu)
        controls_layout.addWidget(self.downloads_btn)

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

        # Bottom bar
        self.page_progressbar = QProgressBar()
        self.page_progressbar.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.page_progressbar.setVisible(False)
        self.page_progressbar.setFixedWidth(200)
        self.page_progressbar.setValue(0)
        bottom_bar_layout.addWidget(self.page_progressbar)

        bottom_bar_layout.addStretch(1)

        self.scale_down_btn = QPushButton()
        self.scale_down_btn.setIcon(qta.icon("ph.magnifying-glass-minus", color=icon_color))
        self.scale_down_btn.setProperty("class", "navbtns")
        self.scale_down_btn.setStyleSheet("padding: 5px")
        self.scale_down_btn.clicked.connect(self.request_scale_page_down)
        bottom_bar_layout.addWidget(self.scale_down_btn)

        self.zoom_factor_label = QLabel("100%")
        bottom_bar_layout.addWidget(self.zoom_factor_label)

        self.scale_up_btn = QPushButton()
        self.scale_up_btn.setIcon(qta.icon("ph.magnifying-glass-plus", color=icon_color))
        self.scale_up_btn.setProperty("class", "navbtns")
        self.scale_up_btn.setStyleSheet("padding: 5px")
        self.scale_up_btn.clicked.connect(self.request_scale_page_up)

        bottom_bar_layout.addWidget(self.scale_up_btn)

    # Translation system
    def load_language(self, lang):
        if lang in LANGUAGE_TO_NAME:
            app.removeTranslator(self.translator)

            if lang != "en_US":
                lang_path = os.path.join(SCRIPT_DIR, "i18n", f"{lang}.qm")

                if os.path.exists(lang_path):
                    self.translator = QTranslator()
                    self.translator.load(lang_path)
                    app.installTranslator(self.translator)
                
                else:
                    print(f"Language file at {lang_path} not found.")
            
            self.retranslate_ui()


    def retranslate_ui(self):
        # Menu bar
        self.fileMenu.setTitle(self.tr("&File"))
        self.editMenu.setTitle(self.tr("&Edit"))
        self.viewMenu.setTitle(self.tr("&View"))
        self.bookmarkMenu.setTitle(self.tr("&Bookmarks"))
        self.aiMenu.setTitle(self.tr("&AI Summarization"))
        self.helpMenu.setTitle(self.tr("&Help"))

        # File Menu
        self.settingsAction.setText(self.tr("Program Settings"))
        self.exitAction.setText(self.tr("Quit"))
        
        # Edit Menu
        self.createNewTabAction.setText(self.tr("New Tab"))
        self.backAction.setText(self.tr("Back"))
        self.nextAction.setText(self.tr("Next"))

        # View menu
        self.scaleUpAction.setText(self.tr("Increase page zoom by 10%"))
        self.scaleDownAction.setText(self.tr("Decrease page zoom by 10%"))
        self.scaleDefaultAction.setText(self.tr("Set page zoom to 100%"))

        # Bookmarks menu
        self.manageBookmarksAction.setText(self.tr("Manage bookmarks"))
        self.addPageToBookmarksAction.setText(self.tr("Add current page to bookmarks"))

        # AI Summarization menu
        self.toggleAIsidebarAction.setText(self.tr("Toggle AI Summarization Sidebar"))
        self.aiSummarizationAction.setText(self.tr("Summarize current page with AI"))

        # Help Menu
        self.documentationAction.setText(self.tr("Project Page"))
        self.aboutAction.setText(self.tr("About"))

        # Main UI
        self.load_btn.setText(self.tr("Go"))
        self.ai_sidebar.retranslate_ui()

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
    
    # AI sidebar
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
        if not current_settings["ai_summarization_enabled"]:
            return
        
        self.ai_sidebar.setVisible(True)
        current_page = self.web_tabs.currentWidget()
        current_page.page().toPlainText(self.ai_sidebar.send_webpage)
    
    def summarize_selected_with_ai(self, selected_text):
        if not current_settings["ai_summarization_enabled"]:
            return
        
        self.ai_sidebar.setVisible(True)
        self.ai_sidebar.send_webpage(selected_text)

    # Website Tabs
    def init_web_engine(self):
        # Tab bar
        self.tab_list = []
        self.web_tabs = QTabWidget()
        self.web_tabs.setTabsClosable(True)
        self.web_tabs.setIconSize(QSize(16, 16))
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
    
    def create_new_tab(self, url=None):
        # Web Engine
        new_tab_index = len(self.tab_list)
        self.tab_list.append(BetterWebEngine(self))
        
        if url:
            self.tab_list[new_tab_index].setUrl(QUrl(url))

        self.tab_list[new_tab_index].loadProgress.connect(self.update_progressbar)
        self.tab_list[new_tab_index].loadFinished.connect(self.page_load_finished)
        self.tab_list[new_tab_index].loadFinished.connect(self.tab_list[new_tab_index].page_load_finished)
        self.tab_list[new_tab_index].loadStarted.connect(self.page_load_started)
        self.tab_list[new_tab_index].urlChanged.connect(self.update_urlbar_content)
        self.tab_list[new_tab_index].iconChanged.connect(self.update_tab_info)
        self.tab_list[new_tab_index].page().profile().downloadRequested.connect(self.request_download)
        self.tab_list[new_tab_index].signals.sum_selected_with_ai.connect(self.summarize_selected_with_ai)
        self.tab_list[new_tab_index].signals.sum_page_with_ai.connect(self.summarize_current_page_ai)

        self.web_tabs.addTab(self.tab_list[new_tab_index], None)
        self.web_tabs.setCurrentIndex(new_tab_index)
        self.update_tab_info()
    
    def remove_web_tab(self, index):
        tab_amount = self.web_tabs.count()
        if index >= 0 and tab_amount > 1:
            self.web_tabs.removeTab(index)
            self.tab_list[index].deleteLater()
            del self.tab_list[index]
            
            self.update_tab_info()
    
    def update_tab_titles(self):
        for tab_index in range(self.web_tabs.count()):
            web_engine = self.tab_list[tab_index]
            title = web_engine.title() if web_engine.title() else self.tr("New Tab")
            self.web_tabs.setTabText(tab_index, f"{" "*3}{title[:10]+"..." if len(title) > 10 else title}{" "*3}")
            self.web_tabs.setTabToolTip(tab_index, web_engine.title())

            if web_engine.iconUrl().isEmpty():
                self.web_tabs.setTabIcon(tab_index, QIcon())

            elif web_engine.icon().isNull():
                animation = qta.Spin(self.web_tabs)
                self.web_tabs.setTabIcon(tab_index, qta.icon("mdi.loading", animation=animation))

            else:
                self.web_tabs.setTabIcon(tab_index, QIcon(web_engine.icon()))

    # Download System
    def show_download_menu(self):
        button_pos = self.downloads_btn.mapToGlobal(self.downloads_btn.rect().bottomLeft())
        self.download_widget.exec(button_pos)
    
    def request_download(self, download):
        if current_settings["download_warnings"]:
            warning_dlg = QMessageBox(self)
            warning_dlg.setWindowTitle(self.tr("Download Request"))
            warning_dlg.setText(f"{self.tr("Do you really want to download")} \"{download.suggestedFileName()}\"?")
            warning_dlg.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
            warning_dlg.setIcon(QMessageBox.Icon.Warning)

            if warning_dlg.exec() == QMessageBox.StandardButton.Ok:
                self.download_widget.add_download(download)
                self.downloads_btn.setVisible(True)
                self.show_download_menu()
    
        else:
            self.download_widget.add_download(download)
            self.downloads_btn.setVisible(True)
            self.show_download_menu()

    # Website content specific functions
    def request_load_page_from_urlbar(self):
        url = self.url_bar.text()
        self.web_tabs.currentWidget().load_page(url)

    def update_urlbar_content(self):
        current_url = self.web_tabs.currentWidget().url().toString()
        self.url_bar.setText(current_url)
    
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
        icon_color = self.get_contrast_color_from_theme()

        if self.web_tabs.currentWidget().page_is_loading:
            self.reload_page_btn.setIcon(qta.icon("ei.remove", color=icon_color))
        else:
            self.reload_page_btn.setIcon(qta.icon("fa6s.arrow-rotate-right", color=icon_color))
    
    # Website navigation
    def request_back_page(self):
        self.web_tabs.currentWidget().history().back()
        self.update_tab_info()

    def request_next_page(self):
        self.web_tabs.currentWidget().history().forward()
        self.update_tab_info()
    
    def request_reload_stop_page(self):
        if self.web_tabs.currentWidget().page_is_loading:
            self.web_tabs.currentWidget().stop_page()
        else:
            self.web_tabs.currentWidget().reload_page()
        
        self.update_tab_info()

    def request_load_page(self, url):
        self.web_tabs.currentWidget().load_page(url)
    
    # Scaling
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
    
    # Theme specific functions
    def get_contrast_color_from_theme(self):
        if theme_manager.get_plain_theme() == "light":
            return "black"
        else:
            return "white"
    
    def update_icon_colors(self):
        icon_color = self.get_contrast_color_from_theme()

        self.ai_sidebar_btn.setIcon(qta.icon("msc.layout-sidebar-left", color=icon_color))
        self.prev_page_btn.setIcon(qta.icon("fa6s.arrow-left", color=icon_color))
        self.next_page_btn.setIcon(qta.icon("fa6s.arrow-right", color=icon_color))

        if self.web_tabs.currentWidget().page_is_loading:
            self.reload_page_btn.setIcon(qta.icon("ei.remove", color=icon_color))
        else:
            self.reload_page_btn.setIcon(qta.icon("fa6s.arrow-rotate-right", color=icon_color))
        
        self.load_btn.setIcon(qta.icon("mdi.arrow-right-bold-box", color=icon_color))
        self.add_tab_btn.setIcon(qta.icon("fa6s.plus", color=icon_color))
        self.ai_summarize_btn.setIcon(qta.icon("ph.sparkle-fill", color=icon_color))
        self.add_to_bookmarks_btn.setIcon(qta.icon("fa5s.bookmark", color=icon_color))
        self.settings_btn.setIcon(qta.icon("fa5s.cog", color=icon_color))
        self.scale_down_btn.setIcon(qta.icon("ph.magnifying-glass-minus", color=icon_color))
        self.scale_up_btn.setIcon(qta.icon("ph.magnifying-glass-plus", color=icon_color))

    # Dialogs
    def add_current_to_bookmarks_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle(self.tr("Add to Bookmarks"))
        dlg.setFixedSize(340, 220)

        layout = QGridLayout()
        form_layout = QFormLayout()

        title_label = QLabel(self.tr("Add Current Page to Bookmarks"))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; padding: 20px")
        form_layout.addRow(title_label)

        name_lineedit = QLineEdit()
        name_lineedit.setText(self.web_tabs.currentWidget().title())
        name_lineedit.setMinimumWidth(200)
        form_layout.addRow(self.tr("Bookmark name: "), name_lineedit)

        url_lineedit = QLineEdit()
        url_lineedit.setText(self.web_tabs.currentWidget().url().toString())
        url_lineedit.setMinimumWidth(200)
        form_layout.addRow(self.tr("Bookmark URL: "), url_lineedit)

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
            
            QMessageBox.information(self, self.tr("Changed bookmarks"), self.tr("Bookmarks will refresh correctly after the program is restarted."))

            updated_bookmarks = {b['name']: b['url'] for b in dlg.temp_bookmarks}
        
            current_bookmarks = updated_bookmarks
        
            # Save to file
            with open(BOOKMARKS_PATH, "w") as f:
                json.dump(updated_bookmarks, f, indent=4)
        
            self.init_bookmark_bar()
    
    def settings_dialog(self):
        global current_settings

        dlg = QDialog(self)
        dlg.setWindowTitle(self.tr("Settings"))
        dlg.setFixedSize(480, 360)

        layout = QGridLayout()

        # Settings tab widget
        tabs = QTabWidget()

        # General Settings
        general_settings = QWidget()
        general_settings_layout = QFormLayout()
        general_settings.setLayout(general_settings_layout)

        title_label = QLabel(self.tr("Browser Settings"))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; padding-top: 20px; padding-bottom: 10px;")
        layout.addWidget(title_label, 0, 0)

        start_page_type_group = QButtonGroup()
        start_page_type_group.setExclusive(True)

        start_page_type_radio_button = QRadioButton(self.tr("Silk Start (local)"))
        start_page_type_radio_button.setChecked(current_settings["start_page_url"] == START_PAGE_PATH)
        start_page_type_radio_button.toggled.connect(lambda: self.toggle_url_edit(False, start_page_urledit))
        start_page_type_group.addButton(start_page_type_radio_button)

        start_page_url_radio_button = QRadioButton(self.tr("URL"))
        start_page_url_radio_button.setChecked(current_settings["start_page_url"] != START_PAGE_PATH)
        start_page_url_radio_button.toggled.connect(lambda: self.toggle_url_edit(True, start_page_urledit))
        start_page_type_group.addButton(start_page_url_radio_button)

        start_page_type_layout = QHBoxLayout()
        start_page_type_layout.addWidget(start_page_type_radio_button)
        start_page_type_layout.addWidget(start_page_url_radio_button)
        general_settings_layout.addRow(self.tr("Start page type: "), start_page_type_layout)

        start_page_urledit = QLineEdit()
        start_page_urledit.setText(current_settings["start_page_url"])
        start_page_urledit.setMinimumWidth(200)
        start_page_urledit.setEnabled(current_settings["start_page_url"] != START_PAGE_PATH)
        general_settings_layout.addRow(self.tr("Start page URL: "), start_page_urledit)

        search_engine_combobox = QComboBox()
        search_engine_combobox.addItems(["Google", "DuckDuckGo", "Brave", "Ecosia", "Yahoo"])
        search_engine_combobox.setCurrentText(current_settings["search_engine"])
        general_settings_layout.addRow(self.tr("Search engine: "), search_engine_combobox)

        # Display settings
        display_settings = QWidget()
        display_settings_layout = QFormLayout()
        display_settings.setLayout(display_settings_layout)

        theme_combobox = QComboBox()
        theme_combobox.addItems(["Light", "Dark", "Automatic", "Legacy"])
        theme_combobox.setCurrentText(current_settings["theme"])
        display_settings_layout.addRow(self.tr("Theme: "), theme_combobox)

        bottom_bar_visability_checkbox = QCheckBox()
        bottom_bar_visability_checkbox.setChecked(current_settings["bottom_bar_visible"])
        display_settings_layout.addRow(self.tr("Show bottom bar: "), bottom_bar_visability_checkbox)
        
        go_button_visibility_checkbox = QCheckBox()
        go_button_visibility_checkbox.setChecked(current_settings["go_button_visible"])
        display_settings_layout.addRow(self.tr("Show 'Go' button in URL bar: "), go_button_visibility_checkbox)

        # Security settings
        security_settings = QWidget()
        security_settings_layout = QFormLayout()
        security_settings.setLayout(security_settings_layout)

        download_warnings_checkbox = QCheckBox()
        download_warnings_checkbox.setChecked(current_settings["download_warnings"])
        security_settings_layout.addRow(self.tr("Display warning when download is requested: "), download_warnings_checkbox)

        # Language Settings
        language_settings = QWidget()
        language_settings_layout = QFormLayout()
        language_settings.setLayout(language_settings_layout)

        language_select_combobox = QComboBox()

        for lan_name, lan_code in NAME_TO_LANGUAGE.items():
            language_select_combobox.addItem(lan_name)
        

        language_select_combobox.setCurrentText(LANGUAGE_TO_NAME[current_settings["language"]])
        language_settings_layout.addRow(self.tr("Program Language: "), language_select_combobox)

        # Engine settings
        engine_settings = QWidget()
        engine_settings_layout = QFormLayout()
        engine_settings.setLayout(engine_settings_layout)

        font_size_spinbox = QSpinBox()
        font_size_spinbox.setRange(10, 80)
        font_size_spinbox.setValue(current_settings["default_font_size"])
        engine_settings_layout.addRow(self.tr("Default font size: "), font_size_spinbox)

        javascript_checkbox = QCheckBox()
        javascript_checkbox.setChecked(current_settings["javascript_enabled"])
        engine_settings_layout.addRow(self.tr("Javascript enabled: "), javascript_checkbox)

        scrollbars_enabled_checkbox = QCheckBox()
        scrollbars_enabled_checkbox.setChecked(current_settings["scrollbars_enabled"])
        engine_settings_layout.addRow(self.tr("Scrollbars enabled: "), scrollbars_enabled_checkbox)

        # AI Summarization settings
        ai_settings = QWidget()
        ai_settings_layout = QFormLayout()
        ai_settings.setLayout(ai_settings_layout)

        install_model_btn = QPushButton()

        try:
            raw_models = ollama.list()
            ollama_model_names = [m.model for m in raw_models.models]
            sum_model_installed = SUM_AI_MODEL["name"] in ollama_model_names

            if not sum_model_installed:
                install_model_btn.setText(f"{self.tr("Install")} ({SUM_AI_MODEL["size"]})")
                install_model_btn.setIcon(qta.icon("fa6s.download", color=self.get_contrast_color_from_theme()))
            else:
                install_model_btn.setText(self.tr("Model Installed"))
                install_model_btn.setIcon(qta.icon("fa6s.check", color=self.get_contrast_color_from_theme()))
            
            install_model_btn.setEnabled(not sum_model_installed)

        except Exception:
            sum_model_installed = False
            install_model_btn.setText(self.tr("Ollama not running"))
            install_model_btn.setIcon(qta.icon("ei.remove", color=self.get_contrast_color_from_theme()))
            install_model_btn.setEnabled(False)

        install_model_btn.setFixedWidth(200)
        install_model_btn.clicked.connect(lambda: self.start_model_installation(install_model_btn))
        ai_settings_layout.addRow(self.tr("Install AI Page Summarization Model: "), install_model_btn)
        
        ai_checkbox = QCheckBox()
        ai_checkbox.setEnabled(sum_model_installed)
        ai_checkbox.setChecked(current_settings["ai_summarization_enabled"])
        ai_settings_layout.addRow(self.tr("Enable AI Page Summarization: "), ai_checkbox)

        # Add widgets to tab widget
        tabs.addTab(general_settings, self.tr("General"))
        tabs.addTab(display_settings, self.tr("Display"))
        tabs.addTab(security_settings, self.tr("Security"))
        tabs.addTab(language_settings, self.tr("Language"))
        tabs.addTab(engine_settings, self.tr("Engine"))
        tabs.addTab(ai_settings, self.tr("AI Features"))

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
            download_warnings = download_warnings_checkbox.isChecked()
            language = language_select_combobox.currentText()
            javascript_enabled = javascript_checkbox.isChecked()
            default_font_size = font_size_spinbox.value()
            default_scrollbars_enabled = scrollbars_enabled_checkbox.isChecked()
            summarize_ai_enabled = ai_checkbox.isChecked()

            # Update settings in browser
            theme_manager.load_theme(theme)

            self.bottom_bar.setVisible(bottom_bar_visible)
            self.load_btn.setVisible(go_button_visible)
            self.ai_summarize_btn.setVisible(summarize_ai_enabled)
            self.ai_sidebar_btn.setVisible(summarize_ai_enabled)
            self.aiMenu.setEnabled(summarize_ai_enabled)

            if self.ai_sidebar.isVisible():
                self.ai_sidebar.setVisible(summarize_ai_enabled)
            
            if language != current_settings["language"]:
                self.load_language(NAME_TO_LANGUAGE[language])

            self.update_web_engine()

            # Prepare settings.json
            updated_settings = {
                "start_page_url":start_page,
                "search_engine":search_engine,
                "theme":theme,
                "bottom_bar_visible":bottom_bar_visible,
                "go_button_visible":go_button_visible,
                "download_warnings":download_warnings,
                "language":NAME_TO_LANGUAGE[language],
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
        install_button.setText(self.tr("Installing..."))
        animation = qta.Spin(install_button)
        install_button.setIcon(qta.icon("mdi.loading", color=self.get_contrast_color_from_theme(), animation=animation))

        self.threadpool = QThreadPool()
        worker = InstallWorker(SUM_AI_MODEL["name"])
        worker.installation_complete.connect(lambda: self.model_installation_complete(install_button))
        self.threadpool.start(worker)
    
    def model_installation_complete(self, install_button):
        install_button.setText(self.tr("Model Installed"))
        install_button.setIcon(qta.icon("fa6s.check", color=self.get_contrast_color_from_theme()))
        
        QMessageBox.information(self, self.tr("Model Installed"), self.tr("The AI page summarization model has been installed successfully. You can now enable AI page summarization in the settings."))
    
    def toggle_url_edit(self, enable, urledit):
        urledit.setEnabled(enable)
    
    def update_web_engine(self):
        for tab in self.tab_list:
            tab.update_engine_config()
        
    def about_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle(self.tr("About"))
        dlg_layout = QVBoxLayout()
        dlg.setFixedSize(240, 325)

        logoLabel = QLabel(self)
        logoLabel.setFixedSize(170, 170)
        logoLabel.setScaledContents(True)
        
        if os.path.exists(LOGO_PATH):
            logoLabel.setPixmap(QPixmap(LOGO_PATH))

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
    theme_manager = ThemeManager(app, current_settings["theme"])
    
    app.setWindowIcon(QIcon(LOGO_PATH))
    app.setStyle("breeze")
    window = BrowserWindow()
    window.show()
    sys.exit(app.exec())