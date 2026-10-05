"""In-process outbox worker: submits due payments to the rail (success path)."""

import asyncio
import json
from datetime import timedelta

from paybridge.config.constants import RETRY_BASE_DELAY_SECONDS, RETRY_MAX_ATTEMPTS
from paybridge.lib.ids import new_event_id
from paybridge.lib.timeutil import iso_z
from paybridge.repository.attempts_repo import AttemptsRepo
from paybridge.repository.db import Database
from paybridge.repository.events_repo import EventsRepo
from paybridge.repository.outbox_repo import OutboxRepo
from paybridge.repository.payments_repo import PaymentsRepo
from paybridge.types.enums import AttemptOutcome, EventType, PaymentState, Rail, ReasonCode
from paybridge.types.errors import PermanentRailError, TransientRailError
from paybridge.types.models import OutboxMessage, PaymentEvent
from paybridge.types.ports import Clock, RailAdapter

POLL_INTERVAL_SECONDS = 0.2
BATCH_SIZE = 20


class OutboxWorker:
    def __init__(
        self,
        database: Database,
        clock: Clock,
        adapters: dict[Rail, RailAdapter],
        poll_interval: float = POLL_INTERVAL_SECONDS,
    ) -> None:
        self._db = database
        self._clock = clock
        self._adapters = adapters
        self._poll_interval = poll_interval

    def _event(self, payment_id: str, type_: EventType, payload: dict[str, str]) -> PaymentEvent:
        return PaymentEvent(
            new_event_id(), payment_id, type_, json.dumps(payload), iso_z(self._clock.now())
        )

    async def process_once(self) -> int:
        now = iso_z(self._clock.now())
        with self._db.read() as conn:
            due = OutboxRepo(conn).list_due(now, BATCH_SIZE)
        for msg in due:
            await self._process(msg)
        return len(due)

    async def _process(self, msg: OutboxMessage) -> None:
        with self._db.write() as conn:
            payment = PaymentsRepo(conn).get(msg.payment_id)
            if payment is None:
                return
            if payment.state is PaymentState.CREATED:
                PaymentsRepo(conn).mark_submitted(payment.id, iso_z(self._clock.now()))
                EventsRepo(conn).append(
                    self._event(
                        payment.id, EventType.PAYMENT_SUBMITTED, {"rail": payment.rail.value}
                    )
                )
            OutboxRepo(conn).mark_in_progress(msg.id, iso_z(self._clock.now()))
        attempt_no = msg.attempts + 1
        try:
            entry = await self._adapters[payment.rail].submit(payment.id, payment.amount_paise)
        except PermanentRailError as exc:
            self._fail(msg, attempt_no, AttemptOutcome.PERMANENT, exc.reason_code, exc.reason_code)
        except TransientRailError as exc:
            self._on_transient(msg, attempt_no, exc.code)
        else:
            self._complete(msg, attempt_no, entry.rail_ref)

    def _complete(self, msg: OutboxMessage, attempt_no: int, rail_ref: str) -> None:
        with self._db.write() as conn:
            now = iso_z(self._clock.now())
            PaymentsRepo(conn).mark_completed(msg.payment_id, rail_ref, now)
            AttemptsRepo(conn).insert(msg.payment_id, attempt_no, AttemptOutcome.SUCCESS, now)
            EventsRepo(conn).append(
                self._event(
                    msg.payment_id, EventType.PAYMENT_COMPLETED, {"rail_reference": rail_ref}
                )
            )
            OutboxRepo(conn).mark_sent(msg.id, attempt_no, now)

    def _fail(
        self,
        msg: OutboxMessage,
        attempt_no: int,
        outcome: AttemptOutcome,
        reason_code: str,
        error_code: str,
    ) -> None:
        with self._db.write() as conn:
            now = iso_z(self._clock.now())
            PaymentsRepo(conn).mark_failed(msg.payment_id, reason_code, now)
            AttemptsRepo(conn).insert(msg.payment_id, attempt_no, outcome, now, error_code)
            EventsRepo(conn).append(
                self._event(msg.payment_id, EventType.PAYMENT_FAILED, {"reason_code": reason_code})
            )
            OutboxRepo(conn).mark_sent(msg.id, attempt_no, now)

    def _on_transient(self, msg: OutboxMessage, attempt_no: int, error_code: str) -> None:
        if attempt_no >= RETRY_MAX_ATTEMPTS:
            reason = ReasonCode.RETRIES_EXHAUSTED.value
            self._fail(msg, attempt_no, AttemptOutcome.TRANSIENT, reason, error_code)
            return
        delay = RETRY_BASE_DELAY_SECONDS * 2 ** (attempt_no - 1)
        with self._db.write() as conn:
            current = self._clock.now()
            now = iso_z(current)
            next_at = iso_z(current + timedelta(seconds=delay))
            AttemptsRepo(conn).insert(
                msg.payment_id, attempt_no, AttemptOutcome.TRANSIENT, now, error_code
            )
            OutboxRepo(conn).reschedule(msg.id, attempt_no, next_at, now)
            EventsRepo(conn).append(
                self._event(
                    msg.payment_id,
                    EventType.PAYMENT_RETRY_SCHEDULED,
                    {"attempt": str(attempt_no), "next_attempt_at": next_at},
                )
            )

    async def run(self) -> None:
        while True:
            await self.process_once()
            await asyncio.sleep(self._poll_interval)
