from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QWidget,
    QLabel,
    QLineEdit,
    QTabWidget,
    QDialogButtonBox,
    QMenuBar,
    QFileDialog,
    QMessageBox,
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction
import qtawesome as qta
import json
from interface.widgets.color_button import QColorButton
from interface.widgets.icon_selector import FontAwesomeIconSelectorBtn
from dataclasses import dataclass, asdict, field
from interface.widgets.manage_navbar_widget import ManageNavigationUI
from interface.widgets.manage_theme_colors_widget import ManageThemeColors
from interface.navigation.nav_manager import NavigationUIElement
from services.theme_mgr import AVAILABLE_THEMES

@dataclass
class ThemeData:
    name: str = None
    theme: str = "dark"
    accent_color: str = "#8370EB"
    navigation_ui_layout: list[NavigationUIElement] = field(default_factory=list) 

class ThemeDialog(QDialog):
    def __init__(self, theme: dict | ThemeData, parent = ...):
        super().__init__(parent)

        self.passed_theme = theme
        self.theme: ThemeData = ThemeData()
        self.setFixedSize(640, 480)
        self.setWindowFilePath(self.tr("Manage Theme"))

        self.init_ui()
        self.init_menu_bar()
        self._load_passed_theme()

    def init_menu_bar(self):
        menu_bar = QMenuBar()

        self.fileMenu = menu_bar.addMenu(self.tr("&File"))
        
        self.importAction = QAction("Import theme pack", self)
        self.importAction.triggered.connect(self.import_theme)
        self.fileMenu.addAction(self.importAction)

        self.exportAction = QAction("Export theme pack", self)
        self.exportAction.triggered.connect(self.export_theme)
        self.fileMenu.addAction(self.exportAction)

        self.layout.setMenuBar(menu_bar)

    def init_ui(self):
        self.layout = QVBoxLayout(self)

        # Title
        self.title_label = QLabel(self.tr("Manage Theme"))
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet("font-size: 20px; font-weight: bold; padding: 20px")
        self.layout.addWidget(self.title_label)

        # Tabs
        self.theme_tabs = QTabWidget()

        # Main interface tab
        self.theme_color_widget = ManageThemeColors(parent=self, passed_colors={})
        self.theme_tabs.addTab(self.theme_color_widget, self.tr("Main interface"))

        # Navigation Editor tab
        self.navigation_editor_widget = ManageNavigationUI(parent=self, passed_layout=self.theme.navigation_ui_layout)
        self.theme_tabs.addTab(self.navigation_editor_widget, self.tr("Navigation interface"))

        # Theme info tab
        self.theme_info_widget = QWidget()
        theme_info_layout = QFormLayout(self.theme_info_widget)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText(self.tr("Enter theme name..."))
        theme_info_layout.addRow(self.tr("Theme name:"), self.name_edit)
        self.theme_tabs.addTab(self.theme_info_widget, self.tr("Theme information"))

        self.layout.addWidget(self.theme_tabs)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        self.layout.addWidget(self.button_box)

    def import_theme(self):
        path, _ = QFileDialog.getOpenFileName(
            self, self.tr("Import Theme Pack"), "", self.tr("Theme Pack (*.json)")
        )
        if not path:
            return

        try:
            with open(path, "r") as f:
                data = json.load(f)

            if not isinstance(data, dict) or "theme" not in data:
                QMessageBox.warning(self, self.tr("Invalid Theme Pack"), self.tr("The selected file is not a valid theme pack."))
                return

            theme_data = data["theme"]
            self.name_edit.setText(theme_data.get("name", ""))
            self.theme_color_widget.load_theme(
                theme_data.get("theme", "dark"),
                theme_data.get("accent_color", "#8370EB"),
            )
            self.navigation_editor_widget.load_passed_layout(
                theme_data.get("navigation_ui_layout", {})
            )
        except (json.JSONDecodeError, OSError) as e:
            QMessageBox.warning(self, self.tr("Import Failed"), str(e))

    def export_theme(self):
        name = self.name_edit.text().strip() or "theme"
        default_filename = f"{name.lower().replace(' ', '_')}.json"

        path, _ = QFileDialog.getSaveFileName(
            self, self.tr("Export Theme Pack"), default_filename, self.tr("Theme Pack (*.json)")
        )
        if not path:
            return

        try:
            data = {"theme": self.get_theme_dict()}
            with open(path, "w") as f:
                json.dump(data, f, indent=4)
        except OSError as e:
            QMessageBox.warning(self, self.tr("Export Failed"), str(e))

    def _update_theme(self):
        self.name_edit.setText(self.theme.name or "")
        self.navigation_editor_widget.load_passed_layout(layout=self.theme.navigation_ui_layout)
        self.theme_color_widget.load_theme(self.theme.theme, self.theme.accent_color)

    def _update_theme_values(self):
        # Get accent color and theme
        theme_index = self.theme_color_widget.theme_combobox.currentIndex()
        
        if len(AVAILABLE_THEMES) - 1 >= theme_index:
            self.theme.theme = AVAILABLE_THEMES[theme_index]
        
        self.theme.accent_color = self.theme_color_widget.accent_color_btn.color()

    def _load_passed_theme(self):
        if isinstance(self.passed_theme, ThemeData):
            self.theme = self.passed_theme

        elif isinstance(self.passed_theme, dict):
            theme_data = ThemeData(
                name=self.passed_theme.get("name"),
                theme=self.passed_theme.get("theme"),
                accent_color=self.passed_theme.get("accent_color"),
                navigation_ui_layout=self.passed_theme.get("navigation_ui_layout")
            )

            self.theme = theme_data

        self._update_theme()

    def get_theme_dict(self):
        self._update_theme_values()

        navigation_ui_layout = self.navigation_editor_widget.get_current_ui_elements_dict()
        name = self.name_edit.text().strip() or self.theme.name

        return {
            "name": name,
            "theme": self.theme.theme,
            "accent_color": self.theme.accent_color,
            "navigation_ui_layout": navigation_ui_layout
        }