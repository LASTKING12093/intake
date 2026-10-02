import os
import sys
import shutil
from pathlib import Path


def root_dir():
    return Path(sys.executable).parent if getattr(sys,'frozen',False) else Path(__file__).resolve().parents[2]


def migrate_legacy(target, legacy):
    """Copy state once, leave V1 and all partial-media paths untouched."""
    if (target/'.migrated-v1').exists(): return
    target.mkdir(parents=True,exist_ok=True)
    for name in ('config.json','queue.json','history.sqlite3'):
        source=legacy/name; destination=target/name
        if source.is_file() and not destination.exists():
            if name.endswith('.sqlite3'):
                import sqlite3
                with sqlite3.connect(f'{source.as_uri()}?mode=ro',uri=True) as old, sqlite3.connect(destination) as new:
                    old.backup(new)
            else: shutil.copy2(source,destination)
    source=legacy/'runtime'/'yt-dlp.exe'; destination=target/'runtime'/'yt-dlp.exe'
    if source.is_file() and not destination.exists():
        destination.parent.mkdir(exist_ok=True); shutil.copy2(source,destination)
    (target/'.migrated-v1').write_text('V1 files preserved; partial downloads retain their original locations.','utf-8')


def data_dir():
    override=os.environ.get('INTAKE_DATA_DIR') or os.environ.get('MEDIAGRAB_DATA_DIR')
    folder=Path(override) if override else Path(os.environ.get('APPDATA',Path.home()))/'INTAKE'
    folder.mkdir(parents=True,exist_ok=True)
    if not override:
        legacy=folder.parent/'MediaGrab'
        if legacy.is_dir(): migrate_legacy(folder,legacy)
    return folder


def runtime_dir(): return root_dir()/'runtime'
