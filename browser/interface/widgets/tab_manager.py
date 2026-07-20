import re
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QScrollArea,
    QLineEdit,
    QPushButton,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon

class TabManager(QWidget):
    tab_selected = Signal(int)

    def __init__(self, web_tabs, theme_manager, parent=None):
        super().__init__(parent)
        self.web_tabs = web_tabs
        self.theme_manager = theme_manager
        self._buttons = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(0)

        search_layout = QHBoxLayout()
        layout.addLayout(search_layout)

        search_layout.addStretch()

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText(self.tr("Search tabs..."))
        self.search_bar.setClearButtonEnabled(True)
        self.search_bar.setStyleSheet("margin: 10px; padding: 8px; font-size: 14px;")
        self.search_bar.textChanged.connect(self._filter)
        search_layout.addWidget(self.search_bar)

        search_layout.addStretch()

        scroll = QScrollArea()
        scroll.setProperty("class", "noborder")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.tab_list = QWidget()
        self.tab_list_layout = QVBoxLayout(self.tab_list)
        self.tab_list_layout.setContentsMargins(10, 10, 10, 10)
        self.tab_list_layout.setSpacing(4)
        self.tab_list_layout.addStretch()

        scroll.setWidget(self.tab_list)
        layout.addWidget(scroll)

    def populate(self):
        layout = self.tab_list_layout
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.search_bar.clear()
        self._buttons = []

        current_index = self.web_tabs.currentIndex()

        for i in range(self.web_tabs.count()):
            web_engine = self.web_tabs.widget(i)
            title = web_engine.title() if web_engine.title() else "New Tab"
            icon = web_engine.icon() if web_engine.icon() else QIcon()

            btn = QPushButton(title)
            btn.setIcon(icon)
            btn.setStyleSheet("text-align: left; padding: 10px; font-size: 14px;")
            btn.clicked.connect(lambda checked, index=i: self.tab_selected.emit(index))

            if i == current_index:
                accent = self.theme_manager.custom_colors['primary']
                btn.setStyleSheet(
                    f"text-align: left; padding: 10px; font-size: 14px; "
                    f"border-left: 3px solid {accent}; font-weight: bold;"
                )

            self._buttons.append((btn, title, i))
            layout.addWidget(btn)

        layout.addStretch()

    def _filter(self, text):
        pattern = text.strip()

        for btn, title, index in self._buttons:
            if not pattern:
                btn.setVisible(True)
                continue

            try:
                visible = bool(re.search(pattern, title, re.IGNORECASE))
            except re.error:
                visible = pattern.lower() in title.lower()

            btn.setVisible(visible)
