import pytest

from vault.region import Region, RegionValidationError, get_region, pin_region


def test_pin_region_defaults_to_supported_region() -> None:
    pinned = pin_region(user_id=5, region=Region.INDIA.value)

    assert pinned == Region.INDIA
    assert get_region(user_id=5) == Region.INDIA


def test_pin_region_switches_region() -> None:
    pinned = pin_region(user_id=6, region=Region.SWITZERLAND.value)

    assert pinned == Region.SWITZERLAND
    assert get_region(user_id=6) == Region.SWITZERLAND


def test_pin_region_invalid_region_raises() -> None:
    with pytest.raises(RegionValidationError):
        pin_region(user_id=7, region="BRAZIL")


def test_get_region_defaults_to_india() -> None:
    assert get_region(user_id=9999) == Region.INDIA


def test_validate_user_region_mismatch_raises() -> None:
    pin_region(user_id=8, region=Region.INDIA.value)

    with pytest.raises(RegionValidationError, match="expected SWITZERLAND"):
        from vault.region import validate_user_region

        validate_user_region(user_id=8, required_region=Region.SWITZERLAND)
