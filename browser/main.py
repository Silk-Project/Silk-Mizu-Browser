import sys
import os
import json
import re
import copy
import datetime
from dataclasses import dataclass, field
import requests
import subprocess
import io
import shutil
import zipfile
import importlib.util
from pathlib import Path
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
    QWidgetAction,
    QScrollArea,
    QStackedWidget,
    QFrame,
    QColorDialog,
)
from PySide6.QtCore import Qt, QUrl, QSize, Slot, Signal, QThreadPool, QRunnable, QObject, QTranslator, QStandardPaths, QTimer
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineSettings, QWebEngineDownloadRequest, QWebEngineProfile, QWebEnginePage
from PySide6.QtGui import QPixmap, QAction, QKeySequence, QIcon, QColor
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
STORAGE_PATH = os.path.join(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation), "Silk-Mizu-Browser")
EXTENSIONS_PATH = os.path.join(SCRIPT_DIR, "extensions")
EXTENSIONS_SETTINGS_PATH = os.path.join(SCRIPT_DIR, "config", "extensions.json")
ADDITIONAL_QSS_PATH = os.path.join(SCRIPT_DIR, "assets", "style.qss")
SUM_AI_MODEL = {"name":"lfm2.5-thinking:1.2b", "size":"700MB"}
VERSION_NUMBER = "0.3.11 Public Preview"
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
    "accent_color":"#8370EB",
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

def check_dependencies(deps_list):
    missing = []
    for dep in deps_list:
        if importlib.util.find_spec(dep) is None:
            missing.append(dep)
    return missing

# Load all configs
load_config(EXTENSIONS_SETTINGS_PATH, extensions_settings, default_extension_settings)
load_config(BOOKMARKS_PATH, current_bookmarks, default_bookmarks)
load_config(CONFIG_PATH, current_settings, default_settings)

class ThemeManager():
    def __init__(self, applic, theme="dark"):
        self.applic = applic
        self.theme = theme
        self.custom_colors = {
            "primary": QColor(current_settings["accent_color"]).name() if current_settings["accent_color"] else QColor("#8370EB")
        }
        self.available_themes = [
            "light",
            "dark",
            "auto",
            "legacy"
        ]
        self.load_theme(theme)
    
    def load_theme(self, theme_input):
        theme_input = theme_input.strip().lower()

        if theme_input in self.available_themes:
            if theme_input != "auto" and theme_input != "legacy":
                qdarktheme.setup_theme(theme_input, custom_colors=self.custom_colors, additional_qss=additional_qss)

            elif theme_input == "auto":
                qdarktheme.setup_theme("auto", custom_colors=self.custom_colors, additional_qss=additional_qss)
            
            elif theme_input == "legacy":
                self.applic.setStyleSheet(additional_qss)
            
            self.theme = theme_input

        else:
            print("Theme not found")
    
    def load_theme_from_index(self, index):
        theme = self.available_themes[index]
        self.load_theme(theme)

    def set_accent_color(self, color: QColor):
        if self.theme == "legacy":
            return

        self.custom_colors["primary"] = color
        qdarktheme.setup_theme(self.theme, custom_colors=self.custom_colors, additional_qss=additional_qss)
    
    def get_plain_theme(self):
        if self.theme != "auto" and self.theme != "legacy":
            return self.theme
        
        else:
            system_theme = "dark" if darkdetect.isDark() else "light"
            return system_theme
    
    def get_contrast_color_from_theme(self):
        if self.get_plain_theme() == "light":
            return "black"
        else:
            return "white"

class ExtensionManager():
    def __init__(self):
        self.installed_extensions_data = []

    def update_extension_list(self):
        self.installed_extensions_data = []

        with os.scandir(EXTENSIONS_PATH) as d:
            for el in d:
                extension_index_path = os.path.join(EXTENSIONS_PATH, el.name, "index.json")

                if el.is_dir() and os.path.exists(extension_index_path):

                    with open(extension_index_path, "r") as f:
                        extension_index = json.load(f)
                    
                    current_ext = ExtensionMetadata(**extension_index)
                    self.installed_extensions_data.append(current_ext)
    
    def get_installed(self):
        return self.installed_extensions_data

@dataclass
class ExtensionMetadata:
    app_id: str
    name: str
    author: str
    description: str
    version: str
    script_path: str = None
    icon_path: str = ""

    # Installables
    dependencies: list[str] = field(default_factory=list)
    download_path: str = None
    index_source: str = None

