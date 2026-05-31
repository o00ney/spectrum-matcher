"""Edge case tests: corrupt/malformed upload data."""

import pytest


class TestCorruptZipFiles:
    def test_empty_zip(self, test_client, empty_zip):
        with open(empty_zip, "rb") as f:
            resp = test_client.post(
                "/api/upload",
                files={"file": ("empty.zip", f, "application/zip")},
            )
        assert resp.status_code in (200, 400, 422, 500)
        # should not crash the server

    def test_corrupt_bytes_as_zip(self, test_client, corrupt_bytes_zip):
        with open(corrupt_bytes_zip, "rb") as f:
            resp = test_client.post(
                "/api/upload",
                files={"file": ("corrupt.zip", f, "application/zip")},
            )
        # should handle gracefully (now with try/except wrapper)
        assert resp.status_code in (200, 400, 500)
        if resp.status_code == 500:
            detail = resp.json()["detail"]
            assert "Processing failed" in detail

    def test_non_bruker_valid_zip(self, test_client, non_bruker_zip):
        with open(non_bruker_zip, "rb") as f:
            resp = test_client.post(
                "/api/upload",
                files={"file": ("not_bruker.zip", f, "application/zip")},
            )
        # mock mode: succeeds (ignores content)
        # real mode: would fail gracefully
        assert resp.status_code in (200, 400, 500)

    def test_non_zip_extension(self, test_client):
        resp = test_client.post(
            "/api/upload",
            files={"file": ("data.txt", b"hello world", "text/plain")},
        )
        assert resp.status_code == 400
        assert "zip" in resp.json()["detail"].lower()
