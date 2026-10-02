import os
from pathlib import Path
import pytest


@pytest.fixture(autouse=True)
def isolated_data(tmp_path, monkeypatch):
    monkeypatch.setenv("MEDIAGRAB_DATA_DIR", str(tmp_path / "app-data"))


@pytest.fixture
def config(tmp_path):
    from app.services.config import Config
    config = Config(tmp_path / "config.json")
    config.set("download_folder", str(tmp_path / "downloads"))
    return config


@pytest.fixture
def runtime(config):
    from app.services.runtime import Runtime
    return Runtime(config)


@pytest.fixture
def history(tmp_path):
    from app.services.history import History
    history = History(tmp_path / "history.sqlite3")
    yield history
    history.db.close()


@pytest.fixture
def service(qapp, config, runtime, history):
    from app.services.download import DownloadService
    service = DownloadService(config, runtime, history)
    yield service
    service.shutdown()
    service.pool.waitForDone(20000)
    service.info_pool.waitForDone(20000)
