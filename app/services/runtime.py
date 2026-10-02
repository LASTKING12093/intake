import hashlib
import json
import os
import shutil
import tempfile
import urllib.request
from pathlib import Path
from app.services.process import run_hidden
from app.utils.paths import runtime_dir, data_dir


def fetch(url, limit=10 * 1024 * 1024):
    request = urllib.request.Request(url, headers={"User-Agent": "INTAKE/2.0", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(request, timeout=40) as response:
        data = response.read(limit + 1)
    if len(data) > limit:
        raise ValueError("Response too large")
    return data


def release_info(repo):
    return json.loads(fetch(f"https://api.github.com/repos/{repo}/releases/latest"))


def download_verified(url, target, expected):
    if not url.startswith("https://") or len(expected) != 64:
        raise ValueError("A trusted HTTPS source and SHA256 digest are required")
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    part = target.with_suffix(target.suffix + ".download")
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "INTAKE/2.0"})
        with urllib.request.urlopen(request, timeout=60) as response, part.open("wb") as output:
            while chunk := response.read(1024 * 1024):
                output.write(chunk)
                digest.update(chunk)
        if digest.hexdigest().lower() != expected.lower():
            raise ValueError("Download integrity check failed")
        part.replace(target)
    finally:
        part.unlink(missing_ok=True)


def release_asset(repo, release, name, target):
    asset = next(a for a in release["assets"] if a["name"] == name)
    digest = asset.get("digest") or ""
    if digest.startswith("sha256:"):
        expected = digest.removeprefix("sha256:")
    elif repo == "yt-dlp/yt-dlp":
        sums = next(a for a in release["assets"] if a["name"] == "SHA2-256SUMS")
        text = fetch(sums["browser_download_url"]).decode()
        expected = next(line.split()[0] for line in text.splitlines() if line.split()[-1].lstrip("*") == name)
    else:
        raise ValueError("The publisher did not provide a SHA256 digest")
    download_verified(asset["browser_download_url"], target, expected)


class Runtime:
    def __init__(self, config):
        self.config = config

    def yt_dlp(self):
        if self.config.get("yt_dlp_path"):
            return Path(self.config.get("yt_dlp_path"))
        updated = data_dir() / "runtime" / "yt-dlp.exe"
        return updated if updated.exists() else runtime_dir() / "yt-dlp" / "yt-dlp.exe"

    def ffmpeg_dir(self):
        path = Path(self.config.get("ffmpeg_path")) if self.config.get("ffmpeg_path") else runtime_dir() / "ffmpeg"
        return path.parent if path.suffix.lower() == ".exe" else path

    def deno(self):
        return runtime_dir() / "deno" / "deno.exe"

    def version(self):
        try:
            result = run_hidden([self.yt_dlp(), "--version"], timeout=20)
            return result.stdout.strip() if result.returncode == 0 else "Unavailable"
        except (OSError, TimeoutError):
            return "Not installed"

    def base_args(self):
        args = [str(self.yt_dlp()), "--ignore-config", "--no-plugin-dirs", "--encoding", "utf-8",
                "--no-colors", "--socket-timeout", "20", "--retries", "3", "--fragment-retries", "3",
                "--ffmpeg-location", str(self.ffmpeg_dir())]
        if self.deno().exists():
            args += ["--js-runtimes", f"deno:{self.deno()}"]
        return args

    def check_update(self):
        return release_info("yt-dlp/yt-dlp")["tag_name"]

    def update(self):
        release = release_info("yt-dlp/yt-dlp")
        destination = data_dir() / "runtime" / "yt-dlp.exe"
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=destination.parent) as folder:
            candidate = Path(folder) / "yt-dlp.exe"
            release_asset("yt-dlp/yt-dlp", release, "yt-dlp.exe", candidate)
            result = run_hidden([candidate, "--version"], timeout=30)
            if result.returncode or result.stdout.strip() != release["tag_name"]:
                raise ValueError("The updated engine did not pass its startup check")
            candidate.replace(destination)
        return release["tag_name"]
