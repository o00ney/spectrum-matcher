import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
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
from .workers import PlotWorker, UploadWorker

DROP_TEXT = "Drag & drop a Bruker spectrum folder here\nor click to select"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.api = SpectrumMatcherApi()
        self.upload_thread = None
        self.plot_thread = None
        self.plot_pixmap = None

        self.setWindowTitle("NMR Spectrum Matcher")
        self.setMinimumSize(900, 600)
        self._setup_ui()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        self.drop_label = QLabel(DROP_TEXT)
        self.drop_label.setAlignment(Qt.AlignCenter)
        self.drop_label.setMinimumHeight(120)
        self.drop_label.setStyleSheet(
            "border: 2px dashed #888; border-radius: 8px; font-size: 14px; color: #666;"
        )
        self.drop_label.mousePressEvent = self._on_select_click
        layout.addWidget(self.drop_label)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        btn_layout = QHBoxLayout()
        self.select_btn = QPushButton("Select Folder")
        self.select_btn.clicked.connect(self._select_folder)
        btn_layout.addWidget(self.select_btn)

        self.status_label = QLabel(f"Server: {get_server_url()}")
        self.status_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        btn_layout.addWidget(self.status_label, 1)
        layout.addLayout(btn_layout)

        splitter = QSplitter(Qt.Vertical)

        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Flavor Name", "Probability"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.setAlternatingRowColors(True)
        splitter.addWidget(self.table)

        self.plot_label = QLabel("No comparison plot loaded.")
        self.plot_label.setAlignment(Qt.AlignCenter)
        self.plot_label.setMinimumHeight(300)
        splitter.addWidget(self.plot_label)

        splitter.setSizes([220, 380])
        layout.addWidget(splitter)

        self.setAcceptDrops(True)

    def _on_select_click(self, event):
        if self.select_btn.isEnabled():
            self._select_folder()

    def _select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Bruker Spectrum Folder")
        if folder:
            self._upload(folder)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls() and self.select_btn.isEnabled():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        if not self.select_btn.isEnabled():
            return

        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if os.path.isdir(path):
                self._upload(path)
                return
        self.status_label.setText("Drop a folder, not a file.")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refresh_plot()

    def _upload(self, folder):
        self._set_busy(True, f"Uploading: {os.path.basename(folder)}...")
        self.table.setRowCount(0)
        self.plot_pixmap = None
        self.plot_label.setText("Waiting for comparison plot...")

        self.upload_thread = UploadWorker(folder, self.api)
        self.upload_thread.finished.connect(self._on_upload_result)
        self.upload_thread.error.connect(self._on_upload_error)
        self.upload_thread.finished.connect(self.upload_thread.deleteLater)
        self.upload_thread.error.connect(self.upload_thread.deleteLater)
        self.upload_thread.start()

    def _on_upload_result(self, data):
        self.upload_thread = None
        self._set_busy(False, DROP_TEXT)

        results = data.get("results", [])
        self._populate_results(results)
        if results:
            self.status_label.setText(f"Loaded {len(results)} result(s).")
        else:
            self.status_label.setText("No match results returned.")

        plot_id = data.get("plot_id")
        if plot_id:
            self._download_plot(plot_id)
        else:
            self.plot_label.setText("No comparison plot returned.")

    def _on_upload_error(self, message):
        self.upload_thread = None
        self._set_busy(False, f"Error: {message}\nClick to retry")
        self.status_label.setText("Upload failed.")
        self.plot_label.setText("No comparison plot loaded.")

    def _download_plot(self, plot_id):
        self.plot_label.setText("Loading comparison plot...")
        self.plot_thread = PlotWorker(plot_id, self.api)
        self.plot_thread.finished.connect(self._on_plot_loaded)
        self.plot_thread.error.connect(self._on_plot_error)
        self.plot_thread.finished.connect(self.plot_thread.deleteLater)
        self.plot_thread.error.connect(self.plot_thread.deleteLater)
        self.plot_thread.start()

    def _on_plot_loaded(self, image_data):
        self.plot_thread = None
        pixmap = QPixmap()
        if not pixmap.loadFromData(image_data):
            self.plot_label.setText("Server returned an invalid plot image.")
            return

        self.plot_pixmap = pixmap
        self._refresh_plot()

    def _on_plot_error(self, message):
        self.plot_thread = None
        self.plot_label.setText(f"Plot error: {message}")

    def _populate_results(self, results):
        self.table.setRowCount(len(results))
        for row, result in enumerate(results):
            name = str(result.get("name") or "<unnamed>")
            probability = result.get("probability")

            self.table.setItem(row, 0, QTableWidgetItem(name))
            try:
                probability_text = f"{float(probability):.4f}"
            except (TypeError, ValueError):
                probability_text = "n/a"

            probability_item = QTableWidgetItem(probability_text)
            probability_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 1, probability_item)

    def _refresh_plot(self):
        if not self.plot_pixmap:
            return

        width = max(300, self.plot_label.width() - 24)
        height = max(200, self.plot_label.height() - 24)
        scaled = self.plot_pixmap.scaled(
            width,
            height,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.plot_label.setPixmap(scaled)

    def _set_busy(self, is_busy, drop_text):
        self.select_btn.setEnabled(not is_busy)
        self.drop_label.setText(drop_text)
        self.progress.setVisible(is_busy)
        if is_busy:
            self.progress.setRange(0, 0)
            self.status_label.setText("Uploading...")
        else:
            self.progress.setRange(0, 1)
