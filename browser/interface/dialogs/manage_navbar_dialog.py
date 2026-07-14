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
from dataclasses import dataclass, asdict

@dataclass
class NavigationUIAdditionalStyling:
    background_color: str | None = None
    border_radius: int | None = None
    stretch_factor: int | None = None
    label: str | None = None

@dataclass
class NavigationUIElement:
    name: str
    type: str
    icon: str | None = None
    action: str = ""
    styling: NavigationUIAdditionalStyling = None

class NavigationUIListItem(QListWidgetItem):
    def __init__(self, data: NavigationUIElement):
        super().__init__()

        self._element = data
        self.setSizeHint(QSize(40, 25))
        self.setText(self._element.name)

class ManageNavigationUIDialog(QDialog):
    def __init__(self, parent, passed_layout: dict):
        super().__init__(parent)

        self.setWindowFilePath(self.tr("Manage Navigation UI"))
        self.setFixedSize(600, 400)

        self.passed_layout: dict = passed_layout
        self.current_bar = "top"
        self.current_layout: dict = {
            "top": [],
            "bottom": []
        }

        self.available_ui_elements = [
            NavigationUIElement("Back Button", "button", "fa6s.arrow-left", "back"),
            NavigationUIElement("Forward Button", "button", "fa6s.arrow-right", "forward"),
            NavigationUIElement("Reload Button", "button", "fa6s.rotate-right", "reload"),
            NavigationUIElement("Bookmark Button", "button", "fa6s.bookmark", "add_bookmark"),
            NavigationUIElement("Adress Bar", "urlbar", None, "adress_bar"),
            NavigationUIElement("Search Bar", "searchbar", None, "search_bar"),
            NavigationUIElement("New Tab Button", "button", "fa6s.plus", "new_tab"),
            NavigationUIElement("Settings Button", "button", "fa6s.gear", "settings"),
            NavigationUIElement("Extensions Button", "button", "fa6s.puzzle-piece", "extensions"),
            NavigationUIElement("Extensions Sidebar Button", "button", "msc.layout-sidebar-left", "extensions_sidebar"),
            NavigationUIElement("Tab Manager Button", "button", "ri.menu-fill", "tab_manager"),
            NavigationUIElement("Go Button", "button", "mdi.arrow-right-bold-box", "go"),
            NavigationUIElement("Download Manager Button", "button", "ei.download", "download_manager"),
            NavigationUIElement("Zoom in Button", "button", "ph.magnifying-glass-plus", "zoom_in"),
            NavigationUIElement("Zoom out Button", "button", "ph.magnifying-glass-minus", "zoom_out"),
            NavigationUIElement("Zoom amount label", "dyn_label", None, "zoom_label"),
            NavigationUIElement("Webpage Progress bar", "progress_bar", None, "page_progressbar"),
            NavigationUIElement("Stretch Space", "spacer", None, "stretch"),
            NavigationUIElement("Text label", "label", None, "label"),
        ]

        self.init_ui()

        self._load_passed_layout(self.passed_layout)
        self._populate_from_layout(self.current_layout["top"])

    def _resolve_icon(self, action: str, icon: str | None) -> str | None:
        if icon:
            return icon
        
        for available in self.available_ui_elements:
            if available.action == action:
                return available.icon
            
        return None
    
    def _load_passed_layout(self, layout):
        if isinstance(layout, dict):
            top_layout = layout.get("top", None)
            bottom_layout = layout.get("bottom", None)

            if top_layout is not None and bottom_layout is not None:
                self.current_layout["top"] = [self._dict_to_element(e) for e in top_layout]
                self.current_layout["bottom"] = [self._dict_to_element(e) for e in bottom_layout]
            elif top_layout is not None:
                self.current_layout["top"] = [self._dict_to_element(e) for e in top_layout]
            elif bottom_layout is not None:
                self.current_layout["bottom"] = [self._dict_to_element(e) for e in bottom_layout]

        elif isinstance(layout, list):
            self.current_layout["top"] = [self._dict_to_element(e) for e in layout]

    def _dict_to_element(self, d: dict) -> NavigationUIElement:
        styling_data = d.get("styling")
        if styling_data and isinstance(styling_data, dict):
            styling = NavigationUIAdditionalStyling(**styling_data)
        else:
            styling = NavigationUIAdditionalStyling()

        return NavigationUIElement(
            name=d.get("name", ""),
            type=d.get("type", ""),
            icon=d.get("icon"),
            action=d.get("action", ""),
            styling=styling,
        )

    def _populate_from_layout(self, layout):
        for elem in layout:
            icon = self._resolve_icon(elem.action, elem.icon)

            name = elem.name
            if not name:
                for available in self.available_ui_elements:
                    if available.action == elem.action:
                        name = available.name
                        break

            item = NavigationUIListItem(NavigationUIElement(
                name=name,
                type=elem.type,
                icon=icon,
                action=elem.action,
                styling=elem.styling
            ))
            self.current_ui_elements_list.addItem(item)

        self.update_preview()

    def init_ui(self):
        self.layout = QVBoxLayout(self)

        # Title
        self.title_label = QLabel(self.tr("Manage Navigation UI"))
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet("font-size: 20px; font-weight: bold; padding: 20px")
        self.layout.addWidget(self.title_label)

        # Bar Selector
        self.bar_selector = QComboBox()
        self.bar_selector.addItems(["Top bar", "Bottom bar"])
        self.bar_selector.currentIndexChanged.connect(self._on_bar_select_changed)
        self.layout.addWidget(self.bar_selector)

        # Top view (UI preview)
        self.preview_frame = QWidget()
        self.preview_frame.setMinimumHeight(40)
        self.preview_frame.setStyleSheet("border: 1px solid #414242; border-radius: 3px;")
        self.layout.addWidget(self.preview_frame)

        self.preview_frame_layout = QHBoxLayout()
        self.preview_frame.setLayout(self.preview_frame_layout)

        self.preview_frame_layout.addStretch()

        # Middle layout (UI controls)
        self.action_layout = QHBoxLayout()
        self.layout.addLayout(self.action_layout)

        self.current_ui_elements_list = QListWidget()
        self.current_ui_elements_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.action_layout.addWidget(self.current_ui_elements_list)

        self.available_ui_elements_list = QListWidget()
        self.available_ui_elements_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)

        for item in self.available_ui_elements:
            list_item = NavigationUIListItem(data=item)
            self.available_ui_elements_list.addItem(list_item)
        
        self.action_layout.addWidget(self.available_ui_elements_list)

        # Add/Remove buttons
        controls_layout = QVBoxLayout()
        self.action_layout.addLayout(controls_layout)

        self.add_element_btn = QPushButton(self.tr("Add"))
        self.add_element_btn.setIcon(qta.icon("fa6s.plus"))
        self.add_element_btn.clicked.connect(self.add_ui_element)
        controls_layout.addWidget(self.add_element_btn)

        self.remove_element_btn = QPushButton(self.tr("Remove"))
        self.remove_element_btn.setIcon(qta.icon("fa6s.minus"))
        self.remove_element_btn.clicked.connect(self.remove_ui_element)
        controls_layout.addWidget(self.remove_element_btn)

        self.move_up_btn = QPushButton(self.tr("Move Up"))
        self.move_up_btn.setIcon(qta.icon("fa6s.arrow-up"))
        self.move_up_btn.clicked.connect(self.move_element_up)
        controls_layout.addWidget(self.move_up_btn)

        self.move_down_btn = QPushButton(self.tr("Move Down"))
        self.move_down_btn.setIcon(qta.icon("fa6s.arrow-down"))
        self.move_down_btn.clicked.connect(self.move_element_down)
        controls_layout.addWidget(self.move_down_btn)

        self.customise_styling_btn = QPushButton(self.tr("Customize Styling"))
        self.customise_styling_btn.setIcon(qta.icon("fa6s.palette"))
        self.customise_styling_btn.clicked.connect(self.customise_styling)
        controls_layout.addWidget(self.customise_styling_btn)

        controls_layout.addStretch()

        # Bottom layout (Save/Cancel buttons)
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

    def add_ui_element(self):
        # Get selected item from available_ui_elements_list
        selected_item = self.available_ui_elements_list.currentItem()

        if selected_item:
            # Add the selected item to the current_ui_elements_list
            new_item = NavigationUIListItem(selected_item._element)
            self.current_ui_elements_list.addItem(new_item)

            self.update_preview()

    def remove_ui_element(self):
        # Get selected item from current_ui_elements_list
        selected_item = self.current_ui_elements_list.currentItem()

        if selected_item:
            # Remove the selected item from the current_ui_elements_list
            self.current_ui_elements_list.takeItem(self.current_ui_elements_list.row(selected_item))

            self.update_preview()
    
    def move_element_up(self):
        current_row = self.current_ui_elements_list.currentRow()
        if current_row > 0:
            item = self.current_ui_elements_list.takeItem(current_row)
            self.current_ui_elements_list.insertItem(current_row - 1, item)
            self.current_ui_elements_list.setCurrentRow(current_row - 1)

            self.update_preview()

    def move_element_down(self):
        current_row = self.current_ui_elements_list.currentRow()
        if 0 <= current_row < self.current_ui_elements_list.count() - 1:
            item = self.current_ui_elements_list.takeItem(current_row)
            self.current_ui_elements_list.insertItem(current_row + 1, item)
            self.current_ui_elements_list.setCurrentRow(current_row + 1)

            self.update_preview()
        
    def customise_styling(self):
        selected_item = self.current_ui_elements_list.currentItem()

        if selected_item:
            current_styling = selected_item._element.styling or NavigationUIAdditionalStyling()
            dialog = CustomiseStylingDialog(self, styling=current_styling, element_type=selected_item._element.type)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # Update the styling of the selected item
                selected_item._element.styling = dialog.styling
                self.update_preview()

    def clear_layout(self, layout):
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
                else:
                    self.clear_layout(item.layout())
    
    def _on_bar_select_changed(self, index):
        self._save_current_bar()
        self.current_ui_elements_list.clear()

        if index == 0:
            self.current_bar = "top"
            self._populate_from_layout(self.current_layout["top"])
        
        elif index == 1:
            self.current_bar = "bottom"
            self._populate_from_layout(self.current_layout["bottom"])
    
    def update_preview(self):
        # Clear the preview layout
        self.clear_layout(self.preview_frame_layout)

        for i in range(self.current_ui_elements_list.count()):
            list_item = self.current_ui_elements_list.item(i)
            widget = self.create_widget(list_item._element)
            self.preview_frame_layout.addWidget(widget)

    def create_widget(self, item: NavigationUIElement):
        if item.type == "button":
            button = QPushButton()
            button.setStyleSheet("padding: 8px;")
            resolved_icon = self._resolve_icon(item.action, item.icon)

            if resolved_icon:
                button.setIcon(qta.icon(resolved_icon))
            
            if item.styling:
                self.apply_styling_to_widget(button, item.styling)

            return button

        elif item.type == "urlbar":
            line = QLineEdit()
            line.setStyleSheet("padding: 8px;")
            line.setReadOnly(True)
            line.setPlaceholderText("https://")

            if item.styling:
                self.apply_styling_to_widget(line, item.styling)

            return line
        
        elif item.type == "searchbar":
            line = QLineEdit()
            line.setStyleSheet("padding: 8px;")
            line.setReadOnly(True)
            line.setPlaceholderText("Search...")

            if item.styling:
                self.apply_styling_to_widget(line, item.styling)

            return line
        
        elif item.type == "spacer":
            spacer = QWidget()
            spacer.setStyleSheet("background: transparent; border: none;")
            spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

            return spacer
        
        elif item.type == "label":
            label = QLabel()
            label.setStyleSheet("padding: 8px; border: none;")

            if item.styling:
                self.apply_styling_to_widget(label, item.styling)

            return label
        
        elif item.type == "dyn_label":
            label = QLabel("100%")
            label.setStyleSheet("padding: 8px; border: none;")

            if item.styling:
                self.apply_styling_to_widget(label, item.styling)

            return label
        
        elif item.type == "progress_bar":
            progress_bar = QProgressBar()
            progress_bar.setMaximum(100)
            progress_bar.setValue(50)
            progress_bar.setTextVisible(True)

            return progress_bar
        
        else:
            label = QLabel(item.name)
            label.setStyleSheet("padding: 8px;")
            return label
    
    def apply_styling_to_widget(self, widget, styling: NavigationUIAdditionalStyling):
        updated_stylesheet = ""

        if styling.background_color:
            updated_stylesheet += f"background-color: {styling.background_color}; "
        if styling.border_radius:
            updated_stylesheet += f"border-radius: {styling.border_radius}px; "
        if styling.stretch_factor:
            widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        widget.setStyleSheet(widget.styleSheet() + updated_stylesheet)
        
        # Check if the widget is a QPushButton QLineEdit or QLabel to add label
        if isinstance(widget, QPushButton) and styling.label:
            widget.setText(styling.label)
        elif isinstance(widget, QLineEdit) and styling.label:
            widget.setPlaceholderText(styling.label)
        elif isinstance(widget, QLabel) and styling.label:
            widget.setText(styling.label)
    
    def get_current_ui_elements(self) -> dict[str, list[NavigationUIElement]]:
        self._save_current_bar()
        return self.current_layout

    def get_current_ui_elements_dict(self) -> dict[str, list[dict]]:
        self._save_current_bar()
        return {
            "top": [asdict(e) for e in self.current_layout["top"]],
            "bottom": [asdict(e) for e in self.current_layout["bottom"]],
        }

    def _save_current_bar(self):
        self.current_layout[self.current_bar] = [
            self.current_ui_elements_list.item(i)._element
            for i in range(self.current_ui_elements_list.count())
        ]

