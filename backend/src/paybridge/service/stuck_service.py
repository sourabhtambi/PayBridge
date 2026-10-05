"""Stuck payment detection: SUBMITTED for strictly more than the threshold."""

import json
from datetime import timedelta

from paybridge.config.constants import STUCK_THRESHOLD_SECONDS
from paybridge.lib.ids import new_event_id
from paybridge.lib.timeutil import iso_z, parse_iso_z
from paybridge.repository.db import Database
from paybridge.repository.events_repo import EventsRepo
from paybridge.repository.payments_repo import PaymentsRepo
from paybridge.types.enums import EventType
from paybridge.types.models import PaymentEvent
from paybridge.types.ports import Clock


def detect_and_list(db: Database, clock: Clock) -> list[dict[str, object]]:
    now = clock.now()
    now_s = iso_z(now)
    cutoff = iso_z(now - timedelta(seconds=STUCK_THRESHOLD_SECONDS))
    with db.write() as conn:
        payments, events = PaymentsRepo(conn), EventsRepo(conn)
        for p in payments.find_unflagged_submitted_before(cutoff):
            if payments.mark_stuck_flagged(p.id, now_s):
                events.append(
                    PaymentEvent(
                        id=new_event_id(),
                        payment_id=p.id,
                        type=EventType.PAYMENT_FLAGGED_STUCK,
                        payload=json.dumps({"submitted_at": p.submitted_at}),
                        at=now_s,
                    )
                )
        flagged = payments.list_flagged_submitted()
    return [
        {
            "payment_id": p.id,
            "rail": p.rail.value,
            "amount_paise": p.amount_paise,
            "submitted_at": p.submitted_at,
            "flagged_at": p.stuck_flagged_at,
            "age_seconds": int((now - parse_iso_z(str(p.submitted_at))).total_seconds()),
        }
        for p in flagged
    ]
