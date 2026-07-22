import ollama
import qtawesome as qta
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QGridLayout,
    QFormLayout,
    QDialog,
    QLabel,
    QDialogButtonBox,
    QTabWidget,
    QRadioButton,
    QButtonGroup,
    QLineEdit,
    QComboBox,
    QCheckBox,
    QSpinBox,
    QPushButton,
)
from PySide6.QtCore import Qt
from services.constants import START_PAGE_PATH, NAME_TO_LANGUAGE, LANGUAGE_TO_NAME, SUM_AI_MODEL
from interface.dialogs.theme_dialog import ThemeDialog
from interface.widgets.dir_select_btn import QDirDialogBtn


class SettingsDialog(QDialog):
    def __init__(self, parent, theme_manager, current_settings):
        super().__init__(parent)
        self.parent = parent
        self.theme_manager = theme_manager
        self.current_settings = current_settings
        
        self.setWindowTitle(self.tr("Settings"))
        self.setFixedSize(480, 360)

        layout = QGridLayout()

        title_label = QLabel(self.tr("Browser Settings"))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; padding-top: 20px; padding-bottom: 10px;")
        layout.addWidget(title_label, 0, 0)

        tabs = QTabWidget()

        # General Tab
        self.general_settings = QWidget()
        general_settings_layout = QFormLayout()
        self.general_settings.setLayout(general_settings_layout)

        start_page_type_group = QButtonGroup()
        start_page_type_group.setExclusive(True)

        self.start_page_type_radio_button = QRadioButton(self.tr("Silk Start (local)"))
        self.start_page_type_radio_button.setChecked(current_settings["start_page_url"] == START_PAGE_PATH)
        self.start_page_type_radio_button.toggled.connect(lambda: self._toggle_url_edit(False))
        start_page_type_group.addButton(self.start_page_type_radio_button)

        self.start_page_url_radio_button = QRadioButton(self.tr("URL"))
        self.start_page_url_radio_button.setChecked(current_settings["start_page_url"] != START_PAGE_PATH)
        self.start_page_url_radio_button.toggled.connect(lambda: self._toggle_url_edit(True))
        start_page_type_group.addButton(self.start_page_url_radio_button)

        start_page_type_layout = QHBoxLayout()
        start_page_type_layout.addWidget(self.start_page_type_radio_button)
        start_page_type_layout.addWidget(self.start_page_url_radio_button)
        general_settings_layout.addRow(self.tr("Start page type: "), start_page_type_layout)

        self.start_page_urledit = QLineEdit()
        self.start_page_urledit.setText(current_settings["start_page_url"])
        self.start_page_urledit.setMinimumWidth(200)
        self.start_page_urledit.setEnabled(current_settings["start_page_url"] != START_PAGE_PATH)
        general_settings_layout.addRow(self.tr("Start page URL: "), self.start_page_urledit)

        self.search_engine_combobox = QComboBox()
        self.search_engine_combobox.addItems(["Google", "DuckDuckGo", "Brave", "Ecosia", "Yahoo"])
        self.search_engine_combobox.setCurrentText(current_settings["search_engine"])
        general_settings_layout.addRow(self.tr("Search engine: "), self.search_engine_combobox)

        # Display settings
        self.display_settings = QWidget()
        display_settings_layout = QFormLayout()
        self.display_settings.setLayout(display_settings_layout)

        manage_theme_btn = QPushButton(self.tr("Manage Theme"))
        manage_theme_btn.clicked.connect(self.open_manage_theme_dialog)
        display_settings_layout.addRow(self.tr("Theme: "), manage_theme_btn)

        # Security settings
        self.security_settings = QWidget()
        security_settings_layout = QFormLayout()
        self.security_settings.setLayout(security_settings_layout)

        self.download_warnings_checkbox = QCheckBox()
        self.download_warnings_checkbox.setChecked(current_settings["download_warnings"])
        security_settings_layout.addRow(self.tr("Display warning when download is requested: "), self.download_warnings_checkbox)

        # Download settings
        self.downloads_settings = QWidget()
        downloads_settings_layout = QFormLayout()
        self.downloads_settings.setLayout(downloads_settings_layout)

        self.downloads_path_selector = QDirDialogBtn(current_settings["downloads_path"])
        downloads_settings_layout.addRow(self.tr("Downloads path: "), self.downloads_path_selector)

        # Language Tab
        self.language_settings = QWidget()
        language_settings_layout = QFormLayout()
        self.language_settings.setLayout(language_settings_layout)

        self.language_select_combobox = QComboBox()
        for lan_name, lan_code in NAME_TO_LANGUAGE.items():
            self.language_select_combobox.addItem(lan_name)
        self.language_select_combobox.setCurrentText(LANGUAGE_TO_NAME[current_settings["language"]])
        language_settings_layout.addRow(self.tr("Program Language: "), self.language_select_combobox)

        # Engine tab settings
        self.engine_settings = QWidget()
        engine_settings_layout = QFormLayout()
        self.engine_settings.setLayout(engine_settings_layout)

        self.font_size_spinbox = QSpinBox()
        self.font_size_spinbox.setRange(10, 80)
        self.font_size_spinbox.setValue(current_settings["default_font_size"])
        engine_settings_layout.addRow(self.tr("Default font size: "), self.font_size_spinbox)

        self.javascript_checkbox = QCheckBox()
        self.javascript_checkbox.setChecked(current_settings["javascript_enabled"])
        engine_settings_layout.addRow(self.tr("Javascript enabled: "), self.javascript_checkbox)

        self.scrollbars_enabled_checkbox = QCheckBox()
        self.scrollbars_enabled_checkbox.setChecked(current_settings["scrollbars_enabled"])
        engine_settings_layout.addRow(self.tr("Scrollbars enabled: "), self.scrollbars_enabled_checkbox)

        # AI tab settings
        self.ai_settings = QWidget()
        ai_settings_layout = QFormLayout()
        self.ai_settings.setLayout(ai_settings_layout)

        self.install_model_btn = QPushButton()

        try:
            raw_models = ollama.list()
            ollama_model_names = [m.model for m in raw_models.models]
            sum_model_installed = SUM_AI_MODEL["name"] in ollama_model_names

            if not sum_model_installed:
                self.install_model_btn.setText(self.tr('Install') + ' (' + SUM_AI_MODEL['size'] + ')')
                self.install_model_btn.setIcon(qta.icon("fa6s.download", color=theme_manager.get_contrast_color_from_theme()))
            else:
                self.install_model_btn.setText(self.tr("Model Installed"))
                self.install_model_btn.setIcon(qta.icon("fa6s.check", color=theme_manager.get_contrast_color_from_theme()))

            self.install_model_btn.setEnabled(not sum_model_installed)

        except Exception:
            sum_model_installed = False
            self.install_model_btn.setText(self.tr("Ollama not running"))
            self.install_model_btn.setIcon(qta.icon("ei.remove", color=theme_manager.get_contrast_color_from_theme()))
            self.install_model_btn.setEnabled(False)

        self.install_model_btn.setFixedWidth(200)
        self.install_model_btn.clicked.connect(lambda: self.parent.start_model_installation(self.install_model_btn))
        ai_settings_layout.addRow(self.tr("Install AI Page Summarization Model: "), self.install_model_btn)

        self.ai_checkbox = QCheckBox()
        self.ai_checkbox.setEnabled(sum_model_installed)
        self.ai_checkbox.setChecked(current_settings["ai_summarization_enabled"])
        ai_settings_layout.addRow(self.tr("Enable AI Page Summarization: "), self.ai_checkbox)

        # Add widgets to tab widget
        tabs.addTab(self.general_settings, self.tr("General"))
        tabs.addTab(self.display_settings, self.tr("Display"))
        tabs.addTab(self.security_settings, self.tr("Security"))
        tabs.addTab(self.downloads_settings, self.tr("Downloads"))
        tabs.addTab(self.language_settings, self.tr("Language"))
        tabs.addTab(self.engine_settings, self.tr("Engine"))
        tabs.addTab(self.ai_settings, self.tr("AI Features"))

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        layout.addWidget(tabs, 1, 0)
        layout.addWidget(button_box, 2, 0, alignment=Qt.AlignmentFlag.AlignRight)

        self.setLayout(layout)

    def _toggle_url_edit(self, enable):
        self.start_page_urledit.setEnabled(enable)
    
    def open_manage_theme_dialog(self):
        dialog = ThemeDialog(parent=self, theme=self.current_settings["theme"])
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.current_settings["theme"] = dialog.get_theme_dict()

    def get_settings(self):
        return {
            "start_page_url": self.start_page_urledit.text() if self.start_page_url_radio_button.isChecked() else START_PAGE_PATH,
            "search_engine": self.search_engine_combobox.currentText(),
            "theme": self.current_settings["theme"],
            "download_warnings": self.download_warnings_checkbox.isChecked(),
            "downloads_path": self.downloads_path_selector.current_path,
            "language": self.language_select_combobox.currentText(),
            "javascript_enabled": self.javascript_checkbox.isChecked(),
            "default_font_size": self.font_size_spinbox.value(),
            "scrollbars_enabled": self.scrollbars_enabled_checkbox.isChecked(),
            "ai_summarization_enabled": self.ai_checkbox.isChecked(),
        }
