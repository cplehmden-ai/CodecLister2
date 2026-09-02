"""Hauptfenster: Ordnerwahl, Fortschritt, Filter und sortierbare Ergebnistabelle."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QSettings, QTimer, Qt
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHeaderView,
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
from codeclister.localization import Translation, available_translations

log = logging.getLogger(__name__)

COLUMNS = ["Filename", "Size", "Resolution", "Video codec", "Audio codec(s) / channels", "HDR"]

HDR_COLORS = {
    HdrType.DOLBY_VISION: QColor("#7b1fa2"),
    HdrType.HDR10: QColor("#ef6c00"),
    HdrType.HDR10_PLUS: QColor("#e65100"),
    HdrType.HLG: QColor("#00838f"),
    HdrType.SDR: QColor("#558b2f"),
}

SELECTION_BG = QColor("#1a5fb4")
SELECTION_FG = QColor("#ffffff")
ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets"


class MediaTableModel(QAbstractTableModel):
    """Tabellenmodell mit Vollbestand + gefilterter Sicht."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._all_items: list[MediaFileInfo] = []
        self._visible: list[MediaFileInfo] = []
        self._filter = MediaFilter()
        self._view = None  # wird vom MainWindow gesetzt (QTableView)
        self._translate = lambda text: text

    def set_translation(self, translate) -> None:
        self._translate = translate
        self.headerDataChanged.emit(Qt.Horizontal, 0, len(COLUMNS) - 1)
        if self.rowCount():
            self.dataChanged.emit(self.index(0, 0), self.index(self.rowCount() - 1, self.columnCount() - 1))

    # -- Qt-Model-API ----------------------------------------------------
    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._visible)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(COLUMNS)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self._translate(COLUMNS[section])
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
                item.video_codec or ("–" if item.is_video else f"({self._translate('Audio')})"),
                item.audio_codecs_text,
                self._translate(item.hdr_type.value) if item.is_video else "–",
            ][column]
        if role == Qt.ToolTipRole:
            tooltip = item.path
            if item.error:
                tooltip += f"\n{self._translate('Error')}: {item.error}"
            return tooltip

        selected = (
            self._view is not None
            and self._view.selectionModel().isRowSelected(index.row(), QModelIndex())
        )
        if role == Qt.ForegroundRole:
            # Selektierte Zeilen: immer weisser Text (Kontrast!), sonst HDR-Farbe.
            if selected:
                return SELECTION_FG
            if column == 5 and item.is_video:
                return HDR_COLORS.get(item.hdr_type)
            return None
        if role == Qt.BackgroundRole and selected:
            # Selektion explizit zeichnen, da Windows-Style die Palette ignoriert.
            return SELECTION_BG
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
        self._settings = QSettings("CodecLister", "CodecLister")
        self._translations = available_translations()
        if not self._translations:
            # Fallback ohne Katalog, falls der translations-Ordner nicht gefunden wird.
            self._translations = [Translation("en", Path())]
        self._translation_by_code = {item.language: item for item in self._translations}
        self._language = self._settings.value("language", "de", type=str)
        if self._language not in self._translation_by_code:
            self._language = "en" if "en" in self._translation_by_code else self._translations[0].language
        self._translation = self._translation_by_code[self._language]

        self.model = MediaTableModel(self)
        self._build_ui()
        self.model._view = self.table
        self.model.set_translation(self._t)
        self._update_scan_buttons()
        self._restore_last_folder()

    def _t(self, message: str) -> str:
        return self._translation.gettext(message)

    def _show_status(self, message: str, timeout: int = 0) -> None:
        self.status_message.setText(message)
        self.status_timer.stop()
        if timeout:
            self.status_timer.start(timeout)

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        central = QWidget(self)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)

        banner = QLabel()
        banner.setAlignment(Qt.AlignCenter)
        banner.setStyleSheet("background-color: #000000;")
        banner_pixmap = QPixmap(str(ASSETS_DIR / "banner.png"))
        banner.setPixmap(banner_pixmap.scaledToHeight(160, Qt.SmoothTransformation))
        root.addWidget(banner)

        # Zeile 1: Ordnerwahl + Scan-Steuerung
        top = QHBoxLayout()
        top.setContentsMargins(9, 0, 9, 0)
        self.btn_choose = QPushButton(self._t("Choose folder..."))
        self.btn_choose.clicked.connect(self.on_choose_folder)
        self.lbl_folder = QLabel(self._t("No folder selected"))
        self.lbl_folder.setStyleSheet("color: palette(mid);")
        self.chk_recursive = QCheckBox(self._t("Include subfolders"))
        self.chk_recursive.setChecked(True)
        self.btn_scan = QPushButton(self._t("Start scan"))
        self.btn_scan.clicked.connect(self.on_start_scan)
        self.btn_cancel = QPushButton(self._t("Cancel"))
        self.btn_cancel.clicked.connect(self.on_cancel_scan)
        top.addWidget(self.btn_choose)
        top.addWidget(self.lbl_folder, stretch=1)
        top.addWidget(self.chk_recursive)
        top.addWidget(self.btn_scan)
        top.addWidget(self.btn_cancel)
        language_label = QLabel(f"{self._t('Language')}:")
        self.cmb_language = QComboBox()
        for translation in self._translations:
            self.cmb_language.addItem(translation.display_name, translation.language)
        self.cmb_language.setCurrentIndex(max(0, self.cmb_language.findData(self._language)))
        self.cmb_language.currentIndexChanged.connect(self.on_language_changed)
        top.addWidget(language_label)
        top.addWidget(self.cmb_language)
        root.addLayout(top)

        # Zeile 2: Filter
        filter_box = QGroupBox(self._t("Filter"))
        filters = QHBoxLayout(filter_box)
        self.cmb_resolution = QComboBox()
        for label, _, _ in RESOLUTION_PRESETS:
            self.cmb_resolution.addItem(self._t(label))
        self.cmb_hdr = QComboBox()
        for label, _ in HDR_PRESETS:
            self.cmb_hdr.addItem(self._t(label))
        self.cmb_type = QComboBox()
        self.cmb_type.addItems([self._t("Video + Audio"), self._t("Video only"), self._t("Audio only")])
        self.edit_vcodec = QLineEdit()
        self.edit_vcodec.setPlaceholderText(self._t("Video codec: HEVC;AVC;!DivX"))
        self.edit_acodec = QLineEdit()
        self.edit_acodec.setPlaceholderText(self._t("Audio codec: TrueHD;!AAC"))
        self.edit_name = QLineEdit()
        self.edit_name.setPlaceholderText(self._t("Filename: film;series;!sample"))
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
        # Selektionsrahmen der Plattform abschalten: die Selektion zeichnet das
        # Model selbst (BackgroundRole), damit die Farben unter Windows gelten.
        self.table.setStyleSheet("QTableView { selection-background-color: transparent; }")
        self.table.setModel(self.model)
        self.table.setSortingEnabled(True)
        self.table.sortByColumn(0, Qt.AscendingOrder)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setColumnWidth(0, 320)
        self.table.setColumnWidth(1, 105)
        self.table.setColumnWidth(2, 200)
        self.table.setColumnWidth(4, 200)
        self.table.setColumnWidth(5, 105)
        self.table.horizontalHeader().setMinimumSectionSize(100)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Interactive)
        # Bei Selektionswechsel Neuzeichnen, damit die HDR-Farbe korrekt
        # ein-/ausgeblendet wird.
        self.table.selectionModel().selectionChanged.connect(
            lambda *_: self.table.viewport().update()
        )
        table_row = QHBoxLayout()
        table_row.setContentsMargins(9, 0, 0, 0)
        table_row.addWidget(self.table)
        root.addLayout(table_row, stretch=1)

        # Zeile 3: Speichern/Laden + Zaehler
        bottom = QHBoxLayout()
        bottom.setContentsMargins(9, 0, 9, 0)
        self.btn_save_json = QPushButton(self._t("Save list (JSON)..."))
        self.btn_save_json.clicked.connect(self.on_save_json)
        self.btn_save_csv = QPushButton(self._t("Export CSV..."))
        self.btn_save_csv.clicked.connect(self.on_save_csv)
        self.btn_load = QPushButton(self._t("Load list (JSON)..."))
        self.btn_load.clicked.connect(self.on_load_json)
        self.lbl_count = QLabel(f"0 {self._t('files')}")
        bottom.addWidget(self.btn_save_json)
        bottom.addWidget(self.btn_save_csv)
        bottom.addWidget(self.btn_load)
        bottom.addStretch(1)
        bottom.addWidget(self.lbl_count)
        root.addLayout(bottom)

        # Statuszeile mit Fortschritt
        self.status_message = QLabel()
        self.status_message.setContentsMargins(9, 0, 0, 0)
        self.status_timer = QTimer(self)
        self.status_timer.setSingleShot(True)
        self.status_timer.timeout.connect(self.status_message.clear)
        self.progress = QProgressBar()
        self.progress.setMaximumWidth(360)
        self.progress.setVisible(False)
        self.statusBar().addWidget(self.status_message, stretch=1)
        self.statusBar().addPermanentWidget(self.progress)
        self._show_status(self._t("Ready."))

        self.setCentralWidget(central)

    def _update_scan_buttons(self, scanning: bool = False) -> None:
        self.btn_scan.setEnabled(self._folder is not None and not scanning)
        self.btn_cancel.setEnabled(scanning)
        self.btn_choose.setEnabled(not scanning)

    def _update_count(self) -> None:
        self.lbl_count.setText(
            f"{len(self.model.visible_items)} / {len(self.model.all_items)} {self._t('files')}"
        )

    def on_language_changed(self, index: int) -> None:
        language = self.cmb_language.itemData(index)
        if not language or language == self._language:
            return
        state = {
            "resolution": self.cmb_resolution.currentIndex(),
            "hdr": self.cmb_hdr.currentIndex(),
            "type": self.cmb_type.currentIndex(),
            "vcodec": self.edit_vcodec.text(),
            "acodec": self.edit_acodec.text(),
            "name": self.edit_name.text(),
            "recursive": self.chk_recursive.isChecked(),
        }
        self._language = language
        self._translation = self._translation_by_code[language]
        self._settings.setValue("language", language)
        self._build_ui()
        self.model._view = self.table
        self.model.set_translation(self._t)
        if self._folder is not None:
            self.lbl_folder.setText(str(self._folder))
            self.lbl_folder.setStyleSheet("")
        self.cmb_resolution.setCurrentIndex(state["resolution"])
        self.cmb_hdr.setCurrentIndex(state["hdr"])
        self.cmb_type.setCurrentIndex(state["type"])
        self.edit_vcodec.setText(state["vcodec"])
        self.edit_acodec.setText(state["acodec"])
        self.edit_name.setText(state["name"])
        self.chk_recursive.setChecked(state["recursive"])
        self.apply_filters()

    # --------------------------------------------------------------- Scan
    def _restore_last_folder(self) -> None:
        """Stellt den zuletzt verwendeten Ordner wieder her (ohne Auto-Scan)."""
        last = self._settings.value("last_folder", "", type=str)
        if last and Path(last).is_dir():
            self._folder = Path(last)
            self.lbl_folder.setText(str(self._folder))
            self.lbl_folder.setStyleSheet("")
            self._update_scan_buttons()
            self._show_status(self._t("Last folder restored."), 5000)

    def on_choose_folder(self) -> None:
        start_dir = str(self._folder) if self._folder else ""
        directory = QFileDialog.getExistingDirectory(self, self._t("Select media folder"), start_dir)
        if not directory:
            return
        self._folder = Path(directory)
        self._settings.setValue("last_folder", str(self._folder))
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
        self._show_status(self._t("Search media files..."))
        self._update_scan_buttons(scanning=True)

        self._worker = ScanWorker(self._folder, self.chk_recursive.isChecked(), self)
        self._worker.scan_started.connect(self.on_scan_started)
        self._worker.file_scanned.connect(self.on_file_scanned)
        self._worker.progress.connect(self.on_progress)
        self._worker.scan_finished.connect(self.on_scan_finished)
        self._worker.start()

    def on_cancel_scan(self) -> None:
        if self._worker is not None:
            self._show_status(self._t("Cancelling..."))
            self._worker.cancel()

    def on_scan_started(self, total: int) -> None:
        self.progress.setRange(0, max(total, 1))
        self.progress.setValue(0)
        self._show_status(self._t("{count} media files found.").format(count=total))

    def on_file_scanned(self, item: MediaFileInfo) -> None:
        self.model.add_item(item)
        self._update_count()

    def on_progress(self, current: int, total: int, name: str) -> None:
        self.progress.setValue(current)
        if name:
            self._show_status(f"[{current}/{total}] {name}")

    def on_scan_finished(self, completed: bool) -> None:
        self.progress.setVisible(False)
        self._update_scan_buttons()
        text = self._t("Scan completed.") if completed else self._t("Scan cancelled.")
        errors = sum(1 for i in self.model.all_items if i.error)
        if errors:
            text += f" ({self._t('{count} file(s) unreadable').format(count=errors)})"
        self._show_status(text, 8000)
        if self._worker is not None:
            self._worker.deleteLater()
            self._worker = None

    def closeEvent(self, event) -> None:
        """Beim Schliessen einen laufenden Scan sauber beenden."""
        if self._worker is not None and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait(5000)
        super().closeEvent(event)

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
            QMessageBox.information(self, __app_name__, self._t("The list is empty."))
            return
        path, _ = QFileDialog.getSaveFileName(
            self, self._t("Save list (JSON)..."), "codeclister.json", "CodecLister (*.json)"
        )
        if not path:
            return
        try:
            # Es wird die gefilterte Sicht gespeichert, wenn Filter aktiv sind.
            items = self.model.visible_items
            save_json(items, Path(path), self._current_folder_text())
            self._show_status(self._t("List saved: {path}").format(path=path), 8000)
        except OSError as exc:
            QMessageBox.critical(self, __app_name__, self._t("Saving failed:\n{error}").format(error=exc))

    def on_save_csv(self) -> None:
        if not self.model.all_items:
            QMessageBox.information(self, __app_name__, self._t("The list is empty."))
            return
        path, _ = QFileDialog.getSaveFileName(
            self, self._t("Export CSV..."), "codeclister.csv", "CSV (*.csv)"
        )
        if not path:
            return
        try:
            save_csv(self.model.visible_items, Path(path))
            self._show_status(self._t("Exported: {path}").format(path=path), 8000)
        except OSError as exc:
            QMessageBox.critical(self, __app_name__, self._t("Export failed:\n{error}").format(error=exc))

    def on_load_json(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, self._t("Load list (JSON)..."), "", "CodecLister (*.json)"
        )
        if not path:
            return
        try:
            items = load_json(Path(path))
        except (OSError, ValueError, KeyError) as exc:
            QMessageBox.critical(self, __app_name__, self._t("Loading failed:\n{error}").format(error=exc))
            return
        self.model.set_items(items)
        self._update_count()
        self._show_status(self._t("{count} entries loaded.").format(count=len(items)), 8000)
