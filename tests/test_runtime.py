import hashlib
import io
from pathlib import Path
from types import SimpleNamespace
import pytest
from app.services import runtime as module


def test_verified_download_accepts_hash(tmp_path, monkeypatch):
    content = b"verified release payload"
    monkeypatch.setattr(module.urllib.request, "urlopen", lambda *a, **k: io.BytesIO(content))
    target = tmp_path / "engine.exe"
    module.download_verified("https://example.org/tool", target, hashlib.sha256(content).hexdigest())
    assert target.read_bytes() == content
    assert not target.with_suffix(".exe.download").exists()


def test_bad_hash_never_replaces_existing_engine(tmp_path, monkeypatch):
    monkeypatch.setattr(module.urllib.request, "urlopen", lambda *a, **k: io.BytesIO(b"corrupt"))
    target = tmp_path / "engine.exe"
    target.write_bytes(b"known good")
    with pytest.raises(ValueError, match="integrity"):
        module.download_verified("https://example.org/tool", target, "0" * 64)
    assert target.read_bytes() == b"known good"


def test_engine_update_validation_and_rollback(runtime, monkeypatch):
    destination = module.data_dir() / "runtime" / "yt-dlp.exe"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(b"old")
    monkeypatch.setattr(module, "release_info", lambda _: {"tag_name": "2026.09.01"})
    monkeypatch.setattr(module, "release_asset", lambda repo, release, name, target: target.write_bytes(b"candidate"))
    monkeypatch.setattr(module, "run_hidden", lambda *a, **k: SimpleNamespace(returncode=1, stdout="broken"))
    with pytest.raises(ValueError):
        runtime.update()
    assert destination.read_bytes() == b"old"
    monkeypatch.setattr(module, "run_hidden", lambda *a, **k: SimpleNamespace(returncode=0, stdout="2026.09.01\n"))
    assert runtime.update() == "2026.09.01"
    assert destination.read_bytes() == b"candidate"


def test_update_blocks_new_metadata_and_queue(service, qtbot, monkeypatch):
    service.maintenance = True
    with qtbot.waitSignal(service.info_failed):
        service.get_info("https://youtu.be/abcdefghijk")
    job = service.add("url", {"title": "Waiting for update"})
    service.enqueue(job)
    assert not service.active
