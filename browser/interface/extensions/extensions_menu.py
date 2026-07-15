from PySide6.QtWidgets import (
    QMenu,
)
from PySide6.QtCore import Signal, QObject
from PySide6.QtGui import QAction

class WebExtensionsMenuSignals(QObject):
    request_manage_extensions = Signal()

class WebExtensionsMenu(QMenu):
    def __init__(self):
        super().__init__()

        self.signals = WebExtensionsMenuSignals()

        self.init_ui()
    
    def init_ui(self):
        # Add base actions
        manage_extensions_action = QAction(self.tr("Manage Extensions"), self)
        manage_extensions_action.triggered.connect(self.signals.request_manage_extensions.emit)

        self.addSeparator()
        self.addAction(manage_extensions_action)