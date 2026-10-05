# PayBridge API Contracts

Binding source for shapes: `conventions.md`. Machine-readable form: `api-contracts.schema.json` (OpenAPI 3.0.3). Base URL `http://localhost:8000`, no `/api` prefix, JSON only (except settlement download = `text/csv`). **Rate limit: none (v1).**

## Common conventions

| Item | Rule |
|---|---|
| Auth headers | `X-Role` (customer, ops, admin), `X-Customer-Id` (required when customer). Demo header auth, not a security control. `/health` and `GET /customers` need none |
| `Idempotency-Key` | POST /payments only, 1-128 chars (UUID from the UI), scoped per customer |
| IDs | `cus_001`, `pay_<12 hex>`, `rfd_...`, `rec_...`, `stl_...`, `evt_...`, `rse_...` |
| Timestamps | ISO 8601 UTC with Z, e.g. `2026-10-04T09:30:00Z` |
| Dates | `YYYY-MM-DD`, an IST calendar day |
| Money | `amount_paise` integer everywhere. Never a float or a rupee string |
| Lists | `{"items": [...], "total": n}`, no pagination, cap 500 |
| CORS | origin `http://localhost:3000`; allow headers X-Role, X-Customer-Id, Idempotency-Key, Content-Type; expose `Idempotent-Replay` |

### Error envelope (every non-2xx except `/health` 503)

```json
{"error": {"code": "VALIDATION_ERROR", "message": "human text", "fields": [{"field": "amount_paise", "message": "Amount must be at least Rs 1"}]}}
```

`fields` appears only on 422. Codes: `UNAUTHENTICATED` 401, `FORBIDDEN` 403, `NOT_FOUND` 404, `VALIDATION_ERROR` 422, `AMOUNT_BELOW_MINIMUM` 422 (field `amount_paise`), `PAYMENT_NOT_REFUNDABLE` 422, `IDEMPOTENCY_KEY_CONFLICT` 409, `REFUND_ALREADY_EXISTS` 409, `REFUND_ALREADY_DECIDED` 409, `RECON_ALREADY_RESOLVED` 409, `INTERNAL_ERROR` 500. Every endpoint can also return 500 `INTERNAL_ERROR`. Check order: 401, 403, 404 (resource), then validation/state errors; role guards run before body validation.

## Role matrix

| Endpoint | customer | ops | admin |
|---|---|---|---|
| GET /health | yes | yes | yes |
| GET /customers | yes | yes | yes |
| POST /payments | yes | no | no |
| GET /payments | yes | yes | yes |
| GET /payments/{id} | yes | yes | yes |
| POST /refunds | yes | no | no |
| GET /refunds | yes | yes | yes |
| POST /refunds/{id}/approve | no | no | yes |
| POST /refunds/{id}/reject | no | no | yes |
| POST /reconciliation/run | no | yes | yes |
| GET /reconciliation/unmatched | no | yes | yes |
| POST /reconciliation/{id}/resolve | no | yes | yes |
| POST /settlement/run | no | no | yes |
| GET /settlement/files | no | no | yes |
| GET /settlement/files/{id} | no | no | yes |
| GET /dashboard/summary | no | no | yes |
| GET /ops/stuck-payments | no | yes | yes |
| GET /admin/simulation | no | no | yes |
| PUT /admin/simulation/{rail} | no | no | yes |

## Schemas

Full definitions are in `api-contracts.schema.json#/components/schemas`. Canonical shapes:

- Customer `{id, name, role}`; Health `{status:"ok", database:"ok"}`
- Payment `{id, customer_id, amount_paise, rail, beneficiary, state, reason_code|null, rail_reference|null, refund|null, created_at, updated_at}`; `refund` = `{id, state, reason_code|null}` or null
- PaymentDetail = Payment + `events:[{id,type,payload,at}]` + `attempts:[{attempt_no,outcome,error_code|null,at}]`
- Refund `{id, payment_id, amount_paise, state, requested_by, decided_by|null, reason_code|null, created_at, updated_at}`
- ReconResult `{id, statement_date, rail, status, payment_id|null, statement_entry_id|null, payment_ref|null, payment_amount_paise|null, statement_amount_paise|null, resolved, resolution_note|null, resolved_by|null, resolved_at|null}`
- SettlementFile `{id, business_date, kind, row_count, checksum, written_at}`; StuckPayment `{payment_id, rail, amount_paise, submitted_at, flagged_at, age_seconds}`
- SimulationConfig `{rail, mode, reason_code|null, transient_failure_rate}`; Dashboard `{date, rails[], status_counts, pending_refunds[], settlement_files[]}`

