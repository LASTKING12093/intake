from pathlib import Path
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QLabel, QPushButton, QComboBox, QMessageBox


def label(text, name="", wrap=False):
    widget = QLabel(text)
    widget.setObjectName(name)
    widget.setWordWrap(wrap)
    return widget


def button(text, callback=None, name=""):
    widget = QPushButton(text)
    widget.setFixedHeight(44)
    widget.setObjectName(name)
    widget.setCursor(__import__("PySide6.QtCore", fromlist=["Qt"]).Qt.CursorShape.PointingHandCursor)
    if callback:
        widget.clicked.connect(callback)
    return widget


def combo(items, current=None):
    widget = QComboBox()
    widget.setMinimumHeight(44)
    widget.addItems(items)
    if current in items:
        widget.setCurrentText(current)
    return widget


def open_path(path, parent=None):
    if not path or not Path(path).exists():
        if parent:
            QMessageBox.information(parent, "File not found", "This file or folder has been moved or deleted.")
        return False
    return QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(path).resolve())))


def duration(seconds):
    seconds = int(seconds or 0)
    if seconds >= 3600:
        return f"{seconds // 3600}:{seconds // 60 % 60:02}:{seconds % 60:02}"
    return f"{seconds // 60}:{seconds % 60:02}"


def size_text(number):
    if not isinstance(number, (int, float)) or number <= 0:
        return "—"
    for unit in ("B", "KB", "MB", "GB"):
        if number < 1024 or unit == "GB":
            return f"{number:.1f} {unit}"
        number /= 1024
