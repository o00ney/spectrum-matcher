"""QSettings wrapper for persisting user preferences."""

from PySide6.QtCore import QSettings

ORGANIZATION = "SpectrumMatcher"
APPLICATION = "NMRMatcher"


class AppSettings:
    def __init__(self):
        self._s = QSettings(ORGANIZATION, APPLICATION)

    @property
    def server_url(self):
        return self._s.value("server_url", "")

    @server_url.setter
    def server_url(self, value):
        self._s.setValue("server_url", value)

    @property
    def window_geometry(self):
        return self._s.value("window_geometry")

    @window_geometry.setter
    def window_geometry(self, value):
        self._s.setValue("window_geometry", value)

    @property
    def window_state(self):
        return self._s.value("window_state")

    @window_state.setter
    def window_state(self, value):
        self._s.setValue("window_state", value)

    @property
    def last_directory(self):
        return self._s.value("last_directory", "")

    @last_directory.setter
    def last_directory(self, value):
        self._s.setValue("last_directory", value)

    @property
    def plot_toolbar_visible(self):
        return self._s.value("plot_toolbar_visible", True, type=bool)

    @plot_toolbar_visible.setter
    def plot_toolbar_visible(self, value):
        self._s.setValue("plot_toolbar_visible", bool(value))
