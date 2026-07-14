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
