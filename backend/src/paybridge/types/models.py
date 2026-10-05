"""Frozen dataclasses for the nine persisted entities and the rail ledger entry.

Timestamps are ISO 8601 UTC strings with Z; dates are IST YYYY-MM-DD strings.
"""

from dataclasses import dataclass
from typing import Literal

from paybridge.types.enums import (
    AttemptOutcome,
    EventType,
    OutboxStatus,
    PaymentState,
    Rail,
    ReconStatus,
    RefundState,
    Role,
    SettlementKind,
)


@dataclass(frozen=True)
class Customer:
    id: str
    name: str
    role: Role
    created_at: str


@dataclass(frozen=True)
class Payment:
    id: str
    customer_id: str
    idempotency_key: str
    request_hash: str
    amount_paise: int
    rail: Rail
    beneficiary: str
    state: PaymentState
    created_at: str
    updated_at: str
    reason_code: str | None = None
    rail_reference: str | None = None
    submitted_at: str | None = None
    completed_at: str | None = None
    stuck_flagged_at: str | None = None
    idempotency_released_at: str | None = None


@dataclass(frozen=True)
class PaymentAttempt:
    id: int
    payment_id: str
    attempt_no: int
    outcome: AttemptOutcome
    at: str
    error_code: str | None = None


@dataclass(frozen=True)
class OutboxMessage:
    id: int
    payment_id: str
    status: OutboxStatus
    next_attempt_at: str
    attempts: int
    created_at: str
    updated_at: str
    claimed_at: str | None = None


@dataclass(frozen=True)
class PaymentEvent:
    id: str
    payment_id: str
    type: EventType
    payload: str
    at: str


@dataclass(frozen=True)
class Refund:
    id: str
    payment_id: str
    amount_paise: int
    state: RefundState
    requested_by: str
    created_at: str
    updated_at: str
    decided_by: str | None = None
    reason_code: str | None = None


@dataclass(frozen=True)
class RailStatementEntry:
    id: str
    rail: Rail
    payment_ref: str
    amount_paise: int
    statement_date: str
    created_at: str
    payment_id: str | None = None
    status: ReconStatus | None = None


@dataclass(frozen=True)
class ReconciliationResult:
    id: str
    statement_date: str
    rail: Rail
    status: ReconStatus
    created_at: str
    updated_at: str
    payment_id: str | None = None
    statement_entry_id: str | None = None
    payment_ref: str | None = None
    payment_amount_paise: int | None = None
    statement_amount_paise: int | None = None
    resolved: bool = False
    resolution_note: str | None = None
    resolved_by: str | None = None
    resolved_at: str | None = None


@dataclass(frozen=True)
class SettlementFile:
    id: str
    business_date: str
    kind: SettlementKind
    sequence: int
    path: str
    row_count: int
    checksum: str
    written_at: str


@dataclass(frozen=True)
class RailLedgerEntry:
    type: Literal["PAYMENT", "REVERSAL"]
    rail: Rail
    payment_id: str
    rail_ref: str
    amount_paise: int
    accepted_at: str
