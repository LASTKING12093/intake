import io
from PySide6.QtCore import QBuffer, QByteArray, QIODevice
from PySide6.QtGui import QImage, QColor
from PySide6.QtWidgets import QLabel
from app.services.thumbnails import Thumbnails


def test_thumbnail_decode_cache_and_deduplicate(qtbot, monkeypatch):
    image = QImage(640, 360, QImage.Format.Format_RGB32)
    image.fill(QColor("#9876ff"))
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "JPG")
    calls = []
    def fetch(*args, **kwargs):
        calls.append(True)
        return io.BytesIO(bytes(data))
    monkeypatch.setattr("app.services.thumbnails.urllib.request.urlopen", fetch)
    thumbnails = Thumbnails()
    first, second = QLabel(), QLabel()
    qtbot.addWidget(first)
    qtbot.addWidget(second)
    thumbnails.load("https://example.org/test.jpg", first)
    thumbnails.load("https://example.org/test.jpg", second)
    qtbot.waitUntil(lambda: not thumbnails.pending)
    assert not first.pixmap().isNull() and not second.pixmap().isNull()
    assert len(calls) == 1
    assert len(list(thumbnails.cache.glob("*.jpg"))) == 1
    third = QLabel()
    qtbot.addWidget(third)
    thumbnails.load("https://example.org/test.jpg", third)
    assert not third.pixmap().isNull() and len(calls) == 1
    thumbnails.pool.waitForDone()
