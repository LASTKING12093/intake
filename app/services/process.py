import logging
import os
import re
import subprocess
import threading

log = logging.getLogger("mediagrab")
HIDDEN = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


def run_hidden(args, **kwargs):
    return subprocess.run([str(a) for a in args], creationflags=HIDDEN, capture_output=True,
                          text=True, encoding="utf-8", errors="replace", **kwargs)


def redact(text):
    # Signed media URLs and tokens never belong in a persistent log.
    return re.sub(r'https?://[^\s\"\']+', "[URL]", text)


class Interrupted(Exception):
    pass


class ProcessRunner:
    def __init__(self):
        self.process = None
        self.stop_event = threading.Event()
        self.lock = threading.Lock()
        self.job_object = None

    def stop(self):
        self.stop_event.set()
        with self.lock:
            process = self.process
            if os.name == "nt" and process and process.poll() is None:
                if self.job_object:
                    self.job_object.terminate()
                else:
                    process.kill()
                return
        if process and process.poll() is None:
            if os.name != "nt":
                import signal
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass

    def run(self, args, on_line=None):
        if self.stop_event.is_set():
            raise Interrupted()
        with self.lock:
            if os.name == "nt":
                from app.services.windows_job import WindowsJob
                self.job_object = WindowsJob()
            try:
                self.process = subprocess.Popen([str(a) for a in args], stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, text=True, encoding="utf-8",
                    errors="replace", creationflags=HIDDEN, start_new_session=os.name != "nt")
            except OSError:
                if self.job_object:
                    self.job_object.close()
                    self.job_object = None
                raise
            if self.job_object:
                try:
                    self.job_object.assign(self.process)
                except OSError:
                    self.process.kill()
                    self.process.wait()
                    self.job_object.close()
                    raise
        if self.stop_event.is_set():
            self.stop()
        lines = []
        try:
            for line in self.process.stdout:
                line = line.strip()
                lines.append(line)
                if len(lines) > 60:
                    lines.pop(0)
                if on_line:
                    on_line(line)
            code = self.process.wait()
        finally:
            self.process.stdout.close()
            if self.process.poll() is None:
                self.stop()
                self.process.wait(timeout=20)
            with self.lock:
                if self.job_object:
                    self.job_object.close()
                    self.job_object = None
        if self.stop_event.is_set():
            raise Interrupted()
        if code:
            detail = redact("\n".join(lines))
            log.error("Process exit=%s %s", code, detail)
            raise RuntimeError(detail)
        return "\n".join(lines)


def friendly_error(error):
    message = str(error).lower()
    if "private" in message or "sign in" in message or "login" in message or "members-only" in message:
        return "Private or restricted video. This content requires access that INTAKE does not have."
    if "unavailable" in message or "removed" in message or "not available" in message:
        return "Video unavailable. It may have been removed or be unavailable in your region."
    if "ffmpeg" in message or "ffprobe" in message:
        return "Media processor unavailable. Check the FFmpeg folder in Settings."
    if "403" in message or "429" in message or "bot" in message:
        return "This site blocked the request. Try again later or refresh the download engine in Settings."
    if any(s in message for s in ("timed out", "connection", "resolve", "network", "10060", "urlopen")):
        return "Network problem. Check your connection, then retry."
    if "requested format" in message:
        return "This format or quality is unavailable. Try Best or another format."
    if "space" in message:
        return "Not enough disk space. Choose another folder or free some space."
    if "permission" in message or "access is denied" in message:
        return "Cannot write to this folder. Choose a writable download or temporary folder."
    if "yt-dlp" in message or isinstance(error, FileNotFoundError):
        return "Download engine unavailable. Check the runtime paths in Settings."
    return "Download failed. Retry, or check for an engine update in Settings. Details are in the log."
