import threading
import time
from pathlib import Path
from app.models.download import State, Options
from app.services.process import Interrupted


def test_bounded_queue_cancel_retry(service, qtbot, monkeypatch):
    service.config.set("concurrent", 2)
    lock = threading.Lock()
    maximum = [0]
    running = [0]
    def fake(job, runner):
        with lock:
            running[0] += 1
            maximum[0] = max(maximum[0], running[0])
        try:
            while not runner.stop_event.wait(.01):
                pass
            raise Interrupted()
        finally:
            with lock:
                running[0] -= 1
    monkeypatch.setattr(service, "_execute", fake)
    jobs = [service.add(f"url{i}", {"title": str(i)}) for i in range(5)]
    for job in jobs:
        service.enqueue(job)
    qtbot.waitUntil(lambda: running[0] == 2)
    assert len(service.active) == 2
    assert sum(j.state == State.WAITING for j in jobs) == 3
    service.pause_all()
    qtbot.waitUntil(lambda: not service.active)
    assert all(j.state == State.PAUSED for j in jobs)
    service.resume_all()
    qtbot.waitUntil(lambda: running[0] == 2)
    service.cancel_all()
    qtbot.waitUntil(lambda: not service.active)
    assert all(j.state == State.CANCELLED for j in jobs)
    assert maximum[0] == 2


def test_failure_then_retry(service, qtbot, monkeypatch):
    attempts = []
    def fake(job, runner):
        attempts.append(job.id)
        if len(attempts) == 1:
            raise RuntimeError("Connection interrupted")
        return str(Path(job.destination) / "test.mp4")
    monkeypatch.setattr(service, "_execute", fake)
    job = service.add("url", {"title": "Test"})
    service.enqueue(job)
    qtbot.waitUntil(lambda: job.state == State.FAILED)
    assert "Network" in job.error
    service.retry(job)
    qtbot.waitUntil(lambda: job.state == State.COMPLETED)
    assert job.error == "" and len(attempts) == 2
    assert service.history.rows()[0]["state"] == "Completed"


def test_restart_restores_without_auto_downloading(service):
    job = service.add("url", {"title": "Restored"})
    job.transition(State.WAITING)
    job.transition(State.INFO)
    service.save_queue()
    service.jobs.clear()
    service.restore_queue()
    assert service.jobs[job.id].state == State.PAUSED
    assert not service.active


def test_cancel_removes_partial_files(service, tmp_path):
    job = service.add("url", {"title": "Cancel"})
    job.stage = str(tmp_path / ("mediagrab-" + job.id))
    Path(job.stage).mkdir()
    partial = Path(job.stage) / "media.mp4.part"
    partial.write_bytes(b"partial")
    service.cancel(job)
    assert job.state == State.CANCELLED and not partial.exists()
