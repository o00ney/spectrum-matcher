"""Tests for client/spectrum_matcher_client/export.py."""

import csv
import json
import os
import tempfile

import pytest

from spectrum_matcher_client.export import (
    export_results_csv,
    export_results_json,
    export_plot_png,
)


class TestExportCsv:
    def test_basic_export(self, temp_dir):
        results = [
            {"name": "Linalool", "probability": 0.9321},
            {"name": "Geraniol", "probability": 0.8174},
        ]
        path = os.path.join(temp_dir, "results.csv")
        export_results_csv(results, path)

        assert os.path.exists(path)
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)
        assert rows[0] == ["Name", "Probability"]
        assert rows[1] == ["Linalool", "0.9321"]
        assert rows[2] == ["Geraniol", "0.8174"]

    def test_empty_results(self, temp_dir):
        path = os.path.join(temp_dir, "empty.csv")
        export_results_csv([], path)
        with open(path, newline="", encoding="utf-8") as f:
            rows = list(csv.reader(f))
        assert len(rows) == 1
        assert rows[0] == ["Name", "Probability"]

    def test_missing_fields(self, temp_dir):
        results = [{"name": "X"}]
        path = os.path.join(temp_dir, "partial.csv")
        export_results_csv(results, path)
        with open(path, newline="", encoding="utf-8") as f:
            rows = list(csv.reader(f))
        assert rows[1] == ["X", ""]


class TestExportJson:
    def test_basic_export(self, temp_dir):
        data = {
            "query_name": "test",
            "results": [{"name": "A", "probability": 0.99}],
            "model": {"name": "DeepMID"},
        }
        path = os.path.join(temp_dir, "results.json")
        export_results_json(data, path)

        assert os.path.exists(path)
        with open(path, encoding="utf-8") as f:
            loaded = json.load(f)
        assert loaded["query_name"] == "test"
        assert loaded["results"][0]["name"] == "A"

    def test_pretty_print(self, temp_dir):
        data = {"key": "value"}
        path = os.path.join(temp_dir, "pretty.json")
        export_results_json(data, path)
        with open(path) as f:
            raw = f.read()
        assert "  " in raw
        assert "\n" in raw

    def test_unicode(self, temp_dir):
        data = {"name": "洋甘菊提取物"}
        path = os.path.join(temp_dir, "unicode.json")
        export_results_json(data, path)
        with open(path, encoding="utf-8") as f:
            loaded = json.load(f)
        assert loaded["name"] == "洋甘菊提取物"


class TestExportPlot:
    def test_save_figure(self, temp_dir):
        """Test plot export without Qt (using matplotlib Agg directly)."""
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots()
        ax.plot([1, 2, 3], [1, 4, 9])
        fig.savefig(os.path.join(temp_dir, "plot.png"), dpi=200)
        plt.close(fig)

        path = os.path.join(temp_dir, "plot.png")
        assert os.path.exists(path)
        assert os.path.getsize(path) > 500

    def test_save_figure_via_export(self, temp_dir):
        """Test save via export_plot_png with a mock widget."""
        from unittest.mock import MagicMock
        widget = MagicMock()
        path = os.path.join(temp_dir, "via_export.png")
        export_plot_png(widget, path)
        widget.save_figure.assert_called_once_with(path)
