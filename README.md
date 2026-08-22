# CodecLister

Ein plattformunabhängiges Desktop-Tool (Windows / Linux / macOS), das einen Ordner
nach Video- und Audiodateien durchsucht und deren technische Details in einer
filterbaren Liste anzeigt:

- **Dateiname** und **Dateigröße**
- **Video-Codec** (z. B. H.264/AVC, H.265/HEVC, AV1, VP9 …)
- **Audio-Codec(s)** (inkl. Erkennung von Atmos / DTS:X, sofern von MediaInfo gemeldet)
- **Auflösung** (Breite × Höhe)
- **Dynamikumfang**: SDR / HDR10 / HDR10+ / HLG / Dolby Vision

Die Ergebnisliste lässt sich als **JSON speichern und wieder laden** (zum
Weiternutzen) oder als **CSV exportieren** (z. B. für Excel).

![Status](https://img.shields.io/badge/status-early%20development-orange)

## Features

- 📁 Ordnerwahl inkl. optionalem rekursivem Scan
- ⏳ Fortschrittsbalken mit Abbruchmöglichkeit während des Einlesens
- 🔎 Filter: Auflösung (z. B. „schlechter als 720p", „1080p und besser", „4K"),
  HDR-Typ, Video-/Audio-Codec, Dateiname, Medientyp. Codec-Filter unterstützen
  mehrere Begriffe mit `;` als ODER-Suche sowie Ausschlüsse mit `!` oder `-`,
  z. B. `DivX;Xvid`, `!HEVC` oder `DivX;Xvid;!HEVC`.

Die Auflösungsfilter berücksichtigen sowohl die tatsächliche Höhe als auch die
16:9-equivalente Breite. Dadurch werden beispielsweise `1920×960` und
`1440×1080` als Full HD sowie `960×720` als 720p eingestuft. Das gilt analog
für UHD/4K-Formate und funktioniert damit auch bei 4:3-Remasters.
- 🔃 Sortierbare Tabelle (Klick auf Spaltenkopf)
- 💾 JSON speichern/laden, CSV-Export
- 🖥️ GUI mit [PySide6](https://doc.qt.io/qtforpython/) (Qt 6)
- 📦 Fertige Binaries via GitHub Actions + [Nuitka](https://nuitka.net/)

## Voraussetzungen

- **Python ≥ 3.10**
- **libmediainfo** (native Bibliothek, wird von `pymediainfo` benötigt):

  | Plattform | Installation |
  |-----------|--------------|
  | Windows   | [MediaInfo-DLL](https://mediaarea.net/de/MediaInfo/Download/Windows) herunterladen (Installer genügt) oder `choco install mediainfo` |
  | Linux     | `sudo apt install libmediainfo-dev` (Debian/Ubuntu) bzw. `mediainfo`-Paket der Distribution |
  | macOS     | `brew install media-info` |

## Installation & Start (Entwicklung)

```bash
git clone https://github.com/<DEIN-USER>/CodecLister2.git
cd CodecLister2

python -m venv .venv
# Windows:  .venv\Scripts\activate
# Linux/Mac: source .venv/bin/activate

pip install -r requirements-dev.txt
pip install -e .          # installiert das Paket inkl. 'codeclister'-Kommando

codeclister               # oder: python -m codeclister
```

> Hinweis: Ohne `pip install -e .` muss `PYTHONPATH` auf `src` zeigen
> (die mitgelieferte VS-Code-Launch-Konfiguration macht das automatisch).

## Tests

```bash
pytest
```

## Lokaler Binary-Build mit Nuitka

```bash
pip install nuitka ordered-set zstandard

# Windows (Beispiel):
python -m nuitka --onefile --enable-plugin=pyside6 ^
  --include-package=pymediainfo ^
  --include-data-files="C:\Program Files\MediaInfo\MediaInfo.dll=MediaInfo.dll" ^
  --windows-console-mode=disable --output-filename=CodecLister.exe ^
  src/codeclister/__main__.py
```

Linux/macOS analog ohne `--windows-console-mode` (Details siehe
[.github/workflows/build.yml](.github/workflows/build.yml)).

## Fertige Binaries (GitHub Actions)

Der Workflow [.github/workflows/build.yml](.github/workflows/build.yml) baut bei
jedem Tag `v*` (oder manuell per *workflow_dispatch*) One-File-Binaries für
**Windows, Linux und macOS** und hängt sie an ein GitHub-Release:

```bash
git tag v0.1.0
git push origin v0.1.0
```

## Projektstruktur

```
src/codeclister/
├── __main__.py              # python -m codeclister
├── app.py                   # QApplication-Setup
├── core/
│   ├── models.py            # MediaFileInfo, HdrType
│   ├── mediainfo_reader.py  # pymediainfo-Analyse, HDR-/Codec-Erkennung
│   ├── scanner.py           # Dateisuche + QThread-Scan-Worker (Fortschritt)
│   ├── filters.py           # MediaFilter + Auflösungs-/HDR-Presets
│   └── exporter.py          # JSON speichern/laden, CSV-Export
└── ui/
    └── main_window.py       # Hauptfenster, Tabelle, Filter, Fortschritt
tests/                       # pytest-Tests (Filter, HDR-Erkennung, Export)
.github/workflows/build.yml  # Nuitka-Matrix-Build + Release
```

## Lizenz

[GPL-3.0-or-later](LICENSE)
