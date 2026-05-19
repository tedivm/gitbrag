"""Tests for report generation services."""

from datetime import timedelta

from gitbrag.services.reports import calculate_date_range, generate_cache_key, normalize_period


def test_generate_cache_key_normalizes_username():
    """Test that cache keys use lowercase usernames."""
    # Test uppercase username
    key_upper = generate_cache_key("TEDIVM", "1_year")
    assert "tedivm" in key_upper
    assert "TEDIVM" not in key_upper
    assert key_upper.startswith("report:tedivm:1_year:")

    # Test mixed case username
    key_mixed = generate_cache_key("TedIVM", "1_year")
    assert "tedivm" in key_mixed
    assert "TedIVM" not in key_mixed
    assert key_mixed.startswith("report:tedivm:1_year:")

    # Test lowercase username (unchanged)
    key_lower = generate_cache_key("tedivm", "1_year")
    assert "tedivm" in key_lower
    assert key_lower.startswith("report:tedivm:1_year:")

    # Verify all generate same cache key
    assert key_upper == key_mixed == key_lower


def test_generate_cache_key_with_different_periods():
    """Test that cache keys differ by period."""
    key_1_year = generate_cache_key("tedivm", "1_year")
    key_2_years = generate_cache_key("tedivm", "2_years")
    key_all_time = generate_cache_key("tedivm", "all_time")

    # All should be lowercase
    assert "tedivm" in key_1_year
    assert "tedivm" in key_2_years
    assert "tedivm" in key_all_time

    # But keys should differ by period
    assert key_1_year != key_2_years
    assert key_1_year != key_all_time
    assert key_2_years != key_all_time


def test_generate_cache_key_with_star_increase():
    """Test that cache keys differ based on show_star_increase parameter."""
    key_without_stars = generate_cache_key("tedivm", "1_year", show_star_increase=False)
    key_with_stars = generate_cache_key("tedivm", "1_year", show_star_increase=True)

    # Both should normalize username
    assert "tedivm" in key_without_stars
    assert "tedivm" in key_with_stars

    # But keys should differ based on parameter
    assert key_without_stars != key_with_stars


def test_normalize_period_returns_3_years():
    """Test that 3_years is accepted as a valid period."""
    assert normalize_period("3_years") == "3_years"
    assert normalize_period("3_Years") == "3_years"
    assert normalize_period("  3_years  ") == "3_years"


def test_normalize_period_fallback():
    """Test that invalid periods fall back to 1_year."""
    assert normalize_period("invalid") == "1_year"
    assert normalize_period(None) == "1_year"
    assert normalize_period("") == "1_year"


def test_calculate_date_range_3_years():
    """Test that 3_years produces a 1095-day range."""
    since, until = calculate_date_range("3_years")
    diff = until - since
    assert diff == timedelta(days=1095)
