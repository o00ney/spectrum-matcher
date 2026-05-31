"""Tests for client config (server URL, timeout)."""

import os

import pytest


class TestServerUrl:
    def test_default_url(self):
        from spectrum_matcher_client.config import DEFAULT_SERVER_URL
        assert "nmr.ooney.xyz" in DEFAULT_SERVER_URL or "192.168" in DEFAULT_SERVER_URL

    def test_get_server_url_default(self, monkeypatch):
        monkeypatch.delenv("SPECTRUM_MATCHER_SERVER_URL", raising=False)
        from spectrum_matcher_client import config
        import importlib
        importlib.reload(config)
        url = config.get_server_url()
        assert url == config.DEFAULT_SERVER_URL

    def test_get_server_url_from_env(self, monkeypatch):
        monkeypatch.setenv("SPECTRUM_MATCHER_SERVER_URL", "http://localhost:9999")
        from spectrum_matcher_client import config
        import importlib
        importlib.reload(config)
        url = config.get_server_url()
        assert url == "http://localhost:9999"

    def test_get_server_url_strips_trailing_slash(self, monkeypatch):
        monkeypatch.setenv("SPECTRUM_MATCHER_SERVER_URL", "http://example.com/")
        from spectrum_matcher_client import config
        import importlib
        importlib.reload(config)
        url = config.get_server_url()
        assert url == "http://example.com"

    def test_get_server_url_empty_env_falls_back(self, monkeypatch):
        monkeypatch.setenv("SPECTRUM_MATCHER_SERVER_URL", "")
        from spectrum_matcher_client import config
        import importlib
        importlib.reload(config)
        url = config.get_server_url()
        assert url == config.DEFAULT_SERVER_URL


class TestTimeout:
    def test_default_timeout(self, monkeypatch):
        monkeypatch.delenv("SPECTRUM_MATCHER_TIMEOUT", raising=False)
        from spectrum_matcher_client import config
        import importlib
        importlib.reload(config)
        timeout = config.get_request_timeout()
        assert timeout == 120

    def test_timeout_from_env(self, monkeypatch):
        monkeypatch.setenv("SPECTRUM_MATCHER_TIMEOUT", "30")
        from spectrum_matcher_client import config
        import importlib
        importlib.reload(config)
        timeout = config.get_request_timeout()
        assert timeout == 30.0

    def test_timeout_invalid_env_falls_back(self, monkeypatch):
        monkeypatch.setenv("SPECTRUM_MATCHER_TIMEOUT", "not_a_number")
        from spectrum_matcher_client import config
        import importlib
        importlib.reload(config)
        timeout = config.get_request_timeout()
        assert timeout == 120

    def test_timeout_zero_env_falls_back(self, monkeypatch):
        monkeypatch.setenv("SPECTRUM_MATCHER_TIMEOUT", "0")
        from spectrum_matcher_client import config
        import importlib
        importlib.reload(config)
        timeout = config.get_request_timeout()
        assert timeout == 120
