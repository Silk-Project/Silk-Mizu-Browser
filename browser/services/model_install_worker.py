import ollama
from PySide6.QtCore import Slot, Signal, QRunnable, QObject

class InstallWorkerSignals(QObject):
    installation_complete = Signal()

class InstallWorker(QRunnable):
    def __init__(self, model_name):
        super().__init__()
        self.signals = InstallWorkerSignals()
        self.model_name = model_name
    
    @Slot()
    def run(self):
        print(f"Installing model: {self.model_name}...")
        ollama.pull(self.model_name)
        print("Model installation complete.")
        self.signals.installation_complete.emit()