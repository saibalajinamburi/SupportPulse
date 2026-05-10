"""
Unit tests for the drift detection math (Phase 9).
Tests PSI and KL divergence calculations with known values — no file I/O needed.
"""
import numpy as np
import pandas as pd
import pytest
from src.monitoring.drift_detector import calculate_psi, calculate_kl_divergence


def make_series(d: dict) -> pd.Series:
    return pd.Series(d)


class TestPSI:
    def test_identical_distributions_near_zero(self):
        """PSI of identical distributions should be ~0."""
        dist = make_series({"incident": 0.5, "bug": 0.3, "billing": 0.2})
        psi = calculate_psi(dist, dist)
        assert psi < 0.05  # Should be essentially 0

    def test_completely_different_distributions_high_psi(self):
        """PSI of totally different distributions should be >> 0.2."""
        expected = make_series({"incident": 0.99, "bug": 0.01})
        actual = make_series({"incident": 0.01, "bug": 0.99})
        psi = calculate_psi(expected, actual)
        assert psi > 0.2

    def test_slight_drift_medium_psi(self):
        """Slight shift should produce PSI between 0.01 and 0.2."""
        expected = make_series({"incident": 0.5, "bug": 0.3, "billing": 0.2})
        actual = make_series({"incident": 0.45, "bug": 0.35, "billing": 0.2})
        psi = calculate_psi(expected, actual)
        assert 0.0 < psi < 0.15

    def test_psi_handles_new_category_in_live(self):
        """PSI should handle categories in live data not seen in training."""
        expected = make_series({"incident": 0.7, "bug": 0.3})
        actual = make_series({"incident": 0.5, "bug": 0.3, "security": 0.2})
        psi = calculate_psi(expected, actual)
        assert psi > 0  # Should detect drift

    def test_psi_is_always_non_negative(self):
        """PSI must always be >= 0."""
        for _ in range(20):
            vals = np.random.dirichlet([1, 1, 1, 1])
            vals2 = np.random.dirichlet([1, 1, 1, 1])
            cats = ["a", "b", "c", "d"]
            psi = calculate_psi(make_series(dict(zip(cats, vals))),
                                make_series(dict(zip(cats, vals2))))
            assert psi >= 0


class TestKLDivergence:
    def test_identical_distributions_near_zero(self):
        dist = make_series({"incident": 0.5, "bug": 0.5})
        kl = calculate_kl_divergence(dist, dist)
        assert kl < 0.05

    def test_divergent_distributions_high_kl(self):
        expected = make_series({"incident": 0.99, "bug": 0.01})
        actual = make_series({"incident": 0.01, "bug": 0.99})
        kl = calculate_kl_divergence(expected, actual)
        assert kl > 1.0

    def test_kl_always_non_negative(self):
        """KL divergence must be >= 0."""
        for _ in range(20):
            vals = np.random.dirichlet([2, 2, 2])
            vals2 = np.random.dirichlet([2, 2, 2])
            cats = ["a", "b", "c"]
            kl = calculate_kl_divergence(make_series(dict(zip(cats, vals))),
                                         make_series(dict(zip(cats, vals2))))
            assert kl >= 0
