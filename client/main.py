"""
Qt (PySide6) client for NMR Spectrum Matcher.

Features:
  - Drag & drop or file dialog to select a Bruker spectrum folder
  - Auto-zip and upload to the server
  - Display ranked match results (QTableWidget)
  - Display comparison plot (QPixmap from server PNG)
"""

import sys
import zipfile
import tempfile
import os

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTableWidget, QTableWidgetItem, QFileDialog,
    QProgressBar, QSplitter, QHeaderView,
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QPixmap, QDragEnterEvent, QDropEvent
import requests

SERVER_URL = "http://cloud.ooney.xyz"


class UploadThread(QThread):
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, folder_path):
        super().__init__()
        self.folder_path = folder_path

    def run(self):
        try:
            tmp = tempfile.NamedTemporaryFile(suffix='.zip', delete=False)
            with zipfile.ZipFile(tmp, 'w') as zf:
                for root, _, files in os.walk(self.folder_path):
                    for f in files:
                        full = os.path.join(root, f)
                        arc = os.path.relpath(full, self.folder_path)
                        zf.write(full, arc)
            tmp.close()

            with open(tmp.name, 'rb') as f:
                resp = requests.post(
                    f"{SERVER_URL}/api/upload",
                    files={'file': (os.path.basename(self.folder_path) + '.zip', f)}
                )
            os.unlink(tmp.name)

            if resp.status_code == 200:
                self.finished.emit(resp.json())
            else:
                self.error.emit(f"Server error: {resp.status_code}")
        except Exception as e:
            self.error.emit(str(e))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NMR Spectrum Matcher")
        self.setMinimumSize(900, 600)
        self._setup_ui()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Upload area
        self.drop_label = QLabel("Drag & drop a Bruker spectrum folder here\nor click to select")
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
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Results area
        splitter = QSplitter(Qt.Vertical)

        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Flavor Name", "Probability"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        splitter.addWidget(self.table)

        self.plot_label = QLabel()
        self.plot_label.setAlignment(Qt.AlignCenter)
        self.plot_label.setMinimumHeight(300)
        splitter.addWidget(self.plot_label)

        splitter.setSizes([200, 400])
        layout.addWidget(splitter)

        self.setAcceptDrops(True)

    def _on_select_click(self, event):
        self._select_folder()

    def _select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Bruker Spectrum Folder")
        if folder:
            self._upload(folder)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if os.path.isdir(path):
                self._upload(path)
                return

    def _upload(self, folder):
        self.drop_label.setText(f"Uploading: {os.path.basename(folder)}...")
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)
        self.thread = UploadThread(folder)
        self.thread.finished.connect(self._on_result)
        self.thread.error.connect(self._on_error)
        self.thread.start()

    def _on_result(self, data):
        self.progress.setVisible(False)
        self.drop_label.setText("Drag & drop a Bruker spectrum folder here\nor click to select")

        results = data.get('results', [])
        self.table.setRowCount(len(results))
        for i, r in enumerate(results):
            self.table.setItem(i, 0, QTableWidgetItem(r['name']))
            prob = QTableWidgetItem(f"{r['probability']:.4f}")
            prob.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 1, prob)

        plot_id = data.get('plot_id', '')
        if plot_id:
            img_data = requests.get(f"{SERVER_URL}/api/plot/{plot_id}").content
            pix = QPixmap()
            pix.loadFromData(img_data)
            self.plot_label.setPixmap(pix.scaledToWidth(800, Qt.SmoothTransformation))

    def _on_error(self, msg):
        self.progress.setVisible(False)
        self.drop_label.setText(f"Error: {msg}\nClick to retry")


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
