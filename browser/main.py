import sys
import os
import json
import re
import datetime
import importlib.util
from pathlib import Path
import qtawesome as qta
import ollama
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QFormLayout,
    QPushButton,
    QLineEdit,
    QDialog,
    QLabel,
    QDialogButtonBox,
    QProgressBar,
    QTabWidget,
    QMessageBox,
    QSizePolicy,
    QTextEdit,
    QFileDialog,
    QMenu,
    QStackedWidget,
)
from PySide6.QtCore import Qt, QUrl, QSize, Slot, Signal, QThreadPool, QRunnable, QObject, QTranslator, QStandardPaths
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineSettings, QWebEngineProfile, QWebEnginePage
from PySide6.QtGui import QPixmap, QAction, QKeySequence, QIcon

# Dialogs
from interface.dialogs.about_dialog import AboutDialog
from interface.dialogs.bookmarks_mgr_dialog import ManageBookmarksDialog
from interface.dialogs.extensions_dialog import WebExtensionsDialog, WebExtensionFetcher
from interface.dialogs.settings_dialog import SettingsDialog
from interface.dialogs.downloads_dialog import DownloadManagerDialog

# Widgets
from interface.widgets.better_webengine import BetterWebEngine
from interface.downloads.download_menu import DownloadMenu
from interface.navigation.nav_items import DownloadManagerBtn

# Navigation
from interface.navigation.nav_manager import NavBarManager

# Services
from services.theme_mgr import ThemeManager
from services.extension_mgr import ExtensionManager, ExtensionMetadata
from interface.downloads.download_mgr import DownloadManager
from services.constants import (
    SCRIPT_DIR, CONFIG_PATH, BOOKMARKS_PATH, LOGO_PATH, START_PAGE_PATH,
    AI_SYSPROMPT_PATH, DOWNLOAD_PATH, EXTENSIONS_PATH, EXTENSIONS_SETTINGS_PATH,
    ADDITIONAL_QSS_PATH, DEFAULT_NAVBAR_LAYOUT_PATH, SUM_AI_MODEL, VERSION_NUMBER,
    NAME_TO_LANGUAGE, LANGUAGE_TO_NAME,
)

STORAGE_PATH = os.path.join(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation), "Silk-Mizu-Browser")

# Get default navigation bar layout
with open(DEFAULT_NAVBAR_LAYOUT_PATH, "r") as f:
    default_navbar_layout = json.load(f)

current_settings = {}
default_settings = {
    "start_page_url":START_PAGE_PATH,
    "search_engine":"Google",
    "theme":"Dark",
    "accent_color":"#8370EB",
    "bottom_bar_visible":False,
    "navigation_ui_elements":default_navbar_layout["navigation_ui_elements"],
    "download_warnings":True,
    "downloads_path":str(Path.home()) + "/Downloads",
    "language":"en_US",
    "javascript_enabled":True,
    "default_font_size":16,
    "scrollbars_enabled":True,
    "ai_summarization_enabled":False
}

current_bookmarks = {}
default_bookmarks = {}

extensions_settings = {}
default_extension_settings = {
    "index_urls":["https://raw.githubusercontent.com/FlipArtYT/Mizu-Browser-Extensions/refs/heads/main/index.json"]
}

# Disable Chromium debug logs
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-logging"

# Create extensions folder if it not already exists
if not os.path.exists(EXTENSIONS_PATH):
    os.makedirs(EXTENSIONS_PATH, exist_ok=True)

# Load AI system prompt
with open(AI_SYSPROMPT_PATH, 'r') as f:
    ai_system_prompt = f.read()

# Load additional QSS stylesheet
with open(ADDITIONAL_QSS_PATH, 'r') as f:
    additional_qss = f.read()

def load_config(path, settings_dict, fallback_dict):
    if os.path.exists(path):
        with open(path, "r") as f:
            d = json.load(f)
        try:
            for key, val in d.items():
                settings_dict[key] = val

            key_added = False

            for key, val in fallback_dict.items():
                if not key in settings_dict:
                    settings_dict[key] = val
                    key_added = True
            
            if key_added:
                with open(path, "w") as f:
                    json.dump(settings_dict, f, indent=4)
        
        except KeyError:
            settings_dict.clear()
            settings_dict.update(fallback_dict)
            print(f"Failed to load {os.path.basename(path)}. Using default values.")
    else:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(fallback_dict, f, indent=4)
        settings_dict.clear()
        settings_dict.update(fallback_dict)