class ExtensionItemWidget(QFrame):
    refresh_local_extensions = Signal()

    def __init__(self, metadata: ExtensionMetadata, installable=False, parent=None):
        super().__init__(parent)
        self.setStyleSheet("ExtensionItemWidget { border: 1px solid #414242; border-radius: 3px; }")
        self.installable = installable
        self.metadata = metadata
        
        self.layout = QHBoxLayout(self)
        details_layout = QVBoxLayout()
        title_layout = QHBoxLayout()

        title_layout.setSpacing(1)
        title_layout.setContentsMargins(0, 0, 0, 0)

        details_layout.addLayout(title_layout)

        # Icon (if available)
        self.extension_icon_path = os.path.join(EXTENSIONS_PATH, self.metadata.app_id, self.metadata.icon_path)

        if os.path.exists(self.extension_icon_path) and self.metadata.icon_path != "":
            icon_label = QLabel()
            icon_label.setStyleSheet("border: none")
            icon_pixmap = QPixmap(self.extension_icon_path)

            icon_label.setPixmap(icon_pixmap)
            icon_label.setScaledContents(True)
            icon_label.setFixedSize(36, 36)

            self.layout.addWidget(icon_label, alignment=Qt.AlignmentFlag.AlignLeft)
                
        self.layout.addLayout(details_layout)

        # Extension details
        extension_title = QLabel(self.metadata.name)
        extension_title.setStyleSheet("font-size: 14px; font-weight: bold; border: none;")
        extension_title.setWordWrap(True)
        extension_title.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        title_layout.addWidget(extension_title, alignment=Qt.AlignmentFlag.AlignLeft)

        extension_author = QLabel(f"{self.tr("by")} {self.metadata.author}")
        extension_author.setStyleSheet("font-size: 10px; color: #808080; border: none;")
        title_layout.addWidget(extension_author, alignment=Qt.AlignmentFlag.AlignLeft)

        title_layout.addStretch()

        if self.installable:
            required_dependencies = check_dependencies(self.metadata.dependencies)

            if len(required_dependencies) > 0:
                extension_deps = QLabel(f"{self.tr("Required libraries: ")}{", ".join(required_dependencies)}")
                extension_deps.setWordWrap(True)
                extension_deps.setStyleSheet("color: #808080; border: none;")
                extension_deps.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
                details_layout.addWidget(extension_deps)
                    
        extension_description = QLabel(self.metadata.description)
        extension_description.setWordWrap(True)
        extension_description.setStyleSheet("color: #808080; border: none;")
        extension_description.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        details_layout.addWidget(extension_description)

        extension_info_btn = QPushButton()
        extension_info_btn.setIcon(qta.icon("fa6s.circle-info"))
        extension_info_btn.setStyleSheet("padding: 8px;")
        extension_info_btn.clicked.connect(self.show_extension_info)
        self.layout.addWidget(extension_info_btn, alignment=Qt.AlignmentFlag.AlignRight)

        # Extension Controls
        if not self.installable:
            self.delete_extension_btn = QPushButton()
            self.delete_extension_btn.setIcon(qta.icon("fa6s.trash"))
            self.delete_extension_btn.setStyleSheet("padding: 8px;")
            self.delete_extension_btn.clicked.connect(self.delete_extension)
            self.layout.addWidget(self.delete_extension_btn, alignment=Qt.AlignmentFlag.AlignRight)
        
        else:
            self.download_extension_btn = QPushButton()
            self.download_extension_btn.setIcon(qta.icon("fa6s.download"))
            self.download_extension_btn.setStyleSheet("padding: 8px;")
            self.download_extension_btn.clicked.connect(self.install_extension)
            self.layout.addWidget(self.download_extension_btn, alignment=Qt.AlignmentFlag.AlignRight)

            self.check_icons_timer = QTimer()
            self.check_icons_timer.setInterval(1000)
            self.check_icons_timer.timeout.connect(self.switch_to_download_icon)
    
    def show_extension_info(self):
        dlg = QDialog(self)
        dlg.setWindowTitle(f"{self.tr("About")} {self.metadata.name}")
        dlg_layout = QVBoxLayout()

        dlg_layout.addStretch()
        
        if os.path.exists(self.extension_icon_path) and self.metadata.icon_path != "":
            dlg.setFixedSize(240, 360)

            logoLabel = QLabel(self)
            logoLabel.setFixedSize(128, 128)
            logoLabel.setScaledContents(True)
            logoLabel.setPixmap(QPixmap(self.extension_icon_path))
            dlg_layout.addWidget(logoLabel, alignment=Qt.AlignmentFlag.AlignCenter)
        
        else:
            dlg.setFixedSize(240, 300)

        about_title = QLabel(self.metadata.name)
        about_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        about_title.setStyleSheet("font-size: 20px; font-weight: bold;")
        dlg_layout.addWidget(about_title)

        about_description = QLabel(self.metadata.description)
        about_description.setWordWrap(True)
        about_description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dlg_layout.addWidget(about_description)

        about_label = QLabel(f"{self.tr("Version: ")}{self.metadata.version}\n{self.tr("by")} {self.metadata.author}")
        about_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dlg_layout.addWidget(about_label)

        if self.installable:
            source_label = QTextEdit(f"{self.tr("Source: ")}{self.metadata.index_source}")
            source_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            source_label.setFixedHeight(90)
            source_label.setReadOnly(True)
            source_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            dlg_layout.addWidget(source_label)

        if os.path.exists(self.extension_icon_path) and self.metadata.icon_path != "":
            dlg_layout.addStretch()

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        button_box.setContentsMargins(0, 8, 0, 8)
        button_box.accepted.connect(dlg.accept)
        dlg_layout.addWidget(button_box, alignment=Qt.AlignmentFlag.AlignCenter)
        
        dlg.setLayout(dlg_layout)
        
        dlg.exec()
    
    def install_extension(self):
        self.download_extension_btn.setEnabled(False)
        animation = qta.Spin(self.download_extension_btn)
        self.download_extension_btn.setIcon(qta.icon("mdi.loading", animation=animation))

        warning_dlg = QMessageBox(self)
        warning_dlg.setWindowTitle(self.tr("Download Request"))
        warning_dlg.setText(f"{self.tr("Do you really want to download")} \"{self.metadata.name}\"?")
        warning_dlg.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
        warning_dlg.setIcon(QMessageBox.Icon.Warning)

        if warning_dlg.exec() == QMessageBox.StandardButton.Ok:
            install_dialog = ExtensionInstallDialog(self.metadata, self)
            
            if install_dialog.exec():
                self.download_extension_btn.setEnabled(True)
                self.download_extension_btn.setIcon(qta.icon("fa6s.check"))

            self.refresh_local_extensions.emit()
            window.extension_sidebar.load_extensions()

            self.check_icons_timer.start()

            return
        
        self.download_extension_btn.setEnabled(True)
        self.download_extension_btn.setIcon(qta.icon("fa6s.download"))
    
    def switch_to_download_icon(self):
        self.download_extension_btn.setIcon(qta.icon("fa6s.download"))
        self.check_icons_timer.stop()
    
    def delete_extension(self):
        warning_dlg = QMessageBox(self)
        warning_dlg.setWindowTitle(self.tr("Download Request"))
        warning_dlg.setText(f"{self.tr("Do you really want to delete")} \"{self.metadata.name}\"?")
        warning_dlg.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
        warning_dlg.setIcon(QMessageBox.Icon.Warning)

        if warning_dlg.exec() == QMessageBox.StandardButton.Ok:
            extension_path = os.path.join(EXTENSIONS_PATH, self.metadata.app_id)

            if os.path.exists(extension_path):
                try:
                    shutil.rmtree(extension_path)
                    self.refresh_local_extensions.emit()
                
                except Exception as e:
                    print(e)

class ExtensionInstallDialog(QDialog):
    def __init__(self, metadata: ExtensionMetadata, parent = ...):
        super().__init__(parent)

        self.setFixedSize(300, 200)

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.metadata = metadata

        self.init_ui()
        self.install_dependencies()
    
    def init_ui(self):
        self.title_label = QLabel("Install Extension")
        self.title_label.setStyleSheet("font-size: 20px; font-weight: bold; padding: 20px;")
        self.layout.addWidget(self.title_label, alignment=Qt.AlignmentFlag.AlignCenter)

        self.install_progress = QProgressBar()
        self.install_progress.setMaximum(len(self.metadata.dependencies))
        self.install_progress.setValue(0)
        self.layout.addWidget(self.install_progress)

        self.status_label = QLabel("Preparing Installation...")
        self.layout.addWidget(self.status_label, alignment=Qt.AlignmentFlag.AlignLeft)

        self.layout.addStretch()
    
    def install_dependencies(self):
        # Install depencies (if needed)
        required_dependencies = check_dependencies(self.metadata.dependencies)

        if len(required_dependencies) > 0:
            self.threadpool = QThreadPool()
            worker = DependencyWorker(required_dependencies=required_dependencies)
            worker.signals.dependencies_installed.connect(self.install_extension)
            worker.signals.dependency_install_started.connect(lambda dep: self.show_status(f"Installing dependencies: {dep}"))
            worker.signals.dependency_installed.connect(self.update_dep_progress)
            self.threadpool.start(worker)
        
        else:
            self.install_extension()
    
    def install_extension(self):
        # Download extension zip
        self.install_progress.setMaximum(0)
        self.show_status(f"Downloading extension: {self.metadata.name}")

        self.threadpool = QThreadPool()
        fetcher = ZipInstaller(self.metadata.download_path, self.metadata.app_id)
        fetcher.singals.zip_fetched.connect(lambda: self.show_status(f"Extracting extension: {self.metadata.name}"))
        fetcher.singals.zip_fetch_failed.connect(self.install_failed)
        fetcher.singals.zip_extracted.connect(self.finish_installation)
        self.threadpool.start(fetcher)
    
    def finish_installation(self):
        self.show_status(f"Extension successfully installed: {self.metadata.name}")
        self.accept()
    
    def install_failed(self, message):
        QMessageBox.critical(self, self.tr("Installation Failed"), f"{self.tr("Failed to install extension: ")}{message}")
        self.reject()
    
    def show_status(self, string):
        self.status_label.setText(string)
    
    def update_dep_progress(self):
        current_progress = self.install_progress.value()
        self.install_progress.setValue(current_progress + 1)

