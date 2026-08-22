"""Hauptfenster: Ordnerwahl, Fortschritt, Filter und sortierbare Ergebnistabelle."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from codeclister import __app_name__, __version__
from codeclister.core.exporter import load_json, save_csv, save_json
from codeclister.core.filters import HDR_PRESETS, RESOLUTION_PRESETS, MediaFilter
from codeclister.core.models import HdrType, MediaFileInfo
from codeclister.core.scanner import ScanWorker

log = logging.getLogger(__name__)

COLUMNS = ["Dateiname", "Größe", "Auflösung", "Video-Codec", "Audio-Codec(s)", "HDR"]

HDR_COLORS = {
    HdrType.DOLBY_VISION: QColor("#7b1fa2"),
    HdrType.HDR10: QColor("#ef6c00"),
    HdrType.HDR10_PLUS: QColor("#e65100"),
    HdrType.HLG: QColor("#00838f"),
    HdrType.SDR: QColor("#558b2f"),
}


class MediaTableModel(QAbstractTableModel):
    """Tabellenmodell mit Vollbestand + gefilterter Sicht."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._all_items: list[MediaFileInfo] = []
        self._visible: list[MediaFileInfo] = []
        self._filter = MediaFilter()

    # -- Qt-Model-API ----------------------------------------------------
    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._visible)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(COLUMNS)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return COLUMNS[section]
        return None

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        item = self._visible[index.row()]
        column = index.column()

        if role == Qt.DisplayRole:
            return [
                item.name,
                item.size_human,
                item.resolution,
                item.video_codec or ("–" if item.is_video else "(Audio)"),
                item.audio_codecs_text,
                item.hdr_type.value if item.is_video else "–",
            ][column]
        if role == Qt.ToolTipRole:
            tooltip = item.path
            if item.error:
                tooltip += f"\nFehler: {item.error}"
            return tooltip
        if role == Qt.ForegroundRole and column == 5 and item.is_video:
            return HDR_COLORS.get(item.hdr_type)
        if role == Qt.UserRole:  # Rohwerte fuer Sortierung
            return [
                item.name.lower(),
                item.size_bytes,
                (item.height or 0),
                (item.video_codec or "").lower(),
                item.audio_codecs_text.lower(),
                item.hdr_type.value,
            ][column]
        return None

    def sort(self, column, order=Qt.AscendingOrder) -> None:
        self.layoutAboutToBeChanged.emit()
        reverse = order == Qt.DescendingOrder
        self._visible.sort(key=lambda i: self._sort_key(i, column), reverse=reverse)
        self.layoutChanged.emit()

    @staticmethod
    def _sort_key(item: MediaFileInfo, column: int):
        return [
            item.name.lower(),
            item.size_bytes,
            (item.height or 0),
            (item.video_codec or "").lower(),
            item.audio_codecs_text.lower(),
            item.hdr_type.value,
        ][column]

    # -- Datenverwaltung --------------------------------------------------
    def add_item(self, item: MediaFileInfo) -> None:
        self._all_items.append(item)
        if self._filter.matches(item):
            row = len(self._visible)
            self.beginInsertRows(QModelIndex(), row, row)
            self._visible.append(item)
            self.endInsertRows()

    def set_items(self, items: list[MediaFileInfo]) -> None:
        self.beginResetModel()
        self._all_items = list(items)
        self._visible = [i for i in self._all_items if self._filter.matches(i)]
        self.endResetModel()

    def clear(self) -> None:
        self.set_items([])

    def set_filter(self, media_filter: MediaFilter) -> None:
        self.beginResetModel()
        self._filter = media_filter
        self._visible = [i for i in self._all_items if self._filter.matches(i)]
        self.endResetModel()

    @property
    def all_items(self) -> list[MediaFileInfo]:
        return list(self._all_items)

    @property
    def visible_items(self) -> list[MediaFileInfo]:
        return list(self._visible)


