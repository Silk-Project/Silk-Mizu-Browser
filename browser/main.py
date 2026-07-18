import sys
import os
import json
from pathlib import Path
import qtawesome as qta
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QGridLayout,
    QFormLayout,
    QPushButton,
    QLineEdit,
    QDialog,
    QLabel,
    QDialogButtonBox,
    QTabWidget,
    QStackedWidget,
    QMessageBox,
)
from PySide6.QtCore import Qt, QUrl, QSize, Slot, Signal, QThreadPool, QRunnable, QObject, QTranslator, QStandardPaths, QTimer
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineSettings, QWebEngineProfile, QWebEnginePage
from PySide6.QtGui import QAction, QKeySequence, QIcon
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

# Dialogs
from interface.dialogs.about_dialog import AboutDialog
from interface.dialogs.bookmarks_mgr_dialog import ManageBookmarksDialog
from interface.dialogs.extensions_dialog import WebExtensionsDialog, WebExtensionFetcher
from interface.dialogs.settings_dialog import SettingsDialog
from interface.dialogs.downloads_dialog import DownloadManagerDialog

# Widgets
from interface.widgets.better_webengine import BetterWebEngine
from interface.widgets.tab_manager import TabManager
from interface.widgets.history_manager import HistoryManagerWidget
from interface.widgets.floating_address_bar import FloatingAddressBar
from interface.downloads.download_menu import DownloadMenu
from interface.navigation.nav_items import DownloadManagerBtn

# Extensions
from interface.extensions.extension_sidebar import Extension_Sidebar

# Navigation
from interface.navigation.nav_manager import NavBarManager