# Load all configs
load_config(EXTENSIONS_SETTINGS_PATH, extensions_settings, default_extension_settings)
load_config(BOOKMARKS_PATH, current_bookmarks, default_bookmarks)
load_config(CONFIG_PATH, current_settings, default_settings)

class WebExtensionsMenuSignals(QObject):
    request_manage_extensions = Signal()

class WebExtensionsMenu(QMenu):
    def __init__(self):
        super().__init__()

        self.signals = WebExtensionsMenuSignals()

        self.init_ui()
    
    def init_ui(self):
        # Add base actions
        manage_extensions_action = QAction(self.tr("Manage Extensions"), self)
        manage_extensions_action.triggered.connect(self.signals.request_manage_extensions.emit)

        self.addSeparator()
        self.addAction(manage_extensions_action)

class Extension_Sidebar_Button(QPushButton):
    def __init__(self, metadata: ExtensionMetadata, parent=None):
        super().__init__(parent)
        self.metadata = metadata

        self.setFixedSize(35, 35)

        # Icon (if available)
        self.extension_icon_path = os.path.join(EXTENSIONS_PATH, self.metadata.app_id, self.metadata.icon_path)

        if os.path.exists(self.extension_icon_path) and self.metadata.icon_path != "":     
            self.setIcon(QIcon(self.extension_icon_path))
        else:
            self.setText(self.metadata.name[0])

class Extension_Sidebar(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setFixedWidth(50)
        self.sidebar_layout = QHBoxLayout()
        self.sidebar_layout.setContentsMargins(5, 5, 5, 5)
        self.sidebar_layout.setSpacing(5)
        self.showing_extension = False
        self.extension_btns = {}

        self.setLayout(self.sidebar_layout)

        self.init_ui()
        self.load_extensions()
    
    def init_ui(self):
        self.extension_bar_layout = QVBoxLayout()
        self.rounded_sec_border = QStackedWidget()
        
        self.rounded_sec_border.setStyleSheet("border-radius: 3px;")
        self.rounded_sec_border.hide()

        self.sidebar_layout.addLayout(self.extension_bar_layout)
        self.sidebar_layout.addWidget(self.rounded_sec_border)

    def load_extensions(self):
        self.clear_layout(self.extension_bar_layout)

        while self.rounded_sec_border.count() > 0:
            widget = self.rounded_sec_border.widget(0)
            self.rounded_sec_border.removeWidget(widget)
            widget.deleteLater()
        
        extension_manager.update_extension_list()
        extensions = extension_manager.get_installed()
        ai_extensions_enabled = current_settings["ai_summarization_enabled"]

        self.extension_bar_layout.addStretch()

        # Extension content
        if ai_extensions_enabled:
            ai_sum_ext_btn = QPushButton()
            ai_sum_ext_btn.setIcon(qta.icon("msc.sparkle-filled"))
            ai_sum_ext_btn.setFixedSize(35, 35)
            ai_sum_ext_btn.clicked.connect(lambda _, i=0: self.toggle_extension(i))
            self.extension_bar_layout.addWidget(ai_sum_ext_btn, alignment=Qt.AlignmentFlag.AlignHCenter)

            self.ai_sum_ext = AI_Extension(self)
            self.rounded_sec_border.addWidget(self.ai_sum_ext)

        for i, el in enumerate(extensions):
            try:
                spec = spec = importlib.util.spec_from_file_location(
                        el.name, 
                        os.path.join(EXTENSIONS_PATH, el.app_id, el.script_path)
                    )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                plugin_class = getattr(module, "MainWidget")
                plugin_instance = plugin_class()
                
                self.rounded_sec_border.addWidget(plugin_instance)

                button = Extension_Sidebar_Button(el)

                if not ai_extensions_enabled:
                    button.clicked.connect(lambda _, i=i: self.toggle_extension(i))

                else:
                    button.clicked.connect(lambda _, i=i: self.toggle_extension(i+1))
                
                self.extension_bar_layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignHCenter)
                
            except Exception as e:
                print(f"Error when trying to load {el.name}: {e}")

        self.extension_bar_layout.addStretch()
    
    def toggle_extension(self, id):
        if id != self.rounded_sec_border.currentIndex():
            self.rounded_sec_border.setCurrentIndex(id)

            if not self.showing_extension:
                self.showing_extension = True
        else:
            self.showing_extension = not self.showing_extension

        if self.showing_extension:
            self.setFixedWidth(450)
            self.rounded_sec_border.show()

        else:
            self.setFixedWidth(50)
            self.rounded_sec_border.hide()
    
    def get_contrast_color_from_theme(self):
        return theme_manager.get_contrast_color_from_theme()
    
    def clear_layout(self, layout):
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
                else:
                    self.clear_layout(item.layout())

