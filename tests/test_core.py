import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import pytest
from app.utils.urls import parse_urls
from app.utils.files import sanitize_filename, publish_file
from app.models.download import Job, Options, State
from app.services.config import Config
from app.services.formats import format_selector, resolutions, postprocess_args
from app.services.ffmpeg import FFmpegService
from app.services.process import friendly_error, redact


def test_url_parsing():
    assert parse_urls("https://youtu.be/abcdefghijk?t=5\nhttps://www.youtube.com/watch?v=abcdefghijk&feature=share") == ["https://www.youtube.com/watch?v=abcdefghijk"]
    assert parse_urls("https://youtube.com/shorts/abcdefghijk https://youtube.com/live/123456789ab") == ["https://www.youtube.com/watch?v=abcdefghijk", "https://www.youtube.com/watch?v=123456789ab"]
    assert parse_urls("https://youtube.com/watch?v=abcdefghijk&list=PL1234567890")[0].endswith("&list=PL1234567890")


@pytest.mark.parametrize("text", ["file:///C:/test", "https://user:password@youtube.com/watch?v=abcdefghijk", "https://youtube.com/watch?v=bad", "--exec calc.exe"])
def test_unsafe_urls_rejected(text):
    assert parse_urls(text) == []


@pytest.mark.parametrize("title, expected", [("a:b/c?d*e", "a_b_c_d_e"), ("CON", "_CON"), ("LPT9.txt", "_LPT9.txt"), ("  . ", "Untitled"), ("Música incrível", "Música incrível")])
def test_sanitization(title, expected):
    assert sanitize_filename(title) == expected


def test_atomic_conflicts(tmp_path):
    sources = []
    for i in range(8):
        source = tmp_path / f"{i}.mp3"
        source.write_bytes(str(i).encode())
        sources.append(source)
    with ThreadPoolExecutor(max_workers=8) as pool:
        outputs = list(pool.map(lambda p: publish_file(p, tmp_path / "out", "Song"), sources))
    assert len(set(outputs)) == 8
    assert {p.name for p in outputs} == {"Song.mp3", *(f"Song ({i}).mp3" for i in range(1, 8))}
    assert {p.read_bytes() for p in outputs} == {str(i).encode() for i in range(8)}


def test_config_roundtrip_and_corruption(config):
    config.set("concurrent", 5)
    assert Config(config.path).get("concurrent") == 5
    config.path.write_text('{"concurrent":99,"metadata":"bad"}', "utf-8")
    reloaded = Config(config.path)
    assert reloaded.get("concurrent") == 5 and reloaded.get("metadata") is True
    config.path.write_text("broken", "utf-8")
    assert Config(config.path).get("concurrent") == 3


def test_state_machine():
    job = Job("url", {}, Options(), ".")
    for state in [State.WAITING, State.INFO, State.DOWNLOADING, State.PAUSED, State.WAITING, State.DOWNLOADING, State.CONVERTING, State.COMPLETED]:
        job.transition(state)
    with pytest.raises(ValueError):
        job.transition(State.DOWNLOADING)


def test_format_selection():
    selected = format_selector(Options(quality="1080p"))
    assert "avc1" in selected and "height<=1080" in selected and "m4a" in selected
    assert format_selector(Options(mode="Audio")) == "bestaudio/best"
    assert "ext=webm" in format_selector(Options(container="WEBM"))
    info = {"formats": [{"height": 1080, "ext": "mp4"}, {"height": 720, "ext": "webm"}]}
    assert resolutions(info, "WEBM") == ["Best", "720p"]
    assert resolutions(info, "MP4") == ["Best", "1080p", "720p"]


def test_audio_and_subtitle_args():
    args = postprocess_args(Options(mode="Audio", container="MP3", quality="320 kbps", thumbnail=True))
    assert args[args.index("--audio-quality") + 1] == "320K"
    assert "--embed-thumbnail" in args
    original = postprocess_args(Options(mode="Audio", container="Original / Best Audio"))
    assert original[original.index("--audio-format") + 1] == "best"
    wav = postprocess_args(Options(mode="Audio", container="WAV"))
    assert "-ar" not in wav
    sub = postprocess_args(Options(subtitle="pt", auto_subtitle=True))
    assert "--write-auto-subs" in sub and "--embed-subs" in sub


def test_ffmpeg_missing(tmp_path):
    assert not FFmpegService(tmp_path).check_installation()


def test_errors_are_friendly():
    assert "Private" in friendly_error(RuntimeError("Private video"))
    assert "Network" in friendly_error(RuntimeError("Connection interrupted"))
    assert "processor" in friendly_error(RuntimeError("ffmpeg not found"))
    assert "token" not in redact("error https://media.example/video?token=secret")
