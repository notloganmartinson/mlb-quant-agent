import numpy as np

def calculate_siera(so, bb, pa, gb, fb, pu):
    """
    Calculates Skill-Interactive Earned Run Average (SIERA).
    Supports both single values and Pandas Series (vectorized).
    """
    # Handle both single values and pandas series
    if hasattr(pa, "__len__"):
        # Vectorized path
        mask = pa > 0
        k_rate = np.where(mask, so / pa, 0)
        bb_rate = np.where(mask, bb / pa, 0)
        net_gb = np.where(mask, (gb - fb - pu) / pa, 0)
        
        base = 6.145 - 16.986 * k_rate + 11.434 * bb_rate - 1.858 * net_gb + 7.653 * (k_rate ** 2)
        base = np.where(net_gb > 0, base - 6.664 * (net_gb ** 2), base + 6.664 * (net_gb ** 2))
        
        return np.round(np.maximum(0, base), 2)
    else:
        # Scalar path
        if pa == 0: return None
        k_rate = so / pa
        bb_rate = bb / pa
        net_gb = (gb - fb - pu) / pa
        base = 6.145 - 16.986 * k_rate + 11.434 * bb_rate - 1.858 * net_gb + 7.653 * (k_rate ** 2)
        if net_gb > 0: base -= 6.664 * (net_gb ** 2)
        else: base += 6.664 * (net_gb ** 2)
        return round(max(0, base), 2)

def calculate_k_minus_bb_percent(so, bb, pa):
    """Calculates K-BB%."""
    if hasattr(pa, "__len__"):
        return np.round(np.where(pa > 0, (so - bb) / pa, 0), 3)
    if pa == 0: return 0.0
    return round((so - bb) / pa, 3)

def calculate_iso(ab, doubles, triples, hr):
    """Calculates Isolated Power (ISO)."""
    if hasattr(ab, "__len__"):
        return np.round(np.where(ab > 0, (doubles + 2 * triples + 3 * hr) / ab, 0), 3)
    if ab == 0: return 0.0
    return round((doubles + 2 * triples + 3 * hr) / ab, 3)