class MainWindow(QMainWindow):
    """Hauptfenster der Anwendung."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{__app_name__} {__version__}")
        self.resize(1100, 650)

        self._folder: Path | None = None
        self._worker: ScanWorker | None = None

        self.model = MediaTableModel(self)
        self._build_ui()
        self._update_scan_buttons()

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        central = QWidget(self)
        root = QVBoxLayout(central)

        # Zeile 1: Ordnerwahl + Scan-Steuerung
        top = QHBoxLayout()
        self.btn_choose = QPushButton("Ordner wählen…")
        self.btn_choose.clicked.connect(self.on_choose_folder)
        self.lbl_folder = QLabel("Kein Ordner ausgewählt")
        self.lbl_folder.setStyleSheet("color: palette(mid);")
        self.chk_recursive = QCheckBox("Unterordner einbeziehen")
        self.chk_recursive.setChecked(True)
        self.btn_scan = QPushButton("Scan starten")
        self.btn_scan.clicked.connect(self.on_start_scan)
        self.btn_cancel = QPushButton("Abbrechen")
        self.btn_cancel.clicked.connect(self.on_cancel_scan)
        top.addWidget(self.btn_choose)
        top.addWidget(self.lbl_folder, stretch=1)
        top.addWidget(self.chk_recursive)
        top.addWidget(self.btn_scan)
        top.addWidget(self.btn_cancel)
        root.addLayout(top)

        # Zeile 2: Filter
        filter_box = QGroupBox("Filter")
        filters = QHBoxLayout(filter_box)
        self.cmb_resolution = QComboBox()
        for label, _, _ in RESOLUTION_PRESETS:
            self.cmb_resolution.addItem(label)
        self.cmb_hdr = QComboBox()
        for label, _ in HDR_PRESETS:
            self.cmb_hdr.addItem(label)
        self.cmb_type = QComboBox()
        self.cmb_type.addItems(["Video + Audio", "Nur Video", "Nur Audio"])
        self.edit_vcodec = QLineEdit()
        self.edit_vcodec.setPlaceholderText("Video-Codec, z. B. HEVC")
        self.edit_acodec = QLineEdit()
        self.edit_acodec.setPlaceholderText("Audio-Codec, z. B. TrueHD")
        self.edit_name = QLineEdit()
        self.edit_name.setPlaceholderText("Dateiname enthält…")
        for widget in (
            self.cmb_resolution, self.cmb_hdr, self.cmb_type,
            self.edit_vcodec, self.edit_acodec, self.edit_name,
        ):
            filters.addWidget(widget)
        self.cmb_resolution.currentIndexChanged.connect(self.apply_filters)
        self.cmb_hdr.currentIndexChanged.connect(self.apply_filters)
        self.cmb_type.currentIndexChanged.connect(self.apply_filters)
        self.edit_vcodec.textChanged.connect(self.apply_filters)
        self.edit_acodec.textChanged.connect(self.apply_filters)
        self.edit_name.textChanged.connect(self.apply_filters)
        root.addWidget(filter_box)

        # Tabelle
        self.table = QTableView()
        # Kontrast in selektierten Zeilen sicherstellen (sonst sind farbige
        # HDR-Texte auf dem Standard-Selektionshintergrund kaum lesbar).
        self.table.setStyleSheet(
            "QTableView {"
            "  selection-background-color: #1a5fb4;"
            "  selection-color: #ffffff;"
            "}"
        )
        self.table.setModel(self.model)
        self.table.setSortingEnabled(True)
        self.table.sortByColumn(0, Qt.AscendingOrder)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setColumnWidth(0, 320)
        root.addWidget(self.table, stretch=1)

        # Zeile 3: Speichern/Laden + Zaehler
        bottom = QHBoxLayout()
        self.btn_save_json = QPushButton("Liste speichern (JSON)…")
        self.btn_save_json.clicked.connect(self.on_save_json)
        self.btn_save_csv = QPushButton("CSV exportieren…")
        self.btn_save_csv.clicked.connect(self.on_save_csv)
        self.btn_load = QPushButton("Liste laden (JSON)…")
        self.btn_load.clicked.connect(self.on_load_json)
        self.lbl_count = QLabel("0 Dateien")
        bottom.addWidget(self.btn_save_json)
        bottom.addWidget(self.btn_save_csv)
        bottom.addWidget(self.btn_load)
        bottom.addStretch(1)
        bottom.addWidget(self.lbl_count)
        root.addLayout(bottom)

        # Statuszeile mit Fortschritt
        self.progress = QProgressBar()
        self.progress.setMaximumWidth(360)
        self.progress.setVisible(False)
        self.statusBar().addPermanentWidget(self.progress)
        self.statusBar().showMessage("Bereit.")

        self.setCentralWidget(central)

    def _update_scan_buttons(self, scanning: bool = False) -> None:
        self.btn_scan.setEnabled(self._folder is not None and not scanning)
        self.btn_cancel.setEnabled(scanning)
        self.btn_choose.setEnabled(not scanning)

    def _update_count(self) -> None:
        self.lbl_count.setText(
            f"{len(self.model.visible_items)} / {len(self.model.all_items)} Dateien"
        )

    # --------------------------------------------------------------- Scan
    def on_choose_folder(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Medienordner wählen")
        if not directory:
            return
        self._folder = Path(directory)
        self.lbl_folder.setText(str(self._folder))
        self.lbl_folder.setStyleSheet("")
        self._update_scan_buttons()
        self.on_start_scan()

    def on_start_scan(self) -> None:
        if self._folder is None:
            return
        self.model.clear()
        self._update_count()
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)  # unbestimmt, bis scan_started kommt
        self.statusBar().showMessage("Suche Mediendateien…")
        self._update_scan_buttons(scanning=True)

        self._worker = ScanWorker(self._folder, self.chk_recursive.isChecked(), self)
        self._worker.scan_started.connect(self.on_scan_started)
        self._worker.file_scanned.connect(self.on_file_scanned)
        self._worker.progress.connect(self.on_progress)
        self._worker.scan_finished.connect(self.on_scan_finished)
        self._worker.start()

    def on_cancel_scan(self) -> None:
        if self._worker is not None:
            self.statusBar().showMessage("Breche ab…")
            self._worker.cancel()

    def on_scan_started(self, total: int) -> None:
        self.progress.setRange(0, max(total, 1))
        self.progress.setValue(0)
        self.statusBar().showMessage(f"{total} Mediendateien gefunden.")

    def on_file_scanned(self, item: MediaFileInfo) -> None:
        self.model.add_item(item)
        self._update_count()

    def on_progress(self, current: int, total: int, name: str) -> None:
        self.progress.setValue(current)
        if name:
            self.statusBar().showMessage(f"[{current}/{total}] {name}")

    def on_scan_finished(self, completed: bool) -> None:
        self.progress.setVisible(False)
        self._update_scan_buttons()
        text = "Scan abgeschlossen." if completed else "Scan abgebrochen."
        errors = sum(1 for i in self.model.all_items if i.error)
        if errors:
            text += f" ({errors} Datei(en) nicht lesbar)"
        self.statusBar().showMessage(text, 8000)
        if self._worker is not None:
            self._worker.deleteLater()
            self._worker = None

    # ------------------------------------------------------------- Filter
    def apply_filters(self) -> None:
        _, min_h, max_h = RESOLUTION_PRESETS[self.cmb_resolution.currentIndex()]
        _, hdr_types = HDR_PRESETS[self.cmb_hdr.currentIndex()]
        type_index = self.cmb_type.currentIndex()
        self.model.set_filter(
            MediaFilter(
                min_height=min_h,
                max_height=max_h,
                hdr_types=hdr_types,
                video_codec_query=self.edit_vcodec.text().strip(),
                audio_codec_query=self.edit_acodec.text().strip(),
                name_query=self.edit_name.text().strip(),
                only_videos=type_index == 1,
                only_audio=type_index == 2,
            )
        )
        self._update_count()

    # -------------------------------------------------------- Speichern/Laden
    def _current_folder_text(self) -> str:
        return str(self._folder) if self._folder else ""

    def on_save_json(self) -> None:
        if not self.model.all_items:
            QMessageBox.information(self, __app_name__, "Die Liste ist leer.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Liste speichern", "codeclister.json", "CodecLister-Liste (*.json)"
        )
        if not path:
            return
        try:
            # Es wird die gefilterte Sicht gespeichert, wenn Filter aktiv sind.
            items = self.model.visible_items
            save_json(items, Path(path), self._current_folder_text())
            self.statusBar().showMessage(f"Gespeichert: {path}", 8000)
        except OSError as exc:
            QMessageBox.critical(self, __app_name__, f"Speichern fehlgeschlagen:\n{exc}")

    def on_save_csv(self) -> None:
        if not self.model.all_items:
            QMessageBox.information(self, __app_name__, "Die Liste ist leer.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "CSV exportieren", "codeclister.csv", "CSV-Datei (*.csv)"
        )
        if not path:
            return
        try:
            save_csv(self.model.visible_items, Path(path))
            self.statusBar().showMessage(f"Exportiert: {path}", 8000)
        except OSError as exc:
            QMessageBox.critical(self, __app_name__, f"Export fehlgeschlagen:\n{exc}")

    def on_load_json(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Liste laden", "", "CodecLister-Liste (*.json)"
        )
        if not path:
            return
        try:
            items = load_json(Path(path))
        except (OSError, ValueError, KeyError) as exc:
            QMessageBox.critical(self, __app_name__, f"Laden fehlgeschlagen:\n{exc}")
            return
        self.model.set_items(items)
        self._update_count()
        self.statusBar().showMessage(f"{len(items)} Einträge geladen.", 8000)
