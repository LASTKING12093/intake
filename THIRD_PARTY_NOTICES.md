# Third-party notices and source access

The MIT license covers original INTAKE code. It does not relicense bundled libraries, executables, fonts, logos or artwork. The application invokes media tools as separate command-line programs; Qt/PySide remains dynamically linked and replaceable in the portable directory. No restriction on modification, replacement, reverse engineering for debugging those modifications, or redistribution is added.

| Component | Version / license | Source and notices |
| --- | --- | --- |
| Python | 3.12.14 / PSF-2.0 | [CPython source](https://github.com/python/cpython/tree/v3.12.14); `runtime/licenses/Python-LICENSE.txt` |
| PySide6 / Shiboken / Qt | 6.10.2 / LGPL-3.0, with upstream third-party licenses | [Qt for Python sources](https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-6.10.2-src/); [Qt source archives](https://download.qt.io/archive/qt/6.10/6.10.2/submodules/); license copies and third-party attributions under `runtime/licenses/qt/` |
| FFmpeg / ffprobe | 9.0.2 Gyan essentials / GPL-3.0 | [Exact FFmpeg source revision](https://github.com/FFmpeg/FFmpeg/tree/946fcce07b); [upstream build and library details](https://www.gyan.dev/ffmpeg/builds/); `runtime/ffmpeg/LICENSE` and `README.txt` |
| yt-dlp | 2026.08.19 / Unlicense for original code; executable contains separately licensed components | [Exact release source](https://github.com/yt-dlp/yt-dlp/tree/2026.08.19); `runtime/licenses/yt-dlp-UNLICENSE.txt` and `yt-dlp-THIRD-PARTY.txt` |
| Deno | 2.9.7 / MIT and upstream dependency licenses | [Release source](https://github.com/denoland/deno/tree/v2.9.7); `runtime/licenses/deno-MIT.txt`, `deno-DEPENDENCIES.txt` and `runtime/deno-source-manifest.json` |
| PyInstaller bootloader | 6.19.0 / GPL-2.0-or-later with bootloader distribution exception | [Source and license](https://github.com/pyinstaller/pyinstaller/tree/v6.19.0); `runtime/licenses/PyInstaller-COPYING.txt` |
| Inno Setup | 7.1.0 / Inno Setup License | [Source and license](https://github.com/jrsoftware/issrc/tree/is-7_1_0); `runtime/licenses/Inno-Setup-LICENSE.txt`; compiler is a build tool, not application code |
| Inter | SIL Open Font License 1.1 | [Source](https://github.com/rsms/inter); `app/resources/fonts/OFL.txt` |
| Lucide | ISC; Feather-derived portions MIT | [Source](https://github.com/lucide-icons/lucide); `app/resources/icons/LICENSE` |
| SVGL platform logos | MIT collection; trademarks retain their owners | [Source collection](https://github.com/pheralb/svgl/tree/main/static/library); `app/resources/icons/SVGL-LICENSE` |

YouTube, TikTok, Spotify and Apple Music marks identify the source service. No endorsement or ownership of those marks is claimed. SF Pro is used only if already installed; it is not redistributed.

## Obtaining and replacing dependencies

`runtime.lock.json` records exact upstream binary URLs and SHA-256 digests. `runtime/manifest.json` records the unpacked executable digests. The included FFmpeg README records its source revision, enabled components and external-library versions. See [dependency source access](docs/DEPENDENCY_SOURCES.md) for source locations and build information. Sources remain under their upstream licenses.

Qt/PySide source packages contain their build instructions and third-party attributions. You can rebuild them and replace the corresponding files in `_internal/PySide6` and `_internal/shiboken6`; INTAKE source is available to rebuild the application against modified versions. FFmpeg and yt-dlp can also be replaced through Settings. Changing bundled files invalidates INTAKE's release checksums; this is an integrity fact, not a restriction on modification.

## Documentation images

Application screenshots are rendered from the actual INTAKE interface using a clean demo profile. Big Buck Bunny artwork and media identification are credited to the Blender Foundation, Copyright 2008, [CC BY 3.0](https://peach.blender.org/about/). They are used only to demonstrate the interface. The INTAKE interface and original brand mark are project assets; third-party media is not covered by the INTAKE MIT license.

In installed/portable builds, application asset licenses are in `_internal/app/resources/`. Deno dependency notices include the full upstream Cargo lockfile set (including development and other-platform packages), so inclusion in that notice list does not imply that every listed package is used by INTAKE.
