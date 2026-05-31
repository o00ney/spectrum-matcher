"""Tests for baseline correction algorithm (airPLS)."""

import math
import sys

import pytest

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    import scipy
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


def _import_airpls():
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "server", "deepmid"))
    from airPLS import airPLS
    return airPLS


needs_scipy = pytest.mark.skipif(not HAS_SCIPY, reason="scipy required")


@needs_scipy
@pytest.mark.skipif(not HAS_NUMPY, reason="numpy required")
class TestAirPLS:
    def test_constant_signal(self):
        airPLS = _import_airpls()
        x = np.ones(1000)
        baseline = airPLS(x, lambda_=10, porder=1, itermax=5)
        assert abs(baseline.mean() - 1.0) < 0.1

    def test_linear_baseline_recovery(self):
        airPLS = _import_airpls()
        n = 1000
        true_baseline = np.linspace(0, 1, n)
        x = true_baseline + 0.01 * np.sin(np.linspace(0, 20 * math.pi, n))
        baseline = airPLS(x, lambda_=100, porder=1, itermax=5)
        err = np.max(np.abs(baseline - true_baseline))
        assert err < 0.2, f"baseline recovery error {err}"

    def test_no_peaks_returns_input(self):
        airPLS = _import_airpls()
        x = np.linspace(0, 5, 500)
        baseline = airPLS(x, lambda_=10, porder=1, itermax=5)
        assert np.max(np.abs(baseline - x)) < 0.01

    def test_larger_lambda_gives_smoother(self):
        airPLS = _import_airpls()
        x = np.random.RandomState(42).randn(100) + np.linspace(0, 10, 100)
        b1 = airPLS(x, lambda_=10, porder=1, itermax=5)
        b2 = airPLS(x, lambda_=1000, porder=1, itermax=5)
        # larger lambda -> smoother -> less variance
        assert np.var(np.diff(b2)) < np.var(np.diff(b1))

    def test_preserves_peak_areas(self):
        airPLS = _import_airpls()
        n = 500
        x = np.linspace(0, 2 * math.pi, n)
        signal = np.sin(x) * 0.5 + np.linspace(0, 0.5, n)
        corrected = airPLS(signal, lambda_=100, porder=1, itermax=5)
        # peaks shouldn't be completely destroyed
        assert np.max(corrected) > 0.4
