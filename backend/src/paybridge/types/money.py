"""Money helpers. Money is integer paise; Decimal is used only for parsing."""

import re
from decimal import Decimal

from paybridge.types.errors import AmountBelowMinimum, ValidationError

MIN_AMOUNT_PAISE = 100
PAISE_PER_RUPEE = 100

_RUPEE_PATTERN = re.compile(r"\d+(\.\d{1,2})?")


def validate_amount(amount_paise: int) -> int:
    if amount_paise < MIN_AMOUNT_PAISE:
        raise AmountBelowMinimum(f"Amount must be at least {MIN_AMOUNT_PAISE} paise")
    return amount_paise


def rupees_to_paise(text: str) -> int:
    cleaned = text.strip().replace(",", "")
    if _RUPEE_PATTERN.fullmatch(cleaned) is None:
        raise ValidationError(f"Invalid rupee amount: {text!r}")
    return int(Decimal(cleaned) * PAISE_PER_RUPEE)


def _group_indian(digits: str) -> str:
    if len(digits) <= 3:
        return digits
    head, tail = digits[:-3], digits[-3:]
    groups: list[str] = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    if head:
        groups.insert(0, head)
    return ",".join([*groups, tail])


def format_paise_as_rupees(amount_paise: int) -> str:
    rupees, paise = divmod(amount_paise, PAISE_PER_RUPEE)
    return f"{_group_indian(str(rupees))}.{paise:02d}"
