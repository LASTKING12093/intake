"""Fetch exact release inputs; verify archive and executable publisher hashes."""
import hashlib
import json
import sys
import tempfile
import zipfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.services.runtime import download_verified


def main():
    runtime = ROOT / "runtime"
    lock = json.loads((ROOT / "runtime.lock.json").read_text("utf-8"))
    manifest = json.loads((runtime / "manifest.json").read_text("utf-8"))
    for artifact in lock["artifacts"]:
        executables = [runtime / target for target in artifact["files"].values() if target.endswith(".exe")]
        if all(path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() == manifest[path.stem]["sha256"] for path in executables):
            print("Verified", artifact["name"])
            continue
        with tempfile.TemporaryDirectory() as folder:
            archive = Path(folder) / "artifact"
            download_verified(artifact["url"], archive, artifact["sha256"])
            if artifact["url"].endswith(".zip"):
                with zipfile.ZipFile(archive) as package:
                    for member, destination in artifact["files"].items():
                        target = runtime / destination
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_bytes(package.read(member))
            else:
                target = runtime / next(iter(artifact["files"].values()))
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.read_bytes())
        for path in executables:
            if hashlib.sha256(path.read_bytes()).hexdigest() != manifest[path.stem]["sha256"]:
                raise ValueError("Executable integrity check failed: " + path.name)
        print("Verified", artifact["name"])


if __name__ == "__main__":
    main()
