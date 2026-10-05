from dataclasses import replace

from paybridge.service.matching import match
from paybridge.types.enums import PaymentState, Rail, ReconStatus
from paybridge.types.models import RailStatementEntry
from tests.support.factories import TS, make_payment

PAY = make_payment(state=PaymentState.COMPLETED, rail_reference="UPI1")


def entry(**kw: object) -> RailStatementEntry:
    base = RailStatementEntry(
        id="rse_1",
        rail=Rail.UPI,
        payment_ref="UPI1",
        amount_paise=10000,
        statement_date="2026-10-04",
        created_at=TS,
        payment_id=PAY.id,
    )
    return replace(base, **kw)  # type: ignore[arg-type]


def test_matched() -> None:
    assert [m.status for m in match([PAY], [entry()])] == [ReconStatus.MATCHED]


def test_one_paise_mismatch() -> None:
    res = match([PAY], [entry(amount_paise=9999)])
    assert [m.status for m in res] == [ReconStatus.AMOUNT_MISMATCH]


# AC-06
def test_unmatched_internal_and_external() -> None:
    res = match([PAY], [entry(id="rse_2", payment_id=None)])
    assert {m.status for m in res} == {
        ReconStatus.UNMATCHED_INTERNAL,
        ReconStatus.UNMATCHED_EXTERNAL,
    }


def test_ref_mismatch_is_not_matched() -> None:
    res = match([PAY], [entry(payment_ref="OTHER")])
    assert {m.status for m in res} == {
        ReconStatus.UNMATCHED_INTERNAL,
        ReconStatus.UNMATCHED_EXTERNAL,
    }
