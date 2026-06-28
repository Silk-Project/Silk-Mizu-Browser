from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QFileDialog,
    QSizePolicy,
)

class QDirDialogBtn(QWidget):
    def __init__(self, default_path:str=None):
        super().__init__()

        self.current_path = default_path

        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self.path_select_btn = QPushButton("Select directory...")
        self.path_select_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.path_select_btn.clicked.connect(self.select_file)
        layout.addWidget(self.path_select_btn)

        self.path_label = QLabel(self.current_path if self.current_path else "No directory selected")
        layout.addWidget(self.path_label)
    
    def select_file(self):
        directory = QFileDialog.getExistingDirectory(self, self.tr("Select a directory"))
        
        if directory:
            self.current_path = directory

            if len(self.current_path) > 40:
                self.path_label.setText(self.current_path[:40] + "...")

            else:
                self.path_label.setText(self.current_path)

            self.path_label.setToolTip(self.current_path)