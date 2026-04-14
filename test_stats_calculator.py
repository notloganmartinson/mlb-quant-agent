import pytest
import numpy as np
from core import stats_calculator

def test_calculate_iso_scalar():
    # 100 AB, 10 2B, 1 3B, 5 HR -> (10 + 2*1 + 3*5) / 100 = 27 / 100 = 0.270
    assert stats_calculator.calculate_iso(100, 10, 1, 5) == 0.270

def test_calculate_iso_vectorized():
    ab = np.array([100, 200])
    doubles = np.array([10, 20])
    triples = np.array([1, 2])
    hr = np.array([5, 10])
    expected = np.array([0.270, 0.270])
    np.testing.assert_array_almost_equal(stats_calculator.calculate_iso(ab, doubles, triples, hr), expected)

def test_calculate_iso_zero_ab_raises():
    with pytest.raises(AssertionError, match="must be > 0"):
        stats_calculator.calculate_iso(0, 0, 0, 0)

def test_calculate_k_minus_bb_percent_scalar():
    # 100 PA, 25 K, 10 BB -> (25 - 10) / 100 = 0.150
    assert stats_calculator.calculate_k_minus_bb_percent(25, 10, 100) == 0.150

def test_calculate_k_minus_bb_percent_zero_pa_raises():
    with pytest.raises(AssertionError, match="must be > 0"):
        stats_calculator.calculate_k_minus_bb_percent(0, 0, 0)

def test_calculate_siera_scalar():
    # so=150, bb=50, pa=600, gb=200, fb=150, pu=20
    # Expected approx 3.22
    assert stats_calculator.calculate_siera(150, 50, 600, 200, 150, 20) == 3.22

def test_calculate_siera_vectorized():
    # p1: k_rate=0.25, bb_rate=0.0833, net_gb=0.05 -> 3.22
    # p2: k_rate=0, bb_rate=0, net_gb=0 -> 6.15
    pa = np.array([600, 100])
    so = np.array([150, 0])
    bb = np.array([50, 0])
    gb = np.array([200, 0])
    fb = np.array([150, 0])
    pu = np.array([20, 0])
    expected = np.array([3.22, 6.14])
    np.testing.assert_array_almost_equal(stats_calculator.calculate_siera(so, bb, pa, gb, fb, pu), expected)

def test_calculate_siera_zero_pa_raises():
    with pytest.raises(AssertionError, match="must be > 0"):
        stats_calculator.calculate_siera(0, 0, 0, 0, 0, 0)

def test_calculate_siera_none_pa_raises():
    with pytest.raises(AssertionError, match="cannot be None"):
        stats_calculator.calculate_siera(0, 0, None, 0, 0, 0)

def test_calculate_vaa_scalar():
    # Basic sanity check
    # vy0=-135, ay=25, vz0=-5, az=-25
    vaa = stats_calculator.calculate_vaa(-135.0, 25.0, -5.0, -25.0)
    assert isinstance(vaa, float)
    assert -15 < vaa < 15

def test_calculate_vaa_none_raises():
    with pytest.raises(AssertionError, match="cannot be None"):
        stats_calculator.calculate_vaa(None, 0, 0, 0)

def test_calculate_break_magnitude():
    # 3, 4 -> 5.0
    assert stats_calculator.calculate_break_magnitude(3.0, 4.0) == 5.0
