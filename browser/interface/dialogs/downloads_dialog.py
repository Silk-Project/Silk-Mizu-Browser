import qtawesome as qta
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QDialog,
    QLabel,
    QSizePolicy,
    QScrollArea,
)
from PySide6.QtCore import Qt
from interface.downloads.download_item_widget import DownloadItemWidget

class DownloadManagerDialog(QDialog):
    def __init__(self, downloads, parent=None):
        super().__init__(parent)

        self.setWindowTitle(self.tr("Manage Downloads"))
        self.setFixedSize(624, 468)
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.downloads = downloads

        self.init_ui()
        self.refresh_downloads()
    
    def init_ui(self):
        title_label = QLabel(self.tr("Manage Downloads"))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; padding: 20px;")
        self.layout.addWidget(title_label)

        # Downloads list
        self.downloads_content = QScrollArea()

        self.downloads_widget = QWidget()
        self.downloads_layout = QVBoxLayout()
        self.downloads_controls_layout = QHBoxLayout()
        self.downloads_main_layout = QVBoxLayout()

        self.downloads_layout.addLayout(self.downloads_controls_layout)
        self.downloads_layout.addLayout(self.downloads_main_layout)

        self.downloads_content.setWidget(self.downloads_widget)
        self.downloads_widget.setLayout(self.downloads_layout)
        self.layout.addWidget(self.downloads_content)

        self.downloads_layout.addStretch()

        # Control Buttons
        self.store_tab_refresh_btn = QPushButton(self.tr("Refresh"))
        self.store_tab_refresh_btn.setIcon(qta.icon("ei.refresh"))
        self.store_tab_refresh_btn.setStyleSheet("border: 1px solid #414242; border-radius: 3px; padding: 8px;")
        self.store_tab_refresh_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.store_tab_refresh_btn.clicked.connect(self.refresh_downloads)
        self.downloads_controls_layout.addWidget(self.store_tab_refresh_btn)

        self.downloads_controls_layout.addStretch()

        self.downloads_content.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.downloads_content.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.downloads_content.setWidgetResizable(True)

    def refresh_downloads(self):
        self.clear_layout(self.downloads_main_layout)

        if len(self.downloads) == 0:
            self.downloads_main_layout.addStretch()

            info_label = QLabel(self.tr("No active downloads."))
            info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            info_label.setStyleSheet("color: grey;")
            self.downloads_main_layout.addWidget(info_label)

            self.downloads_main_layout.addStretch()

            return
        
        for download in self.downloads:
            item = DownloadItemWidget(download, self)
            self.downloads_main_layout.addWidget(item)

    def clear_layout(self, layout):
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
                else:
                    self.clear_layout(item.layout())