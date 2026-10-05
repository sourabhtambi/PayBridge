import pytest

from paybridge.domain.routing import route_rail, routing_reason
from paybridge.types.enums import Rail
from paybridge.types.errors import AmountBelowMinimum


@pytest.mark.parametrize(
    ("amount", "rail"),
    [
        (100, Rail.UPI),
        (10_000_000, Rail.UPI),
        (10_000_001, Rail.IMPS),
        (20_000_000, Rail.IMPS),
        (20_000_001, Rail.NEFT),
        (50_000_000, Rail.NEFT),
        (50_000_001, Rail.RTGS),
        (1_000_000_000_000, Rail.RTGS),
    ],
)
# AC-03
def test_route_rail_boundaries(amount: int, rail: Rail) -> None:
    assert route_rail(amount) is rail


@pytest.mark.parametrize("amount", [0, -1, 99])
def test_route_rail_rejects_below_minimum(amount: int) -> None:
    with pytest.raises(AmountBelowMinimum):
        route_rail(amount)


# AC-03
def test_routing_reason_for_every_rail() -> None:
    assert routing_reason(100, Rail.UPI) == "amount 100 paise <= 10000000: UPI"
    assert routing_reason(10_000_001, Rail.IMPS) == (
        "amount 10000001 paise > 10000000 and <= 20000000: IMPS"
    )
    assert routing_reason(50_000_001, Rail.RTGS) == "amount 50000001 paise > 50000000: RTGS"