class ZipInstallerObject(QObject):
    zip_fetched = Signal()
    zip_fetch_failed = Signal(str)
    zip_extracted = Signal()

class ZipInstaller(QRunnable):
    def __init__(self, url, app_id):
        super().__init__()

        self.app_id = app_id
        self.download_url = url
        self.singals = ZipInstallerObject()

    @Slot()
    def run(self):
        install_dir = os.path.join(EXTENSIONS_PATH, self.app_id)

        try:
            response = requests.get(self.download_url, timeout=10)

            if response.status_code == 200:
                self.singals.zip_fetched.emit()
                
                with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                    if os.path.exists(install_dir):
                        shutil.rmtree(install_dir)
            
                    os.makedirs(install_dir, exist_ok=True)
                    z.extractall(install_dir)
            
                    self.singals.zip_extracted.emit()
        
        except Exception as e:
            self.singals.zip_fetch_failed.emit(str(e))

class DependencyWorkerSignals(QObject):
    dependencies_installed = Signal()
    dependency_install_started = Signal(str)
    dependency_installed = Signal()
    task_failed = Signal(str)

class DependencyWorker(QRunnable):
    def __init__(self, required_dependencies: list):
        super().__init__()

        self.required_dependencies = required_dependencies
        self.signals = DependencyWorkerSignals()

    @Slot()
    def run(self):
        for dep in self.required_dependencies:
            self.signals.dependency_install_started.emit(dep)
            # print(f"Installing: {dep}")
            subprocess.check_call([sys.executable, "-m", "pip", "install", dep])
            self.signals.dependency_installed.emit()
        
        self.signals.dependencies_installed.emit()

class WebExtensionFetcherSignals(QObject):
    response_received = Signal(list)
    task_failed = Signal(str)

class WebExtensionFetcher(QRunnable):
    def __init__(self, index_urls):
        super().__init__()

        self.index_urls = index_urls
        self.jsons = []
        self.signals = WebExtensionFetcherSignals()

    @Slot()
    def run(self):
        try:
            for url in self.index_urls:
                response = requests.get(url)

                try:
                    data = response.json()
                    extensions = data["extensions"]

                    for e in extensions:
                        e["index_source"] = url

                    self.jsons.extend(extensions)

                except Exception as e:
                    self.task_failed.emit(str(e))

            self.signals.response_received.emit(self.jsons)

        except Exception as e:
            self.signals.task_failed.emit(str(e))