## Endpoints

### GET /health

Liveness and database check.

- **Auth/role:** none (public)
- **Rate limit:** none
- **Headers:** none
- **Params:** none
- **Request body:** none
- **Notes:** No headers required.
- **Success responses:**
  - `200` Health: OK
  - `503` Health: Database check failed (not the error envelope): {"status":"error","database":"error"}
- **Error responses:**
  - `500` `INTERNAL_ERROR`: unexpected failure

### GET /customers

List demo users for the picker.

- **Auth/role:** none (public)
- **Rate limit:** none
- **Headers:** none
- **Params:** none
- **Request body:** none
- **Notes:** No headers required.
- **Success responses:**
  - `200` CustomerList: All seeded users (cus_001..003, ops_001, adm_001) with id, name, role
- **Error responses:**
  - `500` `INTERNAL_ERROR`: unexpected failure

### POST /payments

Create a payment (idempotent).

- **Auth/role:** customer
- **Rate limit:** none
- **Headers:** `X-Role`, `X-Customer-Id` (customer), `Idempotency-Key` (required)
- **Params:** none
- **Request body:** CreatePaymentRequest
- **Notes:** Idempotency expiry: once 24 h (IDEMPOTENCY_TTL_SECONDS = 86400) have elapsed since the original payment's created_at, the (customer_id, key) slot is lazily released inside the create transaction and the same key creates a NEW payment (202) regardless of payload (hash not compared); the original payment is unchanged except idempotency_released_at. A replay never extends the window. Routing: 100..10,000,000 UPI; ..20,000,000 IMPS; ..50,000,000 NEFT; above RTGS.
- **Success responses:**
  - `202` Payment: New payment created in state CREATED; rail chosen by amount
  - `200` Payment: Replay: same (customer_id, key) and same payload within 24 h of the ORIGINAL payment's created_at (fixed window, not sliding). Returns the original payment. Header Idempotent-Replay: true
- **Error responses:**
  - `401` `UNAUTHENTICATED`: Missing or unknown X-Role, or invalid X-Customer-Id
  - `403` `FORBIDDEN`: Role not permitted
  - `409` `IDEMPOTENCY_KEY_CONFLICT`: Same key, different payload, within the 24 h window
  - `422` `AMOUNT_BELOW_MINIMUM`: amount_paise < 100 (fields[0].field = amount_paise)
  - `422` `VALIDATION_ERROR`: Missing/invalid Idempotency-Key (field Idempotency-Key), empty or >140 char beneficiary, non-integer amount_paise
  - `500` `INTERNAL_ERROR`: unexpected failure

Request:

```json
{
  "amount_paise": 10000050,
  "beneficiary": "Ravi Kumar"
}
```

Response:

```json
{
  "id": "pay_3f9a1c07b2de", "customer_id": "cus_001", "amount_paise": 10000050,
  "rail": "IMPS", "beneficiary": "Ravi Kumar", "state": "CREATED",
  "reason_code": null, "rail_reference": null, "refund": null,
  "created_at": "2026-10-04T09:30:00Z", "updated_at": "2026-10-04T09:30:00Z"
}
```

Error example (422):

```json
{"error":{"code":"AMOUNT_BELOW_MINIMUM","message":"Amount must be at least 100 paise (Rs 1)","fields":[{"field":"amount_paise","message":"Must be at least 100"}]}}
```

**Idempotency expiry (decision 7).** A replay within 24 hours of the ORIGINAL payment's `created_at` (a fixed window, not sliding; a replay does not extend it) returns `200` with the original payment and header `Idempotent-Replay: true`. A different payload for the same key inside that window returns `409 IDEMPOTENCY_KEY_CONFLICT`. After 24 hours the same `(customer_id, key)` creates a new payment (`202`) regardless of payload; the old payment is unchanged except its `idempotency_released_at`.

