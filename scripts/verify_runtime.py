import hashlib
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.services.process import run_hidden

manifest = json.loads((ROOT / "runtime" / "manifest.json").read_text("utf-8"))
for name, relative in {"yt-dlp": "yt-dlp/yt-dlp.exe", "deno": "deno/deno.exe", "ffmpeg": "ffmpeg/ffmpeg.exe", "ffprobe": "ffmpeg/ffprobe.exe"}.items():
    path = ROOT / "runtime" / relative
    assert path.exists(), f"Missing {path}"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == manifest[name]["sha256"], f"Corrupt runtime: {name}"
    result = run_hidden([path, "-version" if name in {"ffmpeg", "ffprobe"} else "--version"], timeout=30)
    assert result.returncode == 0, f"Runtime startup failed: {name}"
    print(f"Verified {name}")