class WebExtensionsDialog(QDialog):
    def __init__(self, parent = ...):
        super().__init__(parent)

        self.setWindowTitle(self.tr("Browser Extensions"))
        self.setFixedSize(624, 468)

        self.installed_order_asc = True
        self.store_order_asc = True
        self.loaded_store_extensions = []

        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)

        title_label = QLabel(self.tr("Browser Extensions"))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; padding: 20px;")
        layout.addWidget(title_label)

        extension_tabs = QTabWidget()

        # Installed tab
        installed_tab = QScrollArea()
        installed_tab.setProperty("class", "noborder")

        self.installed_widgets_widget = QWidget()
        self.installed_widgets_main_layout = QVBoxLayout()
        self.installed_widgets_controls = QHBoxLayout()
        self.installed_widgets_repeatable_layout = QVBoxLayout()

        self.installed_widgets_main_layout.addLayout(self.installed_widgets_controls)
        self.installed_widgets_main_layout.addLayout(self.installed_widgets_repeatable_layout)

        self.installed_widgets_main_layout.addStretch()

        installed_tab.setWidget(self.installed_widgets_widget)

        self.installed_widgets_widget.setLayout(self.installed_widgets_main_layout)

        # Control Buttons
        self.install_tab_refresh_btn = QPushButton(self.tr("Refresh"))
        self.install_tab_refresh_btn.setIcon(qta.icon("ei.refresh"))
        self.install_tab_refresh_btn.setStyleSheet("border: 1px solid #414242; border-radius: 3px; padding: 8px;")
        self.install_tab_refresh_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.install_tab_refresh_btn.clicked.connect(self.load_installed_extensions)
        self.installed_widgets_controls.addWidget(self.install_tab_refresh_btn)
        
        self.installed_order_btn = QPushButton()
        self.installed_order_btn.setStyleSheet("border: 1px solid #414242; border-radius: 3px; padding: 8px;")
        self.installed_order_btn.setIcon(qta.icon("fa5s.sort-amount-down-alt"))
        self.installed_order_btn.clicked.connect(self.toggle_installed_order)
        self.installed_widgets_controls.addWidget(self.installed_order_btn)

        self.install_tab_sort_combobox = QComboBox()
        self.install_tab_sort_combobox.addItems([self.tr("Sort by name"), self.tr("Sort by developer")])
        self.install_tab_sort_combobox.setStyleSheet("border-radius: 3px;")
        self.install_tab_sort_combobox.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.install_tab_sort_combobox.currentTextChanged.connect(self.load_installed_extensions)
        self.installed_widgets_controls.addWidget(self.install_tab_sort_combobox)

        self.installed_widgets_controls.addStretch()

        self.load_installed_extensions()

        installed_tab.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        installed_tab.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        installed_tab.setWidgetResizable(True)

        # Store tab
        store_tab = QScrollArea()
        store_tab.setProperty("class", "noborder")

        self.store_widgets_widget = QWidget()
        self.store_widgets_main_layout = QVBoxLayout()
        self.store_widgets_controls = QHBoxLayout()
        self.store_widgets_repeatable_layout = QVBoxLayout()

        self.store_widgets_main_layout.addLayout(self.store_widgets_controls)
        self.store_widgets_main_layout.addLayout(self.store_widgets_repeatable_layout)

        self.store_widgets_main_layout.addStretch()

        store_tab.setWidget(self.store_widgets_widget)

        self.store_widgets_widget.setLayout(self.store_widgets_main_layout)

        # Control Buttons
        self.store_tab_refresh_btn = QPushButton(self.tr("Refresh"))
        self.store_tab_refresh_btn.setIcon(qta.icon("ei.refresh"))
        self.store_tab_refresh_btn.setStyleSheet("border: 1px solid #414242; border-radius: 3px; padding: 8px;")
        self.store_tab_refresh_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.store_tab_refresh_btn.clicked.connect(self.load_store_extensions)
        self.store_widgets_controls.addWidget(self.store_tab_refresh_btn)

        self.store_repository_btn = QPushButton(self.tr("Repositories"))
        self.store_repository_btn.setIcon(qta.icon("mdi.source-repository"))
        self.store_repository_btn.setStyleSheet("border: 1px solid #414242; border-radius: 3px; padding: 8px;")
        self.store_repository_btn.setToolTip(f"{self.tr("Repositories: ")}{str(len(extensions_settings["index_urls"]))}")
        self.store_repository_btn.clicked.connect(self.change_repo_url)
        self.store_widgets_controls.addWidget(self.store_repository_btn)
        
        self.store_order_btn = QPushButton()
        self.store_order_btn.setStyleSheet("border: 1px solid #414242; border-radius: 3px; padding: 8px;")
        self.store_order_btn.setIcon(qta.icon("fa5s.sort-amount-down-alt"))
        self.store_order_btn.clicked.connect(self.toggle_store_order)
        self.store_widgets_controls.addWidget(self.store_order_btn)

        self.store_tab_sort_combobox = QComboBox()
        self.store_tab_sort_combobox.addItems([self.tr("Sort by name"), self.tr("Sort by developer")])
        self.store_tab_sort_combobox.setStyleSheet("border-radius: 3px;")
        self.store_tab_sort_combobox.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.store_tab_sort_combobox.currentTextChanged.connect(lambda _: self.show_store_extensions())
        self.store_widgets_controls.addWidget(self.store_tab_sort_combobox)

        self.store_widgets_controls.addStretch()

        self.load_store_extensions()

        store_tab.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        store_tab.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        store_tab.setWidgetResizable(True)
        
        # Tab arrangement
        extension_tabs.addTab(installed_tab, self.tr("Installed"))
        extension_tabs.addTab(store_tab, self.tr("Store"))
        layout.addWidget(extension_tabs)

        # Ok...
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)
    
    def load_installed_extensions(self):
        self.clear_layout(self.installed_widgets_repeatable_layout)
        extension_manager.update_extension_list()
        
        if len(extension_manager.get_installed()) == 0:
            self.installed_order_btn.setEnabled(False)
            self.install_tab_sort_combobox.setEnabled(False)

            self.installed_widgets_repeatable_layout.addStretch()

            info_label = QLabel(self.tr("No extensions found.\nWhy not try to install some?"))
            info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            info_label.setStyleSheet("color: grey;")
            self.installed_widgets_repeatable_layout.addWidget(info_label)

            self.installed_widgets_repeatable_layout.addStretch()

            return

        final_extension_data = extension_manager.get_installed()

        # Sort extensions
        if self.install_tab_sort_combobox.currentIndex() == 0:
            # Sort by extension name
            final_extension_data.sort(key=lambda e: e.name, reverse=not self.installed_order_asc)
            self.installed_order_btn.setEnabled(True)
        
        elif self.install_tab_sort_combobox.currentIndex() == 1:
            # Sort by developer name
            final_extension_data.sort(key=lambda e: e.author, reverse=not self.installed_order_asc)
            self.installed_order_btn.setEnabled(True)
        
        else:
            self.installed_order_btn.setEnabled(False)

        
        for el in final_extension_data:
            item = ExtensionItemWidget(el, False, self)
            item.refresh_local_extensions.connect(self.load_installed_extensions)
            self.installed_widgets_repeatable_layout.addWidget(item)

    def load_store_extensions(self):
        self.clear_layout(self.store_widgets_repeatable_layout)

        self.store_widgets_repeatable_layout.addStretch()

        self.load_label = QLabel(self.tr("Loading extensions..."))
        self.load_label.setStyleSheet("color: grey;")
        self.load_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.store_widgets_repeatable_layout.addWidget(self.load_label)

        self.throbber = qta.IconWidget()
        self.throbber.setAlignment(Qt.AlignmentFlag.AlignCenter)
        animation = qta.Spin(self.throbber)
        spin_icon = qta.icon('mdi.loading', color="grey", animation=animation)
        self.throbber.setIcon(spin_icon)
        self.store_widgets_repeatable_layout.addWidget(self.throbber)

        self.store_widgets_repeatable_layout.addStretch()

        self.threadpool = QThreadPool()
        fetcher = WebExtensionFetcher(extensions_settings["index_urls"])
        fetcher.signals.task_failed.connect(self.store_load_failed)
        fetcher.signals.response_received.connect(self.show_store_extensions)
        self.threadpool.start(fetcher)

    def store_load_failed(self, error):
        self.clear_layout(self.store_widgets_repeatable_layout)

        self.store_widgets_repeatable_layout.addStretch()

        info_label = QLabel(f"{self.tr("Error when trying to load store items: ")}{error}")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setStyleSheet("color: grey;")
        self.store_widgets_repeatable_layout.addWidget(info_label)

        self.store_widgets_repeatable_layout.addStretch()
    
    def show_store_extensions(self, data=[]):
        self.clear_layout(self.store_widgets_repeatable_layout)

        if len(data) == 0 and len(self.loaded_store_extensions) == 0:
            self.store_widgets_repeatable_layout.addStretch()

            info_label = QLabel(self.tr("No extensions found."))
            info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            info_label.setStyleSheet("color: grey;")
            self.installed_widgets_repeatable_layout.addWidget(info_label)

            self.installed_widgets_repeatable_layout.addStretch()

            return
        
        elif len(data) > 0:
            self.loaded_store_extensions = data

        # Copy loaded extensions to a temporary variable
        final_extension_data = self.loaded_store_extensions
        
        # Sort Extensions
        if self.store_tab_sort_combobox.currentIndex() == 0:
            # Sort by extension name
            final_extension_data.sort(key=lambda e: e["name"], reverse=not self.store_order_asc)
            self.store_order_btn.setEnabled(True)
        
        elif self.store_tab_sort_combobox.currentIndex() == 1:
            # Sort by developer name
            final_extension_data.sort(key=lambda e: e["author"], reverse=not self.store_order_asc)
            self.store_order_btn.setEnabled(True)
        
        else:
            self.store_order_btn.setEnabled(False)

        for el in final_extension_data:
            metadata = ExtensionMetadata(**el)
            item = ExtensionItemWidget(metadata, True, self)
            item.refresh_local_extensions.connect(self.load_installed_extensions)
            self.store_widgets_repeatable_layout.addWidget(item)
    
    def change_repo_url(self):
        repo_dlg = ManageExtensionRepositories(self, extensions_settings["index_urls"])

        if repo_dlg.exec():
            extensions_settings["index_urls"] = repo_dlg.temp_repos

            with open(EXTENSIONS_SETTINGS_PATH, "w") as f:
                json.dump(extensions_settings, f, indent=4)
            
            self.load_store_extensions()

    def toggle_installed_order(self):
        self.installed_order_asc = not self.installed_order_asc

        if self.installed_order_asc:
            self.installed_order_btn.setIcon(qta.icon("fa5s.sort-amount-down-alt"))
        else:
            self.installed_order_btn.setIcon(qta.icon("fa5s.sort-amount-up-alt"))
        
        self.load_installed_extensions()
    
    def toggle_store_order(self):
        self.store_order_asc = not self.store_order_asc

        if self.store_order_asc:
            self.store_order_btn.setIcon(qta.icon("fa5s.sort-amount-down-alt"))
        else:
            self.store_order_btn.setIcon(qta.icon("fa5s.sort-amount-up-alt"))
        
        self.show_store_extensions([])
    
    def clear_layout(self, layout):
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
                else:
                    self.clear_layout(item.layout())


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
        self.extension_content = QStackedWidget()
        
        self.extension_content.setStyleSheet("border-radius: 3px;")
        self.extension_content.hide()

        self.sidebar_layout.addLayout(self.extension_bar_layout)
        self.sidebar_layout.addWidget(self.extension_content)

    def load_extensions(self):
        self.clear_layout(self.extension_bar_layout)

        while self.extension_content.count() > 0:
            widget = self.extension_content.widget(0)
            self.extension_content.removeWidget(widget)
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
            self.extension_content.addWidget(self.ai_sum_ext)

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
                
                self.extension_content.addWidget(plugin_instance)

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
        if id != self.extension_content.currentIndex():
            self.extension_content.setCurrentIndex(id)

            if not self.showing_extension:
                self.showing_extension = True
        else:
            self.showing_extension = not self.showing_extension

        if self.showing_extension:
            self.setFixedWidth(450)
            self.extension_content.show()

        else:
            self.setFixedWidth(50)
            self.extension_content.hide()
    
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

