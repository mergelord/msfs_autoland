"""Tests for Navigation (FIX-04)."""


def test_landing_distance_zero_gs():
    """FIX-04: calculate_landing_distance must not raise ZeroDivisionError at GS=0."""
    from modules.navigation import Navigation

    nav = Navigation.__new__(Navigation)
    # Must not raise ZeroDivisionError
    result = nav.calculate_landing_distance(ground_speed=0, headwind=10)
    assert isinstance(result, float)

    result2 = nav.calculate_landing_distance(ground_speed=0, headwind=0)
    assert isinstance(result2, float)

    # Normal case still works
    result3 = nav.calculate_landing_distance(ground_speed=60, headwind=10)
    assert isinstance(result3, float)
    assert result3 > 0


# --- Finding 3: cos(lat) at poles ---

def test_glideslope_intercept_near_pole():
    """Finding 3: calculate_glideslope_intercept_point must not ZeroDivisionError at lat=90."""
    import math
    from modules.navigation import Navigation

    nav = Navigation.__new__(Navigation)
    result = nav.calculate_glideslope_intercept_point(
        runway_threshold_lat=89.999,
        runway_threshold_lon=0.0,
        runway_heading=0,
        runway_elevation=0,
        glideslope_angle=3.0,
    )
    assert isinstance(result, dict)
    assert 'latitude' in result
    assert 'longitude' in result
    assert math.isfinite(result['longitude'])


def test_runway_beacons_near_pole():
    """Finding 3: calculate_runway_beacons must not ZeroDivisionError at lat=90."""
    from modules.navigation import Navigation

    nav = Navigation.__new__(Navigation)
    result = nav.calculate_runway_beacons(
        runway_threshold_lat=89.999,
        runway_threshold_lon=0.0,
        runway_heading=0,
        runway_elevation=0,
    )
    assert isinstance(result, dict)
    assert 'outer' in result
    assert 'inner' in result
