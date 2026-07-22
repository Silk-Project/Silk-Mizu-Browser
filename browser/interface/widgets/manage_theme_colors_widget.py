from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QPushButton,
    QListWidget,
    QLabel,
    QDialogButtonBox,
    QSizePolicy,
    QLineEdit,
    QListWidgetItem,
    QFormLayout,
    QSpinBox,
    QComboBox,
    QProgressBar
)
from PySide6.QtCore import Qt, QSize
import qtawesome as qta
from interface.widgets.color_button import QColorButton
from interface.widgets.icon_selector import FontAwesomeIconSelectorBtn
from dataclasses import dataclass
from services.theme_mgr import AVAILABLE_THEMES

class ManageThemeColors(QWidget):
    def __init__(self, parent, passed_colors: dict):
        super().__init__(parent)

        self.passed_colors = passed_colors
        self.colors = {
            "theme": "dark",
            "accent": "#8370EB"
        }

        self.init_ui()
        self._load_passed_theme()

    def init_ui(self):
        self.layout = QFormLayout(self)

        self.theme_combobox = QComboBox()
        self.theme_combobox.addItems([self.tr("Light"), self.tr("Dark"), self.tr("Automatic"), self.tr("Legacy (Native)")])
        self.theme_combobox.setCurrentIndex(AVAILABLE_THEMES.index(self.colors["theme"]))
        self.layout.addRow(self.tr("Theme: "), self.theme_combobox)

        self.accent_color_btn = QColorButton(color=self.colors["accent"])
        self.layout.addRow(self.tr("Accent color: "), self.accent_color_btn)

    def _update_colors(self):
        if self.colors["theme"] in AVAILABLE_THEMES:
            self.theme_combobox.setCurrentIndex(AVAILABLE_THEMES.index(self.colors["theme"]))

        self.accent_color_btn.setColor(self.colors["accent"])

    def _load_passed_theme(self):
        theme = self.passed_colors.get("theme")
        accent = self.passed_colors.get("accent")

        if theme is not None and isinstance(theme, str):
            if theme in AVAILABLE_THEMES:
                self.colors["theme"] = theme

        if accent is not None and isinstance(accent, str):
            self.colors["accent"] = accent

        self._update_colors()

    def load_theme(self, theme: str, accent: str):
        if theme is not None and isinstance(theme, str):
            if theme in AVAILABLE_THEMES:
                self.colors["theme"] = theme
        
        if accent is not None and isinstance(accent, str):
            self.colors["accent"] = accent
        
        self._update_colors()
