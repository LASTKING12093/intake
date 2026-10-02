import hashlib
import time
import urllib.request
from pathlib import Path
from PySide6.QtCore import QObject, Qt, QThreadPool
from PySide6.QtGui import QPixmap, QImage, QImageReader
from app.workers.task import Task
from app.utils.paths import data_dir


class Thumbnails(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(3)
        self.cache = data_dir() / "cache" / "thumbnails"
        self.cache.mkdir(parents=True, exist_ok=True)
        self.pending = {}
        QImageReader.setAllocationLimit(32)
        for path in self.cache.glob("*.jpg"):
            if time.time() - path.stat().st_mtime > 30 * 86400:
                path.unlink(missing_ok=True)

    def load(self, url, label, width=140, height=80):
        if not url or not url.startswith("https://"):
            return
        path = self.cache / (hashlib.sha256(url.encode()).hexdigest() + ".jpg")
        def display(pixmap):
            try:
                label.setPixmap(pixmap.scaled(width, height, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation))
            except RuntimeError:
                pass  # Card was removed while the request was in flight.
        if path.exists():
            display(QPixmap(str(path)))
            return
        if url in self.pending:
            self.pending[url].append(display)
            return
        self.pending[url] = [display]
        def acquire():
            # DNS/proxy discovery, download and decode all stay off the UI thread.
            request = urllib.request.Request(url, headers={"User-Agent": "MediaGrab/1.0"})
            with urllib.request.urlopen(request, timeout=15) as response:
                data = response.read(3 * 1024 * 1024 + 1)
            if len(data) > 3 * 1024 * 1024:
                return QImage()
            image = QImage.fromData(data)
            if not image.isNull():
                image = image.scaled(320, 180, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                image.save(str(path), "JPG", 82)
            return image
        def done(image):
            if not image.isNull():
                pixmap = QPixmap.fromImage(image)
                for callback in self.pending.get(url, []):
                    callback(pixmap)
        task = Task(acquire)
        task.signals.result.connect(done)
        task.signals.finished.connect(lambda: self.pending.pop(url, None))
        self.pool.start(task)
