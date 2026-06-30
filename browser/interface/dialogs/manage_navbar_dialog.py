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
    QFrame
)
from PySide6.QtCore import Qt, QSize
import copy
import qtawesome as qta
from dataclasses import dataclass, asdict

@dataclass
class NavigationUIElement:
    name: str
    type: str
    icon: str | None = None
    action: str = ""

class NavigationUIListItem(QListWidgetItem):
    def __init__(self, data: NavigationUIElement):
        super().__init__()

        self._element = data
        self.setSizeHint(QSize(40, 25))
        self.setText(self._element.name)

class ManageNavigationUIDialog(QDialog):
    def __init__(self, parent, passed_layout):
        super().__init__(parent)

        self.setWindowFilePath(self.tr("Manage Navigation UI"))
        self.setFixedSize(480, 360)

        self.passed_layout = passed_layout

        self.available_ui_elements = [
            NavigationUIElement("Back Button", "button", "fa6s.arrow-left", "back"),
            NavigationUIElement("Forward Button", "button", "fa6s.arrow-right", "forward"),
            NavigationUIElement("Reload Button", "button", "fa6s.rotate-right", "reload"),
            NavigationUIElement("Bookmark Button", "button", "fa6s.bookmark", "bookmark"),
            NavigationUIElement("Address Bar", "urlbar", None, "address_bar"),
            NavigationUIElement("Search Bar", "searchbar", None, "search_bar"),
            NavigationUIElement("New Tab Button", "button", "fa6s.plus", "new_tab"),
            NavigationUIElement("Settings Button", "button", "fa6s.gear", "settings"),
            NavigationUIElement("Extensions Button", "button", "fa6s.puzzle-piece", "extensions"),
            NavigationUIElement("Extensions Sidebar Button", "button", "msc.layout-sidebar-left", "extensions_sidebar"),
            NavigationUIElement("Go Button", "button", "mdi.arrow-right-bold-box", "go"),
            NavigationUIElement("Download Manager Button", "button", "ei.download", "download_manager"),
            NavigationUIElement("Stretch Space", "spacer", None, "stretch")
        ]

        self.init_ui()
        self._populate_from_layout()

    def _resolve_icon(self, action: str, icon: str | None) -> str | None:
        if icon:
            return icon
        
        for available in self.available_ui_elements:
            if available.action == action:
                return available.icon
            
        return None

    def _populate_from_layout(self):
        for elem in self.passed_layout:
            action = elem.get("action", "")
            icon = self._resolve_icon(action, elem.get("icon"))
            item = NavigationUIListItem(NavigationUIElement(
                name=elem.get("name", ""),
                type=elem.get("type", ""),
                icon=icon,
                action=action
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

        # Top view (UI preview)
        self.preview_frame = QWidget()
        self.preview_frame.setMinimumHeight(50)
        self.preview_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.preview_frame.setStyleSheet("border: 1px solid #414242; border-radius: 3px;")
        self.layout.addWidget(self.preview_frame)

        self.preview_frame_layout = QHBoxLayout()
        self.preview_frame.setLayout(self.preview_frame_layout)

        self.preview_frame_layout.addStretch()

        # Middle layout (UI controls) -> QHBoxLayout (Current UI elements, Available UI elements, Add/Remove buttons)
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
        self.add_element_btn.clicked.connect(self.add_ui_element)
        controls_layout.addWidget(self.add_element_btn)

        self.remove_element_btn = QPushButton(self.tr("Remove"))
        self.remove_element_btn.clicked.connect(self.remove_ui_element)
        controls_layout.addWidget(self.remove_element_btn)

        self.move_up_btn = QPushButton(self.tr("Move Up"))
        self.move_up_btn.clicked.connect(self.move_element_up)
        controls_layout.addWidget(self.move_up_btn)

        self.move_down_btn = QPushButton(self.tr("Move Down"))
        self.move_down_btn.clicked.connect(self.move_element_down)
        controls_layout.addWidget(self.move_down_btn)

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

    def clear_layout(self, layout):
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
                else:
                    self.clear_layout(item.layout())
    
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

            return button

        elif item.type == "urlbar":
            line = QLineEdit()
            line.setStyleSheet("padding: 8px;")
            line.setReadOnly(True)
            line.setPlaceholderText("https://")

            return line
        
        elif item.type == "searchbar":
            line = QLineEdit()
            line.setStyleSheet("padding: 8px;")
            line.setReadOnly(True)
            line.setPlaceholderText("Search...")

            return line
        
        elif item.type == "spacer":
            spacer = QWidget()
            spacer.setStyleSheet("background: transparent; border: none;")
            spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

            return spacer
        
        else:
            label = QLabel(item.name)
            label.setStyleSheet("padding: 8px;")
            return label
    
    def get_current_ui_elements(self) -> list[NavigationUIElement]:
        return [self.current_ui_elements_list.item(i)._element for i in range(self.current_ui_elements_list.count())]
    
    def get_current_ui_elements_dict(self) -> list[dict]:
        return [asdict(self.current_ui_elements_list.item(i)._element) for i in range(self.current_ui_elements_list.count())]