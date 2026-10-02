"""Capture the real UI in an isolated demo profile (one fresh process per view)."""
import os
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
view = sys.argv[1] if len(sys.argv) > 1 else "hero"
if view not in {"hero", "detected-media", "queue"}:
    raise SystemExit("Choose hero, detected-media or queue")
os.environ["INTAKE_DATA_DIR"] = str(ROOT / ".test-data" / ("preview-" + view))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import QTimer, QThreadPool
from PySide6.QtWidgets import QApplication
from app.services.config import Config
from app.models.download import Options
from app.ui.main_window import MainWindow

app = QApplication([])
app.setStyle("Fusion")
config = Config()
config.set("download_folder", "Downloads/INTAKE")
config.set("launch_behavior", "Home")
# Never reuse prior queue/history state for a public capture.
profile = Path(os.environ["INTAKE_DATA_DIR"])
(profile / "queue.json").unlink(missing_ok=True)
window = MainWindow(config)
window.resize(1280, 800)
window.show()

def populate():
    if view != "hero":
        url = "https://www.youtube.com/watch?v=YE7VzlLtp-4"
        info = {"id": "YE7VzlLtp-4", "title": "Big Buck Bunny", "channel": "Blender Foundation",
                "duration": 596, "thumbnail": "https://i.ytimg.com/vi/YE7VzlLtp-4/hqdefault.jpg",
                "webpage_url": url, "formats": [
                    {"format_id": "demo", "height": 1080, "ext": "mp4", "vcodec": "avc1", "acodec": "mp4a"}]}
        window.url.setPlainText(url)
        window.service.add(url, info, Options())
        if view == "queue":
            window.service.add(url, info, Options("Audio", "MP3", "192 kbps"))
            window.show_page(1)
    QTimer.singleShot(8000, capture)

def capture():
    target = ROOT / "docs" / "assets"
    target.mkdir(parents=True, exist_ok=True)
    window.repaint()
    if not window.grab().save(str(target / (view + ".png"))):
        raise RuntimeError("Screenshot save failed")
    QThreadPool.globalInstance().waitForDone()
    window.close()
    app.quit()

QTimer.singleShot(600, populate)
app.exec()
