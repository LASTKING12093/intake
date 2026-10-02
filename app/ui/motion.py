"""Always-on, interruptible Qt motion: part of the INTAKE interaction model."""
import math
from PySide6.QtCore import QPropertyAnimation, QEasingCurve, QTimer
from shiboken6 import isValid
from PySide6.QtWidgets import QGraphicsOpacityEffect
from app.ui.tokens import MOTION

def critical_spring(t):
    return (1-(1+8*t)*math.exp(-8*t))/(1-9*math.exp(-8))

SPRING = QEasingCurve()
SPRING.setCustomType(critical_spring)

class Motion:
    @classmethod
    def animate(cls, target, prop, end, preset='default', start=None, finished=None):
        key = '_motion_' + prop.decode()
        previous = getattr(target, key, None)
        if previous:
            previous.stop()
            previous.deleteLater()
        animation = QPropertyAnimation(target, prop, target)
        setattr(target, key, animation)
        animation.setDuration(MOTION[preset])
        animation.setEasingCurve(SPRING if preset == 'spring' else QEasingCurve.Type.OutCubic)
        animation.setStartValue(target.property(prop.decode()) if start is None else start)
        animation.setEndValue(end)
        if finished:
            animation.finished.connect(finished)
        animation.start()
        return animation

    @classmethod
    def appear(cls, widget):
        effect = widget.graphicsEffect()
        # Qt opacity effects must not stay layered across parent and child widgets.
        parent = widget.parentWidget()
        while parent is not None:
            ancestor = parent.graphicsEffect()
            if isinstance(ancestor, QGraphicsOpacityEffect) and ancestor.isEnabled():
                return
            parent = parent.parentWidget()
        for child_effect in widget.findChildren(QGraphicsOpacityEffect):
            if child_effect is not effect: child_effect.setEnabled(False)
        if not isinstance(effect, QGraphicsOpacityEffect):
            effect = QGraphicsOpacityEffect(widget)
            widget.setGraphicsEffect(effect)
        effect.setOpacity(0.0)
        effect.setEnabled(True)
        def release():
            # Detach the compositor after the fade, once its animation callback returns.
            if isValid(widget) and isValid(effect) and widget.graphicsEffect() is effect and effect.opacity() >= 1.0:
                widget.setGraphicsEffect(None)
        cls.animate(effect, b'opacity', 1.0, start=0.0,
                    finished=lambda: QTimer.singleShot(0, release))

    @classmethod
    def expand(cls, widget, visible):
        if visible:
            start = widget.height() if widget.isVisible() and widget.maximumHeight() < 16777215 else 0
            widget.setVisible(True)
            end = widget.layout().sizeHint().height() if widget.layout() else widget.sizeHint().height()
            cls.animate(widget, b'maximumHeight', end, 'layout', start=start, finished=lambda: widget.setMaximumHeight(16777215))
        else:
            cls.animate(widget, b'maximumHeight', 0, 'layout', start=widget.height(), finished=widget.hide)
