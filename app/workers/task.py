import traceback
import logging
from PySide6.QtCore import QObject, QRunnable, Signal, Slot, QCoreApplication


class TaskSignals(QObject):
    result = Signal(object)
    error = Signal(object)
    finished = Signal()
    completed = Signal(object, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.completed.connect(self.deliver)

    @Slot(object, object)
    def deliver(self, result, error):
        # Deliver public callbacks synchronously on the GUI thread before this
        # signal owner is deleted; fast workers must not lose queued callbacks.
        try:
            if error is None:
                self.result.emit(result)
            else:
                self.error.emit(error)
        finally:
            self.finished.emit()
            self.deleteLater()


class Task(QRunnable):
    def __init__(self, function):
        super().__init__()
        self.function = function
        # The QObject must outlive the QRunnable's auto-deletion: queued Python
        # callbacks can still be pending when the worker returns.
        self.signals = TaskSignals(QCoreApplication.instance())

    @Slot()
    def run(self):
        result, failure = None, None
        try:
            result = self.function()
        except Exception as error:
            from app.services.process import Interrupted
            if not isinstance(error, Interrupted):
                logging.getLogger("mediagrab").exception("Background task failed")
            failure = error
        finally:
            self.signals.completed.emit(result, failure)