class InstallWorkerSignals(QObject):
    installation_complete = Signal()

class InstallWorker(QRunnable):
    def __init__(self, model_name):
        super().__init__()
        self.signals = InstallWorkerSignals()
        self.model_name = model_name
    
    @Slot()
    def run(self):
        print(f"Installing model: {self.model_name}...")
        ollama.pull(self.model_name)
        print("Model installation complete.")
        self.signals.installation_complete.emit()

class AI_SummarizationWorkerSignals(QObject):
    chunk_received = Signal(str)
    finished = Signal()

class AI_SummarizationWorker(QRunnable):
    def __init__(self, text):
        super().__init__()
        self.text = text
        self.signals = AI_SummarizationWorkerSignals()
    
    @Slot()
    def run(self):
        print("Summarizing page content...")
        stream = ollama.chat(
            model=SUM_AI_MODEL["name"],
            messages=[{'role': 'system', 'content': ai_system_prompt},
                      {'role': 'user', 'content': self.text}],
            stream=True,
        )

        for chunk in stream:
            content = chunk['message']['content']
            self.signals.chunk_received.emit(content)
        
        self.signals.finished.emit()

class AI_Extension(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.layout = QVBoxLayout()

        self.init_ui()

    def init_ui(self):
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
        self.download_chat_btn.setIcon(qta.icon("fa6s.download", color=theme_manager.get_contrast_color_from_theme()))
        self.download_chat_btn.clicked.connect(self.download_chat_dlg)
        self.input_controls_layout.addWidget(self.download_chat_btn)

        self.clear_btn = QPushButton(self.tr("Clear"))
        self.clear_btn.setIcon(qta.icon("fa6s.trash", color=theme_manager.get_contrast_color_from_theme()))
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

        # Threadpool
        self.threadpool = QThreadPool()

        # Initialize whole UI
        self.init_menu_bar()
        self.init_extension_sidebar()
        self.init_control_ui()
        self.init_bookmark_bar()
        self.setup_profile()
        self.init_web_engine()

        self.extension_updates = False
        self.check_extension_updates()

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
        self.helpMenu = menu_bar.addMenu(self.tr("&Help"))

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
        self.cutAction = QAction(self.tr("Cut"), self)
        self.cutAction.triggered.connect(lambda: self.web_tabs.currentWidget().page().triggerAction(QWebEnginePage.WebAction.Cut))
        self.cutAction.setShortcut(QKeySequence.Cut)
        self.editMenu.addAction(self.cutAction)

        self.copyAction = QAction(self.tr("Copy"), self)
        self.copyAction.triggered.connect(lambda: self.web_tabs.currentWidget().page().triggerAction(QWebEnginePage.WebAction.Copy))
        self.copyAction.setShortcut(QKeySequence.Copy)
        self.editMenu.addAction(self.copyAction)

        self.pasteAction = QAction(self.tr("Paste"), self)
        self.pasteAction.triggered.connect(lambda: self.web_tabs.currentWidget().page().triggerAction(QWebEnginePage.WebAction.Paste))
        self.pasteAction.setShortcut(QKeySequence.Paste)
        self.editMenu.addAction(self.pasteAction)

        self.editMenu.addSeparator()

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

        self.removeTabAction = QAction(self.tr("Remove current tab"), self)
        self.removeTabAction.triggered.connect(self.remove_tab_shortcut)
        self.removeTabAction.setShortcut(QKeySequence("Ctrl + w"))
        self.editMenu.addAction(self.removeTabAction)

        self.moveToNextTabAction = QAction(self.tr("Next tab"), self)
        self.moveToNextTabAction.triggered.connect(self.move_to_next_tab)
        self.moveToNextTabAction.setShortcut(QKeySequence("Ctrl + Tab"))
        self.editMenu.addAction(self.moveToNextTabAction)

        self.moveToPreviousTabAction = QAction(self.tr("Previous tab"), self)
        self.moveToPreviousTabAction.triggered.connect(self.move_to_previous_tab)
        self.moveToPreviousTabAction.setShortcut(QKeySequence("Ctrl + shift + Tab"))
        self.editMenu.addAction(self.moveToPreviousTabAction)

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

        # Help Menu
        self.documentationAction = QAction(self.tr("Project Page"), self)
        self.documentationAction.triggered.connect(lambda: self.create_new_tab("https://github.com/Silk-Project/Silk-Mizu-Browser/"))
        self.helpMenu.addAction(self.documentationAction)

        self.aboutAction = QAction(self.tr("About"))
        self.aboutAction.triggered.connect(self.about_dialog)
        self.helpMenu.addAction(self.aboutAction)

    def init_control_ui(self):
        # Bottom bar
        self.bottom_bar = QWidget()
        self.bottom_bar.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self.bottom_bar.setContentsMargins(0, 0, 0, 0)
        self.bottom_bar.setVisible(current_settings["bottom_bar_visible"])
        bottom_bar_layout = QHBoxLayout()
        bottom_bar_layout.setContentsMargins(5, 5, 5, 5)
        bottom_bar_layout.setSpacing(5)

        self.bottom_bar.setLayout(bottom_bar_layout)
        self.layout.addWidget(self.bottom_bar, 4, 0)

        # Tab system
        self.web_tabs = QTabWidget()
        self.web_tabs.setTabsClosable(True)
        self.web_tabs.setMovable(True)
        self.web_tabs.setIconSize(QSize(16, 16))
        self.web_tabs.setTabShape(QTabWidget.TabShape.Rounded)
        self.web_tabs.tabBar().setUsesScrollButtons(True)
        self.web_tabs.currentChanged.connect(self.update_tab_info)
        self.web_tabs.tabCloseRequested.connect(self.remove_web_tab)
        self.middle_layout.addWidget(self.web_tabs, 1)
        self.browser_controller = BrowserController(self, self.web_tabs)

        # Controls layout
        self.top_controls_layout = QHBoxLayout()
        self.layout.addLayout(self.top_controls_layout, 0, 0)

        self.top_navbar = NavBarManager(self.browser_controller, theme_manager)
        self.top_controls_layout.addWidget(self.top_navbar, 1)

        self.bottom_controls_layout = QHBoxLayout()
        self.layout.addLayout(self.bottom_controls_layout, 3, 0)

        self.bottom_navbar = NavBarManager(self.browser_controller, theme_manager)
        self.bottom_controls_layout.addWidget(self.bottom_navbar, 1)

        nav_elements = current_settings.get("navigation_ui_elements")

        if isinstance(nav_elements, dict):
            self.top_navbar.rebuild_navbar(nav_elements.get("top", []))
            self.bottom_navbar.rebuild_navbar(nav_elements.get("bottom", []))
        else:
            self.top_navbar.rebuild_navbar(nav_elements or [])
            self.bottom_navbar.rebuild_navbar([])

        self.download_manager = DownloadManager()
        self._update_download_button_visibility()
        self.download_menu = DownloadMenu()
        self.download_manager.download_added.connect(lambda download: self.download_menu.add_download(
            download=download
        ))
        self.download_manager.download_added.connect(self._on_download_added)
        self.download_menu.signals.downloads_dialog_opened.connect(self.show_downloads_dialog)

        # Bottom bar
        self.page_progressbar = QProgressBar()
        self.page_progressbar.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.page_progressbar.setVisible(False)
        self.page_progressbar.setFixedWidth(200)
        self.page_progressbar.setValue(0)
        bottom_bar_layout.addWidget(self.page_progressbar)

        bottom_bar_layout.addStretch(1)

        icon_color = theme_manager.get_contrast_color_from_theme()

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
        
        else:
            print(f"Failed to load language: {lang}")

    def retranslate_ui(self):
        # Menu bar
        self.fileMenu.setTitle(self.tr("&File"))
        self.editMenu.setTitle(self.tr("&Edit"))
        self.viewMenu.setTitle(self.tr("&View"))
        self.bookmarkMenu.setTitle(self.tr("&Bookmarks"))
        self.helpMenu.setTitle(self.tr("&Help"))

        # File Menu
        self.settingsAction.setText(self.tr("Program Settings"))
        self.exitAction.setText(self.tr("Quit"))
        
        # Edit Menu
        self.cutAction.setText(self.tr("Cut"))
        self.copyAction.setText(self.tr("Copy"))
        self.pasteAction.setText(self.tr("Paste"))
        self.createNewTabAction.setText(self.tr("New Tab"))
        self.backAction.setText(self.tr("Back"))
        self.nextAction.setText(self.tr("Next"))
        self.removeTabAction.setText(self.tr("Remove current tab"))
        self.moveToNextTabAction.setText(self.tr("Next tab"))
        self.moveToPreviousTabAction.setText(self.tr("Previous tab"))

        # View menu
        self.scaleUpAction.setText(self.tr("Increase page zoom by 10%"))
        self.scaleDownAction.setText(self.tr("Decrease page zoom by 10%"))
        self.scaleDefaultAction.setText(self.tr("Set page zoom to 100%"))

        # Bookmarks menu
        self.manageBookmarksAction.setText(self.tr("Manage bookmarks"))
        self.addPageToBookmarksAction.setText(self.tr("Add current page to bookmarks"))

        # Help Menu
        self.documentationAction.setText(self.tr("Project Page"))
        self.aboutAction.setText(self.tr("About"))

    def init_bookmark_bar(self):
        # Bookmark bar
        try:
            while self.bookmarks_layout.count():
                item = self.bookmarks_layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
                else:
                    self.clear_layout(item.layout())
            
        except AttributeError:
            pass
        
        self.bookmarks_layout = QHBoxLayout()
        self.bookmarks_layout.setContentsMargins(5, 0, 5, 5)
        self.bookmarks_layout.setSpacing(5)
        self.layout.addLayout(self.bookmarks_layout, 1, 0)

        bookmark_map = {}

        for name, url in current_bookmarks.items():
            bookmark_btn = QPushButton(name)
            bookmark_btn.setStyleSheet("padding: 3px;")
            bookmark_btn.clicked.connect(lambda checked, url=url: self.request_load_page(url))
            bookmark_map[name] = bookmark_btn
            self.bookmarks_layout.addWidget(bookmark_btn)

        self.bookmarks_layout.addStretch(1)
    
    # AI sidebar
    def init_extension_sidebar(self):
        # Create middle layout
        self.middle_layout = QHBoxLayout()
        self.middle_layout.setContentsMargins(0, 0, 0, 0)
        self.middle_layout.setSpacing(0)
        self.layout.addLayout(self.middle_layout, 2, 0)

        # AI Sidebar
        self.extension_sidebar = Extension_Sidebar(self)
        self.extension_sidebar.setVisible(False)
        self.middle_layout.addWidget(self.extension_sidebar)
    
    def toggle_extension_sidebar(self):
        is_visible = self.extension_sidebar.isVisible()
        self.extension_sidebar.setVisible(not is_visible)
    
    def summarize_current_page_ai(self):
        if not current_settings["ai_summarization_enabled"]:
            return
        
        self.extension_sidebar.setVisible(True)
        current_page = self.web_tabs.currentWidget()
        current_page.page().toPlainText(self.extension_sidebar.ai_sum_ext.send_webpage)
    
    def summarize_selected_with_ai(self, selected_text):
        if not current_settings["ai_summarization_enabled"]:
            return
        
        self.extension_sidebar.setVisible(True)
        self.extension_sidebar.send_webpage(selected_text)

    # Website Tabs
    def closeEvent(self, a0):
        self.web_tabs.blockSignals(True)
        while self.web_tabs.count() > 0:
            tab_widget = self.web_tabs.widget(0)
            profile = tab_widget.page().profile()
            profile.clearHttpCache()

            self.web_tabs.removeTab(0)
            tab_widget.deleteLater()

    def init_web_engine(self):
        self.create_new_tab()
    
    def setup_profile(self):
        if not os.path.exists(STORAGE_PATH):
            os.makedirs(STORAGE_PATH)

        self.profile = QWebEngineProfile("Default", self)
        self.profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.DiskHttpCache)
        self.profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies)
        self.profile.setCachePath(STORAGE_PATH)
        self.profile.setPersistentStoragePath(STORAGE_PATH)
        self.profile.setParent(self)
        self.profile.downloadRequested.connect(self.request_download)

    def update_tab_info(self):
        self.update_tab_titles()
    
    def create_new_tab(self, url=None):
        # Web Engine
        web_tab = BetterWebEngine(self, current_settings)
        web_tab.setPage(QWebEnginePage(self.profile, web_tab))
        web_tab.init_engine()

        # Setup localstorage for the new tab
        web_tab.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        
        if url:
            web_tab.setUrl(QUrl(url))

        web_tab.loadProgress.connect(self.update_progressbar)
        web_tab.loadFinished.connect(self.page_load_finished)
        web_tab.loadFinished.connect(web_tab.page_load_finished)
        web_tab.loadStarted.connect(self.page_load_started)
        web_tab.iconChanged.connect(self.update_tab_info)
        web_tab.signals.sum_selected_with_ai.connect(self.summarize_selected_with_ai)
        web_tab.signals.sum_page_with_ai.connect(self.summarize_current_page_ai)

        self.web_tabs.addTab(web_tab, None)
        self.web_tabs.setCurrentIndex(self.web_tabs.count() - 1)
        self.update_tab_info()
    
    def remove_web_tab(self, index):
        if index >= 0 and self.web_tabs.count() > 1:
            widget = self.web_tabs.widget(index)
            self.web_tabs.removeTab(index)
            widget.deleteLater()
            self.update_tab_info()
    
    def update_tab_titles(self):
        for tab_index in range(self.web_tabs.count()):
            web_engine = self.web_tabs.widget(tab_index)
            title = web_engine.title() if web_engine.title() else self.tr("New Tab")
            self.web_tabs.setTabText(tab_index, f"{' '*3}{title[:20]+'...' if len(title) > 20 else title}{' '*3}")
            self.web_tabs.setTabToolTip(tab_index, web_engine.title())

            if web_engine.iconUrl().isEmpty():
                self.web_tabs.setTabIcon(tab_index, QIcon())

            elif web_engine.icon().isNull():
                animation = qta.Spin(self.web_tabs)
                self.web_tabs.setTabIcon(tab_index, qta.icon("mdi.loading", animation=animation))

            else:
                self.web_tabs.setTabIcon(tab_index, QIcon(web_engine.icon()))

    def move_to_next_tab(self):
        current_tab_index = self.web_tabs.currentIndex()

        if current_tab_index >= 0 and current_tab_index < self.web_tabs.count() - 1:
            self.web_tabs.setCurrentIndex(current_tab_index + 1)

        else:
            self.web_tabs.setCurrentIndex(0)
    
    def move_to_previous_tab(self):
        current_tab_index = self.web_tabs.currentIndex()

        if not current_tab_index == 0:
            self.web_tabs.setCurrentIndex(current_tab_index - 1)

        else:
            self.web_tabs.setCurrentIndex(self.web_tabs.count() - 1)
    
    def remove_tab_shortcut(self):
        current_tab_index = self.web_tabs.currentIndex()
        self.remove_web_tab(current_tab_index)

    # Download System
    def _update_download_button_visibility(self):
        has_downloads = len(self.download_manager.downloads) > 0
        for i in range(self.top_navbar.controls_layout.count()):
            item = self.top_navbar.controls_layout.itemAt(i)
            if item is not None:
                widget = item.widget()
                if isinstance(widget, DownloadManagerBtn):
                    widget.setVisible(has_downloads)

    def _on_download_added(self, download):
        self._update_download_button_visibility()
        download.isFinishedChanged.connect(self._on_download_state_changed)

    def _on_download_state_changed(self):
        self._update_download_button_visibility()

    def show_nearest_download_menu(self):
        button = self.browser_controller.get_first_widget_from_navbar(DownloadManagerBtn)
        if button:
            button_pos = button.mapToGlobal(button.rect().bottomLeft())
        else:
            navbar_pos = self.top_navbar.mapToGlobal(
                self.top_navbar.rect().topRight()
            )
            button_pos = navbar_pos
        self.download_menu.exec(button_pos)
    
    def show_downloads_dialog(self):
        dlg = DownloadManagerDialog(downloads=self.download_manager.downloads, parent=self)
        dlg.exec()

    def request_download(self, download):
        try:
            if current_settings["download_warnings"]:
                warning_dlg = QMessageBox(self)
                warning_dlg.setWindowTitle(self.tr("Download Request"))
                warning_dlg.setText(f"{self.tr('Do you really want to download')} \"{download.suggestedFileName()}\"?")
                warning_dlg.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
                warning_dlg.setIcon(QMessageBox.Icon.Warning)

                if warning_dlg.exec() == QMessageBox.StandardButton.Ok:
                    self.download_manager.add_download(download, current_settings.get("downloads_path", DOWNLOAD_PATH))
                    self.show_nearest_download_menu()
            else:
                self.download_manager.add_download(download, current_settings.get("downloads_path", DOWNLOAD_PATH))
                self.show_nearest_download_menu()
        except AttributeError:
            download.accept()

    # Extension system
    def show_extension_menu(self):
        try:
            button_pos = self.web_extensions_btn.mapToGlobal(self.web_extensions_btn.rect().bottomLeft())
            self.web_extensions_menu.exec(button_pos)
        except AttributeError:
            pass

    def web_extension_dialog(self):
        dlg = WebExtensionsDialog(parent=self, extension_manager=extension_manager, index_urls=extensions_settings["index_urls"])
        dlg.exec()
        self.check_extension_updates()
        self.extension_sidebar.load_extensions()
        
    def check_extension_updates(self):
        fetcher = WebExtensionFetcher(extensions_settings["index_urls"])
        fetcher.signals.response_received.connect(self.show_extension_status)
        self.threadpool.start(fetcher)
    
    def show_extension_status(self, store_extensions_json):
        # Get current extensions and compare versions
        local_extensions = extension_manager.get_installed()
        updateable_extensions = 0

        # Parse store extensions into an ExtensionMetadata instance for easier access
        store_extensions = {}
        for ext_data in store_extensions_json:
            try:
                ext_meta = ExtensionMetadata(**ext_data)
                store_extensions[ext_meta.app_id] = ext_meta
            except Exception as e:
                print(f"Error parsing extension data from store: {e}")
                continue

        try:
            self.extension_updates = False

            for el in local_extensions:
                if el.app_id in store_extensions:
                    local_version = self.version_parser(el.version)
                    store_version = self.version_parser(store_extensions[el.app_id].version)

                    if store_version > local_version:
                        updateable_extensions += 1
                        self.extension_updates = True
            
            if self.extension_updates:
                print(f"{self.tr('Extension updates: ')}{updateable_extensions}")
            
            else:
                # No updates
                pass

        except Exception as e:
            print(f"Error when checking extensions for updates: {e}")
    
    def version_parser(self, version_string):
        try:
            version_tuple = tuple(map(int, version_string.split(".")))
            return version_tuple
        except Exception as e:
            print(f"Error parsing version string '{version_string}': {e}")
            return (0,)

    # Website content specific functions
    def update_progressbar(self, prog):
        self.page_progressbar.setVisible(True)
        self.page_progressbar.setValue(prog)

    def page_load_finished(self):
        self.page_progressbar.setVisible(False)
        self.update_tab_info()
    
    def page_load_started(self):
        self.update_progressbar(0)
        self.update_tab_info()
    
    # Website navigation
    def request_back_page(self):
        self.web_tabs.currentWidget().history().back()
        self.update_tab_info()

    def request_next_page(self):
        self.web_tabs.currentWidget().history().forward()
        self.update_tab_info()
    
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
    
    # Dialogs
    def add_current_to_bookmarks_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle(self.tr("Add to Bookmarks"))
        dlg.setFixedSize(340, 220)

        layout = QGridLayout()
        form_layout = QFormLayout()

        title_label = QLabel(self.tr("Add Current Page to Bookmarks"))
        title_label.setWordWrap(True)
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
        dlg = ManageBookmarksDialog(self, current_bookmarks, icon_color=theme_manager.get_contrast_color_from_theme())

        if dlg.exec():
            if dlg.temp_bookmarks == dlg.bookmarks_reference:
                return

            updated_bookmarks = {b['name']: b['url'] for b in dlg.temp_bookmarks}
        
            current_bookmarks = updated_bookmarks
        
            # Save to file
            with open(BOOKMARKS_PATH, "w") as f:
                json.dump(updated_bookmarks, f, indent=4)
        
            self.init_bookmark_bar()
    
    def settings_dialog(self):
        global current_settings

        dlg = SettingsDialog(self, theme_manager, current_settings)
        if dlg.exec():
            settings = dlg.get_settings()

            theme_manager.load_theme_from_index(settings["theme_index"])
            self.bottom_bar.setVisible(settings["bottom_bar_visible"])

            if settings["language"] != current_settings["language"]:
                self.load_language(NAME_TO_LANGUAGE[settings["language"]])

            self.update_web_engine()
            nav_elements = settings["navigation_ui_elements"]

            if isinstance(nav_elements, dict):
                self.top_navbar.rebuild_navbar(nav_elements.get("top", []))
                self.bottom_navbar.rebuild_navbar(nav_elements.get("bottom", []))
            else:
                self.top_navbar.rebuild_navbar(nav_elements or [])
                self.bottom_navbar.rebuild_navbar([])
            
            self._update_download_button_visibility()
            self.browser_controller._on_tab_changed()

            if settings["ai_summarization_enabled"] != current_settings["ai_summarization_enabled"]:
                current_settings["ai_summarization_enabled"] = settings["ai_summarization_enabled"]
                self.extension_sidebar.load_extensions()

            theme_manager.set_accent_color(settings["accent_color"])

            updated_settings = {
                "start_page_url": settings["start_page_url"],
                "search_engine": settings["search_engine"],
                "theme": theme_manager.available_themes[settings["theme_index"]],
                "accent_color": settings["accent_color"],
                "bottom_bar_visible": settings["bottom_bar_visible"],
                "navigation_ui_elements": settings["navigation_ui_elements"],
                "download_warnings": settings["download_warnings"],
                "downloads_path": settings["downloads_path"],
                "language": NAME_TO_LANGUAGE[settings["language"]],
                "javascript_enabled": settings["javascript_enabled"],
                "default_font_size": settings["default_font_size"],
                "scrollbars_enabled": settings["scrollbars_enabled"],
                "ai_summarization_enabled": settings["ai_summarization_enabled"],
            }

            current_settings = updated_settings

            with open(CONFIG_PATH, "w") as f:
                json.dump(updated_settings, f, indent=4)

    def start_model_installation(self, install_button):
        install_button.setEnabled(False)
        install_button.setText(self.tr("Installing..."))
        animation = qta.Spin(install_button)
        install_button.setIcon(qta.icon("mdi.loading", color=theme_manager.get_contrast_color_from_theme(), animation=animation))

        self.threadpool = QThreadPool()
        worker = InstallWorker(SUM_AI_MODEL["name"])
        worker.signals.installation_complete.connect(lambda: self.model_installation_complete(install_button))
        self.threadpool.start(worker)
    
    def model_installation_complete(self, install_button):
        install_button.setText(self.tr("Model Installed"))
        install_button.setIcon(qta.icon("fa6s.check", color=theme_manager.get_contrast_color_from_theme()))
        
        QMessageBox.information(self, self.tr("Model Installed"), self.tr("The AI page summarization model has been installed successfully. You can now enable AI page summarization in the settings."))
    
    def update_web_engine(self):
        for i in range(self.web_tabs.count()):
            self.web_tabs.widget(i).update_engine_config()
        
    def about_dialog(self):
        dlg = AboutDialog(self)
        dlg.exec()

