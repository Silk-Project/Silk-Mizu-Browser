from PySide6.QtCore import QObject, Signal
from PySide6.QtWebEngineCore import QWebEngineDownloadRequest
import os

class DownloadManager(QObject):
    download_added = Signal(QWebEngineDownloadRequest)

    def __init__(self):
        super().__init__()
        self.downloads = []
    
    def add_download(self, download: QWebEngineDownloadRequest, downloads_path: str):
        # Download info
        download_filename = download.suggestedFileName()
        os.makedirs(downloads_path, exist_ok=True)

        download.setDownloadDirectory(downloads_path)
        download.setDownloadFileName(download_filename)

        download.accept()
        self.downloads.append(download)
        self.download_added.emit(download)