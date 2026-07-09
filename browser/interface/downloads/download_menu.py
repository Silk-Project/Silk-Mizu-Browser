import qtawesome as qta
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QProgressBar,
    QMenu,
    QWidgetAction,
)
from PySide6.QtCore import Signal, QObject
from PySide6.QtWebEngineCore import QWebEngineDownloadRequest
from PySide6.QtGui import QAction

class DownloadMenuSignals(QObject):
    downloads_dialog_opened = Signal()

class DownloadMenu(QMenu):
    def __init__(self):
        super().__init__()
        self.signals = DownloadMenuSignals()
        self.manage_downloads_action = QAction("Manage Downloads")
        self.manage_downloads_action.triggered.connect(lambda: self.signals.downloads_dialog_opened.emit())
        self.addAction(self.manage_downloads_action)

    def add_download(self, download: QWebEngineDownloadRequest):
        # Download info
        download_filename = download.suggestedFileName()
        
        # Create layouts for the menu entry
        layout = QVBoxLayout()
        container = QWidget()

        # Download UI elements
        label = QLabel(f"{self.tr('Downloading:')} {self.shorten_if_needed(download_filename)}")
        label.setToolTip(download_filename)
        progress = QProgressBar()
        stop_btn = QPushButton()
        stop_btn.setIcon(qta.icon("ei.remove"))
        stop_btn.clicked.connect(lambda: download.cancel())
        
        layout.addWidget(label)

        # Bottom layout (progress bar, button)
        bottom_layout = QHBoxLayout()
        layout.addLayout(bottom_layout)

        bottom_layout.addWidget(progress)
        bottom_layout.addWidget(stop_btn)

        container.setLayout(layout)

        widget_action = QWidgetAction(self)
        widget_action.setDefaultWidget(container)

        # Insert the new action at the top of the menu
        self.insertAction(self.actions()[0], widget_action)

        # Remove downloads if download amount exceeds 3
        if len(self.actions()) > 4:
            self.removeAction(self.actions()[3])
        
        # 3. Connect signals to track progress and completion
        download.receivedBytesChanged.connect(
            lambda: self.update_progress(download, progress)
        )
        download.isFinishedChanged.connect(
            lambda: self.download_finished(download, label, progress, stop_btn)
        )

    def update_progress(self, download, progress_bar):
        if download.totalBytes() > 0:
            percent = int((download.receivedBytes() / download.totalBytes()) * 100)
            progress_bar.setValue(percent)
    
    def shorten_if_needed(self, download_name):
        if len(download_name) > 15:
            return f"{download_name[:15]}..."
        else:
            return download_name

    def download_finished(self, download, label, progress_bar, stop_btn):
        download_filename = download.suggestedFileName()
        state = download.state()
        stop_btn.setEnabled(False)
    
        if state == QWebEngineDownloadRequest.DownloadState.DownloadCompleted:
            progress_bar.setValue(100)
            label.setText(f"{self.tr('Finished:')} {self.shorten_if_needed(download_filename)}")
        
        elif state == QWebEngineDownloadRequest.DownloadState.DownloadCancelled:
            label.setText(f"{self.tr('Canceled:')} {self.shorten_if_needed(download_filename)}")
            progress_bar.setEnabled(False)
        
        elif state == QWebEngineDownloadRequest.DownloadState.DownloadInterrupted:
            label.setText(f"{self.tr('Error:')} {self.shorten_if_needed(download_filename)}")
            progress_bar.setStyleSheet("QProgressBar::chunk { background-color: red; }")