class BetterWebEngineSignals(QObject):
    sum_selected_with_ai = Signal(str)
    sum_page_with_ai = Signal()

class BetterWebEngine(QWebEngineView):
    def __init__(self, parent):
        super().__init__(parent)
        self.page_is_loading = False
        self.signals = BetterWebEngineSignals()
        self.page().setBackgroundColor(QColor("#101011"))
        self.urlChanged.connect(lambda: self.page().setBackgroundColor(QColor("#101011")))

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
        sum_page_with_ai_action.triggered.connect(lambda: self.signals.sum_page_with_ai.emit())

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
        self.page().setBackgroundColor(QColor("#ffffff"))
    
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

class DownloadManager(QObject):
    download_added = Signal(QWebEngineDownloadRequest)

    def __init__(self):
        super().__init__()
        self.downloads = []
    
    def add_download(self, download: QWebEngineDownloadRequest):
        # Download info
        download_filename = download.suggestedFileName()

        if not os.path.exists(DOWNLOAD_PATH):
            os.makedirs(DOWNLOAD_PATH)

        download.setDownloadDirectory(DOWNLOAD_PATH)
        download.setDownloadFileName(download_filename)

        download.accept()
        self.downloads.append(download)
        self.download_added.emit(download)

class DownloadItemWidget(QFrame):
    def __init__(self, download: QWebEngineDownloadRequest, parent=None):
        super().__init__(parent)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.download = download

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.init_ui()
        self.connect_signals()

        # Check if download is already finished
        if self.download.isFinished():
            self.download_finished()
        
        self.update_progress()
    
    def init_ui(self):
        # Download info
        download_filename = self.download.suggestedFileName()

        # Download UI elements
        self.label = QLabel(f"{self.tr("Downloading:")} {download_filename}")
        self.label.setWordWrap(True)
        self.label.setToolTip(download_filename)

        self.progress = QProgressBar()

        self.stop_btn = QPushButton()
        self.stop_btn.setIcon(qta.icon("ei.remove"))
        self.stop_btn.clicked.connect(lambda: self.download.cancel())
        
        self.layout.addWidget(self.label)

        # Bottom layout (progress bar, button)
        bottom_layout = QHBoxLayout()
        self.layout.addLayout(bottom_layout)

        bottom_layout.addWidget(self.progress)
        bottom_layout.addWidget(self.stop_btn)
    
    def connect_signals(self):
        self.download.receivedBytesChanged.connect(self.update_progress)
        self.download.isFinishedChanged.connect(self.download_finished)
    
    def update_progress(self):
        if self.download.totalBytes() > 0:
            percent = int((self.download.receivedBytes() / self.download.totalBytes()) * 100)
            self.progress.setValue(percent)
    
    def download_finished(self):
        download_filename = self.download.suggestedFileName()
        state = self.download.state()
        self.stop_btn.setEnabled(False)
    
        if state == QWebEngineDownloadRequest.DownloadState.DownloadCompleted:
            self.progress.setValue(100)
            self.label.setText(f"{self.tr("Finished:")} {download_filename}")
        
        elif state == QWebEngineDownloadRequest.DownloadState.DownloadCancelled:
            self.label.setText(f"{self.tr("Canceled:")} {download_filename}")
            self.progress.setEnabled(False)
        
        elif state == QWebEngineDownloadRequest.DownloadState.DownloadInterrupted:
            self.label.setText(f"{self.tr("Error:")} {download_filename}")
            self.progress.setStyleSheet("QProgressBar::chunk { background-color: red; }")

class DownloadManagerWidget(QDialog):
    def __init__(self, downloads):
        super().__init__()

        self.setWindowTitle(self.tr("Manage Downloads"))
        self.setFixedSize(624, 468)
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.downloads = downloads

        self.init_ui()
        self.refresh_downloads()
    
    def init_ui(self):
        title_label = QLabel(self.tr("Manage Downloads"))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; padding: 20px;")
        self.layout.addWidget(title_label)

        # Downloads list
        self.downloads_content = QScrollArea()

        self.downloads_widget = QWidget()
        self.downloads_layout = QVBoxLayout()
        self.downloads_controls_layout = QHBoxLayout()
        self.downloads_main_layout = QVBoxLayout()

        self.downloads_layout.addLayout(self.downloads_controls_layout)
        self.downloads_layout.addLayout(self.downloads_main_layout)

        self.downloads_content.setWidget(self.downloads_widget)
        self.downloads_widget.setLayout(self.downloads_layout)
        self.layout.addWidget(self.downloads_content)

        self.downloads_layout.addStretch()

        # Control Buttons
        self.store_tab_refresh_btn = QPushButton(self.tr("Refresh"))
        self.store_tab_refresh_btn.setIcon(qta.icon("ei.refresh"))
        self.store_tab_refresh_btn.setStyleSheet("border: 1px solid #414242; border-radius: 3px; padding: 8px;")
        self.store_tab_refresh_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.store_tab_refresh_btn.clicked.connect(self.refresh_downloads)
        self.downloads_controls_layout.addWidget(self.store_tab_refresh_btn)

        self.downloads_controls_layout.addStretch()

        self.downloads_content.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.downloads_content.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.downloads_content.setWidgetResizable(True)

    def refresh_downloads(self):
        self.clear_layout(self.downloads_main_layout)

        if len(self.downloads) == 0:
            self.downloads_main_layout.addStretch()

            info_label = QLabel(self.tr("No active downloads."))
            info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            info_label.setStyleSheet("color: grey;")
            self.downloads_main_layout.addWidget(info_label)

            self.downloads_main_layout.addStretch()

            return
        
        for download in self.downloads:
            item = DownloadItemWidget(download, self)
            self.downloads_main_layout.addWidget(item)

    def clear_layout(self, layout):
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
                else:
                    self.clear_layout(item.layout())


