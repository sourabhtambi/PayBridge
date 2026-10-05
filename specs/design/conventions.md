# PayBridge Design Conventions (binding for all /design artifacts)

Both the planner and ui-designer MUST use these names exactly. api-contracts.md is the full detail; this file is the shared source of truth for shapes and decisions.

## Approved decisions
1. `amount_paise` is an integer at the API (request and response). Rupee strings exist only in the UI.
2. Refund of a non-COMPLETED payment: 422 `PAYMENT_NOT_REFUNDABLE`.
3. Stuck list: `GET /ops/stuck-payments` (ops, admin).
4. Exhausted retries: reason code `RETRIES_EXHAUSTED`.
5. E9 is a cross-cutting quality epic (no new endpoints; verification only).
6. Feature registry is `specs/features.json` only.
7. **Expired idempotency key release (resolved here).** See section "Idempotency expiry".

## Idempotency expiry (decision 7)
- `payments` gets a nullable column `idempotency_released_at` (TEXT, UTC ISO 8601).
- Uniqueness is a PARTIAL unique index: `CREATE UNIQUE INDEX ux_payments_customer_key ON payments(customer_id, idempotency_key) WHERE idempotency_released_at IS NULL`. A released row keeps its key for audit but no longer occupies the (customer_id, key) slot.
- Release is lazy, inside the create transaction (BEGIN IMMEDIATE), no sweeper job:
  1. Look up the active row (released_at IS NULL) for (customer_id, key).
  2. If none: insert normally.
  3. If found and `created_at + 24h > now` (injected clock): same payload hash -> replay (200); different hash -> 409 IDEMPOTENCY_KEY_CONFLICT.
  4. If found and `created_at + 24h <= now`: `UPDATE payments SET idempotency_released_at = :now WHERE id = :id AND idempotency_released_at IS NULL`, then insert the new payment, in the same transaction. The payload hash is NOT compared once expired (same or different payload both create a new payment).
- Concurrency: BEGIN IMMEDIATE serialises writers, and the conditional UPDATE plus partial unique index mean exactly one request releases and inserts; the other sees the new active row and replays (or gets DuplicateKeyError mapped to replay).
- The expired payment is otherwise unchanged (state, events, attempts, outbox). A `PAYMENT_IDEMPOTENCY_RELEASED` event is NOT added (payment_events is append-only per state transition; release is not a state transition). Clarification for F028: "original unchanged" means unchanged except `idempotency_released_at`.
- Window is measured from the original payment `created_at`, fixed (not sliding): a replay does not extend it.
- Config constant: `IDEMPOTENCY_TTL_SECONDS = 86400`.

## Transport conventions
- Base URL `http://localhost:8000`, no `/api` prefix. JSON only (except settlement file download = text/csv).
- Request headers: `X-Role` (customer|ops|admin), `X-Customer-Id` (required when customer; ops/admin may omit), `Idempotency-Key` (POST /payments only, 1-128 chars, UUID in UI).
- IDs are prefixed strings: `cus_001`, `pay_<uuid4 hex 12>`, `rfd_...`, `rec_...`, `stl_...`, `evt_...`.
- Timestamps: ISO 8601 UTC with Z (`2026-10-04T09:30:00Z`). Dates (`business_date`, `statement_date`, `date`): `YYYY-MM-DD` = IST calendar day.
- Lists are returned as `{"items": [...], "total": n}`. No pagination in v1 (cap 500 items).
- Error envelope for every non-2xx: `{"error": {"code": "STRING_CODE", "message": "human text", "fields": [{"field": "amount_paise", "message": "..."}]}}` (`fields` only on 422).
- Error codes: `UNAUTHENTICATED`(401) `FORBIDDEN`(403) `NOT_FOUND`(404) `VALIDATION_ERROR`(422) `AMOUNT_BELOW_MINIMUM`(422, field amount_paise) `PAYMENT_NOT_REFUNDABLE`(422) `IDEMPOTENCY_KEY_CONFLICT`(409) `REFUND_ALREADY_EXISTS`(409) `REFUND_ALREADY_DECIDED`(409) `RECON_ALREADY_RESOLVED`(409) `INTERNAL_ERROR`(500).
- Rate limits: none in v1 (state "none" in the contract).
- CORS: origin `http://localhost:3000`, headers X-Role, X-Customer-Id, Idempotency-Key; expose `Idempotent-Replay`.
- Replay response (200) carries header `Idempotent-Replay: true`.

