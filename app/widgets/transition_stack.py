"""Directional page transitions with an interruptible outgoing snapshot."""
from PySide6.QtCore import QPoint, Qt, QTimer
from PySide6.QtWidgets import QStackedWidget, QLabel, QGraphicsOpacityEffect
from shiboken6 import isValid
from app.ui.motion import Motion


class TransitionStack(QStackedWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._outgoing = None
        self._introduced = False

    def showEvent(self, event):
        super().showEvent(event)
        if not self._introduced:
            self._introduced = True
            QTimer.singleShot(0, self.introduce)

    def introduce(self):
        page = self.currentWidget()
        if page is not None:
            origin = self.contentsRect().topLeft()
            Motion.appear(page)
            Motion.animate(page, b'pos', origin, 'soft', start=origin + QPoint(0, 20))

    def setCurrentIndex(self, index):
        previous = self.currentIndex()
        if previous == index or not 0 <= index < self.count():
            return
        if self._outgoing is not None and isValid(self._outgoing):
            self._outgoing.hide()
            self._outgoing.deleteLater()
        old = self.currentWidget()
        snapshot = old.grab() if old is not None and self.isVisible() else None
        super().setCurrentIndex(index)
        page = self.currentWidget()
        direction = 1 if index > previous else -1
        origin = self.contentsRect().topLeft()
        Motion.appear(page)
        if snapshot is not None:
            layer = QLabel(self)
            layer.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            layer.setPixmap(snapshot)
            layer.setGeometry(self.contentsRect())
            layer.show()
            layer.raise_()
            self._outgoing = layer
            effect = QGraphicsOpacityEffect(layer)
            layer.setGraphicsEffect(effect)
            Motion.animate(layer, b'pos', origin - QPoint(32 * direction, 0), 'default', start=origin)
            Motion.animate(effect, b'opacity', 0.0, 'default', start=1.0, finished=layer.deleteLater)
        Motion.animate(page, b'pos', origin, 'soft', start=origin + QPoint(48 * direction, 0))
