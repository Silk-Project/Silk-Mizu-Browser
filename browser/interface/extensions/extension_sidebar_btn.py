import os
from PySide6.QtWidgets import QPushButton
from PySide6.QtGui import QIcon
from services.constants import EXTENSIONS_PATH
from services.extension_mgr import ExtensionMetadata

class Extension_Sidebar_Button(QPushButton):
    def __init__(self, metadata: ExtensionMetadata, parent=None):
        super().__init__(parent)
        self.metadata = metadata

        self.setFixedSize(35, 35)

        # Icon (if available)
        self.extension_icon_path = os.path.join(EXTENSIONS_PATH, self.metadata.app_id, self.metadata.icon_path)

        if os.path.exists(self.extension_icon_path) and self.metadata.icon_path != "":     
            self.setIcon(QIcon(self.extension_icon_path))
        else:
            self.setText(self.metadata.name[0])