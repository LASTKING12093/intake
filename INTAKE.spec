# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
import re
from PyInstaller.utils.win32.versioninfo import VSVersionInfo, FixedFileInfo, StringFileInfo, StringTable, StringStruct, VarFileInfo, VarStruct

release = re.search(r'__version__\s*=\s*[\"\x27]([^\"\x27]+)', Path('app/__init__.py').read_text('utf-8')).group(1)
version_tuple = tuple(map(int, release.split('.'))) + (0,)
windows_version = VSVersionInfo(
    ffi=FixedFileInfo(filevers=version_tuple, prodvers=version_tuple, mask=0x3f, flags=0, OS=0x40004, fileType=1, subtype=0, date=(0, 0)),
    kids=[StringFileInfo([StringTable('040904B0', [
        StringStruct('CompanyName', 'LASTKING12093'),
        StringStruct('FileDescription', 'INTAKE — Universal Media Downloader'),
        StringStruct('FileVersion', release), StringStruct('ProductVersion', release),
        StringStruct('ProductName', 'INTAKE'), StringStruct('OriginalFilename', 'INTAKE.exe'),
        StringStruct('LegalCopyright', 'Copyright 2026 INTAKE contributors'),
    ])]), VarFileInfo([VarStruct('Translation', [1033, 1200])])],
)


a = Analysis(
    ['run.py'],
    pathex=[],
    binaries=[],
    datas=[('app/resources', 'app/resources')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets', 'PySide6.QtQml', 'PySide6.QtQuick'],
    noarchive=False,
    optimize=0,
)
# Qt's Windows wheels import the operating system ICU ABI (unsuffixed symbols).
# Build hosts such as scientific Python bundles may inject Poppler's different
# ICU ABI into DLL discovery even after PATH is cleaned. Never ship that copy.
a.binaries = [entry for entry in a.binaries
              if entry[0].lower() != 'icuuc.dll'
              and not entry[0].lower().startswith('icudt')]
# Qt's generic GUI hook also collects PDF and virtual-keyboard plugins, which
# pull in unused QML/Quick modules. Ship only the desktop plugins INTAKE uses.
unused_modules = ('qt6qml', 'qt6quick', 'qt6virtualkeyboard', 'qt6pdf')
def used_binary(entry):
    name = entry[0].replace('\\', '/').lower()
    base = name.rsplit('/', 1)[-1]
    if base.startswith(unused_modules):
        return False
    if '/plugins/platforminputcontexts/' in name or '/plugins/generic/' in name:
        return False
    if base == 'qpdf.dll':
        return False
    if '/plugins/platforms/' in name and base != 'qwindows.dll':
        return False
    return True
a.binaries = [entry for entry in a.binaries if used_binary(entry)]
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='INTAKE',
    version=windows_version,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['app\\resources\\icon.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='INTAKE',
)
