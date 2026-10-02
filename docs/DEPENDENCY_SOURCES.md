# Dependency source access

The public release includes unchanged upstream media helper executables. These source references accompany the binaries and their complete included notices; the upstream licenses continue to apply. INTAKE's source archive is not a substitute for the dependencies' sources.

- **FFmpeg 9.0.2:** [source revision 946fcce07b](https://github.com/FFmpeg/FFmpeg/tree/946fcce07b), [source archive](https://github.com/FFmpeg/FFmpeg/archive/946fcce07b.tar.gz), [building FFmpeg](https://ffmpeg.org/platform.html#Windows). The exact provider configuration and external-library versions are in [`runtime/ffmpeg/README.txt`](../runtime/ffmpeg/README.txt); the executable reports its configure switches in `runtime/ffmpeg/BUILD-CONFIG.txt`. These are Gyan's GPLv3 essentials executables; INTAKE does not relink or modify them.
- **Qt 6.10.2:** [module source archives](https://download.qt.io/archive/qt/6.10/6.10.2/submodules/), qtbase, qtsvg and qtimageformats for the shipped modules; [Qt build instructions](https://doc.qt.io/qt-6/windows-building.html).
- **PySide6/Shiboken 6.10.2:** [source distribution](https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-6.10.2-src/), [build instructions](https://doc.qt.io/qtforpython-6/building_from_source/index.html).
- **yt-dlp 2026.08.19:** [source and build instructions](https://github.com/yt-dlp/yt-dlp/tree/2026.08.19). Its included third-party notice identifies the bundled executable's dependencies and upstream source-access contact.
- **Deno 2.9.7:** [source and build instructions](https://github.com/denoland/deno/tree/v2.9.7). The complete upstream Cargo lockfile dependency set is indexed with exact downloadable crate source archives and integrity hashes in [`runtime/deno-source-manifest.json`](../runtime/deno-source-manifest.json); notices are included in `runtime/licenses/deno-DEPENDENCIES.txt`.
- **Python:** [CPython 3.12 source](https://github.com/python/cpython/tree/v3.12.14), [Windows build instructions](https://github.com/python/cpython/tree/v3.12.14/PCbuild).

The exact Qt/PySide source archive URLs and SHA-256 hashes are recorded in [`runtime/qt-source-manifest.json`](../runtime/qt-source-manifest.json). Their upstream license and attribution files are included under `runtime/licenses/qt/`.

## FFmpeg external libraries

The provider README is authoritative for the exact revisions. Source projects for the enabled external libraries follow; use the tags/commits listed in that README rather than a moving default branch.

| Library | Source |
| --- | --- |
| AMF | https://github.com/GPUOpen-LibrariesAndSDKs/AMF |
| AOM | https://aomedia.googlesource.com/aom/ |
| AviSynthPlus | https://github.com/AviSynth/AviSynthPlus |
| Cairo | https://gitlab.freedesktop.org/cairo/cairo |
| NV codec headers | https://github.com/FFmpeg/nv-codec-headers |
| FreeType | https://gitlab.freedesktop.org/freetype/freetype |
| FriBidi | https://github.com/fribidi/fribidi |
| GSM | https://www.quut.com/gsm/ |
| HarfBuzz | https://github.com/harfbuzz/harfbuzz |
| LAME | https://sourceforge.net/projects/lame/files/lame/ |
| libass | https://github.com/libass/libass |
| Game Music Emu | https://github.com/libgme/game-music-emu |
| OpenCORE AMR / vo-amrwbenc | https://sourceforge.net/projects/opencore-amr/files/ |
| libssh | https://git.libssh.org/projects/libssh.git/ |
| Theora / Vorbis / Speex | https://gitlab.xiph.org/xiph |
| WebP | https://chromium.googlesource.com/webm/libwebp/ |
| OpenAL Soft | https://github.com/kcat/openal-soft |
| OpenJPEG | https://github.com/uclouvain/openjpeg |
| OpenMPT | https://github.com/OpenMPT/openmpt |
| Opus | https://github.com/xiph/opus |
| Rubber Band | https://github.com/breakfastquay/rubberband |
| SDL | https://github.com/libsdl-org/SDL |
| SRT | https://github.com/Haivision/srt |
| VAAPI | https://github.com/intel/libva |
| vid.stab | https://github.com/georgmartius/vid.stab |
| VMAF | https://github.com/Netflix/vmaf |
| oneVPL | https://github.com/intel/libvpl |
| VPX | https://chromium.googlesource.com/webm/libvpx/ |
| x264 | https://code.videolan.org/videolan/x264 |
| x265 | https://bitbucket.org/multicoreware/x265_git/ |
| Xvid | https://www.xvid.com/download/ |
| ZeroMQ | https://github.com/zeromq/libzmq |
| zimg | https://github.com/sekrit-twc/zimg |
| GnuTLS / GMP / iconv / gettext | https://ftp.gnu.org/gnu/ |
| bzip2 | https://sourceware.org/bzip2/ |
| XZ | https://github.com/tukaani-project/xz |
| libxml2 | https://gitlab.gnome.org/GNOME/libxml2 |
| zlib | https://zlib.net/ |
| Fontconfig | https://gitlab.freedesktop.org/fontconfig/fontconfig |

If a source link becomes unavailable, report the missing source access privately to the release maintainer through the repository's security reporting channel. Do not remove upstream license notices when redistributing modified packages.

The pinned Windows Python distribution is from [python-build-standalone 20260929](https://github.com/astral-sh/python-build-standalone/tree/20260929), which records its build recipes and dependency sources. `scripts/get_build_python.ps1` identifies the exact binary archive and digest.
