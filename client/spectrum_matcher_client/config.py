import os

DEFAULT_SERVER_URL = "https://nmr.ooney.xyz"
LOCAL_SERVER_URL = "http://192.168.3.6:8000"
DEFAULT_TIMEOUT_SECONDS = 15


def get_server_url():
    url = os.getenv("SPECTRUM_MATCHER_SERVER_URL", DEFAULT_SERVER_URL).strip()
    return url.rstrip("/") or DEFAULT_SERVER_URL


def get_request_timeout():
    value = os.getenv("SPECTRUM_MATCHER_TIMEOUT", "").strip()
    if not value:
        return DEFAULT_TIMEOUT_SECONDS
    try:
        timeout = float(value)
    except ValueError:
        return DEFAULT_TIMEOUT_SECONDS
    if timeout <= 0:
        return DEFAULT_TIMEOUT_SECONDS
    return timeout
