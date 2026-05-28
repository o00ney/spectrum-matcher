import os
import tempfile
import traceback
import zipfile

from PySide6.QtCore import QThread, Signal

from .api import ApiError, SpectrumMatcherApi


class UploadWorker(QThread):
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, path, api=None):
        super().__init__()
        self.path = path
        self.api = api or SpectrumMatcherApi()
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        zip_path = None
        try:
            if self._is_cancelled:
                return
            if os.path.isfile(self.path) and self.path.lower().endswith(".zip"):
                zip_path = self.path
            else:
                zip_path = _zip_folder(self.path)
            if self._is_cancelled:
                return
            filename = os.path.basename(zip_path)
            result = self.api.upload_zip(zip_path, filename)
            if not self._is_cancelled:
                self.finished.emit(result)
        except Exception as exc:
            traceback.print_exc()
            msg = str(exc) if str(exc) else type(exc).__name__
            self.error.emit("Upload: " + msg)
        finally:
            if zip_path and zip_path != self.path and os.path.exists(zip_path):
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
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            if self._is_cancelled:
                return
            data = self.api.fetch_plot(self.plot_id)
            if not self._is_cancelled:
                self.finished.emit(data)
        except Exception as exc:
            traceback.print_exc()
            msg = str(exc) if str(exc) else type(exc).__name__
            self.error.emit("Plot: " + msg)


class HealthCheckWorker(QThread):
    done = Signal(bool)

    def __init__(self, api=None):
        super().__init__()
        self.api = api or SpectrumMatcherApi()
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        if not self._is_cancelled:
            self.done.emit(self.api.check_connection())


def _zip_folder(folder_path):
    if not os.path.isdir(folder_path):
        raise ValueError("Please select a valid folder or .zip file.")

    has_pdata = False
    for _root, dirs, _files in os.walk(folder_path):
        if os.path.basename(_root) == "pdata":
            has_pdata = True
            break
    if not has_pdata:
        raise ValueError(
            "No Bruker spectrum found. The folder must contain "
            "a 'pdata' subdirectory."
        )

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
