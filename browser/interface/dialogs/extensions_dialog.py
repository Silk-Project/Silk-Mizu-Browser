from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QWidget,
    QLabel,
    QDialogButtonBox,
    QScrollArea,
    QTabWidget,
    QFrame,
    QSizePolicy,
    QProgressBar,
    QTextEdit,
    QComboBox,
    QMessageBox,
)
from PySide6.QtCore import Qt, Signal, Slot, QThreadPool, QRunnable, QObject, QTimer
from PySide6.QtGui import QPixmap
from services.constants import EXTENSIONS_PATH, EXTENSIONS_SETTINGS_PATH
from services.extension_mgr import ExtensionMetadata, check_dependencies
from services.extension_mgr import ExtensionManager
from interface.dialogs.manage_ext_repos_dialog import ManageExtensionRepositories
import requests
import zipfile
import io
import shutil
import qtawesome as qta
import os
import subprocess
import sys
import json

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

        extension_author = QLabel(self.tr('by') + ' ' + self.metadata.author)
        extension_author.setStyleSheet("font-size: 10px; color: #808080; border: none;")
        title_layout.addWidget(extension_author, alignment=Qt.AlignmentFlag.AlignLeft)

        title_layout.addStretch()

        if self.installable:
            required_dependencies = check_dependencies(self.metadata.dependencies)

            if len(required_dependencies) > 0:
                extension_deps = QLabel(self.tr('Required libraries: ') + ', '.join(required_dependencies))
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
        dlg.setWindowTitle(self.tr('About') + ' ' + self.metadata.name)
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

        about_label = QLabel(self.tr('Version: ') + self.metadata.version + '\n' + self.tr('by') + ' ' + self.metadata.author)
        about_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dlg_layout.addWidget(about_label)

        if self.installable:
            source_label = QTextEdit(self.tr('Source: ') + self.metadata.index_source)
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
        warning_dlg.setText(self.tr('Do you really want to download') + ' "' + self.metadata.name + '"?')
        warning_dlg.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
        warning_dlg.setIcon(QMessageBox.Icon.Warning)

        if warning_dlg.exec() == QMessageBox.StandardButton.Ok:
            install_dialog = ExtensionInstallDialog(self.metadata, self)
            
            if install_dialog.exec():
                self.download_extension_btn.setEnabled(True)
                self.download_extension_btn.setIcon(qta.icon("fa6s.check"))

            self.refresh_local_extensions.emit()

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
        warning_dlg.setText(self.tr('Do you really want to delete') + ' "' + self.metadata.name + '"?')
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
        QMessageBox.critical(self, self.tr("Installation Failed"), self.tr('Failed to install extension: ') + message)
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
    def __init__(self, index_urls: list, extension_manager: ExtensionManager, parent = None):
        super().__init__(parent)

        self.setWindowTitle(self.tr("Browser Extensions"))
        self.setFixedSize(624, 468)

        self.installed_order_asc = True
        self.store_order_asc = True
        self.loaded_store_extensions = []
        self.index_urls = index_urls
        self.extension_manager = extension_manager

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
        self.store_repository_btn.setToolTip(self.tr('Repositories: ') + str(len(self.index_urls)))
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
        self.extension_manager.update_extension_list()
        
        if len(self.extension_manager.get_installed()) == 0:
            self.installed_order_btn.setEnabled(False)
            self.install_tab_sort_combobox.setEnabled(False)

            self.installed_widgets_repeatable_layout.addStretch()

            info_label = QLabel(self.tr("No extensions found.\nWhy not try to install some?"))
            info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            info_label.setStyleSheet("color: grey;")
            self.installed_widgets_repeatable_layout.addWidget(info_label)

            self.installed_widgets_repeatable_layout.addStretch()

            return

        final_extension_data = self.extension_manager.get_installed()

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
        fetcher = WebExtensionFetcher(self.index_urls)
        fetcher.signals.task_failed.connect(self.store_load_failed)
        fetcher.signals.response_received.connect(self.show_store_extensions)
        self.threadpool.start(fetcher)

    def store_load_failed(self, error):
        self.clear_layout(self.store_widgets_repeatable_layout)

        self.store_widgets_repeatable_layout.addStretch()

        info_label = QLabel(self.tr('Error when trying to load store items: ') + error)
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
        repo_dlg = ManageExtensionRepositories(self, self.index_urls)

        if repo_dlg.exec():
            self.index_urls = repo_dlg.temp_repos

            with open(EXTENSIONS_SETTINGS_PATH, "w") as f:
                json.dump({"index_urls": self.index_urls}, f, indent=4)
            
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