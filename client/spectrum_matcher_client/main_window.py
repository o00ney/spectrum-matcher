import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .api import SpectrumMatcherApi
from .config import get_server_url
from .workers import HealthCheckWorker, PlotWorker, UploadWorker

DROP_TEXT = (
    "Drag & drop a Bruker spectrum folder (or .zip) here\nor click to browse"
)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.api = SpectrumMatcherApi()
        self._upload_thread = None
        self._plot_thread = None
        self._health_thread = None
        self._plot_pixmap = None

        self.setWindowTitle("NMR Spectrum Matcher")
        self.setMinimumSize(900, 650)
        self._setup_ui()
        self._check_connection()

    # ---- close event ----

    def closeEvent(self, event):
        for t in (self._upload_thread, self._plot_thread, self._health_thread):
            if t is not None and t.isRunning():
                t.cancel()
                t.quit()
                t.wait(3000)
        event.accept()

    # ---- ui setup ----

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # --- server row ---
        server_layout = QHBoxLayout()
        server_label = QLabel("Server:")
        server_label.setFixedWidth(45)
        server_layout.addWidget(server_label)

        self.server_input = QLineEdit(get_server_url())
        self.server_input.setPlaceholderText("http://192.168.3.6:8000")
        self.server_input.editingFinished.connect(self._on_server_changed)
        server_layout.addWidget(self.server_input)

        self.test_btn = QPushButton("Test")
        self.test_btn.setFixedWidth(50)
        self.test_btn.clicked.connect(self._test_server)
        server_layout.addWidget(self.test_btn)

        self.status_label = QLabel("Checking...")
        self.status_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        server_layout.addWidget(self.status_label, 1)
        layout.addLayout(server_layout)

        # --- drop area ---
        self.drop_label = QLabel(DROP_TEXT)
        self.drop_label.setAlignment(Qt.AlignCenter)
        self.drop_label.setMinimumHeight(100)
        self.drop_label.setStyleSheet(
            "border: 2px dashed #888; border-radius: 8px; "
            "font-size: 14px; color: #666;"
        )
        self.drop_label.mousePressEvent = self._on_drop_click
        layout.addWidget(self.drop_label)

        # --- progress ---
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        # --- buttons ---
        btn_layout = QHBoxLayout()
        self.select_btn = QPushButton("Select Folder")
        self.select_btn.clicked.connect(self._select_folder)
        btn_layout.addWidget(self.select_btn)

        self.select_zip_btn = QPushButton("Select .zip")
        self.select_zip_btn.clicked.connect(self._select_zip)
        btn_layout.addWidget(self.select_zip_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # --- results + plot ---
        splitter = QSplitter(Qt.Vertical)

        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Flavor Name", "Probability"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeToContents
        )
        self.table.setAlternatingRowColors(True)
        splitter.addWidget(self.table)

        self.plot_label = QLabel("No comparison plot loaded.")
        self.plot_label.setAlignment(Qt.AlignCenter)
        self.plot_label.setMinimumHeight(300)
        splitter.addWidget(self.plot_label)

        splitter.setSizes([220, 380])
        layout.addWidget(splitter)

        self.setAcceptDrops(True)

    # ---- connection ----

    def _check_connection(self):
        self._cleanup_thread(self._health_thread)
        self.status_label.setText("Checking...")
        self.status_label.setStyleSheet("color: #888;")
        self._health_thread = HealthCheckWorker(self.api)
        self._health_thread.done.connect(self._on_health_result)
        self._health_thread.done.connect(self._health_thread.deleteLater)
        self._health_thread.start()

    def _on_health_result(self, ok):
        self._health_thread = None
        if ok:
            self.status_label.setText("Connected")
            self.status_label.setStyleSheet("color: #16a34a;")
        else:
            self.status_label.setText("Unreachable")
            self.status_label.setStyleSheet("color: #dc2626;")

    def _on_server_changed(self):
        url = self.server_input.text().strip()
        if url:
            self.api.server_url = url
            self._check_connection()

    def _test_server(self):
        self._on_server_changed()

    # ---- file selection ----

    def _on_drop_click(self, event):
        if self.select_btn.isEnabled():
            self._select_folder()

    def _select_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Select Bruker Spectrum Folder"
        )
        if folder:
            self._upload(folder)

    def _select_zip(self):
        zip_file, _ = QFileDialog.getOpenFileName(
            self, "Select Bruker Spectrum .zip", "", "ZIP files (*.zip)"
        )
        if zip_file:
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
        self.status_label.setText("Drop a Bruker folder or .zip file.")
        self.status_label.setStyleSheet("color: #dc2626;")

    # ---- upload flow ----

    def _upload(self, path):
        self._cleanup_thread(self._upload_thread)

        name = os.path.basename(os.path.normpath(path))
        self._set_busy(True, "Uploading: " + name + " ...")
        self.table.setRowCount(0)
        self._plot_pixmap = None
        self.plot_label.setText("Waiting for comparison plot...")

        self._upload_thread = UploadWorker(path, self.api)
        self._upload_thread.finished.connect(self._on_upload_result)
        self._upload_thread.error.connect(self._on_upload_error)
        self._upload_thread.finished.connect(self._upload_thread.deleteLater)
        self._upload_thread.error.connect(self._upload_thread.deleteLater)
        self._upload_thread.start()

    def _on_upload_result(self, data):
        self._upload_thread = None
        self._set_busy(False, DROP_TEXT)

        results = data.get("results", [])
        self._populate_results(results)
        if results:
            top = results[0]
            pct = float(top.get("probability", 0)) * 100
            nm = str(top.get("name", "?"))
            self.status_label.setText(
                "Top: " + nm + " (" + format(pct, ".1f") + "%)"
            )
            self.status_label.setStyleSheet("color: #16a34a;")
        else:
            self.status_label.setText("No match results returned.")
            self.status_label.setStyleSheet("color: #888;")

        plot_id = data.get("plot_id")
        if plot_id:
            self._download_plot(plot_id)
        else:
            self.plot_label.setText("No comparison plot returned.")

    def _on_upload_error(self, message):
        self._upload_thread = None
        self._set_busy(False, DROP_TEXT)
        self.status_label.setText(str(message)[:120])
        self.status_label.setStyleSheet("color: #dc2626;")
        self.plot_label.setText("No comparison plot loaded.")

    # ---- plot fetch ----

    def _download_plot(self, plot_id):
        self._cleanup_thread(self._plot_thread)
        self.plot_label.setText("Loading comparison plot...")
        self._plot_thread = PlotWorker(plot_id, self.api)
        self._plot_thread.finished.connect(self._on_plot_loaded)
        self._plot_thread.error.connect(self._on_plot_error)
        self._plot_thread.finished.connect(self._plot_thread.deleteLater)
        self._plot_thread.error.connect(self._plot_thread.deleteLater)
        self._plot_thread.start()

    def _on_plot_loaded(self, image_data):
        self._plot_thread = None
        pixmap = QPixmap()
        if pixmap.loadFromData(image_data):
            self._plot_pixmap = pixmap
            self._refresh_plot()
        else:
            self.plot_label.setText("Server returned an invalid plot image.")

    def _on_plot_error(self, message):
        self._plot_thread = None
        self.plot_label.setText(str(message)[:120])

    # ---- helpers ----

    @staticmethod
    def _cleanup_thread(thread):
        if thread is not None and thread.isRunning():
            thread.cancel()
            thread.quit()
            thread.wait(3000)

    def _populate_results(self, results):
        self.table.setRowCount(len(results))
        for row, result in enumerate(results):
            name = str(result.get("name") or "<unnamed>")
            probability = result.get("probability")
            self.table.setItem(row, 0, QTableWidgetItem(name))
            try:
                text = format(float(probability), ".4f")
            except (TypeError, ValueError):
                text = "n/a"
            item = QTableWidgetItem(text)
            item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 1, item)

    def _refresh_plot(self):
        if not self._plot_pixmap:
            return
        w = max(300, self.plot_label.width() - 24)
        h = max(200, self.plot_label.height() - 24)
        scaled = self._plot_pixmap.scaled(
            w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.plot_label.setPixmap(scaled)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refresh_plot()

    def _set_busy(self, is_busy, drop_text):
        self.select_btn.setEnabled(not is_busy)
        self.select_zip_btn.setEnabled(not is_busy)
        self.server_input.setEnabled(not is_busy)
        self.test_btn.setEnabled(not is_busy)
        self.drop_label.setText(drop_text)
        self.progress.setVisible(is_busy)
        if is_busy:
            self.progress.setRange(0, 0)
        else:
            self.progress.setRange(0, 1)
