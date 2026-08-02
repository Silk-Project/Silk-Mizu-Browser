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
    QFrame,
    QScrollArea
)
import pyperclip
from PySide6.QtCore import Qt, Slot, Signal, QThreadPool, QRunnable, QObject, QTimer
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

class MessageBox(QFrame):
    def __init__(self, message: dict, color: str = "#464646", parent = None):
        super().__init__(parent)

        self.message: dict = message
        self.color: str = color

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self.setStyleSheet(f"padding: 4px; border-radius: 16px; background-color: {self.color}")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)

        self.content_textedit = QTextEdit()
        self.content_textedit.setReadOnly(True)
        self.content_textedit.setStyleSheet("border: none;")
        self.content_textedit.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        layout.addWidget(self.content_textedit)

        role = self.message.get("role", "Unknown")
        content = self.message.get("content", "")
        self.content_textedit.setMarkdown(f"**{role}**:\n{content}")

        controls_layout = QHBoxLayout()
        layout.addLayout(controls_layout)

        controls_layout.addStretch()

        self.copy_btn = QPushButton()
        self.copy_btn.setStyleSheet("background-color: none; border: none")
        self.copy_btn.setIcon(qta.icon("fa6s.copy"))
        self.copy_btn.setToolTip("Copy message")
        self.copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.copy_btn.clicked.connect(self._copy_message)
        controls_layout.addWidget(self.copy_btn)

        self.copy_timer = QTimer()
        self.copy_timer.setInterval(500)
        self.copy_timer.timeout.connect(self._reset_icon)

        self.content_textedit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        self.content_textedit.document().contentsChanged.connect(self.adjust_height)

    def adjust_height(self):
        doc = self.content_textedit.document()
        doc.setTextWidth(self.content_textedit.viewport().width())
        height = doc.size().height()
        self.content_textedit.setFixedHeight(int(height) + 8)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.adjust_height()

    def update_color(self, color: str):
        self.color = color
        self.setStyleSheet(f"padding: 4px; border-radius: 16px; background-color: {self.color}")

    def _copy_message(self):
        pyperclip.copy(self.message.get("content", ""))
        self.copy_btn.setIcon(qta.icon("fa6s.check"))
        self.copy_timer.start()

    def _reset_icon(self):
        self.copy_btn.setIcon(qta.icon("fa6s.copy"))
        self.copy_timer.stop()

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

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        self.message_container = QWidget()
        self.message_container_layout = QVBoxLayout(self.message_container)
        self.message_container_layout.setContentsMargins(10, 10, 10, 10)
        self.message_container_layout.setSpacing(4)

        scroll.setWidget(self.message_container)
        self.layout.addWidget(scroll)

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
    
    def send_webpage(self, prompt) -> None:
        prompt = prompt.strip()
        self.messages.append({"role": "User", "content": f"[Sum]: {prompt[:400]}..."})
        self.update_output()

        # Start AI worker
        worker = AI_SummarizationWorker(f"Summarize this text the way your system prompt intended to:\"{prompt}\"")
        worker.signals.chunk_received.connect(self.handle_chunk)
        worker.signals.finished.connect(self.summarization_complete)

        QThreadPool.globalInstance().start(worker)
    
    def clear_output(self) -> None:
        self.messages = []
        self.update_output()
    
    def update_output(self) -> None:
        layout = self.message_container_layout
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        for message in self.messages:
            color = "#464646"

            if message.get("role") == "User":
                color = self.theme_manager.custom_colors['primary']

            message_box = MessageBox(
                message=message,
                color=color
            )
            
            self.message_container_layout.addWidget(message_box)
        
        self.message_container_layout.addStretch()
    
    def handle_chunk(self, chunk) -> None:
        if self.messages and self.messages[-1]['role'] == "AI":
            self.messages[-1]['content'] += chunk
        else:
            self.messages.append({"role": "AI", "content": chunk})
        
        self.update_output()
    
    def summarization_complete(self) -> None:
        self.update_output()

    def get_chat_content(self) -> str:
        formatted_content = ""

        for message in self.messages:
            formatted_content += f"**{message.get("role", "Unknown")}**: {message.get("content", "")}\n"

        return formatted_content

    def download_chat_dlg(self) -> None:
        chat_content = self.get_chat_content()
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
    
    def retranslate_ui(self) -> None:
        self.title_label.setText(self.tr("AI Summary"))
        self.download_chat_btn.setText(self.tr("Download"))
        self.clear_btn.setText(self.tr("Clear"))