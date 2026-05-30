import io
import os
import threading

import requests

from .config import get_request_timeout, get_server_url


class ApiError(Exception):
    """Raised when the spectrum matcher API cannot complete a request."""


class _ProgressReader:
    """Wrapper that reports read progress to a callback."""

    def __init__(self, file_obj, total_size, callback):
        self._f = file_obj
        self._size = total_size
        self._cb = callback
        self._read = 0

    def read(self, size=-1):
        data = self._f.read(size)
        self._read += len(data)
        if self._cb:
            self._cb(self._read, self._size)
        return data

    def seek(self, offset, whence=0):
        return self._f.seek(offset, whence)

    def tell(self):
        return self._f.tell()

    def close(self):
        self._f.close()


class SpectrumMatcherApi:
    def __init__(self, server_url=None, timeout=None):
        self.server_url = (server_url or get_server_url()).rstrip("/")
        self.timeout = timeout if timeout is not None else get_request_timeout()
        self._cancel_event = threading.Event()

    def cancel(self):
        self._cancel_event.set()

    def check_connection(self):
        """Quick connectivity check. Returns True if server is reachable."""
        try:
            resp = requests.get(
                f"{self.server_url}/docs",
                timeout=min(self.timeout, 5),
            )
            return resp.status_code == 200
        except requests.RequestException:
            return False

    def upload_zip(self, zip_path, filename=None, progress_cb=None):
        self._cancel_event.clear()
        upload_name = filename or os.path.basename(zip_path)
        total = os.path.getsize(zip_path)

        try:
            with open(zip_path, "rb") as file_obj:
                wrapped = _ProgressReader(file_obj, total, progress_cb)
                response = requests.post(
                    f"{self.server_url}/api/upload",
                    files={"file": (upload_name, wrapped, "application/zip")},
                    timeout=self.timeout,
                    stream=True,
                )
        except requests.Timeout as exc:
            raise ApiError(
                "Server response timeout. The model may still be loading."
            ) from exc
        except requests.ConnectionError as exc:
            raise ApiError(
                "Cannot connect to " + self.server_url
                + ". Check the server URL and network."
            ) from exc
        except requests.RequestException as exc:
            raise ApiError("Upload failed: " + str(exc)) from exc

        self._raise_for_status(response)

        # read response with cancel awareness
        chunks = []
        try:
            for chunk in response.iter_content(chunk_size=8192):
                if self._cancel_event.is_set():
                    response.close()
                    raise ApiError("Upload cancelled by user.")
                chunks.append(chunk)
        except requests.RequestException:
            response.close()
            raise

        raw = b"".join(chunks)
        response._content = raw
        try:
            return response.json()
        except ValueError as exc:
            raise ApiError("Server returned invalid JSON.") from exc

    def _raise_for_status(self, response):
        if response.status_code < 400:
            return

        detail = response.text.strip()
        try:
            payload = response.json()
        except ValueError:
            payload = None
        if isinstance(payload, dict) and payload.get("detail"):
            detail = str(payload["detail"])

        message = "Server error " + str(response.status_code)
        if detail:
            message = message + ": " + detail
        raise ApiError(message)
