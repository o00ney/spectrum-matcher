"""Tests for server/downsample.py."""

import math

import pytest


def _import_downsample():
    """Late import so server deps aren't needed for client-only tests."""
    import sys
    from pathlib import Path
    server_dir = str(Path(__file__).resolve().parent.parent / "server")
    sys.path.insert(0, server_dir)
    from downsample import downsample
    return downsample


class TestDownsample:
    """Uniform stride-based downsampling."""

    def test_exact_target(self):
        downsample = _import_downsample()
        arr = list(range(100))
        result = downsample(arr, target_points=100)
        assert len(result) == 100
        assert result == arr

    def test_small_array_unchanged(self):
        downsample = _import_downsample()
        arr = [1.0, 2.0, 3.0]
        result = downsample(arr, target_points=100)
        assert len(result) == 3
        assert result == arr

    def test_typical_nmr_reduction(self):
        downsample = _import_downsample()
        arr = [0.0] * 32724
        result = downsample(arr, target_points=3000)
        assert 2990 <= len(result) <= 3010
        assert len(result) < len(arr) * 0.1

    def test_preserves_first(self):
        downsample = _import_downsample()
        arr = list(range(1000))
        result = downsample(arr, target_points=50)
        assert result[0] == 0
        assert result[-1] >= 900

    def test_empty_array(self):
        downsample = _import_downsample()
        result = downsample([], target_points=100)
        assert result == []

    def test_single_element(self):
        downsample = _import_downsample()
        result = downsample([42], target_points=100)
        assert result == [42]

    def test_numpy_array(self):
        downsample = _import_downsample()
        try:
            import numpy as np
        except ImportError:
            pytest.skip("numpy not available")
        arr = np.linspace(10.7, 0.3, 32724)
        result = downsample(arr, target_points=3000)
        assert 2990 <= len(result) <= 3010
        assert isinstance(result[0], (float, np.floating))

    def test_target_larger_than_input(self):
        downsample = _import_downsample()
        arr = list(range(10))
        result = downsample(arr, target_points=100)
        assert result == arr

    def test_output_is_plain_list(self):
        downsample = _import_downsample()
        arr = list(range(32724))
        result = downsample(arr, target_points=100)
        assert isinstance(result, list)
