"""End-to-end tests against production server (opt-in)."""

import pytest


pytestmark = [pytest.mark.network, pytest.mark.server_real]


@pytest.mark.skip(reason="requires production server access and network")
class TestProductionServer:
    def test_connectivity(self):
        import requests
        resp = requests.get("https://nmr.ooney.xyz/docs", timeout=10)
        assert resp.status_code == 200

    def test_upload_b1_sample(self):
        import os
        from pathlib import Path
        import requests
        sample = Path(__file__).resolve().parent.parent / "b1_sample.zip"
        if not sample.exists():
            pytest.skip("b1_sample.zip not found")
        with open(sample, "rb") as f:
            resp = requests.post(
                "https://nmr.ooney.xyz/api/upload",
                files={"file": ("b1_sample.zip", f, "application/zip")},
                timeout=120,
            )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["results"]) == 13
        assert data["results"][0]["probability"] > 0.5

    def test_gzip_compression(self):
        import requests
        import os
        from pathlib import Path
        sample = Path(__file__).resolve().parent.parent / "b1_sample.zip"
        if not sample.exists():
            pytest.skip("b1_sample.zip not found")
        with open(sample, "rb") as f:
            resp = requests.post(
                "https://nmr.ooney.xyz/api/upload",
                files={"file": ("b1_sample.zip", f, "application/zip")},
                headers={"Accept-Encoding": "gzip"},
                timeout=120,
            )
        assert resp.status_code == 200
        assert resp.headers.get("Content-Encoding") == "gzip"
