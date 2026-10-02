from pathlib import Path
from app.services.process import run_hidden


class FFmpegService:
    """Blocking service; callers use workers. No shell expansion and no overwrites."""
    def __init__(self, directory):
        self.directory = Path(directory)

    def check_installation(self):
        try:
            return all(run_hidden([self.directory / f"{name}.exe", "-version"], timeout=15).returncode == 0 for name in ("ffmpeg", "ffprobe"))
        except (OSError, TimeoutError):
            return False

    def get_version(self):
        try:
            result = run_hidden([self.directory / "ffmpeg.exe", "-version"], timeout=15)
            return result.stdout.splitlines()[0] if result.returncode == 0 else "Unavailable"
        except (OSError, IndexError, TimeoutError):
            return "Not installed"

    def _run(self, args, target):
        result = run_hidden([self.directory / "ffmpeg.exe", "-hide_banner", "-nostdin", "-n", *args, target], timeout=3600)
        if result.returncode:
            raise RuntimeError("FFmpeg: " + result.stderr[-2000:])
        return Path(target)

    def convert_audio(self, source, target, codec="pcm_s16le", bitrate=None):
        args = ["-i", source, "-vn", "-c:a", codec]
        if bitrate:
            args += ["-b:a", str(bitrate)]
        return self._run(args, target)

    def merge_video_audio(self, video, audio, target):
        return self._run(["-i", video, "-i", audio, "-map", "0:v:0", "-map", "1:a:0", "-c", "copy"], target)

    def embed_metadata(self, source, target, metadata):
        args = ["-i", source, "-map", "0", "-c", "copy"]
        for key, value in metadata.items():
            args += ["-metadata", f"{key}={value}"]
        return self._run(args, target)

    def embed_thumbnail(self, source, image, target):
        return self._run(["-i", source, "-i", image, "-map", "0:a", "-map", "1:v", "-c:a", "copy", "-c:v", "mjpeg", "-disposition:v", "attached_pic"], target)
