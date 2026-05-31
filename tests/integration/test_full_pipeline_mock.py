"""End-to-end tests against mock server."""

import base64

import pytest


class TestFullPipelineMock:
    def test_upload_zip_returns_200(self, mock_server, sample_zip):
        from spectrum_matcher_client.api import SpectrumMatcherApi
        api = SpectrumMatcherApi(server_url=mock_server, timeout=10)
        result = api.upload_zip(sample_zip)
        assert "results" in result

    def test_upload_bruker_has_13_results(self, mock_server, sample_zip):
        from spectrum_matcher_client.api import SpectrumMatcherApi
        api = SpectrumMatcherApi(server_url=mock_server, timeout=10)
        result = api.upload_zip(sample_zip)
        assert len(result["results"]) == 13

    def test_results_descending(self, mock_server, sample_zip):
        from spectrum_matcher_client.api import SpectrumMatcherApi
        api = SpectrumMatcherApi(server_url=mock_server, timeout=10)
        result = api.upload_zip(sample_zip)
        probs = [r["probability"] for r in result["results"]]
        for i in range(len(probs) - 1):
            assert probs[i] >= probs[i + 1]

    def test_plot_is_valid_png(self, mock_server, sample_zip):
        from spectrum_matcher_client.api import SpectrumMatcherApi
        api = SpectrumMatcherApi(server_url=mock_server, timeout=10)
        result = api.upload_zip(sample_zip)
        img = base64.b64decode(result["plot_base64"])
        assert img[:8] == b"\x89PNG\r\n\x1a\n"

    def test_query_name_from_filename(self, mock_server):
        from spectrum_matcher_client.api import SpectrumMatcherApi
        api = SpectrumMatcherApi(server_url=mock_server, timeout=10)
        result = api.upload_zip(__file__)
        assert len(result["query_name"]) > 0

    def test_all_demo_zips_upload(self, mock_server, demo_zips):
        from spectrum_matcher_client.api import SpectrumMatcherApi
        api = SpectrumMatcherApi(server_url=mock_server, timeout=10)
        for name, path in demo_zips.items():
            result = api.upload_zip(path)
            assert len(result["results"]) == 13, f"failed for {name}"
            assert len(result["query_ppm"]) > 100, f"no downsample data for {name}"
