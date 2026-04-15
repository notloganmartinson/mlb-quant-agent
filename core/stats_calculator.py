import numpy as np
import pandas as pd

def calculate_siera(so, bb, pa, gb, fb, pu):
    """
    Calculates Skill-Interactive Earned Run Average (SIERA).
    Supports both single values and Pandas Series (vectorized).
    """
    assert pa is not None, "Plate Appearances (pa) cannot be None"
    
    # Handle both single values and pandas series
    if hasattr(pa, "__len__"):
        # Vectorized path
        mask = pa > 0
        # Ensure we don't have all zeros if calling in a context expecting data
        # but we allow zeros in arrays if we mask them. 
        # However, the protocol says prevent divide-by-zero. 
        # np.where is safe but some prefer explicit check if any are > 0.
        k_rate = np.where(mask, so / pa, 0)
        bb_rate = np.where(mask, bb / pa, 0)
        net_gb = np.where(mask, (gb - fb - pu) / pa, 0)
        
        base = 6.145 - 16.986 * k_rate + 11.434 * bb_rate - 1.858 * net_gb + 7.653 * (k_rate ** 2)
        base = np.where(net_gb > 0, base - 6.664 * (net_gb ** 2), base + 6.664 * (net_gb ** 2))
        
        return np.round(np.maximum(0, base), 2)
    else:
        # Scalar path
        assert pa > 0, f"Division by zero: Plate Appearances (pa) must be > 0. Received: {pa}"
        k_rate = so / pa
        bb_rate = bb / pa
        net_gb = (gb - fb - pu) / pa
        base = 6.145 - 16.986 * k_rate + 11.434 * bb_rate - 1.858 * net_gb + 7.653 * (k_rate ** 2)
        if net_gb > 0: base -= 6.664 * (net_gb ** 2)
        else: base += 6.664 * (net_gb ** 2)
        return round(max(0, base), 2)

def calculate_k_minus_bb_percent(so, bb, pa):
    """Calculates K-BB%."""
    assert pa is not None, "Plate Appearances (pa) cannot be None"
    if hasattr(pa, "__len__"):
        return np.round(np.where(pa > 0, (so - bb) / pa, 0), 3)
    
    assert pa > 0, f"Division by zero: Plate Appearances (pa) must be > 0. Received: {pa}"
    return round((so - bb) / pa, 3)

def calculate_iso(ab, doubles, triples, hr):
    """Calculates Isolated Power (ISO)."""
    assert ab is not None, "At Bats (ab) cannot be None"
    if hasattr(ab, "__len__"):
        return np.round(np.where(ab > 0, (doubles + 2 * triples + 3 * hr) / ab, 0), 3)
    
    assert ab > 0, f"Division by zero: At Bats (ab) must be > 0. Received: {ab}"
    return round((doubles + 2 * triples + 3 * hr) / ab, 3)

def calculate_vaa(vy0, ay, vz0, az):
    """
    Calculates Vertical Approach Angle (VAA) at the plate (y=1.417 ft).
    Standard Statcast coordinates: y=50 is release, y=0 is plate.
    """
    assert all(v is not None for v in [vy0, ay, vz0, az]), "Physics inputs cannot be None"
    y_target = 17/12.0 # 1.417 ft
    y_start = 50.0
    dist = y_target - y_start
    
    # vy_f = -sqrt(vy0^2 + 2 * ay * dist)
    # vy0 is negative in Statcast (towards plate)
    v_yf_sq = vy0**2 + 2 * ay * dist
    assert np.all(v_yf_sq > 0), "Invalid physics: velocity squared must be positive"
    
    vy_f = -np.sqrt(v_yf_sq)
    t = (vy_f - vy0) / ay
    vz_f = vz0 + az * t
    
    vaa = -np.degrees(np.arctan(vz_f / vy_f))
    return np.round(vaa, 2)

def calculate_break_magnitude(pfx_x, pfx_z):
    """Calculates the total movement magnitude (in inches)."""
    assert pfx_x is not None and pfx_z is not None, "Movement inputs cannot be None"
    return np.round(np.sqrt(pfx_x**2 + pfx_z**2), 2)

def calculate_rolling_stuff_plus(pitch_values, window=500, prior_val=100, prior_weight=100):
    """
    Calculates the point-in-time rolling Stuff+ for a pitcher.
    Uses a Bayesian prior (league average = 100) to stabilize small samples (rookies).
    
    Args:
        pitch_values (list/np.array): A chronologically ordered list of Stuff+ values for a pitcher's prior pitches.
        window (int): The trailing pitch window to average. Default 500 (~5-7 starts).
        prior_val (int): The league average baseline (e.g., 100).
        prior_weight (int): Strength of the prior in pitch equivalents. Default 100.
        
    Returns:
        float: The calculated Rolling Stuff+ score.
    """
    assert isinstance(pitch_values, (list, np.ndarray, pd.Series)), "pitch_values must be a sequence"
    
    # Take the trailing window
    recent_pitches = pitch_values[-window:] if len(pitch_values) > 0 else []
    
    # Bayesian Average: (Sum of Samples + PriorValue * PriorWeight) / (Count + PriorWeight)
    sample_sum = np.sum(recent_pitches)
    sample_count = len(recent_pitches)
    
    rolling_val = (sample_sum + (prior_val * prior_weight)) / (sample_count + prior_weight)
    
    return float(np.round(rolling_val, 2))
