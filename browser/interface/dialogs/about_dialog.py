from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QDialog,
    QLabel,
    QDialogButtonBox,
    QTabWidget,
)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt
from services.constants import LOGO_PATH, VERSION_NUMBER
import os

class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setFixedSize(240, 325)
        self.setWindowTitle(self.tr("About"))
        self.dlg_layout = QVBoxLayout()
        self.setLayout(self.dlg_layout)

        self.init_ui()

    def init_ui(self):
        top_layout = QHBoxLayout()
        top_info_layout = QVBoxLayout()

        logoLabel = QLabel(self)
        logoLabel.setFixedSize(80, 80)
        logoLabel.setScaledContents(True)
        
        if os.path.exists(LOGO_PATH):
            logoLabel.setPixmap(QPixmap(LOGO_PATH))

        top_layout.addWidget(logoLabel, alignment=Qt.AlignmentFlag.AlignCenter)

        about_title = QLabel("Mizu Browser")
        about_title.setStyleSheet("font-size: 17px; font-weight: bold;")
        top_info_layout.addWidget(about_title)

        about_label = QLabel(f"Version: {VERSION_NUMBER}")
        about_label.setWordWrap(True)
        top_info_layout.addWidget(about_label)

        top_info_layout.addWidget(QLabel())

        self.dlg_layout.addLayout(top_layout)
        top_layout.addLayout(top_info_layout)
        top_layout.addStretch()

        # Add tab widget
        tab_widget = QTabWidget()
        self.dlg_layout.addWidget(tab_widget)

        # About tab
        about_tab = QWidget()
        about_layout = QVBoxLayout()
        about_tab.setLayout(about_layout)

        about_description = QLabel("A simple PySide6 browser for Silk and Linux devices.\nSilk Project 2025-2026")
        about_description.setWordWrap(True)
        about_layout.addWidget(about_description)

        about_layout.addStretch()

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        button_box.setContentsMargins(0, 8, 0, 8)
        button_box.accepted.connect(self.accept)

        tab_widget.addTab(about_tab, "About")

        self.dlg_layout.addWidget(button_box, alignment=Qt.AlignmentFlag.AlignCenter)

        # Components tab
        components_tab = QWidget()
        components_layout = QVBoxLayout()
        components_tab.setLayout(components_layout)

        components = [{
            "name": "PySide6 (Qt)",
            "version":"6.11.0",
            "license":"LGPL-3.0"
        }]

        for component in components:
            item = QWidget()
            item.setStyleSheet("border: 1px solid #3f4042; border-radius: 3px;")
            item_layout = QVBoxLayout()
            item.setLayout(item_layout)

            name = QLabel(component.get("name", "No name"))
            name.setStyleSheet("font-weight: bold; border: none;")

            version = QLabel(component.get("version", "No version"))
            version.setStyleSheet("color: grey; border: none;")

            license = QLabel(component.get("license", "No license"))
            license.setStyleSheet("color: grey; border: none;")

            item_layout.addWidget(name)
            item_layout.addWidget(version)
            item_layout.addWidget(license)

            components_layout.addWidget(item)

        components_layout.addStretch()
        
        tab_widget.addTab(components_tab, "Components")