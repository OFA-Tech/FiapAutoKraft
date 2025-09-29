import pytest

from shared.validation import (
    ValidationError,
    ensure_positive_float,
    parse_float,
    parse_int,
)


def test_parse_int_with_minimum():
    assert parse_int("5", "Field", minimum=3) == 5
    with pytest.raises(ValidationError):
        parse_int("2", "Field", minimum=3)


def test_parse_float_and_positive():
    assert parse_float("2.5", "Field", minimum=0.0) == pytest.approx(2.5)
    with pytest.raises(ValidationError):
        parse_float("-1", "Field", minimum=0.0)


def test_ensure_positive_float():
    assert ensure_positive_float("0.5", "Zoom") == pytest.approx(0.5)
    with pytest.raises(ValidationError):
        ensure_positive_float("0", "Zoom")
