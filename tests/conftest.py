"""Shared test fixtures for spectrum-matcher tests."""

import os
import sys
import tempfile
import threading
import time
from pathlib import Path

import pytest

# Add server and client to path
TESTS_DIR = Path(__file__).resolve().parent
PROJECT_DIR = TESTS_DIR.parent
SERVER_DIR = PROJECT_DIR / "server"
CLIENT_DIR = PROJECT_DIR / "client"

sys.path.insert(0, str(SERVER_DIR))
sys.path.insert(0, str(CLIENT_DIR))


@pytest.fixture(scope="session")
def project_dir():
    return PROJECT_DIR


@pytest.fixture(scope="session")
def sample_zip():
    """Path to the B1 sample Bruker spectrum zip."""
    path = TESTS_DIR / "b1_sample.zip"
    if not path.exists():
        pytest.skip("b1_sample.zip not found")
    return str(path)


@pytest.fixture(scope="session")
def sample_dir():
    """Path to the B1 sample Bruker spectrum directory."""
    path = TESTS_DIR / "b1_sample"
    if not path.exists():
        pytest.skip("b1_sample/ not found")
    return str(path)


@pytest.fixture
def temp_dir():
    """A temporary directory that is cleaned up after the test."""
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def temp_zip(temp_dir):
    """Create an empty zip file for testing."""
    import zipfile
    zip_path = os.path.join(temp_dir, "empty.zip")
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("dummy.txt", "test")
    return zip_path


@pytest.fixture
def temp_bruker_zip(temp_dir):
    """Create a minimal valid Bruker-like zip with pdata/ structure."""
    import zipfile
    zip_path = os.path.join(temp_dir, "bruker.zip")
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("1/pdata/1/1r", b"\x00" * 1024)
        zf.writestr("1/pdata/1/proc", "# Minimal proc file")
        zf.writestr("1/acqu", "## Minimal acqu file")
    return zip_path


@pytest.fixture
def mock_server():
    """Start the mock server in a background thread."""
    from tools.mock_server import MockHandler, ThreadingHTTPServer
    server = ThreadingHTTPServer(("127.0.0.1", 0), MockHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    url = f"http://{host}:{port}"
    time.sleep(0.2)
    yield url
    server.shutdown()
    thread.join(timeout=2)


@pytest.fixture
def api_client():
    """Create a SpectrumMatcherApi pointing at a configurable URL."""
    from spectrum_matcher_client.api import SpectrumMatcherApi
    return SpectrumMatcherApi(server_url="http://127.0.0.1:1", timeout=5)


@pytest.fixture
def api_client_mock(mock_server):
    """Create a SpectrumMatcherApi pointed at the mock server."""
    from spectrum_matcher_client.api import SpectrumMatcherApi
    return SpectrumMatcherApi(server_url=mock_server, timeout=10)


@pytest.fixture(scope="session")
def server_app():
    """Return the FastAPI app (mock mode) for TestClient use."""
    from main import app  # server/main.py
    return app


@pytest.fixture
def test_client(server_app):
    """FastAPI TestClient for server endpoint tests."""
    from fastapi.testclient import TestClient
    with TestClient(server_app) as c:
        yield c


@pytest.fixture
def fixtures_dir():
    """Path to the test fixtures directory."""
    return TESTS_DIR / "fixtures"


@pytest.fixture
def empty_zip(fixtures_dir):
    return str(fixtures_dir / "empty.zip")


@pytest.fixture
def corrupt_bytes_zip(fixtures_dir):
    return str(fixtures_dir / "corrupt_bytes.zip")


@pytest.fixture
def non_bruker_zip(fixtures_dir):
    return str(fixtures_dir / "non_bruker_valid.zip")


@pytest.fixture
def no_pdata_zip(fixtures_dir):
    return str(fixtures_dir / "no_pdata.zip")


@pytest.fixture(scope="session")
def demo_zips():
    """Return dict of all demo zip paths."""
    demos = {}
    for name in [
        "demo_chamomile_flavor", "demo_fig_extract", "demo_citrus_blend",
        "demo_tobacco_sample", "demo_unknown_mixture", "demo_quick_scan",
    ]:
        path = TESTS_DIR / f"{name}.zip"
        if path.exists():
            demos[name] = str(path)
    return demos


@pytest.fixture
def configurable_mock_server():
    """Mock server that can be configured via X-Test-Config header.

    X-Test-Config values:
      status=N   -> return HTTP status N
      delay=N    -> delay N milliseconds before responding
      garbage=1  -> return non-JSON response
    """
    import json
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    class ConfigurableHandler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def do_GET(self):
            self._respond(200, {"status": "ok"})

        def do_POST(self):
            config = self.headers.get("X-Test-Config", "")
            # delay
            import re
            delay_match = re.search(r"delay=(\d+)", config)
            if delay_match:
                time.sleep(int(delay_match.group(1)) / 1000.0)
            # status
            status_match = re.search(r"status=(\d+)", config)
            if status_match:
                code = int(status_match.group(1))
                self._respond(code, {"detail": f"Simulated error {code}"})
                return
            # garbage
            if "garbage=1" in config:
                self._send_bytes(b"<html>not json</html>", "text/html", 200)
                return
            # default: normal mock response
            self._respond(200, {
                "query_name": "mock",
                "results": [
                    {"name": "Test A", "probability": 0.95},
                    {"name": "Test B", "probability": 0.80},
                ],
                "plot_base64": "AAAA",
                "model": {"name": "MockModel", "arch": "Test", "params": "1K", "task": "test"},
            })

        def _respond(self, status, payload):
            body = json.dumps(payload).encode()
            self._send_bytes(body, "application/json", status)

        def _send_bytes(self, body, content_type, status=200):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), ConfigurableHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    url = f"http://{host}:{port}"
    time.sleep(0.1)
    yield url
    server.shutdown()
    thread.join(timeout=2)
