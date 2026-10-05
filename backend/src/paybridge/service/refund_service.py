"""Refund requests: full refund of a COMPLETED payment, one per payment."""

import json
import sqlite3

from paybridge.lib.ids import new_event_id, new_refund_id
from paybridge.lib.timeutil import iso_z
from paybridge.repository.db import Database
from paybridge.repository.events_repo import EventsRepo
from paybridge.repository.payments_repo import PaymentsRepo
from paybridge.repository.refunds_repo import RefundsRepo
from paybridge.types.enums import EventType, PaymentState, Rail, ReasonCode, RefundState
from paybridge.types.errors import (
    DuplicateKeyError,
    NotFound,
    PaymentNotRefundable,
    PermanentRailError,
    RefundAlreadyDecided,
    RefundAlreadyExists,
)
from paybridge.types.models import PaymentEvent, Refund
from paybridge.types.ports import Clock, RailAdapter
from paybridge.types.state_machine import assert_payment_transition


class RefundService:
    def __init__(
        self,
        database: Database,
        clock: Clock,
        adapters: dict[Rail, RailAdapter] | None = None,
    ) -> None:
        self._db = database
        self._clock = clock
        self._adapters = adapters or {}

    def _event(self, conn: sqlite3.Connection, refund: Refund, kind: EventType, now: str) -> None:
        EventsRepo(conn).append(
            PaymentEvent(
                id=new_event_id(),
                payment_id=refund.payment_id,
                type=kind,
                payload=json.dumps({"refund_id": refund.id}),
                at=now,
            )
        )

    def _claim(
        self, refund_id: str, admin_id: str, state: RefundState, reason: str | None
    ) -> Refund:
        """Atomically move a REQUESTED refund to APPROVED or REJECTED."""
        now = iso_z(self._clock.now())
        with self._db.write() as conn:
            repo = RefundsRepo(conn)
            refund = repo.get(refund_id)
            if refund is None:
                raise NotFound("Refund not found")
            if refund.state is not RefundState.REQUESTED:
                raise RefundAlreadyDecided("Refund is not REQUESTED")
            repo.update_state(refund_id, state, now, admin_id, reason)
            kind = (
                EventType.REFUND_APPROVED
                if state is RefundState.APPROVED
                else EventType.REFUND_REJECTED
            )
            self._event(conn, refund, kind, now)
            return repo.get(refund_id) or refund

    def reject(self, refund_id: str, admin_id: str) -> Refund:
        return self._claim(refund_id, admin_id, RefundState.REJECTED, ReasonCode.REJECTED_BY_ADMIN)

    async def approve(self, refund_id: str, admin_id: str) -> Refund:
        refund = self._claim(refund_id, admin_id, RefundState.APPROVED, None)
        with self._db.read() as conn:
            payment = PaymentsRepo(conn).get(refund.payment_id)
        assert payment is not None
        reason: str | None = None
        try:
            await self._adapters[payment.rail].reverse(payment.id, refund.amount_paise)
        except PermanentRailError as exc:
            reason = exc.reason_code
        final, kind = (
            (RefundState.FAILED, EventType.REFUND_FAILED)
            if reason
            else (RefundState.EXECUTED, EventType.REFUND_EXECUTED)
        )
        now = iso_z(self._clock.now())
        with self._db.write() as conn:
            RefundsRepo(conn).update_state(refund_id, final, now, reason_code=reason)
            self._event(conn, refund, kind, now)
            if final is RefundState.EXECUTED:
                assert_payment_transition(PaymentState.COMPLETED, PaymentState.REFUNDED)
                PaymentsRepo(conn).mark_refunded(refund.payment_id, now)
                self._event(conn, refund, EventType.PAYMENT_REFUNDED, now)
            return RefundsRepo(conn).get(refund_id) or refund

    def request_refund(self, customer_id: str, payment_id: str) -> Refund:
        now = iso_z(self._clock.now())
        try:
            with self._db.write() as conn:
                payment = PaymentsRepo(conn).get(payment_id)
                if payment is None or payment.customer_id != customer_id:
                    raise NotFound("Payment not found")
                if payment.state is not PaymentState.COMPLETED:
                    raise PaymentNotRefundable("Only COMPLETED payments can be refunded")
                refunds = RefundsRepo(conn)
                if refunds.get_for_payment(payment_id) is not None:
                    raise RefundAlreadyExists("A refund already exists for this payment")
                refund = Refund(
                    id=new_refund_id(),
                    payment_id=payment_id,
                    amount_paise=payment.amount_paise,
                    state=RefundState.REQUESTED,
                    requested_by=customer_id,
                    created_at=now,
                    updated_at=now,
                )
                refunds.insert(refund)
                EventsRepo(conn).append(
                    PaymentEvent(
                        id=new_event_id(),
                        payment_id=payment_id,
                        type=EventType.REFUND_REQUESTED,
                        payload=json.dumps(
                            {"refund_id": refund.id, "amount_paise": refund.amount_paise}
                        ),
                        at=now,
                    )
                )
        except DuplicateKeyError:
            raise RefundAlreadyExists("A refund already exists for this payment") from None
        return refund
