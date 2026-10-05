import pytest

from paybridge.types.errors import AmountBelowMinimum, DomainError, ValidationError
from paybridge.types.money import (
    MIN_AMOUNT_PAISE,
    format_paise_as_rupees,
    rupees_to_paise,
    validate_amount,
)


@pytest.mark.parametrize("amount", [0, -1, 1, 99])
def test_validate_amount_rejects_below_minimum(amount: int) -> None:
    with pytest.raises(AmountBelowMinimum) as exc:
        validate_amount(amount)
    assert exc.value.code == "AMOUNT_BELOW_MINIMUM"
    assert isinstance(exc.value, ValidationError)
    assert isinstance(exc.value, DomainError)


def test_validate_amount_accepts_minimum() -> None:
    assert MIN_AMOUNT_PAISE == 100
    assert validate_amount(100) == 100


def test_rupees_to_paise_indian_grouping() -> None:
    result = rupees_to_paise("1,00,000.50")
    assert result == 10000050
    assert type(result) is int


@pytest.mark.parametrize(
    ("text", "paise"),
    [("1", 100), ("0.5", 50), (" 12.34 ", 1234), ("0.01", 1), ("1,000", 100000)],
)
def test_rupees_to_paise_valid(text: str, paise: int) -> None:
    assert rupees_to_paise(text) == paise


@pytest.mark.parametrize("text", ["1.005", "abc", "", "-5", "1e3", "NaN", "1.", ".5x", "1..2"])
def test_rupees_to_paise_rejects_invalid(text: str) -> None:
    with pytest.raises(ValidationError) as exc:
        rupees_to_paise(text)
    assert exc.value.code == "VALIDATION_ERROR"


def test_format_paise_as_rupees() -> None:
    assert format_paise_as_rupees(10000050) == "1,00,000.50"
    assert format_paise_as_rupees(100) == "1.00"
    assert format_paise_as_rupees(5) == "0.05"
    assert format_paise_as_rupees(123456789) == "12,34,567.89"
