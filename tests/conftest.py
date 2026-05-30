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
