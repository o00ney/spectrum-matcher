"""Tests for client/spectrum_matcher_client/api.py."""

import os
import json

import pytest


class TestApiError:
    def test_basic_error(self):
        from spectrum_matcher_client.api import ApiError
        e = ApiError("test message")
        assert str(e) == "test message"
        assert isinstance(e, Exception)

    def test_error_chain(self):
        from spectrum_matcher_client.api import ApiError
        cause = ValueError("root")
        e = ApiError("wrapped")
        e.__cause__ = cause
        assert e.__cause__ is cause


class TestSpectrumMatcherApi:
    def test_construction_defaults(self, api_client):
        from spectrum_matcher_client.api import SpectrumMatcherApi
        assert isinstance(api_client, SpectrumMatcherApi)

    def test_custom_timeout(self):
        from spectrum_matcher_client.api import SpectrumMatcherApi
        api = SpectrumMatcherApi(timeout=30)
        assert api.timeout == 30

    def test_server_url_strips_slash(self):
        from spectrum_matcher_client.api import SpectrumMatcherApi
        api = SpectrumMatcherApi(server_url="http://example.com/")
        assert api.server_url == "http://example.com"

    def test_check_connection_unreachable(self, api_client):
        result = api_client.check_connection()
        assert result is False

    def test_check_connection_ok(self, api_client_mock):
        result = api_client_mock.check_connection()
        assert result is True

    def test_upload_zip_to_mock(self, api_client_mock, temp_zip):
        result = api_client_mock.upload_zip(temp_zip)
        assert isinstance(result, dict)
        assert "results" in result
        assert "plot_base64" in result
        assert "query_ppm" in result
        assert "query_fid" in result

    def test_upload_zip_results_format(self, api_client_mock, temp_zip):
        result = api_client_mock.upload_zip(temp_zip)
        results = result["results"]
        assert len(results) == 13
        top = results[0]
        assert "name" in top
        assert "probability" in top
        assert float(top["probability"]) > 0

    def test_upload_zip_downsamples_in_response(self, api_client_mock, temp_zip):
        result = api_client_mock.upload_zip(temp_zip)
        assert len(result["query_ppm"]) < 4000
        assert len(result["query_fid"]) < 4000

    def test_upload_zip_ppm_ds_top3_only(self, api_client_mock, temp_zip):
        result = api_client_mock.upload_zip(temp_zip)
        for i, r in enumerate(result["results"]):
            if i < 3:
                assert "ppm_ds" in r, f"result {i} missing ppm_ds"
                assert "fid_ds" in r, f"result {i} missing fid_ds"
            else:
                assert "ppm_ds" not in r, f"result {i} should not have ppm_ds"

    def test_upload_zip_model_info(self, api_client_mock, temp_zip):
        result = api_client_mock.upload_zip(temp_zip)
        model = result["model"]
        assert model["name"] == "DeepMID"
        assert "arch" in model
        assert "params" in model

    def test_upload_zip_base64_is_valid_png(self, api_client_mock, temp_zip):
        import base64
        result = api_client_mock.upload_zip(temp_zip)
        img = base64.b64decode(result["plot_base64"])
        assert img[:8] == b'\x89PNG\r\n\x1a\n'

    def test_upload_zip_bruker_structure(self, api_client_mock, temp_bruker_zip):
        result = api_client_mock.upload_zip(temp_bruker_zip)
        assert "results" in result
        assert len(result["results"]) == 13

    def test_cancel_flag(self, api_client_mock):
        api_client_mock.cancel()
        assert api_client_mock._cancel_event.is_set()

    def test_cancel_reset_before_upload(self, api_client_mock, temp_zip):
        api_client_mock.cancel()
        result = api_client_mock.upload_zip(temp_zip)
        assert "results" in result
