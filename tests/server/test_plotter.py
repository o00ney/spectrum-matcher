"""Tests for server/plotter.py."""

import os
import struct
import sys

import pytest

SERVER_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "server")
sys.path.insert(0, SERVER_DIR)

# Force Agg backend before importing plotter
import matplotlib
matplotlib.use("Agg")


@pytest.fixture
def plot_data():
    """Generate sample ppm/fid for plotting."""
    n = 3000
    query_ppm = [10.7 - 10.4 * i / (n - 1) for i in range(n)]
    query_fid = [0.5 + 0.5 * (1 - i / n) for i in range(n)]
    results = [
        {
            "name": "Reference A",
            "probability": 0.95,
            "ppm": query_ppm[:],
            "fid": [0.3 + 0.7 * (1 - i / n) for i in range(n)],
        },
        {
            "name": "Reference B",
            "probability": 0.80,
            "ppm": query_ppm[:],
            "fid": [0.1 + 0.9 * (1 - i / n) for i in range(n)],
        },
    ]
    return query_ppm, query_fid, results


class TestPlotComparison:
    def test_creates_file(self, plot_data, tmp_path, monkeypatch):
        import plotter
        monkeypatch.setattr(plotter, "PLOT_DIR", str(tmp_path))
        query_ppm, query_fid, results = plot_data
        filename = plotter.plot_comparison(query_ppm, query_fid, results)
        filepath = os.path.join(str(tmp_path), filename)
        assert os.path.exists(filepath)
        assert os.path.getsize(filepath) > 1000

    def test_is_valid_png(self, plot_data, tmp_path, monkeypatch):
        import plotter
        monkeypatch.setattr(plotter, "PLOT_DIR", str(tmp_path))
        query_ppm, query_fid, results = plot_data
        filename = plotter.plot_comparison(query_ppm, query_fid, results)
        filepath = os.path.join(str(tmp_path), filename)
        with open(filepath, "rb") as f:
            header = f.read(8)
        assert header == b"\x89PNG\r\n\x1a\n"

    def test_plot_dir_created(self, plot_data, tmp_path, monkeypatch):
        import plotter
        new_dir = os.path.join(str(tmp_path), "nested", "plots")
        monkeypatch.setattr(plotter, "PLOT_DIR", new_dir)
        query_ppm, query_fid, results = plot_data
        plotter.plot_comparison(query_ppm, query_fid, results)
        assert os.path.isdir(new_dir)

    def test_works_with_empty_results(self, plot_data, tmp_path, monkeypatch):
        import plotter
        monkeypatch.setattr(plotter, "PLOT_DIR", str(tmp_path))
        query_ppm, query_fid, _ = plot_data
        filename = plotter.plot_comparison(query_ppm, query_fid, [])
        assert os.path.exists(os.path.join(str(tmp_path), filename))

    def test_works_with_results_no_ppm_fid(self, plot_data, tmp_path, monkeypatch):
        import plotter
        monkeypatch.setattr(plotter, "PLOT_DIR", str(tmp_path))
        query_ppm, query_fid, _ = plot_data
        results = [{"name": "NoData", "probability": 0.5}]
        filename = plotter.plot_comparison(query_ppm, query_fid, results)
        assert os.path.exists(os.path.join(str(tmp_path), filename))

    def test_uses_correct_resolution(self, plot_data, tmp_path, monkeypatch):
        import plotter
        monkeypatch.setattr(plotter, "PLOT_DIR", str(tmp_path))
        query_ppm, query_fid, results = plot_data
        filename = plotter.plot_comparison(query_ppm, query_fid, results)
        filepath = os.path.join(str(tmp_path), filename)
        with open(filepath, "rb") as f:
            f.read(8)  # signature
            f.read(4)  # length
            f.read(4)  # IHDR
            width = struct.unpack(">I", f.read(4))[0]
            height = struct.unpack(">I", f.read(4))[0]
        assert width == 2800
        assert height == 1200

    def test_filename_is_uuid_hex_png(self, plot_data, tmp_path, monkeypatch):
        import plotter
        monkeypatch.setattr(plotter, "PLOT_DIR", str(tmp_path))
        query_ppm, query_fid, results = plot_data
        filename = plotter.plot_comparison(query_ppm, query_fid, results)
        assert len(filename) == 36  # 32-char hex + ".png"
        assert filename.endswith(".png")
