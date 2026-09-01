# CodecLister

A cross-platform desktop tool for Windows, Linux, and macOS that scans a
folder for video and audio files and displays their technical details in a
filterable list:

- **Filename** and **file size**
- **Video codec** such as H.264/AVC, H.265/HEVC, AV1, or VP9
- **Audio codec(s)** including channel count and Atmos/DTS:X when reported by MediaInfo
- **Resolution** (width x height)
- **Dynamic range**: SDR, HDR10, HDR10+, HLG, or Dolby Vision

Results can be saved and loaded as **JSON** for later use or exported as
**CSV** for spreadsheets such as Excel.

![Status](https://img.shields.io/badge/status-stable-brightgreen)

## Features

- Folder selection with optional recursive scanning
- Progress bar with cancellation while scanning
- Filters for resolution, HDR type, video/audio codec, filename, and media type
- Codec filters support semicolon-separated OR terms and exclusions with `!` or `-`:
  `DivX;Xvid`, `!HEVC`, or `DivX;Xvid;!HEVC`
- Resolution filters support widescreen, 4:3 remasters, and CinemaScope formats.
  For example, `1920x960` and `1440x1080` count as Full HD, `960x720` as 720p,
  and `2880x2160` as UHD/4K
- Sortable table by clicking a column header
- Save/load JSON lists and export CSV
- GUI built with [PySide6](https://doc.qt.io/qtforpython/) (Qt 6)
- GUI language switch between all languages found in `translations/*.po`
  (built-in: German, English, French)
- Custom languages can be added through `translations/<code>.po`; see
  [translations/README.md](translations/README.md)
- Ready for binary builds via GitHub Actions and [Nuitka](https://nuitka.net/)

## Requirements

- **Python >= 3.10**
- **libmediainfo**, the native library required by `pymediainfo`:

  | Platform | Installation |
  |----------|--------------|
  | Windows  | Download the [MediaInfo DLL](https://mediaarea.net/en/MediaInfo/Download/Windows) or run `choco install mediainfo` |
  | Linux    | `sudo apt install libmediainfo-dev` on Debian/Ubuntu, or install the distribution's MediaInfo package |
  | macOS    | `brew install media-info` |

## Installation and start

```bash
git clone https://github.com/cplehmden-ai/CodecLister2.git
cd CodecLister2

python -m venv .venv
# Windows:  .venv\\Scripts\\activate
# Linux/Mac: source .venv/bin/activate

pip install -r requirements-dev.txt
pip install -e .

codeclister               # or: python -m codeclister
```

Without `pip install -e .`, set `PYTHONPATH` to `src` instead. The included
VS Code launch configuration does this automatically.

## Tests

```bash
pytest
```

## Local binary build with Nuitka

```bash
pip install nuitka ordered-set zstandard

# Windows example:
python -m nuitka --onefile --enable-plugin=pyside6 ^
  --include-package=pymediainfo ^
  --include-data-dir=src\codeclister\assets=codeclister\assets ^
  --include-data-dir=translations=translations ^
  --include-data-files="C:\\Program Files\\MediaInfo\\MediaInfo.dll=MediaInfo.dll" ^
  --windows-icon-from-ico=src\codeclister\assets\icon.ico ^
  --windows-console-mode=disable --output-filename=CodecLister.exe ^
  src/codeclister/__main__.py
```

On Linux/macOS, omit `--windows-console-mode`. See
[.github/workflows/build.yml](.github/workflows/build.yml) for details.

## Release binaries

The workflow [.github/workflows/build.yml](.github/workflows/build.yml) builds
one-file binaries for Windows, Linux, and macOS on every `v*` tag, or manually
via `workflow_dispatch`, and attaches them to a GitHub release:

```bash
git tag v1.0.0
git push origin v1.0.0
```

## Project structure

```
src/codeclister/
├── __main__.py              # python -m codeclister
├── app.py                   # QApplication setup
├── assets/                  # banner.png, icon.png, icon.ico
├── core/
│   ├── models.py            # MediaFileInfo, HdrType
│   ├── mediainfo_reader.py  # pymediainfo analysis and HDR/codec detection
│   ├── scanner.py           # file search and QThread scan worker
│   ├── filters.py           # MediaFilter and resolution/HDR presets
│   └── exporter.py          # JSON save/load and CSV export
└── ui/
    └── main_window.py       # main window, table, filters, progress
tests/                       # pytest tests
translations/                # built-in and custom PO translations
.github/workflows/build.yml  # Nuitka matrix build and release
```

## License

[GPL-3.0-or-later](LICENSE)