class BrowserController(QObject):
    currentBrowserChanged = Signal(QWebEngineView)

    def __init__(self, window: BrowserWindow, tabs: QTabWidget):
        super().__init__()
        self.window = window
        self.tabs = tabs
        tabs.currentChanged.connect(self._on_tab_changed)

    def _on_tab_changed(self):
        self.currentBrowserChanged.emit(self.current_browser())

    def current_browser(self):
        return self.tabs.currentWidget()
    
    def get_first_widget_from_navbar(self, widget_type):
        for i in range(self.window.top_navbar.controls_layout.count()):
            item = self.window.top_navbar.controls_layout.itemAt(i)

            if item is not None:
                widget = item.widget()

                if isinstance(widget, widget_type):
                    return widget
        
        return None

    def toggle_sidebar(self):
        self.window.toggle_extension_sidebar()
    
    def open_download_manager(self):
        print("Opening download manager...")
        self.window.show_downloads_dialog()

    def open_download_menu(self, button):
        button_pos = button.mapToGlobal(button.rect().bottomLeft())
        self.window.download_menu.exec(button_pos)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("Silk Mizu")
    app.setApplicationVersion(VERSION_NUMBER)
    app.setOrganizationName("Silk Project")

    # Load theme
    theme_manager = ThemeManager(app, additional_qss, current_settings.get("accent_color", "#8370EB"), current_settings["theme"])

    # Load extension manager
    extension_manager = ExtensionManager()
    
    app.setWindowIcon(QIcon(LOGO_PATH))
    app.setStyle("breeze")
    window = BrowserWindow()
    window.show()
    sys.exit(app.exec())