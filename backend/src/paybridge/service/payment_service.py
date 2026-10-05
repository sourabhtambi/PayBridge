"""Payment creation: validate, route, and persist payment + outbox + event atomically."""

import json
from datetime import timedelta
from typing import NamedTuple

from paybridge.domain.idempotency import request_hash
from paybridge.domain.money import validate_amount
from paybridge.domain.routing import route_rail, routing_reason
from paybridge.lib.ids import new_event_id, new_payment_id
from paybridge.lib.masking import register_sensitive
from paybridge.lib.timeutil import iso_z, parse_iso_z
from paybridge.repository.db import Database
from paybridge.repository.events_repo import EventsRepo
from paybridge.repository.outbox_repo import OutboxRepo
from paybridge.repository.payments_repo import PaymentsRepo
from paybridge.types.enums import EventType, PaymentState
from paybridge.types.errors import IdempotencyConflict, ValidationError
from paybridge.types.models import Payment, PaymentEvent
from paybridge.types.ports import Clock

MAX_BENEFICIARY_LENGTH = 140
IDEMPOTENCY_TTL = timedelta(seconds=86400)


def load_known_beneficiaries(database: Database) -> None:
    """Re-register every stored beneficiary so masking survives restarts."""
    with database.read() as conn:
        names = PaymentsRepo(conn).distinct_beneficiaries()
    for name in names:
        register_sensitive(name)


class CreateResult(NamedTuple):
    payment: Payment
    replay: bool


class PaymentService:
    def __init__(self, database: Database, clock: Clock) -> None:
        self._db = database
        self._clock = clock

    def create_payment(
        self, customer_id: str, idempotency_key: str, amount_paise: int, beneficiary: str
    ) -> CreateResult:
        validate_amount(amount_paise)
        if not beneficiary.strip() or len(beneficiary) > MAX_BENEFICIARY_LENGTH:
            raise ValidationError(
                f"Beneficiary must be 1-{MAX_BENEFICIARY_LENGTH} characters", "beneficiary"
            )
        register_sensitive(beneficiary)
        now = iso_z(self._clock.now())
        payment = Payment(
            id=new_payment_id(),
            customer_id=customer_id,
            idempotency_key=idempotency_key,
            request_hash=request_hash(amount_paise, beneficiary),
            amount_paise=amount_paise,
            rail=route_rail(amount_paise),
            beneficiary=beneficiary,
            state=PaymentState.CREATED,
            created_at=now,
            updated_at=now,
        )
        event = PaymentEvent(
            id=new_event_id(),
            payment_id=payment.id,
            type=EventType.PAYMENT_CREATED,
            payload=json.dumps(
                {
                    "rail": payment.rail.value,
                    "amount_paise": amount_paise,
                    "reason": routing_reason(amount_paise, payment.rail),
                }
            ),
            at=now,
        )
        with self._db.write() as conn:
            repo = PaymentsRepo(conn)
            existing = repo.find_active_by_key(customer_id, idempotency_key)
            if existing is not None:
                if parse_iso_z(existing.created_at) + IDEMPOTENCY_TTL > self._clock.now():
                    if existing.request_hash != payment.request_hash:
                        raise IdempotencyConflict("Idempotency key reused with different payload")
                    return CreateResult(existing, True)
                repo.release_idempotency(existing.id, now)
            repo.insert(payment)
            OutboxRepo(conn).insert(payment.id, now, now)
            EventsRepo(conn).append(event)
        return CreateResult(payment, False)
