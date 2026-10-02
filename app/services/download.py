import json
import logging
import shutil
import shlex
import threading
from dataclasses import asdict
from pathlib import Path
from PySide6.QtCore import QObject, QThreadPool, Signal, QTimer
from app.models.download import Job, Options, State, ACTIVE
from app.services.formats import format_selector, postprocess_args
from app.services.process import ProcessRunner, Interrupted, friendly_error
from app.workers.task import Task
from app.utils.files import publish_file
from app.utils.paths import data_dir
from app.utils.urls import source_name
from app.services.catalog import catalog_info, match_music, inspect_media, lyrics_for, request, CatalogError

log = logging.getLogger("mediagrab")


def clean_info(info):
    keys = ("id", "title", "duration", "channel", "uploader", "thumbnail", "webpage_url", "playlist_title", "playlist_index", "upload_date", "catalog", "artist", "album", "release_date", "genre", "source_url", "match_score", "match_approved", "matched_title", "matched_channel", "match_candidates", "needs_catalog")
    result = {k: info[k] for k in keys if k in info}
    result["formats"] = [{k: f.get(k) for k in ("format_id", "ext", "height", "vcodec", "acodec", "filesize", "filesize_approx")} for f in info.get("formats", [])]
    for key in ("subtitles", "automatic_captions"):
        result[key] = {lang: [] for lang in info.get(key, {})}
    return result


class WorkerEvents(QObject):
    progress = Signal(str, dict)


