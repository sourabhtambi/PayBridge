import sqlite3
from dataclasses import replace

from paybridge.lib.ids import new_statement_entry_id
from paybridge.repository.payments_repo import PaymentsRepo
from paybridge.repository.recon_repo import ReconRepo
from paybridge.repository.statements_repo import StatementsRepo
from paybridge.service.reconciliation_service import ReconciliationService
from paybridge.service.statement_service import StatementService
from paybridge.types.enums import PaymentState, Rail, ReconStatus
from paybridge.types.models import RailStatementEntry
from tests.support.corpus import load_corpus
from tests.support.factories import TS, make_payment
from tests.support.fake_clock import FakeClock

DATE = "2026-10-04"


def _add_completed(conn: sqlite3.Connection, **kw: object) -> None:
    PaymentsRepo(conn).insert(
        make_payment(state=PaymentState.COMPLETED, completed_at=TS, **kw)  # type: ignore[arg-type]
    )


def _services(
    conn: sqlite3.Connection, clock: FakeClock
) -> tuple[StatementService, ReconciliationService, StatementsRepo]:
    pr, sr, rr = PaymentsRepo(conn), StatementsRepo(conn), ReconRepo(conn)
    return StatementService(pr, sr, clock), ReconciliationService(pr, sr, rr, clock), sr


def test_generate_one_entry_per_completed_payment(
    conn: sqlite3.Connection, clock: FakeClock
) -> None:
    _add_completed(conn, rail_reference="UPI1")
    PaymentsRepo(conn).insert(
        make_payment(id="pay_000000000002", idempotency_key="k2")
    )  # CREATED, excluded
    stmt, _, _ = _services(conn, clock)
    entries = stmt.generate(DATE)
    stmt.generate(DATE)
    assert [
        (e.rail, e.payment_ref, e.amount_paise, e.statement_date) for e in stmt.generate(DATE)
    ] == [(Rail.UPI, "UPI1", 10000, DATE)]
    assert len(entries) == 1


def test_run_matched_and_idempotent(conn: sqlite3.Connection, clock: FakeClock) -> None:
    _add_completed(conn, rail_reference="UPI1")
    stmt, rec, _ = _services(conn, clock)
    stmt.generate(DATE)
    assert [m.status for m in rec.run(DATE)] == [ReconStatus.MATCHED]
    rec.run(DATE)
    count = conn.execute("SELECT COUNT(*) FROM reconciliation_results").fetchone()[0]
    assert count == 1


# AC-06
def test_corpus_flags_exactly_seeded_anomalies(conn: sqlite3.Connection, clock: FakeClock) -> None:
    corpus = load_corpus()
    for i, p in enumerate(corpus["payments"]):
        _add_completed(
            conn,
            id=p["id"],
            rail=Rail(p["rail"]),
            amount_paise=p["amount_paise"],
            rail_reference=p["ref"],
            idempotency_key=f"k{i}",
        )
    _, rec, sr = _services(conn, clock)
    for e in corpus["entries"]:
        sr.insert_or_ignore(
            RailStatementEntry(
                id=new_statement_entry_id(),
                rail=Rail(e["rail"]),
                payment_ref=e["ref"],
                payment_id=e["payment_id"],
                amount_paise=e["amount_paise"],
                statement_date=corpus["statement_date"],
                created_at=TS,
            )
        )
    rec.run(corpus["statement_date"])
    flagged = {
        (r["status"], r["payment_id"], r["payment_ref"] if r["payment_id"] is None else None)
        for r in conn.execute("SELECT * FROM reconciliation_results WHERE status <> 'matched'")
    }
    expected = {
        (a["status"], a.get("payment_id"), a.get("payment_ref")) for a in corpus["anomalies"]
    }
    assert flagged == expected
    assert replace  # keep import used
