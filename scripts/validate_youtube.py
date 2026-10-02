"""Opt-in live validation using the Blender Foundation CC BY 3.0 open movie.

Copyright 2008 Blender Foundation / www.bigbuckbunny.org
License: https://peach.blender.org/about/
These test downloads are kept in .test-data and never included in the release.
"""
import json
import os
import sys
import time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["MEDIAGRAB_DATA_DIR"] = str(ROOT / ".test-data" / ("youtube-app-" + time.strftime('%Y%m%d-%H%M%S')))
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from app.ui.main_window import MainWindow
from app.models.download import Options, State
from app.services.process import run_hidden

app = QApplication([])
window = MainWindow()
window.config.set("download_folder", str(ROOT / ".test-data" / "youtube-downloads"))
window.update_folder_label()
window.show()
url = "https://www.youtube.com/watch?v=YE7VzlLtp-4"
started = time.monotonic()
retried = set()
report = {"url": url, "license": "CC BY 3.0", "attribution": "Copyright 2008 Blender Foundation / www.bigbuckbunny.org", "results": []}
scheduled = False

def info(url, details):
    global scheduled
    if scheduled:
        return
    scheduled = True
    report["title"] = details.get("title")
    report["formats"] = len(details.get("formats", []))
    report["subtitles"] = list(details.get("subtitles", {}))
    report["automatic_captions"] = list(details.get("automatic_captions", {}))
    print(f"Metadata: {details['title']}, {report['formats']} formats", flush=True)
    # MainWindow's normal Add handler already creates the video card.
    job = list(window.service.jobs.values())[-1]
    card = window.current_result
    card.container.setCurrentText("MP4")
    card.quality.setCurrentText("360p")
    card.primary_action()
    for options in [Options("Audio", "Original / Best Audio", "Best"), Options("Audio", "MP3", "192 kbps", thumbnail=True), Options("Audio", "WAV", "PCM")]:
        job = window.service.add(url, details, options)
        window.service.enqueue(job)

window.service.info_ready.connect(info)
window.service.info_failed.connect(lambda u, message: (print(message, flush=True), report.update(error=message)))
window.url.setPlainText(url)
window.add_links()

def poll():
    jobs = list(window.service.jobs.values())
    terminal = {State.COMPLETED, State.FAILED, State.CANCELLED}
    for job in jobs:
        if job.state == State.FAILED and job.id not in retried:
            retried.add(job.id)
            print(f"Retrying {job.options.container} once after the reported failure", flush=True)
            window.service.retry(job)
            return
    if scheduled and jobs and all(j.state in terminal for j in jobs):
        for job in jobs:
            result = {"format": job.options.container, "status": str(job.state), "error": job.error, "output": job.output}
            if job.output:
                probe = run_hidden([window.runtime.ffmpeg_dir() / "ffprobe.exe", "-v", "error", "-show_streams", "-show_format", "-of", "json", job.output], timeout=30)
                result["probe"] = json.loads(probe.stdout)
            report["results"].append(result)
            print(f"{job.options.container}: {job.state} {job.error}", flush=True)
        finish()
    elif report.get("error") or time.monotonic() - started > 480:
        report["timeout"] = not bool(report.get("error"))
        window.service.cancel_all()
        finish()

def finish():
    timer.stop()
    folder = ROOT / ".test-data" / "youtube-validation"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "report.json").write_text(json.dumps(report, indent=2), "utf-8")
    (folder / f"report-{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(json.dumps(report, indent=2), "utf-8")
    window.grab().save(str(folder / "youtube-queue.png"))
    window.close()

timer = QTimer()
timer.timeout.connect(poll)
timer.start(500)
app.exec()
raise SystemExit(0 if report["results"] and all(r["status"] == "Completed" for r in report["results"]) else 1)
