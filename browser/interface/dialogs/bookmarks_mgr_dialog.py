from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QPushButton,
    QLineEdit,
    QListWidget,
    QLabel,
    QDialogButtonBox,)
from PySide6.QtCore import Qt, QSize
import copy
import qtawesome as qta

class ManageBookmarksDialog(QDialog):
    def __init__(self, parent, passed_bookmarks, icon_color="black"):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Manage Bookmarks"))
        self.setFixedSize(400, 300)

        self.icon_color = icon_color

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
        icon_color = self.icon_color
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