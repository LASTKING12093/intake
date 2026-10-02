"""Opt-in packaged smoke test using only original, locally generated media."""
import functools
import http.server
import json
import threading
import time
from pathlib import Path
from PySide6.QtCore import QTimer, QThreadPool
from app.models.download import Options, State
from app.services.process import run_hidden
from app.utils.paths import data_dir
from app.workers.task import Task


def start_smoke_test(window):
    folder = data_dir() / "smoke"
    folder.mkdir(parents=True, exist_ok=True)
    output = folder / "downloads"
    window.config.set("download_folder", str(output))
    window.update_folder_label()
    context = {"server": None, "jobs": [], "started": time.monotonic(), "finished": False}
    window.selftest_exit = 1

    class QuietHandler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

    def generate():
        result = run_hidden([window.runtime.ffmpeg_dir() / "ffmpeg.exe", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", "testsrc2=size=320x180:rate=24", "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100",
            "-t", "1", "-c:v", "libx264", "-c:a", "aac", folder / "original.mp4"], timeout=30)
        if result.returncode:
            raise RuntimeError(result.stderr)
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(QuietHandler, directory=str(folder)))
        context["server"] = server
        threading.Thread(target=server.serve_forever, daemon=True).start()
        return f"http://127.0.0.1:{server.server_port}/original.mp4"

    def ready(url):
        for options in (Options(), Options("Audio", "MP3", "192 kbps")):
            job = window.service.add(url, {"title": "INTAKE packaged test", "channel": "Original local fixture", "duration": 1}, options)
            context["jobs"].append(job)
            window.service.enqueue(job)

    def finish(success, detail):
        if context["finished"]:
            return
        context["finished"] = True
        timer.stop()
        window.grab().save(str(folder / "window.png"))
        if success:
            (folder / "result.txt").write_text("INTAKE packaged UI, yt-dlp, MP4 and MP3 verified\n" + detail, "utf-8")
            window.selftest_exit = 0
        else:
            (folder / "failure.txt").write_text(detail, "utf-8")
            window.service.cancel_all()
        if context["server"]:
            threading.Thread(target=context["server"].shutdown, daemon=True).start()
        window.close()

    def inspect_outputs():
        evidence = []
        for job in context["jobs"]:
            result = run_hidden([window.runtime.ffmpeg_dir() / "ffprobe.exe", "-v", "error", "-show_streams", "-of", "json", job.output], timeout=20)
            if result.returncode:
                raise RuntimeError("Packaged ffprobe failed")
            streams = json.loads(result.stdout)["streams"]
            expected = "h264" if job.options.mode == "Video" else "mp3"
            if not any(s["codec_name"] == expected for s in streams):
                raise RuntimeError("Unexpected packaged output codec")
            evidence.append(f"{job.options.container}: {expected}, {Path(job.output).stat().st_size} bytes")
        return "\n".join(evidence)

    def poll():
        jobs = context["jobs"]
        if jobs and all(j.state in {State.COMPLETED, State.FAILED} for j in jobs):
            timer.stop()
            if not all(j.state == State.COMPLETED for j in jobs):
                finish(False, "\n".join(j.error for j in jobs))
            else:
                task = Task(inspect_outputs)
                task.signals.result.connect(lambda evidence: finish(True, evidence))
                task.signals.error.connect(lambda error: finish(False, str(error)))
                QThreadPool.globalInstance().start(task)
        elif time.monotonic() - context["started"] > 50:
            finish(False, "Packaged test timed out")

    timer = QTimer(window)
    timer.timeout.connect(poll)
    timer.start(250)
    task = Task(generate)
    task.signals.result.connect(ready)
    task.signals.error.connect(lambda error: finish(False, str(error)))
    QThreadPool.globalInstance().start(task)
