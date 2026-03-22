"""Smoke tests for the dominion-setup package.

These tests verify that the most critical functionality of the package works.
They are designed to catch major breakage and ensure basic operations succeed.
"""


def test_import() -> None:
    """Test importing the package."""
    import dominion_setup  # noqa: F401, PLC0415