## Enumerations
- Role: `customer`, `ops`, `admin`. Rail: `UPI`, `IMPS`, `NEFT`, `RTGS`.
- PaymentState: `CREATED`, `SUBMITTED`, `COMPLETED`, `FAILED`. RefundState: `REQUESTED`, `APPROVED`, `EXECUTED`, `REJECTED`, `FAILED`.
- ReconStatus: `matched`, `unmatched_internal`, `unmatched_external`, `amount_mismatch`.
- Attempt outcome: `success`, `transient`, `permanent`. Outbox status: `PENDING`, `IN_PROGRESS`, `SENT`.
- Settlement kind: `primary`, `followup`. Simulation mode: `success`, `permanent_failure`, `transient`.
- Event types: `PAYMENT_CREATED` `PAYMENT_SUBMITTED` `PAYMENT_RETRY_SCHEDULED` `PAYMENT_COMPLETED` `PAYMENT_FAILED` `PAYMENT_FLAGGED_STUCK` `REFUND_REQUESTED` `REFUND_APPROVED` `REFUND_REJECTED` `REFUND_EXECUTED` `REFUND_FAILED`.
- Reason codes (permanent, selectable in simulation): `INSUFFICIENT_FUNDS`, `INVALID_BENEFICIARY`, `BENEFICIARY_ACCOUNT_CLOSED`, `LIMIT_EXCEEDED`. System code: `RETRIES_EXHAUSTED`. Refund reversal failure reuses the configured permanent reason code.

## Canonical response shapes
Customer: `{id, name, role}`
Health: `{status:"ok", database:"ok"}`
Payment: `{id, customer_id, amount_paise, rail, beneficiary, state, reason_code|null, rail_reference|null, refund|null, created_at, updated_at}` where `refund` = `{id, state, reason_code|null}` or null.
PaymentDetail = Payment + `events:[{id, type, payload:{}, at}]` (chronological) + `attempts:[{attempt_no, outcome, error_code|null, at}]`.
CreatePaymentRequest: `{amount_paise:int>=100, beneficiary:str 1..140}` + header Idempotency-Key. 202 new, 200 replay.
Refund: `{id, payment_id, amount_paise, state, requested_by, decided_by|null, reason_code|null, created_at, updated_at}`. `POST /refunds` body `{payment_id}` -> 201.
Reconciliation run: `POST /reconciliation/run` body `{statement_date}` -> `{statement_date, counts:{matched, unmatched_internal, unmatched_external, amount_mismatch}}`.
ReconResult: `{id, statement_date, rail, status, payment_id|null, statement_entry_id|null, payment_ref|null, payment_amount_paise|null, statement_amount_paise|null, resolved:bool, resolution_note|null, resolved_by|null, resolved_at|null}`. `GET /reconciliation/unmatched?status=&rail=` -> list. `POST /reconciliation/{id}/resolve` body `{note}` -> ReconResult.
SettlementFile: `{id, business_date, kind, row_count, checksum, written_at}`. `POST /settlement/run` body `{business_date}` (optional, default today IST) -> 201 `{file: SettlementFile, message}` first run; 200 `{file: SettlementFile|null, message}` repeat (follow-up written, or message that primary exists). `GET /settlement/files` -> list. `GET /settlement/files/{id}` -> text/csv. CSV columns: payment_id,rail,amount_paise,rail_ref,recon_status,unmatched_flag; footer lines `# row_count=N` and `# sha256=<hex>`.
Stuck: `GET /ops/stuck-payments` -> list of `{payment_id, rail, amount_paise, submitted_at, flagged_at, age_seconds}`.
Simulation: `GET /admin/simulation` -> `{items:[{rail, mode, reason_code|null, transient_failure_rate}]}`; `PUT /admin/simulation/{rail}` body `{mode, reason_code?, transient_failure_rate?}` -> the rail config.
Dashboard: `GET /dashboard/summary?date=` -> `{date, rails:[{rail, payment_count, total_paise}], status_counts:{CREATED,SUBMITTED,COMPLETED,FAILED}, pending_refunds:[Refund], settlement_files:[SettlementFile]}`; always all four rails and four states, zeros when no activity.
Refund endpoints: `POST /refunds/{id}/approve`, `POST /refunds/{id}/reject` -> Refund. `GET /refunds?state=` list.
Payments list: `GET /payments?state=&customer_id=` -> list of Payment.

## Role matrix
customer: POST/GET /payments, POST/GET /refunds, GET /customers. ops: GET /payments, GET /refunds(not decide), /reconciliation/*, GET /ops/stuck-payments. admin: everything ops can, plus /refunds/{id}/approve|reject, /settlement/*, /dashboard/summary, /admin/simulation*. /health and GET /customers need no role headers.

## UI shell
Hash-free routes: `/payments`, `/payments/new`, `/payments/:id`, `/reconciliation`, `/stuck-payments`, `/dashboard`, `/settlement`, `/simulation`. Nav per role per story E1-S4.
