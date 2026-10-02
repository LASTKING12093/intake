import logging
import logging.handlers
import sys
from pathlib import Path
from PySide6.QtCore import QTimer, QLockFile
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QApplication, QMessageBox
from app.utils.paths import data_dir, root_dir
from app.services.process import redact


class SafeFormatter(logging.Formatter):
    def format(self, record):
        return redact(super().format(record))


def main():
    logs = data_dir() / "logs"
    logs.mkdir(exist_ok=True)
    handler = logging.handlers.RotatingFileHandler(logs / "intake.log", maxBytes=2 * 1024 * 1024, backupCount=4, encoding="utf-8")
    handler.setFormatter(SafeFormatter("%(asctime)s %(levelname)s %(message)s"))
    logging.basicConfig(level=logging.INFO, handlers=[handler])
    app = QApplication(sys.argv)
    app.setApplicationName("INTAKE")
    app.setOrganizationName("INTAKE")
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 10))
    lock = QLockFile(str(data_dir() / "intake.lock"))
    lock.setStaleLockTime(0)
    if not lock.tryLock(0):
        QMessageBox.information(None, "INTAKE is already open", "Use the INTAKE window that is already running.")
        return 0
    resource_root = Path(getattr(sys, "_MEIPASS", root_dir()))
    app.setWindowIcon(QIcon(str(resource_root / "app" / "resources" / "icon.ico")))
    def unhandled(kind, value, trace):
        logging.getLogger("mediagrab").error("Unhandled exception", exc_info=(kind, value, trace))
        QMessageBox.warning(None, "INTAKE", "Something went wrong. Details were saved to the log. You can retry the action.")
    sys.excepthook = unhandled
    from app.ui.main_window import MainWindow
    window = MainWindow()
    window.show()
    if "--smoke-test" in sys.argv:
        from app.selftest import start_smoke_test
        QTimer.singleShot(250, lambda: start_smoke_test(window))
    code = app.exec()
    return getattr(window, "selftest_exit", code)


if __name__ == "__main__":
    raise SystemExit(main())
