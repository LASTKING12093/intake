import json
import logging
from pathlib import Path
from app.utils.paths import data_dir

DEFAULTS = {
    "download_folder": str(Path.home() / "Downloads" / "INTAKE"),
    "theme": "Dark", "launch_behavior": "Downloads", "video_container": "MP4",
    "video_quality": "Best", "audio_format": "MP3", "audio_bitrate": "Best",
    "metadata": True, "thumbnails": False, "concurrent": 3,
    "temp_folder": "", "yt_dlp_path": "", "ffmpeg_path": "",
    "smart_defaults": True, "lyrics": True,
}


class Config:
    def __init__(self, path: Path | None = None):
        self.path = path or data_dir() / "config.json"
        self.values = dict(DEFAULTS)
        try:
            loaded = json.loads(self.path.read_text("utf-8"))
            if isinstance(loaded, dict):
                for key, default in DEFAULTS.items():
                    if key in loaded and type(loaded[key]) is type(default):
                        self.values[key] = loaded[key]
        except (OSError, ValueError):
            pass
        self.values["concurrent"] = max(1, min(5, self.values["concurrent"]))

    def get(self, key):
        return self.values[key]

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(self.values, indent=2, ensure_ascii=False), "utf-8")
        temporary.replace(self.path)

    def set(self, key, value):
        self.values[key] = value
        self.save()
