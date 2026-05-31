import base64
import os
import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QDragEnterEvent, QDropEvent, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .api import SpectrumMatcherApi
from .config import get_server_url
from .export import export_results_csv, export_results_json, export_plot_png
from .plot_widget import SpectrumPlotWidget
from .settings import AppSettings
from .workers import HealthCheckWorker, UploadWorker

DROP_TEXT = (
    "Drag & drop a Bruker spectrum folder (or .zip) here\nor click to browse"
)
HISTORY_MAX = 20


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.api = SpectrumMatcherApi()
        self._upload_thread = None
        self._health_thread = None
        self._plot_pixmap = None
        self._last_result_data = None
        self._result_history = []
        self.settings = AppSettings()

        self._elapsed_timer = QTimer(self)
        self._elapsed_timer.setInterval(200)
        self._elapsed_timer.timeout.connect(self._tick_elapsed)
        self._start_ts = 0.0

        self.setWindowTitle("NMR Spectrum Matcher")
        self.setMinimumSize(1100, 680)

        self._setup_menu()
        self._setup_ui()
        self._setup_statusbar()
        self._restore_settings()
        self._check_connection()

    # ---- close event ----

    def closeEvent(self, event):
        self._elapsed_timer.stop()
        self.settings.window_geometry = self.saveGeometry()
        self.settings.window_state = self.saveState()
        for t in (self._upload_thread, self._health_thread):
            if t is not None and t.isRunning():
                t.cancel()
                t.quit()
                t.wait(3000)
        event.accept()

    # ---- settings ----

    def _restore_settings(self):
        saved_url = self.settings.server_url
        if saved_url:
            self.server_input.setText(saved_url)
            self.api.server_url = saved_url
        geo = self.settings.window_geometry
        if geo:
            self.restoreGeometry(geo)
        state = self.settings.window_state
        if state:
            self.restoreState(state)

    # ---- menu bar ----

    def _setup_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("&File")
        file_menu.addAction(
            QAction("&Open Folder...", self, shortcut="Ctrl+O",
                    triggered=self._select_folder))
        file_menu.addAction(
            QAction("Open &Zip...", self, shortcut="Ctrl+Shift+O",
                    triggered=self._select_zip))
        file_menu.addSeparator()
        file_menu.addAction(
            QAction("&Export Results CSV...", self, shortcut="Ctrl+E",
                    triggered=self._export_csv))
        file_menu.addAction(
            QAction("Export Results &JSON...", self, shortcut="Ctrl+Shift+E",
                    triggered=self._export_json))
        file_menu.addAction(
            QAction("Export &Plot PNG...", self, shortcut="Ctrl+P",
                    triggered=self._export_plot))
        file_menu.addSeparator()
        file_menu.addAction(
            QAction("&Quit", self, shortcut="Ctrl+Q", triggered=self.close))

        view_menu = menubar.addMenu("&View")
        toggle_tb = QAction("Plot &Toolbar", self, checkable=True)
        toggle_tb.setChecked(self.settings.plot_toolbar_visible)
        toggle_tb.toggled.connect(self._on_toggle_toolbar)
        view_menu.addAction(toggle_tb)

        help_menu = menubar.addMenu("&Help")
        help_menu.addAction(
            QAction("&About", self, triggered=self._show_about))

    # ---- status bar ----

    def _setup_statusbar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

    def _status(self, message, color=None, timeout=0):
        self.status_bar.showMessage(message, timeout)
        if color:
            self.status_bar.setStyleSheet(
                "QStatusBar { color: " + color + "; }"
            )
        else:
            self.status_bar.setStyleSheet("")

    # ---- ui setup ----

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        outer = QHBoxLayout(central)
        outer.setContentsMargins(6, 6, 6, 6)

        # ---- left panel ----
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 4, 0)
        left_layout.setSpacing(4)

        # server row
        server_layout = QHBoxLayout()
        server_label = QLabel("Server:")
        server_label.setFixedWidth(42)
        server_layout.addWidget(server_label)

        self.server_input = QLineEdit(get_server_url())
        self.server_input.setPlaceholderText("http://192.168.3.6:8000")
        self.server_input.setToolTip(
            "Server URL (e.g., https://nmr.ooney.xyz or http://192.168.3.6:8000)"
        )
        self.server_input.editingFinished.connect(self._on_server_changed)
        server_layout.addWidget(self.server_input)

        self.test_btn = QPushButton("Test")
        self.test_btn.setFixedWidth(48)
        self.test_btn.setToolTip("Test connectivity to the server")
        self.test_btn.clicked.connect(self._test_server)
        server_layout.addWidget(self.test_btn)
        left_layout.addLayout(server_layout)

        # drop area
        self.drop_label = QLabel(DROP_TEXT)
        self.drop_label.setAlignment(Qt.AlignCenter)
        self.drop_label.setMinimumHeight(68)
        self.drop_label.setStyleSheet(
            "border: 2px dashed #888; border-radius: 6px; "
            "font-size: 13px; color: #666;"
        )
        self.drop_label.setToolTip(
            "Drag a Bruker spectrum folder or .zip file here, or click to browse"
        )
        self.drop_label.mousePressEvent = self._on_drop_click
        left_layout.addWidget(self.drop_label)

        # progress
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setToolTip("Upload and processing progress")
        left_layout.addWidget(self.progress)

        # buttons
        btn_layout = QHBoxLayout()
        self.select_btn = QPushButton("Select Folder")
        self.select_btn.setToolTip("Browse for a Bruker spectrum folder")
        self.select_btn.clicked.connect(self._select_folder)
        btn_layout.addWidget(self.select_btn)

        self.select_zip_btn = QPushButton("Select .zip")
        self.select_zip_btn.setToolTip(
            "Browse for a .zip file containing Bruker spectrum data"
        )
        self.select_zip_btn.clicked.connect(self._select_zip)
        btn_layout.addWidget(self.select_zip_btn)

        self.time_label = QLabel("")
        self.time_label.setStyleSheet("color: #888; font-size: 12px;")
        btn_layout.addWidget(self.time_label)

        self.history_combo = QComboBox()
        self.history_combo.setMinimumWidth(140)
        self.history_combo.setToolTip("Previous upload results")
        self.history_combo.setEnabled(False)
        self.history_combo.currentIndexChanged.connect(self._on_history_selected)
        btn_layout.addWidget(self.history_combo)
        btn_layout.addStretch()
        left_layout.addLayout(btn_layout)

        # results table
        table_wrapper = QWidget()
        table_layout = QVBoxLayout(table_wrapper)
        table_layout.setContentsMargins(0, 0, 0, 0)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["#", "Flavor Name", "Probability"])
        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.Stretch
        )
        self.table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeToContents
        )
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(False)
        self.table.setToolTip("Click column headers to sort results")
        table_layout.addWidget(self.table)

        self.model_label = QLabel("")
        self.model_label.setStyleSheet(
            "color: #6b7280; font-size: 11px; padding: 2px 4px;"
        )
        self.model_label.setAlignment(Qt.AlignRight)
        table_layout.addWidget(self.model_label)

        # ---- right panel (plot) ----
        self.plot_widget = SpectrumPlotWidget()
        self.plot_widget.setToolTip(
            "Comparison plot of query spectrum vs. top matches"
        )
        self.plot_widget.toolbar().setVisible(
            self.settings.plot_toolbar_visible
        )

        # ---- horizontal splitter ----
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left)
        splitter.addWidget(self.plot_widget)
        splitter.setSizes([460, 640])
        outer.addWidget(splitter)

        self.setAcceptDrops(True)

    # ---- connection ----

    def _check_connection(self):
        self._cleanup_thread(self._health_thread)
        self._status("Checking...")
        self._health_thread = HealthCheckWorker(self.api)
        self._health_thread.done.connect(self._on_health_result)
        self._health_thread.done.connect(self._health_thread.deleteLater)
        self._health_thread.start()

    def _on_health_result(self, ok):
        self._health_thread = None
        if ok:
            self._status("Connected to " + self.api.server_url)
        else:
            self._status("Server unreachable", color="#dc2626")

    def _on_server_changed(self):
        url = self.server_input.text().strip()
        if url:
            self.api.server_url = url
            self.settings.server_url = url
            self._check_connection()

    def _test_server(self):
        self._on_server_changed()

    # ---- elapsed time ----

    def _start_elapsed(self):
        self._start_ts = time.monotonic()
        self._elapsed_timer.start()
        self._tick_elapsed()

    def _stop_elapsed(self):
        self._elapsed_timer.stop()
        elapsed = time.monotonic() - self._start_ts
        self.time_label.setText("Done in " + self._fmt_time(elapsed))

    def _tick_elapsed(self):
        elapsed = time.monotonic() - self._start_ts
        self.time_label.setText("Elapsed: " + self._fmt_time(elapsed))

    @staticmethod
    def _fmt_time(seconds):
        if seconds < 60:
            return format(seconds, ".1f") + "s"
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return str(mins) + "m " + str(secs) + "s"

    # ---- file selection ----

    def _on_drop_click(self, event):
        if self.select_btn.isEnabled():
            self._select_folder()

    def _select_folder(self):
        start_dir = self.settings.last_directory or ""
        folder = QFileDialog.getExistingDirectory(
            self, "Select Bruker Spectrum Folder", start_dir
        )
        if folder:
            self.settings.last_directory = folder
            self._upload(folder)

    def _select_zip(self):
        start_dir = self.settings.last_directory or ""
        zip_file, _ = QFileDialog.getOpenFileName(
            self, "Select Bruker Spectrum .zip", start_dir, "ZIP files (*.zip)"
        )
        if zip_file:
            self.settings.last_directory = os.path.dirname(zip_file)
            self._upload(zip_file)

    # ---- drag & drop ----

    def dragEnterEvent(self, event: QDragEnterEvent):
        if not self.select_btn.isEnabled():
            return
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                path = url.toLocalFile()
                if os.path.isdir(path) or path.lower().endswith(".zip"):
                    event.acceptProposedAction()
                    return

    def dropEvent(self, event: QDropEvent):
        if not self.select_btn.isEnabled():
            return
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if os.path.isdir(path) or path.lower().endswith(".zip"):
                self._upload(path)
                return
        self._status("Drop a Bruker folder or .zip file.", color="#dc2626")

    # ---- upload flow ----

    def _upload(self, path):
        # disconnect old worker signals to prevent stale interference
        if self._upload_thread is not None:
            try:
                self._upload_thread.finished.disconnect()
                self._upload_thread.error.disconnect()
                self._upload_thread.progress.disconnect()
            except (RuntimeError, TypeError):
                pass
        self._cleanup_thread(self._upload_thread)

        name = os.path.basename(os.path.normpath(path))
        self._set_busy(True, "Uploading: " + name + " ...")
        self.table.setRowCount(0)
        self._plot_pixmap = None
        self.plot_widget.clear()
        self.model_label.setText("")
        self._start_elapsed()
        self._status("Uploading " + name + " ...")

        self._upload_thread = UploadWorker(path, self.api)
        self._upload_thread.finished.connect(self._on_upload_result)
        self._upload_thread.error.connect(self._on_upload_error)
        self._upload_thread.progress.connect(self._on_upload_progress)
        # Use Qt's built-in finished signal for safe cleanup (fires after run() returns)
        self._upload_thread.finished.connect(self._upload_thread.deleteLater)
        self._upload_thread.start()

    def _on_upload_progress(self, sent, total):
        self.progress.setRange(0, total)
        self.progress.setValue(sent)

    def _on_upload_result(self, data):
        self._upload_thread = None
        self._stop_elapsed()
        self._set_busy(False, DROP_TEXT)

        self._last_result_data = data
        self._add_to_history(data)

        results = data.get("results", [])
        self._populate_results(results)

        model = data.get("model", {})
        if model:
            self.model_label.setText(
                "Model: " + model.get("name", "DeepMID")
                + "  |  " + model.get("arch", "")
                + "  |  Params: " + model.get("params", "")
            )

        if results:
            top = results[0]
            pct = float(top.get("probability", 0)) * 100
            nm = str(top.get("name", "?"))
            self._status(
                "Top: " + nm + " (" + format(pct, ".1f") + "%)  —  "
                + str(len(results)) + " results",
                timeout=15000,
            )
        else:
            self._status("No match results returned.")

        # prefer interactive plot from downsampled data
        query_ppm = data.get("query_ppm")
        query_fid = data.get("query_fid")
        if query_ppm and query_fid:
            self.plot_widget.render_comparison(query_ppm, query_fid, results)
            self._plot_pixmap = None
        else:
            # fallback to base64 PNG
            plot_b64 = data.get("plot_base64", "")
            if plot_b64:
                self._show_plot_b64(plot_b64)
            else:
                self.plot_widget.clear()

    def _on_upload_error(self, message):
        self._upload_thread = None
        self._stop_elapsed()
        self._set_busy(False, DROP_TEXT)
        self._status(str(message)[:120], color="#dc2626")
        self.plot_widget.clear()
        self.time_label.setText("")

    # ---- inline plot ----

    def _show_plot_b64(self, b64_string):
        try:
            image_data = base64.b64decode(b64_string)
        except Exception:
            return
        pixmap = QPixmap()
        if pixmap.loadFromData(image_data):
            self._plot_pixmap = pixmap
            self.plot_widget.render_fallback(pixmap)
        else:
            self.plot_widget.clear()

    # ---- results table ----

    def _populate_results(self, results):
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(results))
        for row, result in enumerate(results):
            rank = QTableWidgetItem()
            rank.setData(Qt.DisplayRole, row + 1)
            rank.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 0, rank)

            name = QTableWidgetItem(str(result.get("name") or "<unnamed>"))
            self.table.setItem(row, 1, name)

            prob = QTableWidgetItem()
            try:
                prob.setData(Qt.DisplayRole, float(result.get("probability", 0)))
            except (TypeError, ValueError):
                pass
            prob.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 2, prob)

        self.table.setSortingEnabled(True)

    # ---- result history ----

    def _add_to_history(self, data):
        entry = {
            "timestamp": time.time(),
            "query_name": data.get("query_name", ""),
            "data": data,
        }
        # remove duplicate query_name entries
        self._result_history = [
            h for h in self._result_history
            if h["query_name"] != entry["query_name"]
        ]
        self._result_history.insert(0, entry)
        if len(self._result_history) > HISTORY_MAX:
            self._result_history = self._result_history[:HISTORY_MAX]
        self._rebuild_history_combo()

    def _rebuild_history_combo(self):
        self.history_combo.blockSignals(True)
        self.history_combo.clear()
        self.history_combo.addItem("(history)")
        for h in self._result_history:
            ts = time.strftime("%H:%M:%S", time.localtime(h["timestamp"]))
            label = ts + "  " + h["query_name"]
            self.history_combo.addItem(label)
        self.history_combo.setCurrentIndex(0)
        self.history_combo.setEnabled(len(self._result_history) > 0)
        self.history_combo.blockSignals(False)

    def _on_history_selected(self, index):
        if index <= 0 or index > len(self._result_history):
            return
        entry = self._result_history[index - 1]
        data = entry["data"]
        self._last_result_data = data
        results = data.get("results", [])
        self._populate_results(results)

        model = data.get("model", {})
        if model:
            self.model_label.setText(
                "Model: " + model.get("name", "DeepMID")
                + "  |  " + model.get("arch", "")
                + "  |  Params: " + model.get("params", "")
            )

        query_ppm = data.get("query_ppm")
        query_fid = data.get("query_fid")
        if query_ppm and query_fid:
            self.plot_widget.render_comparison(query_ppm, query_fid, results)
        else:
            plot_b64 = data.get("plot_base64", "")
            if plot_b64:
                self._show_plot_b64(plot_b64)

        top = results[0] if results else {}
        nm = str(top.get("name", "?"))
        pct = float(top.get("probability", 0)) * 100
        self._status("History: " + nm + " (" + format(pct, ".1f") + "%)")

    # ---- export ----

    def _export_csv(self):
        if not self._last_result_data:
            self._status("No results to export.", color="#dc2626")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Results CSV", "", "CSV (*.csv)"
        )
        if not path:
            return
        try:
            export_results_csv(self._last_result_data.get("results", []), path)
            self._status("Exported CSV: " + os.path.basename(path), timeout=5000)
        except OSError as e:
            self._status("Export failed: " + str(e), color="#dc2626")

    def _export_json(self):
        if not self._last_result_data:
            self._status("No results to export.", color="#dc2626")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Results JSON", "", "JSON (*.json)"
        )
        if not path:
            return
        try:
            export_results_json(self._last_result_data, path)
            self._status("Exported JSON: " + os.path.basename(path), timeout=5000)
        except OSError as e:
            self._status("Export failed: " + str(e), color="#dc2626")

    def _export_plot(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Plot PNG", "comparison_plot.png", "PNG (*.png)"
        )
        if not path:
            return
        try:
            export_plot_png(self.plot_widget, path)
            self._status("Exported PNG: " + os.path.basename(path), timeout=5000)
        except OSError as e:
            self._status("Export failed: " + str(e), color="#dc2626")

    # ---- view ----

    def _on_toggle_toolbar(self, visible):
        self.plot_widget.set_toolbar_visible(visible)
        self.settings.plot_toolbar_visible = visible

    # ---- about ----

    def _show_about(self):
        QMessageBox.about(
            self,
            "About NMR Spectrum Matcher",
            "<h3>NMR Spectrum Matcher</h3>"
            "<p>Deep learning-based NMR spectrum component identification.</p>"
            "<p><b>Model:</b> DeepMID — Siamese CNN + Spatial Pyramid Pooling<br>"
            "<b>Parameters:</b> 470K<br>"
            "<b>Task:</b> Plant flavor component identification from 1H-NMR</p>"
            "<p>Version 0.1.0</p>",
        )

    # ---- helpers ----

    @staticmethod
    def _cleanup_thread(thread):
        if thread is not None and thread.isRunning():
            thread.cancel()
            thread.quit()
            thread.wait(3000)

    def _set_busy(self, is_busy, drop_text):
        self.select_btn.setEnabled(not is_busy)
        self.select_zip_btn.setEnabled(not is_busy)
        self.server_input.setEnabled(not is_busy)
        self.test_btn.setEnabled(not is_busy)
        self.history_combo.setEnabled(
            not is_busy and len(self._result_history) > 0
        )
        self.drop_label.setText(drop_text)
        self.progress.setVisible(is_busy)
        if is_busy:
            self.progress.setRange(0, 0)
        else:
            self.progress.setRange(0, 1)