class CustomiseStylingDialog(QDialog):
    def __init__(self, parent, styling: NavigationUIAdditionalStyling | None = None, element_type: str = ""):
        super().__init__(parent)

        self.setWindowTitle(self.tr("Customize Styling"))
        self.setFixedSize(400, 300)

        self.styling = styling if styling else NavigationUIAdditionalStyling()
        self.element_type = element_type

        self.init_ui()
    
    def init_ui(self):
        self.layout = QVBoxLayout(self)

        # Title
        self.title_label = QLabel(self.tr("Customize Styling"))
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet("font-size: 20px; font-weight: bold;")
        self.layout.addWidget(self.title_label)

        # Form layout for styling options
        self.form_layout = QFormLayout()
        self.layout.addLayout(self.form_layout)

        # Background color
        self.bg_color_button = QColorButton(color=self.styling.background_color)
        self.form_layout.addRow(self.tr("Background Color:"), self.bg_color_button)

        # Border radius
        self.border_radius_spinbox = QSpinBox()
        self.border_radius_spinbox.setRange(0, 100)
        self.border_radius_spinbox.setValue(self.styling.border_radius if self.styling.border_radius is not None else 0)
        self.form_layout.addRow(self.tr("Border Radius:"), self.border_radius_spinbox)

        # Stretch factor
        self.stretch_factor_spinbox = QSpinBox()
        self.stretch_factor_spinbox.setRange(0, 10)
        self.stretch_factor_spinbox.setValue(self.styling.stretch_factor if self.styling.stretch_factor is not None else 0)
        self.form_layout.addRow(self.tr("Stretch Factor:"), self.stretch_factor_spinbox)

        # Label
        self.label_lineedit = QLineEdit()
        self.label_lineedit.setText(self.styling.label if self.styling.label is not None else "")

        if self.element_type == "dyn_label":
            self.label_lineedit.setEnabled(False)
            self.label_lineedit.setPlaceholderText(self.tr("Dynamic - cannot be customized"))
        
        self.form_layout.addRow(self.tr("Label:"), self.label_lineedit)

        # Dialog buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        self.reset_button = QPushButton(self.tr("Reset"))
        self.reset_button.clicked.connect(self.reset_styling)
        self.button_box.addButton(self.reset_button, QDialogButtonBox.ButtonRole.ResetRole)

        self.layout.addWidget(self.button_box)

    def reset_styling(self):
        self.bg_color_button.setColor(None)
        self.border_radius_spinbox.setValue(0)
        self.stretch_factor_spinbox.setValue(0)
        self.label_lineedit.setText("")

    def accept(self):
        # Update the styling based on user input
        self.styling.background_color = self.bg_color_button.color()
        self.styling.border_radius = self.border_radius_spinbox.value()
        self.styling.stretch_factor = self.stretch_factor_spinbox.value()
        if self.label_lineedit.isEnabled():
            self.styling.label = self.label_lineedit.text()

        super().accept()