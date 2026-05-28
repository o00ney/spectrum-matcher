import os

import requests

from .config import get_request_timeout, get_server_url


class ApiError(Exception):
    """Raised when the spectrum matcher API cannot complete a request."""


class SpectrumMatcherApi:
    def __init__(self, server_url=None, timeout=None):
        self.server_url = (server_url or get_server_url()).rstrip("/")
        self.timeout = timeout if timeout is not None else get_request_timeout()

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

    def upload_zip(self, zip_path, filename=None):
        upload_name = filename or os.path.basename(zip_path)
        try:
            with open(zip_path, "rb") as file_obj:
                response = requests.post(
                    f"{self.server_url}/api/upload",
                    files={"file": (upload_name, file_obj, "application/zip")},
                    timeout=self.timeout,
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
        try:
            return response.json()
        except ValueError as exc:
            raise ApiError("Server returned invalid JSON.") from exc

    def fetch_plot(self, plot_id):
        if not plot_id:
            raise ApiError("Missing plot id.")

        try:
            response = requests.get(
                f"{self.server_url}/api/plot/{plot_id}",
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise ApiError("Plot download failed: " + str(exc)) from exc

        self._raise_for_status(response)
        if not response.content:
            raise ApiError("Server returned an empty plot image.")
        return response.content

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
