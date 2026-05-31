"""Tests for AppSettings QSettings wrapper (requires QApplication)."""

import pytest


@pytest.fixture
def app_settings(qtbot):
    """AppSettings with isolated QSettings (uses in-memory on most platforms)."""
    from spectrum_matcher_client.settings import AppSettings
    settings = AppSettings()
    settings._s.clear()
    return settings


class TestAppSettingsDefaults:
    def test_server_url_default_empty(self, app_settings):
        assert app_settings.server_url == ""

    def test_plot_toolbar_default_true(self, app_settings):
        assert app_settings.plot_toolbar_visible is True

    def test_last_directory_default_empty(self, app_settings):
        assert app_settings.last_directory == ""


class TestAppSettingsRoundtrip:
    def test_server_url_roundtrip(self, app_settings):
        app_settings.server_url = "http://custom:1234"
        assert app_settings.server_url == "http://custom:1234"

    def test_plot_toolbar_roundtrip(self, app_settings):
        app_settings.plot_toolbar_visible = False
        assert app_settings.plot_toolbar_visible is False
        app_settings.plot_toolbar_visible = True
        assert app_settings.plot_toolbar_visible is True

    def test_last_directory_roundtrip(self, app_settings):
        app_settings.last_directory = "/custom/path"
        assert app_settings.last_directory == "/custom/path"

    def test_window_geometry_roundtrip(self, app_settings):
        app_settings.window_geometry = b"test_bytes"
        assert app_settings.window_geometry == b"test_bytes"