class DownloadMenu(QMenu):
    def __init__(self):
        super().__init__()
        self.manage_downloads_action = QAction("Manage Downloads")
        self.manage_downloads_action.triggered.connect(self.open_manage_downloads)
        self.addAction(self.manage_downloads_action)

    def add_download(self, download: QWebEngineDownloadRequest):
        # Download info
        download_filename = download.suggestedFileName()
        
        # Create layouts for the menu entry
        layout = QVBoxLayout()
        container = QWidget()

        # Download UI elements
        label = QLabel(f"{self.tr("Downloading:")} {self.shorten_if_needed(download_filename)}")
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

        # Insert the new action at the top of the menu
        self.insertAction(self.actions()[0], widget_action)

        # Remove downloads if download amount exceeds 3
        if len(self.actions()) > 4:
            self.removeAction(self.actions()[3])
        
        # 3. Connect signals to track progress and completion
        download.receivedBytesChanged.connect(
            lambda: self.update_progress(download, progress)
        )
        download.isFinishedChanged.connect(
            lambda: self.download_finished(download, label, progress, stop_btn)
        )

    def update_progress(self, download, progress_bar):
        if download.totalBytes() > 0:
            percent = int((download.receivedBytes() / download.totalBytes()) * 100)
            progress_bar.setValue(percent)
    
    def shorten_if_needed(self, download_name):
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
            label.setText(f"{self.tr("Finished:")} {self.shorten_if_needed(download_filename)}")
        
        elif state == QWebEngineDownloadRequest.DownloadState.DownloadCancelled:
            label.setText(f"{self.tr("Canceled:")} {self.shorten_if_needed(download_filename)}")
            progress_bar.setEnabled(False)
        
        elif state == QWebEngineDownloadRequest.DownloadState.DownloadInterrupted:
            label.setText(f"{self.tr("Error:")} {self.shorten_if_needed(download_filename)}")
            progress_bar.setStyleSheet("QProgressBar::chunk { background-color: red; }")
    
    def open_manage_downloads(self):
        dlg = DownloadManagerWidget(window.download_manager.downloads)
        dlg.exec()

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
        icon_color = theme_manager.get_contrast_color_from_theme()
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

class ManageExtensionRepositories(QDialog):
    def __init__(self, parent, passed_repositories):
        super().__init__(parent)

        self.setWindowTitle(self.tr("Manage Repositories"))
        self.setFixedSize(400, 300)

        # Temporary copy of bookmarks for editing
        self.temp_repos = passed_repositories

        self.init_ui()

        # Select first item if exists
        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        content_layout = QHBoxLayout()

        # Title
        title_label = QLabel(self.tr("Manage Repositories"))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; padding: 20px")
        layout.addWidget(title_label)

        # Left side: Repository list
        self.list_widget = QListWidget()
        self.list_widget.addItems(self.temp_repos)
        self.list_widget.currentRowChanged.connect(self.load_bookmark_to_inputs)
        content_layout.addWidget(self.list_widget, 1)

        # Right side: Repository actions
        icon_color = theme_manager.get_contrast_color_from_theme()
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

        # Middle: Live editor of selected repository
        edit_layout = QFormLayout()
        edit_layout.setContentsMargins(0, 5, 0, 5)

        self.url_lineedit = QLineEdit()
        self.url_lineedit.textEdited.connect(self.sync_data_live)
        edit_layout.addRow(self.tr("Repository URL: "), self.url_lineedit)

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
        self.url_lineedit.blockSignals(True)
        
        if row >= 0 and row < len(self.temp_repos):
            rp = self.temp_repos[row]
            self.url_lineedit.setText(rp)
            self.url_lineedit.setEnabled(True)
        else:
            self.url_lineedit.clear()
            self.url_lineedit.setEnabled(False)
        
        self.url_lineedit.blockSignals(False)

    def sync_data_live(self):
        row = self.list_widget.currentRow()
        if row >= 0:
            new_url = self.url_lineedit.text()
            
            # Update the temporary data list
            self.temp_repos[row] = new_url
            
            # Update the list item text live so the user sees the rename
            self.list_widget.item(row).setText(new_url)

    def add_bookmark(self):
        new_url = "https://"
        self.temp_repos.append(new_url)
        self.list_widget.addItem(new_url)
        self.list_widget.setCurrentRow(self.list_widget.count() - 1)

    def delete_bookmark(self):
        row = self.list_widget.currentRow()
        if row >= 0:
            self.temp_repos.pop(row)
            self.list_widget.takeItem(row)

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

class QColorButton(QPushButton):
    colorChanged = Signal(object)

    def __init__(self, *args, color=None, **kwargs):
        super().__init__(*args, **kwargs)

        self._color = None
        self._default = color if color else "#ffffff"
        self._static_styles = "border-radius: 6px"
        self.setStyleSheet(f"background-color: {self._default}; {self._static_styles}")
        self.pressed.connect(self.onColorPicker)
        self.installEventFilter(self)

        # Set the initial/default state.
        self.setColor(self._default)

    def setColor(self, color):
        if color != self._color:
            self._color = color
            self.colorChanged.emit(color)

        if self._color:
            self.setStyleSheet(f"background-color: {self._color}; {self._static_styles}")
        else:
            self.setStyleSheet("")

    def color(self):
        return self._color

    def onColorPicker(self):
        dlg = QColorDialog(self)
        if self._color:
            dlg.setCurrentColor(QColor(self._color))

        if dlg.exec():
            self.setColor(dlg.currentColor().name())

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.RightButton:
            self.setColor(self._default)

        return super().mousePressEvent(e)