### GET /payments

List payments, newest first.

- **Auth/role:** customer, ops, admin
- **Rate limit:** none
- **Headers:** `X-Role`, `X-Customer-Id` (customer)
- **Params:** `state` (query); `customer_id` (query) Ops/admin only; ignored for customers (they always get their own)
- **Request body:** none
- **Success responses:**
  - `200` PaymentList: Customer: own payments. Ops/admin: all (optional customer_id filter). Cap 500.
- **Error responses:**
  - `401` `UNAUTHENTICATED`: Missing or unknown X-Role, or invalid X-Customer-Id
  - `422` `VALIDATION_ERROR`: Invalid state
  - `500` `INTERNAL_ERROR`: unexpected failure

### GET /payments/{id}

Payment detail with events and attempts.

- **Auth/role:** customer, ops, admin
- **Rate limit:** none
- **Headers:** `X-Role`, `X-Customer-Id` (customer)
- **Params:** `id` (path, required)
- **Request body:** none
- **Success responses:**
  - `200` PaymentDetail: Payment + events (chronological) + attempts
- **Error responses:**
  - `401` `UNAUTHENTICATED`: Missing or unknown X-Role, or invalid X-Customer-Id
  - `404` `NOT_FOUND`: Unknown id, or another customer's payment when role=customer
  - `500` `INTERNAL_ERROR`: unexpected failure

### POST /refunds

Request a full refund.

- **Auth/role:** customer
- **Rate limit:** none
- **Headers:** `X-Role`, `X-Customer-Id` (customer)
- **Params:** none
- **Request body:** CreateRefundRequest
- **Success responses:**
  - `201` Refund: state REQUESTED, amount_paise = payment amount, requested_by = customer id
- **Error responses:**
  - `401` `UNAUTHENTICATED`: Missing or unknown X-Role, or invalid X-Customer-Id
  - `403` `FORBIDDEN`: Role not permitted
  - `404` `NOT_FOUND`: Unknown payment or not the caller's
  - `422` `PAYMENT_NOT_REFUNDABLE`: Payment is CREATED, SUBMITTED or FAILED
  - `409` `REFUND_ALREADY_EXISTS`: A refund exists for the payment in any state
  - `422` `VALIDATION_ERROR`: payment_id missing
  - `500` `INTERNAL_ERROR`: unexpected failure

Request:

```json
{"payment_id": "pay_3f9a1c07b2de"}
```

Response:

```json
{"id":"rfd_8c1d2e4f5a6b","payment_id":"pay_3f9a1c07b2de","amount_paise":10000050,"state":"REQUESTED","requested_by":"cus_001","decided_by":null,"reason_code":null,"created_at":"2026-10-04T10:00:00Z","updated_at":"2026-10-04T10:00:00Z"}
```

### GET /refunds

List refunds.

- **Auth/role:** customer, ops, admin
- **Rate limit:** none
- **Headers:** `X-Role`, `X-Customer-Id` (customer)
- **Params:** `state` (query)
- **Request body:** none
- **Success responses:**
  - `200` RefundList: Customer: own (requested_by). Ops/admin: all. Cap 500.
- **Error responses:**
  - `401` `UNAUTHENTICATED`: Missing or unknown X-Role, or invalid X-Customer-Id
  - `422` `VALIDATION_ERROR`: Invalid state
  - `500` `INTERNAL_ERROR`: unexpected failure

### POST /refunds/{id}/approve

Approve and execute a refund.

- **Auth/role:** admin
- **Rate limit:** none
- **Headers:** `X-Role`, `X-Customer-Id` (customer)
- **Params:** `id` (path, required)
- **Request body:** none
- **Success responses:**
  - `200` Refund: Final state EXECUTED, or FAILED with reason_code when the reversal fails permanently; decided_by = admin id
- **Error responses:**
  - `401` `UNAUTHENTICATED`: Missing or unknown X-Role, or invalid X-Customer-Id
  - `403` `FORBIDDEN`: Role not permitted
  - `404` `NOT_FOUND`: Unknown refund
  - `409` `REFUND_ALREADY_DECIDED`: Refund is not REQUESTED
  - `500` `INTERNAL_ERROR`: unexpected failure

