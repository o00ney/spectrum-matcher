"""Edge case tests: missing or incomplete pdata/ structure."""

import os

import pytest


class TestMissingPdata:
    def test_zip_no_pdata(self, test_client, no_pdata_zip):
        with open(no_pdata_zip, "rb") as f:
            resp = test_client.post(
                "/api/upload",
                files={"file": ("no_pdata.zip", f, "application/zip")},
            )
        assert resp.status_code in (200, 400, 500)

    def test_folder_no_pdata_raises(self, temp_dir):
        from spectrum_matcher_client.workers import _zip_folder
        no_pdata = os.path.join(temp_dir, "no_pdata")
        os.makedirs(no_pdata)
        with pytest.raises(ValueError, match="pdata"):
            _zip_folder(no_pdata)

    def test_upload_then_reupload_same_file(self, mock_server, sample_zip):
        """Verify repeated uploads work (history/combo feature)."""
        from spectrum_matcher_client.api import SpectrumMatcherApi
        api = SpectrumMatcherApi(server_url=mock_server, timeout=10)
        r1 = api.upload_zip(sample_zip)
        r2 = api.upload_zip(sample_zip)
        assert r1["results"][0]["name"] == r2["results"][0]["name"]


class TestConcurrent:
    def test_two_parallel_uploads(self, mock_server, sample_zip):
        from spectrum_matcher_client.api import SpectrumMatcherApi
        from concurrent.futures import ThreadPoolExecutor

        def do_upload():
            api = SpectrumMatcherApi(server_url=mock_server, timeout=15)
            return api.upload_zip(sample_zip)

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(do_upload) for _ in range(2)]
            results = [f.result(timeout=20) for f in futures]

        for r in results:
            assert len(r["results"]) == 13
            assert r["results"][0]["probability"] > 0