class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setFixedSize(240, 325)
        self.setWindowTitle(self.tr("About"))
        self.dlg_layout = QVBoxLayout()
        self.setLayout(self.dlg_layout)

        self.init_ui()

    def init_ui(self):
        top_layout = QHBoxLayout()
        top_info_layout = QVBoxLayout()

        logoLabel = QLabel(self)
        logoLabel.setFixedSize(80, 80)
        logoLabel.setScaledContents(True)
        
        if os.path.exists(LOGO_PATH):
            logoLabel.setPixmap(QPixmap(LOGO_PATH))

        top_layout.addWidget(logoLabel, alignment=Qt.AlignmentFlag.AlignCenter)

        about_title = QLabel("RSS MGR")
        about_title.setStyleSheet("font-size: 17px; font-weight: bold;")
        top_info_layout.addWidget(about_title)

        about_label = QLabel(f"Version: {VERSION_NUMBER}")
        about_label.setWordWrap(True)
        top_info_layout.addWidget(about_label)

        top_info_layout.addWidget(QLabel())

        self.dlg_layout.addLayout(top_layout)
        top_layout.addLayout(top_info_layout)
        top_layout.addStretch()

        # Add tab widget
        tab_widget = QTabWidget()
        self.dlg_layout.addWidget(tab_widget)

        # About tab
        about_tab = QWidget()
        about_layout = QVBoxLayout()
        about_tab.setLayout(about_layout)

        about_description = QLabel("A simple PySide6 browser for Silk and Linux devices.\nSilk Project 2025-2026")
        about_description.setWordWrap(True)
        about_layout.addWidget(about_description)

        about_layout.addStretch()

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        button_box.setContentsMargins(0, 8, 0, 8)
        button_box.accepted.connect(self.accept)

        tab_widget.addTab(about_tab, "About")

        self.dlg_layout.addWidget(button_box, alignment=Qt.AlignmentFlag.AlignCenter)

        # Components tab
        components_tab = QWidget()
        components_layout = QVBoxLayout()
        components_tab.setLayout(components_layout)

        components = [{
            "name": "PySide6 (Qt)",
            "version":"6.11.0",
            "license":"LGPL-3.0"
        }]

        for component in components:
            item = QWidget()
            item.setStyleSheet("border: 1px solid #3f4042; border-radius: 3px;")
            item_layout = QVBoxLayout()
            item.setLayout(item_layout)

            name = QLabel(component.get("name", "No name"))
            name.setStyleSheet("font-weight: bold; border: none;")

            version = QLabel(component.get("version", "No version"))
            version.setStyleSheet("color: grey; border: none;")

            license = QLabel(component.get("license", "No license"))
            license.setStyleSheet("color: grey; border: none;")

            item_layout.addWidget(name)
            item_layout.addWidget(version)
            item_layout.addWidget(license)

            components_layout.addWidget(item)

        components_layout.addStretch()
        
        tab_widget.addTab(components_tab, "Components")

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
        self.init_control_ui()
        self.init_bookmark_bar()
        self.init_extension_sidebar()
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
        icon_color = theme_manager.get_contrast_color_from_theme()

        # Left side: Basic navigation (Back, Forward page)
        self.extension_sidebar_btn = QPushButton()
        self.extension_sidebar_btn.setIcon(qta.icon("msc.layout-sidebar-left", color=icon_color))
        self.extension_sidebar_btn.setProperty("class", "navbtns")
        self.extension_sidebar_btn.setStyleSheet("padding: 8px;")
        self.extension_sidebar_btn.clicked.connect(self.toggle_extension_sidebar)
        controls_layout.addWidget(self.extension_sidebar_btn)

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

        self.download_manager = DownloadManager()
        self.download_menu = DownloadMenu()
        self.download_manager.download_added.connect(self.download_menu.add_download)
        self.downloads_btn = QPushButton()
        self.downloads_btn.setIcon(qta.icon("ei.download", color=icon_color))
        self.downloads_btn.setStyleSheet("padding: 8px;")
        self.downloads_btn.setVisible(False)
        self.downloads_btn.clicked.connect(self.show_download_menu)
        controls_layout.addWidget(self.downloads_btn)

        self.add_to_bookmarks_btn = QPushButton()
        self.add_to_bookmarks_btn.setIcon(qta.icon("fa5s.bookmark", color=icon_color))
        self.add_to_bookmarks_btn.setProperty("class", "navbtns")
        self.add_to_bookmarks_btn.setStyleSheet("padding: 8px;")
        self.add_to_bookmarks_btn.clicked.connect(self.add_current_to_bookmarks_dialog)
        controls_layout.addWidget(self.add_to_bookmarks_btn)

        self.web_extensions_menu = WebExtensionsMenu()
        self.web_extensions_menu.signals.request_manage_extensions.connect(self.web_extension_dialog)
        self.web_extensions_btn = QPushButton()
        self.web_extensions_btn.setIcon(qta.icon("mdi6.puzzle", color=icon_color))
        self.web_extensions_btn.setProperty("class", "navbtns")
        self.web_extensions_btn.setStyleSheet("padding: 8px;")
        self.web_extensions_btn.clicked.connect(self.show_extension_menu)
        controls_layout.addWidget(self.web_extensions_btn)

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

        # Help Menu
        self.documentationAction.setText(self.tr("Project Page"))
        self.aboutAction.setText(self.tr("About"))

        # Main UI
        self.load_btn.setText(self.tr("Go"))

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
        for tab in range(0, self.web_tabs.count()):
            tab_widget = self.tab_list[0]
            profile = tab_widget.page().profile()
            profile.clearHttpCache()

            self.web_tabs.removeTab(0)
            tab_widget.deleteLater()
            self.tab_list.pop(0)


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
    
    def setup_profile(self):
        if not os.path.exists(STORAGE_PATH):
            os.makedirs(STORAGE_PATH)

        self.profile = QWebEngineProfile("Default", self)
        self.profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.DiskHttpCache)
        self.profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies)
        self.profile.setCachePath(STORAGE_PATH)
        self.profile.setPersistentStoragePath(STORAGE_PATH)
        self.profile.setParent(self)

    def update_tab_info(self):
        self.update_urlbar_content()
        self.update_nav_btn_status()
        self.update_tab_titles()
    
    def create_new_tab(self, url=None):
        # Web Engine
        web_tab = BetterWebEngine(self)
        web_tab.setPage(QWebEnginePage(self.profile, web_tab))
        web_tab.init_engine()

        # Setup localstorage for the new tab
        web_tab.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)

        self.tab_list.append(web_tab)
        
        if url:
            self.tab_list[-1].setUrl(QUrl(url))

        self.tab_list[-1].loadProgress.connect(self.update_progressbar)
        self.tab_list[-1].loadFinished.connect(self.page_load_finished)
        self.tab_list[-1].loadFinished.connect(self.tab_list[-1].page_load_finished)
        self.tab_list[-1].loadStarted.connect(self.page_load_started)
        self.tab_list[-1].urlChanged.connect(self.update_urlbar_content)
        self.tab_list[-1].iconChanged.connect(self.update_tab_info)
        self.tab_list[-1].page().profile().downloadRequested.connect(self.request_download)
        self.tab_list[-1].signals.sum_selected_with_ai.connect(self.summarize_selected_with_ai)
        self.tab_list[-1].signals.sum_page_with_ai.connect(self.summarize_current_page_ai)

        self.web_tabs.addTab(self.tab_list[-1], None)
        self.web_tabs.setCurrentIndex(len(self.tab_list) - 1)
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
        self.download_menu.exec(button_pos)
    
    def request_download(self, download):
        if current_settings["download_warnings"]:
            warning_dlg = QMessageBox(self)
            warning_dlg.setWindowTitle(self.tr("Download Request"))
            warning_dlg.setText(f"{self.tr("Do you really want to download")} \"{download.suggestedFileName()}\"?")
            warning_dlg.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
            warning_dlg.setIcon(QMessageBox.Icon.Warning)

            if warning_dlg.exec() == QMessageBox.StandardButton.Ok:
                self.download_manager.add_download(download)
                self.downloads_btn.setVisible(True)
                self.show_download_menu()
    
        else:
            self.download_manager.add_download(download)
            self.downloads_btn.setVisible(True)
            self.show_download_menu()

    # Extension system
    def show_extension_menu(self):
        button_pos = self.web_extensions_btn.mapToGlobal(self.web_extensions_btn.rect().bottomLeft())
        self.web_extensions_menu.exec(button_pos)

    def web_extension_dialog(self):
        dlg = WebExtensionsDialog(self)

        if dlg.exec():
            self.check_extension_updates()
        
        else:
            self.check_extension_updates()

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
                self.web_extensions_btn.setToolTip(f"{self.tr("Extension updates: ")}{updateable_extensions}")
            
            else:
                self.web_extensions_btn.setToolTip("")
            
            self.update_icon_colors()

        except Exception as e:
            print(f"Error when checking extensions for updates: {e}")
    
    def version_parser(self, version_string):
        # Simple version parser that converts a version string like "1.2.3" into a tuple of integers (1, 2, 3)
        try:
            version_tuple = tuple(map(int, version_string.split(".")))
            return version_tuple
        except Exception as e:
            print(f"Error parsing version string '{version_string}': {e}")
            return (0,)

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
        icon_color = theme_manager.get_contrast_color_from_theme()

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
    def update_icon_colors(self):
        icon_color = theme_manager.get_contrast_color_from_theme()

        self.extension_sidebar_btn.setIcon(qta.icon("msc.layout-sidebar-left", color=icon_color))
        self.prev_page_btn.setIcon(qta.icon("fa6s.arrow-left", color=icon_color))
        self.next_page_btn.setIcon(qta.icon("fa6s.arrow-right", color=icon_color))

        if self.web_tabs.currentWidget().page_is_loading:
            self.reload_page_btn.setIcon(qta.icon("ei.remove", color=icon_color))
        else:
            self.reload_page_btn.setIcon(qta.icon("fa6s.arrow-rotate-right", color=icon_color))
        
        self.load_btn.setIcon(qta.icon("mdi.arrow-right-bold-box", color=icon_color))
        self.add_tab_btn.setIcon(qta.icon("fa6s.plus", color=icon_color))
        self.add_to_bookmarks_btn.setIcon(qta.icon("fa5s.bookmark", color=icon_color))

        if self.extension_updates:
            self.web_extensions_btn.setIcon(qta.icon("mdi6.puzzle-plus", color=icon_color))
        
        else:
            self.web_extensions_btn.setIcon(qta.icon("mdi6.puzzle", color=icon_color))
        
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
        dlg = ManageBookmarksDialog(self, current_bookmarks)

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

        dlg = QDialog(self)
        dlg.setWindowTitle(self.tr("Settings"))
        dlg.setFixedSize(480, 360)

        layout = QGridLayout()

        # Settings tab widget
        tabs = QTabWidget()

        # General Tab
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
        theme_combobox.addItems([self.tr("Light"), self.tr("Dark"), self.tr("Automatic"), self.tr("Legacy (Native)")])
        theme_combobox.setCurrentIndex(theme_manager.available_themes.index(theme_manager.theme))
        display_settings_layout.addRow(self.tr("Theme: "), theme_combobox)

        accent_color_btn = QColorButton(color=current_settings["accent_color"])
        display_settings_layout.addRow(self.tr("Accent color: "), accent_color_btn)

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

        # Language Tab
        language_settings = QWidget()
        language_settings_layout = QFormLayout()
        language_settings.setLayout(language_settings_layout)

        language_select_combobox = QComboBox()

        for lan_name, lan_code in NAME_TO_LANGUAGE.items():
            language_select_combobox.addItem(lan_name)
        

        language_select_combobox.setCurrentText(LANGUAGE_TO_NAME[current_settings["language"]])
        language_settings_layout.addRow(self.tr("Program Language: "), language_select_combobox)

        # Engine tab settings
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

        # AI tab settings
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
                install_model_btn.setIcon(qta.icon("fa6s.download", color=theme_manager.get_contrast_color_from_theme()))
            else:
                install_model_btn.setText(self.tr("Model Installed"))
                install_model_btn.setIcon(qta.icon("fa6s.check", color=theme_manager.get_contrast_color_from_theme()))
            
            install_model_btn.setEnabled(not sum_model_installed)

        except Exception:
            sum_model_installed = False
            install_model_btn.setText(self.tr("Ollama not running"))
            install_model_btn.setIcon(qta.icon("ei.remove", color=theme_manager.get_contrast_color_from_theme()))
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
            theme_index = theme_combobox.currentIndex()
            accent_color = accent_color_btn.color()
            go_button_visible = go_button_visibility_checkbox.isChecked()
            bottom_bar_visible = bottom_bar_visability_checkbox.isChecked()
            download_warnings = download_warnings_checkbox.isChecked()
            language = language_select_combobox.currentText()
            javascript_enabled = javascript_checkbox.isChecked()
            default_font_size = font_size_spinbox.value()
            default_scrollbars_enabled = scrollbars_enabled_checkbox.isChecked()
            summarize_ai_enabled = ai_checkbox.isChecked()

            # Update settings in browser
            theme_manager.load_theme_from_index(theme_index)

            self.bottom_bar.setVisible(bottom_bar_visible)
            self.load_btn.setVisible(go_button_visible)
            
            if language != current_settings["language"]:
                self.load_language(NAME_TO_LANGUAGE[language])

            self.update_web_engine()

            if summarize_ai_enabled != current_settings["ai_summarization_enabled"]:
                current_settings["ai_summarization_enabled"] = not current_settings["ai_summarization_enabled"]
                self.extension_sidebar.load_extensions()
            
            theme_manager.set_accent_color(accent_color)

            # Prepare settings.json
            updated_settings = {
                "start_page_url":start_page,
                "search_engine":search_engine,
                "theme":theme_manager.available_themes[theme_index],
                "accent_color":accent_color,
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
        install_button.setIcon(qta.icon("mdi.loading", color=theme_manager.get_contrast_color_from_theme(), animation=animation))

        self.threadpool = QThreadPool()
        worker = InstallWorker(SUM_AI_MODEL["name"])
        worker.signals.installation_complete.connect(lambda: self.model_installation_complete(install_button))
        self.threadpool.start(worker)
    
    def model_installation_complete(self, install_button):
        install_button.setText(self.tr("Model Installed"))
        install_button.setIcon(qta.icon("fa6s.check", color=theme_manager.get_contrast_color_from_theme()))
        
        QMessageBox.information(self, self.tr("Model Installed"), self.tr("The AI page summarization model has been installed successfully. You can now enable AI page summarization in the settings."))
    
    def toggle_url_edit(self, enable, urledit):
        urledit.setEnabled(enable)
    
    def update_web_engine(self):
        for tab in self.tab_list:
            tab.update_engine_config()
        
    def about_dialog(self):
        dlg = AboutDialog(self)
        dlg.exec()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("Silk Mizu")
    app.setApplicationVersion(VERSION_NUMBER)
    app.setOrganizationName("Silk Project")

    # Load theme
    theme_manager = ThemeManager(app, current_settings["theme"])

    # Load extension manager
    extension_manager = ExtensionManager()
    
    app.setWindowIcon(QIcon(LOGO_PATH))
    app.setStyle("breeze")
    window = BrowserWindow()
    window.show()
    sys.exit(app.exec())