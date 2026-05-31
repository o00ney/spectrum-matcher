"""Tests for interactive matplotlib plot widget."""

import os

import pytest


@pytest.fixture
def plot_widget(qtbot):
    from spectrum_matcher_client.plot_widget import SpectrumPlotWidget
    widget = SpectrumPlotWidget()
    qtbot.addWidget(widget)
    return widget


@pytest.fixture
def plot_data():
    n = 500
    query_ppm = [10.7 - 10.4 * i / (n - 1) for i in range(n)]
    query_fid = [0.5 + 0.5 * (1 - i / n) for i in range(n)]
    results = [
        {
            "name": "Ref A", "probability": 0.95,
            "ppm_ds": query_ppm[:], "fid_ds": [0.3 + 0.7 * (1 - i / n) for i in range(n)],
        },
        {
            "name": "Ref B", "probability": 0.80,
            "ppm_ds": query_ppm[:], "fid_ds": [0.1 + 0.9 * (1 - i / n) for i in range(n)],
        },
    ]
    return query_ppm, query_fid, results


class TestPlotWidget:
    def test_creation(self, plot_widget):
        assert plot_widget._canvas is not None
        assert plot_widget._toolbar is not None

    def test_clear(self, plot_widget):
        plot_widget._figure.add_subplot(111).plot([1, 2], [3, 4])
        assert len(plot_widget._figure.axes) == 1
        plot_widget.clear()
        assert len(plot_widget._figure.axes) == 0

    def test_render_comparison(self, plot_widget, plot_data):
        query_ppm, query_fid, results = plot_data
        plot_widget.render_comparison(query_ppm, query_fid, results)
        assert len(plot_widget._figure.axes) == 1

    def test_render_empty_results(self, plot_widget, plot_data):
        query_ppm, query_fid, _ = plot_data
        plot_widget.render_comparison(query_ppm, query_fid, [])
        assert len(plot_widget._figure.axes) == 1

    def test_save_figure(self, plot_widget, plot_data, temp_dir):
        query_ppm, query_fid, results = plot_data
        plot_widget.render_comparison(query_ppm, query_fid, results)
        path = os.path.join(temp_dir, "plot.png")
        plot_widget.save_figure(path)
        assert os.path.exists(path)
        assert os.path.getsize(path) > 500

    def test_toolbar_visibility(self, plot_widget):
        plot_widget.set_toolbar_visible(False)
        assert not plot_widget._toolbar.isVisible()
        plot_widget.set_toolbar_visible(True)
        assert plot_widget._toolbar.isVisible()

    def test_render_fallback(self, plot_widget, qtbot):
        from PySide6.QtGui import QPixmap
        pm = QPixmap(100, 50)
        pm.fill()
        plot_widget.render_fallback(pm)
        assert len(plot_widget._figure.axes) == 1
