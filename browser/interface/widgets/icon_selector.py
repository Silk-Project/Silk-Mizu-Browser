from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QGridLayout,
    QPushButton,
    QWidget,
    QLabel,
    QDialogButtonBox,
    QScrollArea,
    QLineEdit,
    QSizePolicy,
)
from PySide6.QtCore import Qt, Signal, QObject
import qtawesome as qta

GRID_WIDTH = 6

class IconDatabase(QObject):
    def __init__(self):
        super().__init__()

        self.icon_database = {
            self.tr("Default"): [
                "fa6s.arrow-left",
                "fa6s.arrow-right",
                "fa6s.arrow-rotate-right",
                "msc.layout-sidebar-left",
                "ri.menu-fill",
                "fa6s.clock-rotate-left",
                "mdi.arrow-right-bold-box",
                "fa6s.download",
                "ph.magnifying-glass-plus",
                "ph.magnifying-glass-minus",
            ],
            self.tr("General"): [
                "fa6s.angle-left",
                "fa6s.angle-right",
                "fa6s.angle-up",
                "fa6s.angle-down",
                "fa6s.arrow-rotate-left",
                "fa6s.arrow-pointer",
                "fa6s.arrows-rotate",
                "fa6s.circle-arrow-left",
                "fa6s.circle-arrow-right",
                "fa6s.circle-arrow-up",
                "fa6s.circle-arrow-down",
                "fa6s.circle-chevron-left",
                "fa6s.circle-chevron-right",
                "fa6s.circle-chevron-up",
                "fa6s.circle-chevron-down",
                "fa6s.circle-left",
                "fa6s.circle-right",
                "fa6s.circle-up",
                "fa6s.circle-down",
                "fa6s.circle",
                "fa6s.circle-dot",
            ],
            self.tr("People"): [
                "ei.adult",
                "ei.child",
                "ei.smiley",
                "ei.user",
                "ei.wheelchair",
                "ei.hand-left",
                "ei.hand-right",
                "ei.hand-down",
                "ei.hand-up",
                "ei.person",
                "ei.torso",
                "ei.universal-access",
            ],
            self.tr("Brands / Companies"): [
                "ei.youtube",
                "ei.wordpress",
                "ei.vkontakte",
                "ei.vimeo",
                "ei.w3c",
                "ei.twitter",
                "ei.tumblr",
                "ei.viadeo",
                "ei.stumbleupon",
                "ei.slideshare",
                "ei.spotify",
                "ei.stackoverflow",
                "ei.soundcloud",
                "ei.skype",
                "ei.reddit",
                "ei.redux",
                "ei.livejournal",
                "ei.instagram",
                "ei.github",
                "ei.foursquare",
                "ei.friendfeed",
                "ei.facebook",
                "ei.blogger",
                "ei.behance",
                "ei.myspace",
                "fa5b.amazon",
                "fa5b.app-store",
            ],
            self.tr("Miscellaneous"): [
                "fa6s.circle-radiation",
                "fa6s.graduation-cap",
                "fa6s.radio",
                "fa6s.hammer",
                "fa5s.adjust",
                "fa5s.anchor",
                "fa6s.dna",
            ]
        }

class FontAwesomeIconSelectorBtn(QPushButton):
    icon_changed = Signal(str)

    def __init__(self, parent=None, icon: str = None):
        super().__init__()

        self.selected_icon = icon

        self.setStyleSheet("padding: 8px;")
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.clicked.connect(self.open_dialog)

        if self.selected_icon is not None:
            try:
                self.setIcon(qta.icon(self.selected_icon))

            except Exception as e:
                print(f"Failed to set icon on button: {e}")
    
    def open_dialog(self):
        dlg = FontAwesomeIconSelector(parent=self)

        if dlg.exec():
            icon = dlg.get_selected_icon()

            if icon != self.selected_icon and icon is not None:
                self.icon_changed.emit(icon)
            
                self.selected_icon = icon
                self.setIcon(qta.icon(self.selected_icon))

class FontAwesomeIconSelector(QDialog):
    def __init__(self, parent=None, icon: str = None):
        super().__init__()

        self.setFixedSize(400, 360)
        self.selected_icon = icon

        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)

        title_label = QLabel(self.tr("Select an icon"))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; padding-top: 20px; padding-bottom: 10px;")
        layout.addWidget(title_label)

        grid = GridIconView()
        grid.icon_selected.connect(self._on_icon_selected)
        layout.addWidget(grid)

        self.icon_name_lineedit = QLineEdit()
        self.icon_name_lineedit.setReadOnly(True)
        self.icon_name_lineedit.setStyleSheet("padding: 8px")
        layout.addWidget(self.icon_name_lineedit)

        layout.addStretch()

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)
    
    def _on_icon_selected(self, icon):
        self.selected_icon = icon
        self.icon_name_lineedit.setText(icon)
    
    def get_selected_icon(self) -> str | None:
        return self.selected_icon

class GridIconView(QWidget):
    icon_selected = Signal(str)

    def __init__(self):
        super().__init__()
        self.setFixedHeight(200)
        self.icons = IconDatabase().icon_database

        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        scroll = QScrollArea()
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.icon_grid = QWidget()
        self.icon_grid_layout = QGridLayout(self.icon_grid)
        self.icon_grid_layout.setContentsMargins(10, 10, 10, 10)
        self.icon_grid_layout.setSpacing(4)
        self._populate_icons()

        scroll.setWidget(self.icon_grid)
        layout.addWidget(scroll)
    
    def _populate_icons(self):
        layout = self.icon_grid_layout
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        row = 0
        col = 0
        group = []

        for category in self.icons.keys():
            title = QLabel(self.tr(category))
            title.setStyleSheet("font-size: 16px; font-weight: bold; padding-top: 10px; padding-bottom: 5px;")

            layout.addWidget(title, row, 0, 1, GRID_WIDTH)

            row += 2
            col = 0

            group = self.icons[category]

            for icon in group:
                button = QPushButton()
                button.clicked.connect(lambda _, icon=icon: self.icon_selected.emit(icon))
                button.setFixedSize(50, 50)
                button.setIcon(qta.icon(icon))

                layout.addWidget(button, row, col)

                col += 1

                if col == GRID_WIDTH:
                    row += 1
                    col = 0

            if col != 0:
                row += 1
                col = 0