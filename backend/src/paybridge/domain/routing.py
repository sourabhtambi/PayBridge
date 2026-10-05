"""Rail routing bands (BRD 5.3). Upper bounds are inclusive, in paise."""

from paybridge.domain.money import validate_amount
from paybridge.types.enums import Rail

UPI_MAX_PAISE = 10_000_000
IMPS_MAX_PAISE = 20_000_000
NEFT_MAX_PAISE = 50_000_000

_BANDS: tuple[tuple[int, Rail], ...] = (
    (UPI_MAX_PAISE, Rail.UPI),
    (IMPS_MAX_PAISE, Rail.IMPS),
    (NEFT_MAX_PAISE, Rail.NEFT),
)


def route_rail(amount_paise: int) -> Rail:
    validate_amount(amount_paise)
    for upper_bound, rail in _BANDS:
        if amount_paise <= upper_bound:
            return rail
    return Rail.RTGS


def routing_reason(amount_paise: int, rail: Rail) -> str:
    """Human-readable explanation of why `rail` was selected for the amount (AC-03)."""
    lower = 0
    for upper_bound, band_rail in _BANDS:
        if band_rail is rail:
            bound = f"<= {upper_bound}" if lower == 0 else f"> {lower} and <= {upper_bound}"
            return f"amount {amount_paise} paise {bound}: {rail.value}"
        lower = upper_bound
    return f"amount {amount_paise} paise > {lower}: {rail.value}"