class DownloadService(QObject):
    added = Signal(object)
    changed = Signal(object)
    removed = Signal(str)
    info_ready = Signal(str, dict)
    info_failed = Signal(str, str)
    activity = Signal()

    def __init__(self, config, runtime, history, parent=None):
        super().__init__(parent)
        self.config, self.runtime, self.history = config, runtime, history
        self.jobs = {}
        self.active = {}
        self.inspectors = {}
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(5)
        self.info_pool = QThreadPool(self)
        self.info_pool.setMaxThreadCount(2)
        self.events = WorkerEvents()
        self.events.progress.connect(self._progress)
        self.queue_paused = False
        self.closing = False
        self.maintenance = False
        self.queue_path = data_dir() / "queue.json"

    def get_info(self, url):
        if self.maintenance:
            self.info_failed.emit(url, "The download engine is being updated. Try again when the update finishes.")
            return
        if url in self.inspectors or self.closing:
            return
        runner = ProcessRunner()
        self.inspectors[url] = runner
        log.info("Getting info url=%s", url)
        def inspect():
            if source_name(url) in {"Spotify", "Apple Music"}:
                info = catalog_info(url)
                return info if "entries" in info else match_music(self.runtime, runner, info)
            return inspect_media(self.runtime, runner, url)
        task = Task(inspect)
        task.signals.result.connect(lambda info: self.info_ready.emit(url, info))
        task.signals.error.connect(lambda error: self.info_failed.emit(url, str(error) if isinstance(error, CatalogError) else friendly_error(error)))
        task.signals.finished.connect(lambda: self._inspection_done(url))
        self.info_pool.start(task)
        self.activity.emit()

    def _inspection_done(self, url):
        self.inspectors.pop(url, None)
        self.activity.emit()

    def get_formats(self, url):
        self.get_info(url)

    def add(self, url, info, options=None):
        job = Job(url, clean_info(info), options or Options(), self.config.get("download_folder"))
        self.jobs[job.id] = job
        self.added.emit(job)
        self.save_queue()
        return job

    def download_video(self, job):
        self.enqueue(job)

    def download_audio(self, job):
        self.enqueue(job)

    def enqueue(self, job):
        if job.id in self.active or job.state in ACTIVE or job.state == State.COMPLETED:
            return
        job.transition(State.WAITING)
        if job.info.get("catalog") and job.info.get("source_url") and job.info.get("match_score", 0) < .78 and not job.info.get("match_approved"):
            job.transition(State.FAILED)
            job.error = "Review this recording in Options before downloading. The match is uncertain."
            self.changed.emit(job)
            self.save_queue()
            return
        job.error = ""
        self.changed.emit(job)
        self.save_queue()
        self._pump()

    def _pump(self):
        if self.closing or self.queue_paused or self.maintenance:
            return
        for job in self.jobs.values():
            if len(self.active) >= self.config.get("concurrent"):
                break
            if job.state == State.WAITING and job.id not in self.active:
                self._start(job)
        self.activity.emit()

    def _start(self, job):
        runner = ProcessRunner()
        self.active[job.id] = (runner, None)
        job.transition(State.INFO)
        if not job.stage:
            base = Path(self.config.get("temp_folder") or data_dir() / "temp")
            job.stage = str(base / ("mediagrab-" + job.id))
        self.changed.emit(job)
        log.info("Start id=%s url=%s format=%s quality=%s", job.id, job.url, job.options.container, job.options.quality)
        task = Task(lambda: self._execute(job, runner))
        task.signals.result.connect(lambda output: self._done(job.id, output, None))
        task.signals.error.connect(lambda error: self._done(job.id, "", error))
        self.pool.start(task)

    def _execute(self, job, runner):
        stage = job.stage_path()
        stage.mkdir(parents=True, exist_ok=True)
        fingerprint = json.dumps(asdict(job.options), sort_keys=True)
        fingerprint_file = stage / "options.json"
        if fingerprint_file.exists() and fingerprint_file.read_text("utf-8") != fingerprint:
            # A retry with different codecs must not reuse incompatible outputs.
            shutil.rmtree(stage)
            stage.mkdir(parents=True)
        fingerprint_file.write_text(fingerprint, "utf-8")
        download_url = job.info.get("source_url") or job.url
        if job.info.get("catalog") and not job.info.get("source_url"):
            metadata = catalog_info(job.url) if job.info.get("needs_catalog") else job.info
            matched = match_music(self.runtime, runner, metadata)
            if matched["match_score"] < .78:
                raise CatalogError("No confident recording match. Inspect this track individually to choose a source.")
            job.info.update(clean_info(matched))
            download_url = matched["source_url"]
        args = self.runtime.base_args() + ["--no-playlist", "--newline", "--progress", "--progress-delta", "0.3",
            "--output-na-placeholder", "null",
            "--no-simulate", "--continue", "--no-overwrites", "--windows-filenames", "--no-mtime",
            "-P", str(stage), "-o", "media.%(ext)s", "-f", format_selector(job.options),
            "--progress-template", 'download:MG_PROGRESS {"downloaded":%(progress.downloaded_bytes)j,"total":%(progress.total_bytes)j,"estimate":%(progress.total_bytes_estimate)j,"speed":%(progress.speed)j,"eta":%(progress.eta)j}',
            "--print", 'before_dl:MG_STATE downloading %(id)s', "--print", 'post_process:MG_STATE processing %(id)s',
            "--print", 'after_move:MG_FILE %(filepath)j', *postprocess_args(job.options)]
        if job.options.mode == "Audio" and job.options.metadata:
            tags = []
            if job.info.get("playlist_title"):
                tags += ["-metadata", "album=" + str(job.info["playlist_title"])]
            if job.info.get("playlist_index"):
                tags += ["-metadata", "track=" + str(job.info["playlist_index"])]
            if job.info.get("catalog"):
                for field, tag in (("title", "title"), ("artist", "artist"), ("album", "album"), ("release_date", "date"), ("genre", "genre")):
                    if job.info.get(field):
                        tags += ["-metadata", tag + "=" + str(job.info[field])]
            if tags:
                args += ["--postprocessor-args", "Metadata+ffmpeg_o:" + shlex.join(tags)]
        args += ["--", download_url]
        final = []
        def line_received(line):
            if line.startswith("MG_PROGRESS "):
                try:
                    self.events.progress.emit(job.id, json.loads(line[12:]))
                except ValueError:
                    pass
            elif line.startswith("MG_STATE "):
                self.events.progress.emit(job.id, {"state": line[9:].split()[0]})
            elif line.startswith("MG_FILE "):
                final.append(Path(json.loads(line[8:])))
            elif "[ExtractAudio]" in line or "[VideoConvertor]" in line:
                self.events.progress.emit(job.id, {"state": "converting"})
            elif any(s in line for s in ("[Merger]", "[Metadata]", "[Embed", "[VideoRemuxer]")):
                self.events.progress.emit(job.id, {"state": "processing"})
        runner.run(args, line_received)
        if runner.stop_event.is_set():
            raise Interrupted()
        if not final or not final[-1].is_file() or not final[-1].resolve().is_relative_to(stage.resolve()):
            raise RuntimeError("Download produced no final file")
        self.events.progress.emit(job.id, {"state": "processing"})
        media = final[-1]
        if job.info.get("catalog") and job.options.thumbnail and job.info.get("thumbnail"):
            try:
                art = stage / "catalog-cover.jpg"
                art.write_bytes(request(job.info["thumbnail"], 5 * 1024 * 1024))
                if media.suffix.lower() in {".mp3", ".m4a", ".flac"}:
                    tagged = stage / ("tagged" + media.suffix)
                    runner.run([str(self.runtime.ffmpeg_dir() / "ffmpeg.exe"), "-hide_banner", "-loglevel", "error", "-y", "-i", str(media), "-i", str(art), "-map", "0:a", "-map", "1:v", "-map_metadata", "0", "-c:a", "copy", "-c:v", "mjpeg", "-disposition:v", "attached_pic", str(tagged)])
                    media = tagged
            except Interrupted:
                raise
            except Exception:
                log.warning("Optional catalog artwork could not be embedded for %s", job.id)
        if runner.stop_event.is_set():
            raise Interrupted()
        lyric = lyrics_for(job.info) if job.options.mode == "Audio" and job.options.lyrics else None
        if runner.stop_event.is_set():
            raise Interrupted()
        output = publish_file(media, Path(job.destination), job.options.filename or job.title)
        try:
            if lyric and lyric["text"]:
                sidecar = stage / ("lyrics" + lyric["extension"])
                sidecar.write_text(lyric["text"], "utf-8")
                publish_file(sidecar, output.parent, output.stem)
            cover = stage / "catalog-cover.jpg"
            if cover.exists() and output.suffix.lower() not in {".mp3", ".m4a", ".flac"}:
                publish_file(cover, output.parent, output.stem + ".cover")
            if job.options.subtitle_mode == "Download .srt separately":
                for subtitle in stage.glob("*.srt"):
                    language = subtitle.stem.removeprefix("media.")
                    publish_file(subtitle, output.parent, output.stem + "." + language)
        except OSError:
            log.exception("Subtitle publication failed; video already saved at %s", output)
        shutil.rmtree(stage, ignore_errors=True)
        return str(output)

    def _progress(self, job_id, data):
        job = self.jobs.get(job_id)
        if not job or job_id not in self.active:
            return
        state = data.get("state")
        if job.state == State.INFO:
            job.transition(State.DOWNLOADING)
        if state in {"processing", "converting"}:
            job.transition(State.PROCESSING if state == "processing" else State.CONVERTING)
        total = data.get("total") or data.get("estimate") or 0
        if isinstance(total, (int, float)) and total > 0:
            job.total = total
            job.progress = min(100, 100 * (data.get("downloaded") or 0) / total)
        job.speed = data.get("speed") or 0
        job.eta = data.get("eta") or 0
        self.changed.emit(job)

    def _done(self, job_id, output, error):
        job = self.jobs[job_id]
        _, requested = self.active.pop(job_id)
        if output:
            if job.state == State.INFO:
                job.transition(State.DOWNLOADING)
            job.transition(State.COMPLETED)
            job.progress, job.output = 100, output
        elif requested:
            job.transition(requested)
            if requested == State.CANCELLED:
                shutil.rmtree(job.stage_path(), ignore_errors=True)
                job.stage = ""
        else:
            job.transition(State.FAILED)
            job.error = str(error) if isinstance(error, CatalogError) else friendly_error(error)
        if job.state in {State.COMPLETED, State.FAILED, State.CANCELLED}:
            self.history.record(job)
        log.info("Finished id=%s status=%s", job.id, job.state)
        self.changed.emit(job)
        self.save_queue()
        self._pump()
        self.activity.emit()

    def pause(self, job):
        if job.id in self.active:
            runner, _ = self.active[job.id]
            self.active[job.id] = (runner, State.PAUSED)
            threading.Thread(target=runner.stop, daemon=True).start()
        elif job.state == State.WAITING:
            job.transition(State.PAUSED)
            self.changed.emit(job)
            self.save_queue()

    def cancel(self, job):
        if job.id in self.active:
            runner, _ = self.active[job.id]
            self.active[job.id] = (runner, State.CANCELLED)
            threading.Thread(target=runner.stop, daemon=True).start()
        elif job.state not in {State.COMPLETED, State.CANCELLED}:
            job.transition(State.CANCELLED)
            if job.stage:
                shutil.rmtree(job.stage_path(), ignore_errors=True)
                job.stage = ""
            self.changed.emit(job)
            self.history.record(job)
            self.save_queue()

    def retry(self, job):
        self.enqueue(job)

    def pause_all(self):
        self.queue_paused = True
        for job in self.jobs.values():
            self.pause(job)

    def resume_all(self):
        self.queue_paused = False
        for job in self.jobs.values():
            if job.state == State.PAUSED:
                job.transition(State.WAITING)
                self.changed.emit(job)
        self._pump()

    def cancel_all(self):
        for job in self.jobs.values():
            self.cancel(job)

    def remove(self, job):
        if job.id in self.active:
            return
        if job.stage:
            shutil.rmtree(job.stage_path(), ignore_errors=True)
        del self.jobs[job.id]
        self.removed.emit(job.id)
        self.save_queue()

    def save_queue(self):
        rows = [asdict(j) for j in self.jobs.values() if j.state != State.COMPLETED]
        temporary = self.queue_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(rows, ensure_ascii=False), "utf-8")
        temporary.replace(self.queue_path)

    def restore_queue(self):
        try:
            rows = json.loads(self.queue_path.read_text("utf-8"))
        except (OSError, ValueError):
            return
        for row in rows:
            try:
                row["options"] = Options(**row["options"])
                row["state"] = State(row["state"])
                if row["state"] in ACTIVE | {State.WAITING}:
                    row["state"] = State.PAUSED
                job = Job(**row)
                # Persisted cleanup paths must be owned job directories.
                if job.stage and Path(job.stage).name != "mediagrab-" + job.id:
                    job.stage = ""
                self.jobs[job.id] = job
                self.added.emit(job)
            except (TypeError, ValueError, KeyError):
                log.warning("Ignoring invalid saved queue entry")

    def shutdown(self):
        self.closing = True
        self.pause_all()
        for runner in self.inspectors.values():
            threading.Thread(target=runner.stop, daemon=True).start()
