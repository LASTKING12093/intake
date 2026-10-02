from pathlib import Path
from PySide6.QtCore import Qt, QThreadPool
from app.models.download import State
from app.ui.main_window import MainWindow
from app.dialogs.playlist import PlaylistDialog


INFO = {"id": "abcdefghijk", "title": "A quiet afternoon — original test film", "channel": "MediaGrab Studio", "duration": 153,
        "formats": [{"height": 1080, "ext": "mp4", "vcodec": "avc1"}, {"height": 720, "ext": "webm", "vcodec": "vp9"}],
        "subtitles": {"en": [], "pt-BR": []}, "automatic_captions": {"en": [], "fr": []}}


def test_add_link_format_controls_and_screenshot(qtbot, config, monkeypatch):
    window = MainWindow(config)
    qtbot.addWidget(window)
    window.show()
    def inspect(url):
        window.service.info_ready.emit(url, INFO)
    monkeypatch.setattr(window.service, "get_info", inspect)
    window.url.setPlainText("https://youtu.be/abcdefghijk")
    qtbot.mouseClick(window.add_button, Qt.MouseButton.LeftButton)
    assert len(window.cards) == 1
    card = window.current_result
    assert card.title_label.text() == INFO["title"]
    assert card.quality.findText("1080p") >= 0
    assert card.quality.findText("2160p") < 0
    card.mode.setCurrentText("Audio")
    card.container.setCurrentText("MP3")
    card.quality.setCurrentText("320 kbps")
    assert card.job.options.quality == "320 kbps"
    card.container.setCurrentText("WAV")
    assert card.quality.currentText() == "PCM"
    card.mode.setCurrentText("Video")
    assert card.subtitle.count() == 5
    out = Path(__file__).resolve().parents[1] / ".test-data" / "screenshots"
    out.mkdir(parents=True, exist_ok=True)
    qtbot.wait(150)
    window.grab().save(str(out / "queue.png"))
    window.show_page(3)
    qtbot.wait(100)
    window.grab().save(str(out / "settings.png"))
    window.show_page(2)
    window.grab().save(str(out / "history.png"))
    QThreadPool.globalInstance().waitForDone(30000)
    qtbot.wait(50)
    window.close()


def test_playlist_selection(qtbot, config):
    window = MainWindow(config)
    qtbot.addWidget(window)
    info = {"title": "Original playlist", "entries": [{"id": str(i), "title": f"Video {i}", "duration": 12} for i in range(8)]}
    dialog = PlaylistDialog(info, window.thumbnails, window)
    qtbot.addWidget(dialog)
    assert len(dialog.selected()) == 8
    dialog.select("none")
    assert not dialog.selected()
    dialog.select("invert")
    assert len(dialog.selected()) == 8
    QThreadPool.globalInstance().waitForDone(30000)
    qtbot.wait(50)
    window.close()
