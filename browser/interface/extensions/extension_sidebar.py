import os
import importlib.util
import qtawesome as qta
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QStackedWidget,
)
from services.constants import EXTENSIONS_PATH
from interface.extensions.ai_extension import AI_Extension
from interface.extensions.extension_sidebar_btn import Extension_Sidebar_Button
from PySide6.QtCore import Qt

class Extension_Sidebar(QWidget):
    def __init__(self, parent, extension_manager, theme_manager, ai_enabled=False):
        super().__init__(parent)
        self.setFixedWidth(50)
        self.sidebar_layout = QHBoxLayout()
        self.sidebar_layout.setContentsMargins(5, 5, 5, 5)
        self.sidebar_layout.setSpacing(5)

        self.extension_manager = extension_manager
        self.theme_manager = theme_manager
        self.showing_extension = False
        self.extension_btns = {}

        self.setLayout(self.sidebar_layout)

        self.init_ui()
        self.load_extensions(ai_enabled)
    
    def init_ui(self):
        self.extension_bar_layout = QVBoxLayout()
        self.rounded_sec_border = QStackedWidget()
        
        self.rounded_sec_border.setStyleSheet("border-radius: 3px;")
        self.rounded_sec_border.hide()

        self.sidebar_layout.addLayout(self.extension_bar_layout)
        self.sidebar_layout.addWidget(self.rounded_sec_border)

    def load_extensions(self, ai_extensions_enabled: bool = False):
        self.clear_layout(self.extension_bar_layout)

        while self.rounded_sec_border.count() > 0:
            widget = self.rounded_sec_border.widget(0)
            self.rounded_sec_border.removeWidget(widget)
            widget.deleteLater()
        
        self.extension_manager.update_extension_list()
        extensions = self.extension_manager.get_installed()

        self.extension_bar_layout.addStretch()

        # Extension content
        if ai_extensions_enabled:
            ai_sum_ext_btn = QPushButton()
            ai_sum_ext_btn.setIcon(qta.icon("msc.sparkle-filled"))
            ai_sum_ext_btn.setFixedSize(35, 35)
            ai_sum_ext_btn.clicked.connect(lambda _, i=0: self.toggle_extension(i))
            self.extension_bar_layout.addWidget(ai_sum_ext_btn, alignment=Qt.AlignmentFlag.AlignHCenter)

            self.ai_sum_ext = AI_Extension(self, theme_manager=self.theme_manager)
            self.rounded_sec_border.addWidget(self.ai_sum_ext)

        for i, el in enumerate(extensions):
            try:
                spec = spec = importlib.util.spec_from_file_location(
                        el.name, 
                        os.path.join(EXTENSIONS_PATH, el.app_id, el.script_path)
                    )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                plugin_class = getattr(module, "MainWidget")
                plugin_instance = plugin_class()
                
                self.rounded_sec_border.addWidget(plugin_instance)

                button = Extension_Sidebar_Button(el)

                if not ai_extensions_enabled:
                    button.clicked.connect(lambda _, i=i: self.toggle_extension(i))

                else:
                    button.clicked.connect(lambda _, i=i: self.toggle_extension(i+1))
                
                self.extension_bar_layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignHCenter)
                
            except Exception as e:
                print(f"Error when trying to load {el.name}: {e}")

        self.extension_bar_layout.addStretch()
    
    def toggle_extension(self, id):
        if id != self.rounded_sec_border.currentIndex():
            self.rounded_sec_border.setCurrentIndex(id)

            if not self.showing_extension:
                self.showing_extension = True
        else:
            self.showing_extension = not self.showing_extension

        if self.showing_extension:
            self.setFixedWidth(450)
            self.rounded_sec_border.show()

        else:
            self.setFixedWidth(50)
            self.rounded_sec_border.hide()
    
    def get_contrast_color_from_theme(self):
        return self.theme_manager.get_contrast_color_from_theme()
    
    def clear_layout(self, layout):
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
                else:
                    self.clear_layout(item.layout())