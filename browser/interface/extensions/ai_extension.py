import os
import datetime
import qtawesome as qta
import ollama
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QMessageBox,
    QSizePolicy,
    QTextEdit,
    QFileDialog,
)
from PySide6.QtCore import Qt, Slot, Signal, QThreadPool, QRunnable, QObject
from services.constants import SUM_AI_MODEL, AI_SYSPROMPT_PATH

# Load AI system prompt
with open(AI_SYSPROMPT_PATH, 'r') as f:
    ai_system_prompt = f.read()

class AI_SummarizationWorkerSignals(QObject):
    chunk_received = Signal(str)
    finished = Signal()

class AI_SummarizationWorker(QRunnable):
    def __init__(self, text):
        super().__init__()
        self.text = text
        self.signals = AI_SummarizationWorkerSignals()
    
    @Slot()
    def run(self):
        print("Summarizing page content...")
        stream = ollama.chat(
            model=SUM_AI_MODEL["name"],
            messages=[{'role': 'system', 'content': ai_system_prompt},
                      {'role': 'user', 'content': self.text}],
            stream=True,
        )

        for chunk in stream:
            content = chunk['message']['content']
            self.signals.chunk_received.emit(content)
        
        self.signals.finished.emit()

class AI_Extension(QWidget):
    def __init__(self, parent, theme_manager):
        super().__init__(parent)
        self.theme_manager = theme_manager
        self.layout = QVBoxLayout()

        self.init_ui()

    def init_ui(self):
        self.messages = []

        self.input_controls_layout = QHBoxLayout()

        self.title_label = QLabel(self.tr("AI Summary"))
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet("font-size: 18px; font-weight: bold; padding: 20px")
        self.layout.addWidget(self.title_label)

        self.output_textedit = QTextEdit()
        self.output_textedit.setReadOnly(True)
        self.output_textedit.setPlaceholderText(self.tr("Summarization output will appear here..."))
        self.output_textedit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.layout.addWidget(self.output_textedit)

        self.download_chat_btn = QPushButton(self.tr("Download"))
        self.download_chat_btn.setIcon(qta.icon("fa6s.download", color=self.theme_manager.get_contrast_color_from_theme()))
        self.download_chat_btn.clicked.connect(self.download_chat_dlg)
        self.input_controls_layout.addWidget(self.download_chat_btn)

        self.clear_btn = QPushButton(self.tr("Clear"))
        self.clear_btn.setIcon(qta.icon("fa6s.trash", color=self.theme_manager.get_contrast_color_from_theme()))
        self.clear_btn.clicked.connect(self.clear_output)
        self.input_controls_layout.addWidget(self.clear_btn)

        self.update_output()

        self.layout.addLayout(self.input_controls_layout)
        self.setLayout(self.layout)
    
    def send_webpage(self, prompt):
        prompt = prompt.strip()
        self.messages.append({"role": "User", "content": f"[Sum]: {prompt[:400]}..."})
        self.update_output()

        # Start AI worker
        worker = AI_SummarizationWorker(f"Summarize this text the way your system prompt intended to:\"{prompt}\"")
        worker.signals.chunk_received.connect(self.handle_chunk)
        worker.signals.finished.connect(self.summarization_complete)

        QThreadPool.globalInstance().start(worker)
    
    def clear_output(self):
        self.messages = []
        self.update_output()
    
    def update_output(self):
        self.output_textedit.clear()

        formatted_output = ""
        for message in self.messages:
            formatted_output += f"**{message["role"]}:**  {message["content"]}\n\n"
        
        self.output_textedit.setMarkdown(formatted_output)
    
    def handle_chunk(self, chunk):
        if self.messages and self.messages[-1]['role'] == "AI":
            self.messages[-1]['content'] += chunk
        else:
            self.messages.append({"role": "AI", "content": chunk})
        
        self.update_output()
    
    def summarization_complete(self):
        self.update_output()

    def download_chat_dlg(self):
        chat_content = self.output_textedit.toMarkdown()
        time_now = datetime.datetime.now()
        time_formatted = time_now.strftime("%H:%M-%d-%m-%Y")
        file_name = f"chat-{time_formatted}.txt"

        if not chat_content:
            return
        
        dir_name = QFileDialog.getExistingDirectory(self, self.tr("Select a Directory"))
        file_path = os.path.join(dir_name, file_name)

        if os.path.exists(file_path):
            QMessageBox.critical(self, self.tr("Cannot write file", f"The file {file_name} already exists in the selected directory."))
        
        with open(file_path, "w") as f:
            f.write(chat_content)
    
    def retranslate_ui(self):
        self.title_label.setText(self.tr("AI Summary"))
        self.output_textedit.setPlaceholderText(self.tr("Summarization output will appear here..."))
        self.download_chat_btn.setText(self.tr("Download"))
        self.clear_btn.setText(self.tr("Clear"))