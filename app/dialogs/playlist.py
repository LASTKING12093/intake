from app.widgets.surfaces import Artwork
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView
from app.widgets.common import label, button, duration
from app.ui.assets import icon


class PlaylistDialog(QDialog):
    def __init__(self, info, thumbnails, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Playlist detected")
        self.resize(800, 620)
        self.entries = [e for e in info.get("entries", []) if e]
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.addWidget(label("Playlist detected", "title"))
        layout.addWidget(label(f"{info.get('title', 'Playlist')}  ·  {len(self.entries)} items", "muted", True))
        controls = QHBoxLayout()
        controls.addWidget(button("Select all", lambda: self.select("all")))
        controls.addWidget(button("Select none", lambda: self.select("none")))
        controls.addWidget(button("Invert selection", lambda: self.select("invert")))
        controls.addStretch()
        layout.addLayout(controls)
        self.table = QTableWidget(len(self.entries), 4)
        self.table.setHorizontalHeaderLabels(["#", "Preview", "Media", "Duration"])
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 66)
        self.table.setColumnWidth(1, 94)
        self.table.setColumnWidth(3, 82)
        for row, entry in enumerate(self.entries):
            item = QTableWidgetItem(str(row + 1))
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            self.table.setItem(row, 0, item)
            thumb = Artwork()
            thumb.setPixmap(icon("music-2", size=28).pixmap(28,28))
            thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setCellWidget(row, 1, thumb)
            thumbnail = entry.get("thumbnail") or next((t["url"] for t in reversed(entry.get("thumbnails", [])) if t.get("url")), "")
            entry["thumbnail"] = thumbnail
            self.table.setItem(row, 2, QTableWidgetItem(entry.get("title") or "Unavailable item"))
            self.table.setItem(row, 3, QTableWidgetItem(duration(entry.get("duration"))))
            self.table.setRowHeight(row, 54)
        self.thumbnails = thumbnails
        self.loaded = set()
        self.table.verticalScrollBar().valueChanged.connect(self.load_visible)
        layout.addWidget(self.table, 1)
        bottom = QHBoxLayout()
        bottom.addWidget(button("Cancel", self.reject))
        bottom.addStretch()
        bottom.addWidget(button("Download entire playlist", self.entire))
        bottom.addWidget(button("Download selected", self.accept, "primary"))
        layout.addLayout(bottom)

    def showEvent(self, event):
        super().showEvent(event)
        self.load_visible()

    def load_visible(self):
        start = max(0, self.table.rowAt(0))
        end = self.table.rowAt(self.table.viewport().height() - 1)
        if end < 0:
            end = min(len(self.entries) - 1, start + 12)
        for row in range(start, end + 1):
            if row not in self.loaded:
                self.loaded.add(row)
                self.thumbnails.load(self.entries[row].get("thumbnail", ""), self.table.cellWidget(row, 1), 90, 50)

    def select(self, mode):
        for row in range(len(self.entries)):
            item = self.table.item(row, 0)
            checked = mode == "all" or (mode == "invert" and item.checkState() != Qt.CheckState.Checked)
            item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)

    def entire(self):
        self.select("all")
        self.accept()

    def selected(self):
        return [(row + 1, entry) for row, entry in enumerate(self.entries) if self.table.item(row, 0).checkState() == Qt.CheckState.Checked]
