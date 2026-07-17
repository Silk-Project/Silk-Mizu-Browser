import qtawesome as qta
from PySide6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QProgressBar,
    QSizePolicy,
    QFrame,
)
from PySide6.QtWebEngineCore import QWebEngineDownloadRequest

class DownloadItemWidget(QFrame):
    def __init__(self, download: QWebEngineDownloadRequest, parent=None):
        super().__init__(parent)

        self.setStyleSheet("border: 1px solid #414242; border-radius: 3px;")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.download = download

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.init_ui()
        self.connect_signals()

        # Check if download is already finished
        if self.download.isFinished():
            self.download_finished()
        
        self.update_progress()
    
    def init_ui(self):
        # Download info
        download_filename = self.download.suggestedFileName()

        # Download UI elements
        self.label = QLabel(self.tr('Downloading:') + ' ' + download_filename)
        self.label.setStyleSheet("border: none;")
        self.label.setWordWrap(True)
        self.label.setToolTip(download_filename)

        self.progress = QProgressBar()

        self.stop_btn = QPushButton()
        self.stop_btn.setIcon(qta.icon("ei.remove"))
        self.stop_btn.clicked.connect(lambda: self.download.cancel())
        
        self.layout.addWidget(self.label)

        # Bottom layout (progress bar, button)
        bottom_layout = QHBoxLayout()
        self.layout.addLayout(bottom_layout)

        bottom_layout.addWidget(self.progress)
        bottom_layout.addWidget(self.stop_btn)
    
    def connect_signals(self):
        self.download.receivedBytesChanged.connect(self.update_progress)
        self.download.isFinishedChanged.connect(self.download_finished)
    
    def update_progress(self):
        if self.download.totalBytes() > 0:
            percent = int((self.download.receivedBytes() / self.download.totalBytes()) * 100)
            self.progress.setValue(percent)
    
    def download_finished(self):
        download_filename = self.download.suggestedFileName()
        state = self.download.state()
        self.stop_btn.setEnabled(False)
    
        if state == QWebEngineDownloadRequest.DownloadState.DownloadCompleted:
            self.progress.setValue(100)
            self.label.setText(self.tr('Finished:') + ' ' + download_filename)
        
        elif state == QWebEngineDownloadRequest.DownloadState.DownloadCancelled:
            self.label.setText(self.tr('Canceled:') + ' ' + download_filename)
            self.progress.setEnabled(False)
        
        elif state == QWebEngineDownloadRequest.DownloadState.DownloadInterrupted:
            self.label.setText(self.tr('Error:') + ' ' + download_filename)
            self.progress.setStyleSheet("QProgressBar::chunk { background-color: red; }")