import os
import tempfile
import zipfile

from PySide6.QtCore import QThread, Signal

from .api import ApiError, SpectrumMatcherApi


class UploadWorker(QThread):
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, folder_path, api=None):
        super().__init__()
        self.folder_path = folder_path
        self.api = api or SpectrumMatcherApi()

    def run(self):
        zip_path = None
        try:
            zip_path = _zip_folder(self.folder_path)
            filename = f"{os.path.basename(os.path.normpath(self.folder_path))}.zip"
            self.finished.emit(self.api.upload_zip(zip_path, filename))
        except (OSError, zipfile.BadZipFile, ApiError, ValueError) as exc:
            self.error.emit(str(exc))
        finally:
            if zip_path and os.path.exists(zip_path):
                try:
                    os.unlink(zip_path)
                except OSError:
                    pass


class PlotWorker(QThread):
    finished = Signal(bytes)
    error = Signal(str)

    def __init__(self, plot_id, api=None):
        super().__init__()
        self.plot_id = plot_id
        self.api = api or SpectrumMatcherApi()

    def run(self):
        try:
            self.finished.emit(self.api.fetch_plot(self.plot_id))
        except ApiError as exc:
            self.error.emit(str(exc))


def _zip_folder(folder_path):
    if not os.path.isdir(folder_path):
        raise ValueError("Please select a valid folder.")

    tmp = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
    zip_path = tmp.name
    tmp.close()

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for root, _, files in os.walk(folder_path):
            for filename in files:
                full_path = os.path.join(root, filename)
                archive_name = os.path.relpath(full_path, folder_path)
                archive.write(full_path, archive_name)

    return zip_path