### POST /refunds/{id}/reject

Reject a refund.

- **Auth/role:** admin
- **Rate limit:** none
- **Headers:** `X-Role`, `X-Customer-Id` (customer)
- **Params:** `id` (path, required)
- **Request body:** none
- **Success responses:**
  - `200` Refund: state REJECTED, decided_by, reason_code REJECTED_BY_ADMIN; payment stays COMPLETED
- **Error responses:**
  - `401` `UNAUTHENTICATED`: Missing or unknown X-Role, or invalid X-Customer-Id
  - `403` `FORBIDDEN`: Role not permitted
  - `404` `NOT_FOUND`: Unknown refund
  - `409` `REFUND_ALREADY_DECIDED`: Refund is not REQUESTED
  - `500` `INTERNAL_ERROR`: unexpected failure

### POST /reconciliation/run

Generate statements and reconcile an IST date.

- **Auth/role:** ops, admin
- **Rate limit:** none
- **Headers:** `X-Role`, `X-Customer-Id` (customer)
- **Params:** none
- **Request body:** ReconRunRequest
- **Notes:** Idempotent: re-running adds no duplicate results.
- **Success responses:**
  - `200` ReconRunResponse: Counts per status
- **Error responses:**
  - `401` `UNAUTHENTICATED`: Missing or unknown X-Role, or invalid X-Customer-Id
  - `403` `FORBIDDEN`: Role not permitted
  - `422` `VALIDATION_ERROR`: Malformed or future statement_date
  - `500` `INTERNAL_ERROR`: unexpected failure

### GET /reconciliation/unmatched

Unresolved non-matched results.

- **Auth/role:** ops, admin
- **Rate limit:** none
- **Headers:** `X-Role`, `X-Customer-Id` (customer)
- **Params:** `status` (query) matched is accepted but always returns an empty list; `rail` (query); `statement_date` (query)
- **Request body:** none
- **Success responses:**
  - `200` ReconResultList: Results with resolved=false and status != matched
- **Error responses:**
  - `401` `UNAUTHENTICATED`: Missing or unknown X-Role, or invalid X-Customer-Id
  - `403` `FORBIDDEN`: Role not permitted
  - `422` `VALIDATION_ERROR`: Invalid filter
  - `500` `INTERNAL_ERROR`: unexpected failure

### POST /reconciliation/{id}/resolve

Resolve a result with a note.

- **Auth/role:** ops, admin
- **Rate limit:** none
- **Headers:** `X-Role`, `X-Customer-Id` (customer)
- **Params:** `id` (path, required)
- **Request body:** ResolveRequest
- **Notes:** Never changes payments or amounts.
- **Success responses:**
  - `200` ReconResult: resolved=true, note stored, resolved_by = caller id
- **Error responses:**
  - `401` `UNAUTHENTICATED`: Missing or unknown X-Role, or invalid X-Customer-Id
  - `403` `FORBIDDEN`: Role not permitted
  - `404` `NOT_FOUND`: Unknown result
  - `409` `RECON_ALREADY_RESOLVED`: Already resolved
  - `422` `VALIDATION_ERROR`: Empty/blank note, note > 500 chars, or result status is matched
  - `500` `INTERNAL_ERROR`: unexpected failure

### POST /settlement/run

Generate settlement file for a business date.

- **Auth/role:** admin
- **Rate limit:** none
- **Headers:** `X-Role`, `X-Customer-Id` (customer)
- **Params:** none
- **Request body:** SettlementRunRequest (body optional)
- **Notes:** business_date defaults to today IST. Never overwrites an existing file.
- **Success responses:**
  - `201` SettlementRunResponse: First run: primary file written
  - `200` SettlementRunResponse: Repeat run: follow-up written (file set) or no new file (file null, message says the primary exists)
- **Error responses:**
  - `401` `UNAUTHENTICATED`: Missing or unknown X-Role, or invalid X-Customer-Id
  - `403` `FORBIDDEN`: Role not permitted
  - `422` `VALIDATION_ERROR`: Malformed or future business_date
  - `500` `INTERNAL_ERROR`: unexpected failure

### GET /settlement/files

List settlement files.

