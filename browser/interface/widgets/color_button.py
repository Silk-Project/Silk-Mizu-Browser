from PySide6.QtWidgets import (
    QPushButton,
    QColorDialog,
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QColor

class QColorButton(QPushButton):
    colorChanged = Signal(object)

    def __init__(self, *args, color=None, **kwargs):
        super().__init__(*args, **kwargs)

        self._color = None
        self._default = color if color else "#ffffff"
        self._static_styles = "border-radius: 6px"
        self.setStyleSheet(f"background-color: {self._default}; {self._static_styles}")
        self.pressed.connect(self.onColorPicker)
        self.installEventFilter(self)

        # Set the initial/default state.
        self.setColor(self._default)

    def setColor(self, color):
        if color != self._color:
            self._color = color
            self.colorChanged.emit(color)

        if self._color:
            self.setStyleSheet(f"background-color: {self._color}; {self._static_styles}")
        else:
            self.setStyleSheet("")

    def color(self):
        return self._color

    def onColorPicker(self):
        dlg = QColorDialog(self)
        if self._color:
            dlg.setCurrentColor(QColor(self._color))

        if dlg.exec():
            self.setColor(dlg.currentColor().name())

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.RightButton:
            self.setColor(self._default)

        return super().mousePressEvent(e)