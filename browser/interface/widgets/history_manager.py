import re
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QScrollArea,
    QLineEdit,
    QPushButton,
    QComboBox,
    QLabel,
    QMessageBox,
)
from PySide6.QtCore import Qt, Signal
import qtawesome as qta
from services.history_mgr import HistoryEntryData


class HistoryEntryWidget(QWidget):
    selected = Signal(str)
    delete_requested = Signal(object)

    def __init__(self, entry: HistoryEntryData, parent=None):
        super().__init__(parent)
        self.entry = entry
        self._init_ui()

    def _init_ui(self):
        row = QHBoxLayout(self)
        row.setContentsMargins(4, 4, 4, 4)
        row.setSpacing(8)

        display_title = self.entry.title if self.entry.title else "No title"
        time_str = self.entry.visited_at.strftime("%H:%M")

        btn_label = f"{display_title}  —  {time_str}"
        btn = QPushButton(btn_label)
        btn.setStyleSheet("text-align: left; padding: 8px; font-size: 13px;")
        btn.setToolTip(self.entry.url)
        btn.clicked.connect(lambda: self.selected.emit(self.entry.url))
        row.addWidget(btn, 1)

        del_btn = QPushButton()
        del_btn.setIcon(qta.icon("fa6s.xmark", color="gray"))
        del_btn.setFixedSize(28, 28)
        del_btn.setStyleSheet("padding: 4px;")
        del_btn.setToolTip("Delete entry")
        del_btn.clicked.connect(lambda: self.delete_requested.emit(self.entry))
        row.addWidget(del_btn)


class HistoryManagerWidget(QWidget):
    history_entry_selected = Signal(str)

    def __init__(self, history_manager, theme_manager, parent=None):
        super().__init__(parent)
        self.history_manager = history_manager
        self.theme_manager = theme_manager
        self._entries = []
        self._sort_order = "latest"
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(0)

        controls_layout = QHBoxLayout()
        layout.addLayout(controls_layout)

        controls_layout.addStretch()

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText(self.tr("Search history..."))
        self.search_bar.setClearButtonEnabled(True)
        self.search_bar.setStyleSheet("margin: 10px; padding: 8px; font-size: 14px;")
        self.search_bar.textChanged.connect(self._filter)
        controls_layout.addWidget(self.search_bar)

        self.sort_combo = QComboBox()
        self.sort_combo.addItems([self.tr("Latest first"), self.tr("Oldest first")])
        self.sort_combo.setStyleSheet("margin: 10px; padding: 4px; font-size: 14px;")
        self.sort_combo.currentIndexChanged.connect(self._on_sort_changed)
        controls_layout.addWidget(self.sort_combo)

        self.clear_btn = QPushButton(" " + self.tr("Clear History"))
        self.clear_btn.setIcon(qta.icon("fa6s.trash"))
        self.clear_btn.setStyleSheet("margin: 10px; padding: 8px; font-size: 14px;")
        self.clear_btn.clicked.connect(self._clear_history)
        controls_layout.addWidget(self.clear_btn)

        controls_layout.addStretch()

        scroll = QScrollArea()
        scroll.setProperty("class", "noborder")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.history_list = QWidget()
        self.history_list_layout = QVBoxLayout(self.history_list)
        self.history_list_layout.setContentsMargins(10, 10, 10, 10)
        self.history_list_layout.setSpacing(4)
        self.history_list_layout.addStretch()

        scroll.setWidget(self.history_list)
        layout.addWidget(scroll)

    def _on_sort_changed(self, index):
        self._sort_order = "latest" if index == 0 else "oldest"
        self.populate()

    def populate(self):
        layout = self.history_list_layout
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._entries = []
        filter_text = self.search_bar.text().strip()

        grouped = self.history_manager.get_history_grouped_by_date()

        reverse_groups = self._sort_order == "latest"

        for day in sorted(grouped.keys(), reverse=reverse_groups):
            entries = grouped[day]

            entries_sorted = sorted(
                entries,
                key=lambda e: e.visited_at,
                reverse=reverse_groups,
            )

            if filter_text:
                entries_sorted = [
                    e for e in entries_sorted
                    if self._matches_filter(e, filter_text)
                ]

            if not entries_sorted:
                continue

            date_label = QLabel(day.strftime("%B %d, %Y"))
            date_label.setStyleSheet("font-weight: bold; font-size: 13px; padding: 8px 4px 2px 4px;")
            layout.addWidget(date_label)

            for entry in entries_sorted:
                entry_widget = HistoryEntryWidget(entry)
                entry_widget.selected.connect(self.history_entry_selected.emit)
                entry_widget.delete_requested.connect(self._delete_entry)
                self._entries.append(entry_widget)
                layout.addWidget(entry_widget)

        layout.addStretch()

    def _matches_filter(self, entry: HistoryEntryData, pattern):
        text = entry.title + entry.url

        try:
            return bool(re.search(pattern, text, re.IGNORECASE))
        except re.error:
            return pattern.lower() in text.lower()

    def _delete_entry(self, entry: HistoryEntryData):
        self.history_manager.delete_entry(entry)
        self.populate()

    def _clear_history(self):
        reply = QMessageBox.question(
            self,
            "Clear History",
            "Are you sure you want to clear all history?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.history_manager.clear_history()
            self.populate()

    def _filter(self, text):
        self.populate()