- **Auth/role:** admin
- **Rate limit:** none
- **Headers:** `X-Role`, `X-Customer-Id` (customer)
- **Params:** `business_date` (query)
- **Request body:** none
- **Success responses:**
  - `200` SettlementFileList: Newest business_date first, then sequence
- **Error responses:**
  - `401` `UNAUTHENTICATED`: Missing or unknown X-Role, or invalid X-Customer-Id
  - `403` `FORBIDDEN`: Role not permitted
  - `500` `INTERNAL_ERROR`: unexpected failure

### GET /settlement/files/{id}

Download a settlement CSV.

- **Auth/role:** admin
- **Rate limit:** none
- **Headers:** `X-Role`, `X-Customer-Id` (customer)
- **Params:** `id` (path, required)
- **Request body:** none
- **Success responses:**
  - `200` text/csv: text/csv: header, data rows, footer lines '# row_count=N' and '# sha256=<hex>'. Content-Disposition: attachment; filename=<date>-<kind>.csv
- **Error responses:**
  - `401` `UNAUTHENTICATED`: Missing or unknown X-Role, or invalid X-Customer-Id
  - `403` `FORBIDDEN`: Role not permitted
  - `404` `NOT_FOUND`: Unknown id
  - `500` `INTERNAL_ERROR`: unexpected failure

### GET /dashboard/summary

Daily aggregates.

- **Auth/role:** admin
- **Rate limit:** none
- **Headers:** `X-Role`, `X-Customer-Id` (customer)
- **Params:** `date` (query) IST date, default today IST
- **Request body:** none
- **Success responses:**
  - `200` Dashboard: Always all four rails and four states; zeros when empty
- **Error responses:**
  - `401` `UNAUTHENTICATED`: Missing or unknown X-Role, or invalid X-Customer-Id
  - `403` `FORBIDDEN`: Role not permitted
  - `422` `VALIDATION_ERROR`: Malformed or future date
  - `500` `INTERNAL_ERROR`: unexpected failure

### GET /ops/stuck-payments

Payments stuck in SUBMITTED > 300 s.

- **Auth/role:** ops, admin
- **Rate limit:** none
- **Headers:** `X-Role`, `X-Customer-Id` (customer)
- **Params:** none
- **Request body:** none
- **Success responses:**
  - `200` StuckPaymentList: Runs detection first, then lists flagged SUBMITTED payments
- **Error responses:**
  - `401` `UNAUTHENTICATED`: Missing or unknown X-Role, or invalid X-Customer-Id
  - `403` `FORBIDDEN`: Role not permitted
  - `500` `INTERNAL_ERROR`: unexpected failure

### GET /admin/simulation

Config of all four rails.

- **Auth/role:** admin
- **Rate limit:** none
- **Headers:** `X-Role`, `X-Customer-Id` (customer)
- **Params:** none
- **Request body:** none
- **Success responses:**
  - `200` SimulationList: Default success for all rails
- **Error responses:**
  - `401` `UNAUTHENTICATED`: Missing or unknown X-Role, or invalid X-Customer-Id
  - `403` `FORBIDDEN`: Role not permitted
  - `500` `INTERNAL_ERROR`: unexpected failure

### PUT /admin/simulation/{rail}

Set mock rail behaviour.

- **Auth/role:** admin
- **Rate limit:** none
- **Headers:** `X-Role`, `X-Customer-Id` (customer)
- **Params:** `rail` (path, required)
- **Request body:** SimulationUpdate
- **Success responses:**
  - `200` SimulationConfig: Echo of stored config (in-memory; resets on restart)
- **Error responses:**
  - `401` `UNAUTHENTICATED`: Missing or unknown X-Role, or invalid X-Customer-Id
  - `403` `FORBIDDEN`: Role not permitted
  - `404` `NOT_FOUND`: Unknown rail
  - `422` `VALIDATION_ERROR`: permanent_failure without valid reason_code, transient without rate, or rate outside [0,1]
  - `500` `INTERNAL_ERROR`: unexpected failure

Request:

```json
{"mode":"permanent_failure","reason_code":"INSUFFICIENT_FUNDS"}
```

Response:

```json
{"rail":"UPI","mode":"permanent_failure","reason_code":"INSUFFICIENT_FUNDS","transient_failure_rate":0}
```
