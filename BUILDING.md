# Building INTAKE

## Requirements

- Windows x64; release verification uses Windows 11.
- Python 3.12 or newer with `venv` and `pip` (release build: 3.12.14).
- PowerShell 7, Git and an internet connection for pinned dependencies.
- Inno Setup 7.1.0 to produce the installer. The helper below verifies its published digest before installation.

## Development

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe scripts/bootstrap_runtime.py
.\.venv\Scripts\python.exe run.py
```

`runtime.lock.json` pins upstream artifact URLs and publisher SHA-256 digests. `runtime/manifest.json` pins the unpacked helper executable hashes. Bootstrap verifies both; it does not select "latest". Python packages are version-locked in `requirements-lock.txt`.

## Tests

```powershell
New-Item -ItemType Directory -Force .test-data | Out-Null
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.test-data/tests
```

Integration tests generate original media and use an ephemeral loopback server. They exercise the real bundled extractors and FFmpeg; these test-only local addresses are intentional. Tests isolate configuration and never need browser cookies or an account. Live site checks are separate from deterministic tests.

## Portable application

```powershell
.\build.ps1 -Python python
```

This creates a fresh build environment, verifies runtime hashes, runs tests, builds the windowed application with PyInstaller and performs an isolated packaged MP4/MP3 smoke test. Output: `dist/INTAKE/INTAKE.exe` and a distribution ZIP. Build products and local environments must not be committed.

## Public release artifacts

```powershell
.\scripts\get_build_python.ps1
.\scripts\get_release_tools.ps1
.\scripts\release.ps1 -Python (Join-Path $PWD ".tools/python/python.exe") -Compiler .tools/inno/ISCC.exe
```

Output in `release/`:

- `Intake-Setup-x64.exe`: per-user installer with Start menu entry and uninstaller.
- `Intake-Portable-x64.zip`: complete portable application, including helpers.
- `SHA256SUMS.txt`: hashes of downloadable binaries.

The application version in `app/__init__.py` must match `pyproject.toml`; the release tag is `v` plus that version. The installer embeds that version. Artifacts are unsigned unless a future release introduces an explicitly configured signing process. Private signing keys must never enter the repository.

To make a **source-only** archive, use `git archive --format=zip --prefix=intake/ --output=Intake-Source.zip HEAD`. The portable application ZIP is not source code. GitHub also generates source archives from each release tag.

## CI and reproducibility

Pull requests and main-branch pushes run Windows tests and the packaged smoke test. Version tags build the installer and portable ZIP, test installation/uninstallation, and publish the assets with checksums. Workflows use the same scripts as a local build.

Pinned inputs make the build repeatable, not byte-for-byte deterministic: PE timestamps, compression and host tooling can change output hashes. Release checksums describe the exact published artifacts. Before distribution, review dependency licenses and source-access references in `THIRD_PARTY_NOTICES.md`.

The release Python helper downloads the SHA-256-verified CPython 3.12.14 Windows archive from Astral python-build-standalone release 20260929. This also covers security-maintenance Python versions absent from the setup-python Windows catalog. Its source/build recipes and dependency license texts are available at https://github.com/astral-sh/python-build-standalone/tree/20260929 and under `runtime/licenses/python/`.