# Services
from services.theme_mgr import ThemeManager
from services.extension_mgr import ExtensionManager, ExtensionMetadata
from services.model_install_worker import InstallWorker
from services.history_mgr import HistoryManager
from interface.downloads.download_mgr import DownloadManager
from services.constants import (
    SCRIPT_DIR, CONFIG_PATH, BOOKMARKS_PATH, LOGO_PATH, START_PAGE_PATH,
    DOWNLOAD_PATH, EXTENSIONS_PATH, EXTENSIONS_SETTINGS_PATH, ADDITIONAL_QSS_PATH, 
    DEFAULT_NAVBAR_LAYOUT_PATH, SUM_AI_MODEL, VERSION_NUMBER, NAME_TO_LANGUAGE, 
    LANGUAGE_TO_NAME, NAVIGATION_SOUND_PATH
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

        # Navigation sound
        # self.player = QMediaPlayer()
        # self.audio_output = QAudioOutput()
        # self.player.setAudioOutput(self.audio_output)
        # self.audio_output.setVolume(0.7)
        # self.player.setSource(NAVIGATION_SOUND_PATH)

        # Install translator
        self.translator = QTranslator()
        self.load_language(current_settings["language"])

        self.init_extension_sidebar()
        self.init_control_ui()
        self.init_bookmark_bar()
        self.setup_profile()
        self.init_web_engine()

        self.extension_updates = False
        self.check_extension_updates()

        # Add main widget
        widget = QWidget()
        widget.setLayout(self.layout)
        self.setCentralWidget(widget)

        # Floating address bar
        self.floating_address_bar = FloatingAddressBar(self.browser_controller, self.centralWidget())

        if not os.path.exists(START_PAGE_PATH):
            QMessageBox.critical(self, self.tr("Start page not found"),
                                 self.tr("The Silk Start submodule was not found. Make sure you follow the cloning instructions carefully."))

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

        self.reloadPageAction = QAction(self.tr("Reload current tab"), self)
        self.reloadPageAction.triggered.connect(self.request_reload_page)
        self.reloadPageAction.setShortcuts(["Ctrl + R", "F5"])
        self.editMenu.addAction(self.reloadPageAction)

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

        self.editMenu.addSeparator()

        self.toggleFloatingBarAction = QAction(self.tr("Toggle address bar"), self)
        self.toggleFloatingBarAction.triggered.connect(self.toggle_floating_address_bar)
        self.toggleFloatingBarAction.setShortcut(QKeySequence("Ctrl + Space"))
        self.editMenu.addAction(self.toggleFloatingBarAction)

        # View Menu
        self.toggleSidebarAction = QAction(self.tr("Toggle extension sidebar"), self)
        self.toggleSidebarAction.triggered.connect(self.toggle_extension_sidebar)
        self.toggleSidebarAction.setShortcut(QKeySequence("Ctrl + s"))
        self.viewMenu.addAction(self.toggleSidebarAction)

        self.toggleFocusModeAction = QAction(self.tr("Toggle focus mode"), self)
        self.toggleFocusModeAction.triggered.connect(self.toggle_focus_mode)
        self.toggleFocusModeAction.setShortcut(QKeySequence("Ctrl + f"))
        self.viewMenu.addAction(self.toggleFocusModeAction)

        self.toggleTabManagerAction = QAction(self.tr("Toggle tab manager"), self)
        self.toggleTabManagerAction.triggered.connect(self.toggle_tab_manager)
        self.toggleTabManagerAction.setShortcut(QKeySequence("Ctrl + ."))
        self.viewMenu.addAction(self.toggleTabManagerAction)

        self.toggleHistoryManagerAction = QAction(self.tr("Toggle history manager"), self)
        self.toggleHistoryManagerAction.triggered.connect(self.toggle_history_manager)
        self.toggleHistoryManagerAction.setShortcut(QKeySequence("Ctrl + h"))
        self.viewMenu.addAction(self.toggleHistoryManagerAction)

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
        # Tab system
        self.web_tabs = QTabWidget()
        self.web_tabs.setTabsClosable(True)
        self.web_tabs.setMovable(True)
        self.web_tabs.setIconSize(QSize(16, 16))
        self.web_tabs.setTabShape(QTabWidget.TabShape.Rounded)
        self.web_tabs.tabBar().setUsesScrollButtons(True)
        self.web_tabs.currentChanged.connect(self.update_tab_titles)
        self.web_tabs.currentChanged.connect(self._refresh_tab_manager_if_visible)
        self.web_tabs.tabCloseRequested.connect(self.remove_web_tab)

        self.tab_manager_stack = QStackedWidget()
        self.tab_manager_stack.addWidget(self.web_tabs)
        self.tab_manager = TabManager(self.web_tabs, theme_manager)
        self.tab_manager.tab_selected.connect(self._on_tab_manager_selected)
        self.tab_manager_stack.addWidget(self.tab_manager)

        # Setup History Manager and Browser Controller
        self.browser_controller = BrowserController(self, self.web_tabs)
        self.history_manager = HistoryManager(controller=self.browser_controller)
        self.browser_controller.history = self.history_manager

        # History Manager UI
        self.history_manager_widget = HistoryManagerWidget(self.history_manager, theme_manager)
        self.history_manager_widget.history_entry_selected.connect(self._on_history_entry_selected)

        # Outer stack: index 0 = tab_manager_stack, index 1 = history_manager_widget
        self.history_manager_stack = QStackedWidget()
        self.history_manager_stack.addWidget(self.tab_manager_stack)
        self.history_manager_stack.addWidget(self.history_manager_widget)
        self.middle_layout.addWidget(self.history_manager_stack, 1)

        # Controls layout
        self.focus_mode = False
        self.top_navbar = NavBarManager(self.browser_controller, theme_manager)
        self.layout.addWidget(self.top_navbar, 0, 0)

        self.bottom_navbar = NavBarManager(self.browser_controller, theme_manager)
        self.layout.addWidget(self.bottom_navbar, 3, 0)

        nav_elements = current_settings.get("navigation_ui_elements")

        if isinstance(nav_elements, dict):
            top_nav_layout = nav_elements.get("top", [])
            bottom_nav_layout = nav_elements.get("bottom", [])

            self.top_navbar.rebuild_navbar(top_nav_layout)
            self.bottom_navbar.rebuild_navbar(bottom_nav_layout)

            if top_nav_layout == []:
                self.top_navbar.setVisible(False)
            
            else:
                self.top_navbar.setVisible(True)

            if bottom_nav_layout == []:
                self.bottom_navbar.setVisible(False)
            
            else:
                self.bottom_navbar.setVisible(True)

        else:
            top_nav_layout = nav_elements or []

            self.top_navbar.rebuild_navbar(top_nav_layout)
            self.bottom_navbar.rebuild_navbar([])

            if top_nav_layout == []:
                self.top_navbar.setVisible(False)
            
            else:
                self.top_navbar.setVisible(True)

            self.bottom_navbar.setVisible(False)

        self.download_manager = DownloadManager()
        self._update_download_button_visibility()
        self.download_menu = DownloadMenu()
        self.download_manager.download_added.connect(lambda download: self.download_menu.add_download(
            download=download
        ))
        self.download_manager.download_added.connect(self._on_download_added)
        self.download_menu.signals.downloads_dialog_opened.connect(self.show_downloads_dialog)
    
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
        self.reloadPageAction.setText(self.tr("Reload current tab"))
        self.toggleFloatingBarAction.setText(self.tr("Toggle address bar"))

        # View menu
        self.toggleSidebarAction.setText(self.tr("Toggle extension sidebar"))
        self.toggleFocusModeAction.setText(self.tr("Toggle focus mode"))
        self.toggleTabManagerAction.setText(self.tr("Toggle tab manager"))
        self.toggleHistoryManagerAction.setText(self.tr("Toggle history manager"))
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
        self.extension_sidebar = Extension_Sidebar(self,
                                                   extension_manager=extension_manager,
                                                   theme_manager=theme_manager,
                                                   ai_enabled=current_settings["ai_summarization_enabled"])
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
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.floating_address_bar.isVisible():
            self.floating_address_bar.show_bar()

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
    
    def create_new_tab(self, url=None):
        # Web Engine
        web_tab = BetterWebEngine(self, current_settings)
        web_tab.setPage(QWebEnginePage(self.profile, web_tab))
        web_tab.init_engine()

        # Setup localstorage for the new tab
        web_tab.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        
        if url:
            web_tab.setUrl(QUrl(url))
        
        web_tab.loadFinished.connect(self.update_tab_titles)
        web_tab.loadFinished.connect(web_tab.page_load_finished)
        web_tab.loadStarted.connect(self.update_tab_titles)
        # web_tab.loadStarted.connect(self.player.play)
        web_tab.iconChanged.connect(self.update_tab_titles)
        web_tab.signals.sum_selected_with_ai.connect(self.summarize_selected_with_ai)
        web_tab.signals.sum_page_with_ai.connect(self.summarize_current_page_ai)

        self.web_tabs.addTab(web_tab, None)
        self.web_tabs.setCurrentIndex(self.web_tabs.count() - 1)
        self.update_tab_titles()
    
    def remove_web_tab(self, index):
        if index >= 0 and self.web_tabs.count() > 1:
            widget = self.web_tabs.widget(index)
            self.web_tabs.removeTab(index)
            widget.deleteLater()
            self.update_tab_titles()
            self._refresh_tab_manager_if_visible()
    
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

    # Tab Manager
    def _refresh_tab_manager_if_visible(self):
        if self.history_manager_stack.currentIndex() == 0 and self.tab_manager_stack.currentIndex() == 1:
            self.tab_manager.populate()

    def _on_tab_manager_selected(self, index):
        self.web_tabs.setCurrentIndex(index)
        self.tab_manager_stack.setCurrentIndex(0)

    def toggle_tab_manager(self):
        if self.history_manager_stack.currentIndex() == 1:
            self.history_manager_stack.setCurrentIndex(0)

        if self.tab_manager_stack.currentIndex() == 0:
            self.tab_manager.populate()
            self.tab_manager.search_bar.setFocus()
            self.tab_manager_stack.setCurrentIndex(1)
        else:
            self.tab_manager_stack.setCurrentIndex(0)

    # History Manager
    def _on_history_entry_selected(self, url):
        self.web_tabs.currentWidget().setUrl(QUrl(url))
        self.history_manager_stack.setCurrentIndex(0)

    def toggle_history_manager(self):
        if self.history_manager_stack.currentIndex() == 0:
            self.history_manager_widget.populate()
            self.history_manager_widget.search_bar.setFocus()
            self.history_manager_stack.setCurrentIndex(1)
        else:
            self.history_manager_stack.setCurrentIndex(0)

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
                warning_dlg.setText(self.tr('Do you really want to download') + ' "' + download.suggestedFileName() + '"?')
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
        self.extension_sidebar.load_extensions(ai_extensions_enabled=current_settings["ai_summarization_enabled"])
        
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
                print(self.tr('Extension updates: ') + str(updateable_extensions))
            
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
    
    # Website navigation
    def request_back_page(self):
        self.web_tabs.currentWidget().history().back()
        self.update_tab_titles()

    def request_next_page(self):
        self.web_tabs.currentWidget().history().forward()
        self.update_tab_titles()

    def request_reload_page(self):
        self.web_tabs.currentWidget().reload_page()

    # Scaling
    def request_scale_page_up(self):
        self.web_tabs.currentWidget().scale_page_up()
    
    def request_scale_page_down(self):
        self.web_tabs.currentWidget().scale_page_down()
    
    def request_scale_page_reset(self):
        self.web_tabs.currentWidget().scale_page_reset()
    
    # Misc
    def toggle_focus_mode(self):
        self.focus_mode = not self.focus_mode

        if self.focus_mode:
            self.top_navbar.setVisible(False)
            self.bottom_navbar.setVisible(False)
        
        else:
            if self.top_navbar.controls_layout.count() != 0:
                self.top_navbar.setVisible(True)

            if self.bottom_navbar.controls_layout.count() != 0:
                self.bottom_navbar.setVisible(True)
    
    def toggle_floating_address_bar(self):
        if self.floating_address_bar.isVisible():
            self.floating_address_bar.hide_bar()
        else:
            self.floating_address_bar.show_bar()
    
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

            if settings["language"] != current_settings["language"]:
                self.load_language(NAME_TO_LANGUAGE[settings["language"]])

            self.update_web_engine()
            nav_elements = settings["navigation_ui_elements"]

            if isinstance(nav_elements, dict):
                top_nav_layout = nav_elements.get("top", [])
                bottom_nav_layout = nav_elements.get("bottom", [])

                self.top_navbar.rebuild_navbar(top_nav_layout)
                self.bottom_navbar.rebuild_navbar(bottom_nav_layout)

                if not self.focus_mode:
                    if top_nav_layout == []:
                        self.top_navbar.setVisible(False)
                    
                    else:
                        self.top_navbar.setVisible(True)

                    if bottom_nav_layout == []:
                        self.bottom_navbar.setVisible(False)
                    
                    else:
                        self.bottom_navbar.setVisible(True)

            else:
                top_nav_layout = nav_elements or []
                
                self.top_navbar.rebuild_navbar(top_nav_layout)
                self.bottom_navbar.rebuild_navbar([])

                if not self.focus_mode:
                    if top_nav_layout == []:
                        self.top_navbar.setVisible(False)
                    
                    else:
                        self.top_navbar.setVisible(True)

                    self.bottom_navbar.setVisible(False)
            
            self._update_download_button_visibility()
            self.browser_controller._on_tab_changed()

            if settings["ai_summarization_enabled"] != current_settings["ai_summarization_enabled"]:
                self.extension_sidebar.load_extensions(ai_extensions_enabled=settings["ai_summarization_enabled"])

            theme_manager.set_accent_color(settings["accent_color"])

            updated_settings = {
                "start_page_url": settings["start_page_url"],
                "search_engine": settings["search_engine"],
                "theme": theme_manager.available_themes[settings["theme_index"]],
                "accent_color": settings["accent_color"],
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
        self.timer = QTimer()

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
    
    def toggle_tab_manager(self):
        self.window.toggle_tab_manager()

    def toggle_history_manager(self):
        self.window.toggle_history_manager()

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
    window = BrowserWindow()
    window.show()
    sys.exit(app.exec())