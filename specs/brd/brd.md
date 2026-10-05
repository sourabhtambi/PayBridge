# PayBridge Business Requirements Document

Status: APPROVED by the user (2026-10-04). Proceed to `/spec`.

## 1. Executive Summary

PayBridge is a payments routing, reconciliation and settlement hub for a simulated bank. It places UPI, NEFT, RTGS and IMPS behind one platform. The platform routes each payment to exactly one rail by amount, guarantees idempotent payment creation, retries transient rail errors, supports refunds, reconciles payments against rail statements, and generates a daily settlement CSV.

This is a learning and demo project simulating a bank's payments operations team. All rails are mock adapters. Authentication is a header-based role switch. Account balances are out of scope: PayBridge is a routing and settlement hub, not a core banking system.

Chosen approach: a payment state machine with a persisted outbox and background worker (Option B), plus an append-only `payment_events` audit table.

## 2. Problem Statement

A bank needs to consolidate several payment rails behind one hub. Without it:
- Reconciliation across rails is manual.
- Duplicate payments are a risk.
- There is no single view of payment status.
- Settlement files are produced by hand and arrive late.

## 3. Target Users

| Persona | Technical level | Needs |
|---|---|---|
| Customer | Non-technical | Initiate payments, track status, request refunds |
| Ops analyst | Moderate | Run reconciliation, work the unmatched queue, review stuck payments |
| Admin | Moderate | View daily volumes, approve or reject refunds, view settlement reports, control mock rail simulation |

## 4. Success Metrics (90 days)

| # | Metric | Measurable target |
|---|---|---|
| M1 | Zero duplicate payments | An automated test replays the same idempotency key N times concurrently and sequentially, and exactly one payment results |
| M2 | Rails route correctly | 100% of payments in a boundary-value test suite route to the rail in section 5.3 |
| M3 | Daily settlement file generated automatically | A scheduled job generates the file by the 23:59 IST cutoff for the business date |
| M4 | Reconciliation flags all unmatched entries | 100% of unmatched entries flagged, measured against a seeded test corpus |
| M5 | Refund flow works end to end | Request, approval, mock-rail reversal and EXECUTED state verified by an end-to-end test |

M1, M3 and M4 use the bracketed default definitions agreed in the interview (see Assumptions).

## 5. Scope

### 5.1 In scope (v1)
- Role switch (Customer, Ops, Admin) with a customer picker. No real login.
- Payment initiation, status tracking, automatic rail routing (no customer override).
- Idempotency keys on payment creation.
- Retry of transient rail errors.
- Refund request, approval and execution (full refunds only).
- Reconciliation with an unmatched-entries queue.
- Daily settlement CSV and an on-demand trigger.
- Admin dashboard (volumes, refund queue, settlement reports).
- Stuck-payment flagging.
- Admin mock-rail simulation controls.

### 5.2 Out of scope (v1)
- Real bank or NPCI integration.
- Multi-currency.
- KYC or fraud checks.
- Email or SMS notifications.
- Partial refunds.
- Any scheduler more complex than a simple daily job.
- Multi-tenancy.
- Account balances, debit and credit logic, and any managed beneficiary list.
- CSV upload of rail statements.
- Regulatory compliance (PCI-DSS, RBI).

### 5.3 Routing table
Money is stored as integer paise (1 rupee = 100 paise). The user supplied the table in rupees. This BRD defines the bands in paise so that no fractional amount falls between bands. **Interpretation for the approval gate:** the upper bound of each band is inclusive, the lower bound of each band after UPI is exclusive (the previous band's upper bound), and every integer paise amount maps to exactly one rail.

| Rail | Paise range | Rupee equivalent |
|---|---|---|
| UPI | 100 to 10,000,000 inclusive | Rs 1.00 to Rs 1,00,000.00 |
| IMPS | 10,000,001 to 20,000,000 inclusive | above Rs 1,00,000.00 to Rs 2,00,000.00 |
| NEFT | 20,000,001 to 50,000,000 inclusive | above Rs 2,00,000.00 to Rs 5,00,000.00 |
| RTGS | 50,000,001 and above | above Rs 5,00,000.00, no cap |

- Amounts of 99 paise or less, zero and negatives are rejected with a validation error (422). There is no maximum.
- Example: Rs 1,00,000.50 is 10,000,050 paise and routes to IMPS.
- No precedence rule is needed. Each amount falls into exactly one rail.
- Fallback: a permanent rail failure sets the payment to FAILED with a reason code. There is no automatic fallback to another rail.
- Discrepancy flagged: earlier in the interview RTGS was mentioned as starting at Rs 2 lakh. The user then gave this explicit table, in which RTGS starts above Rs 5 lakh. This BRD uses the explicit table. The user referred to "the PDF" for these conventions. No PDF exists in the workspace, so the table above rests on the user's stated answers alone.

## 6. MVP Definition

The smallest deployable slice: initiate a payment, route it, apply idempotency, and show its status.

MVP includes:
- Role switch and customer picker.
- `POST /payments`, `GET /payments/{id}`, `GET /payments`.
- Routing, idempotency, the outbox, a minimal worker with mock adapters in success mode, and `payment_events`.
- Customer screens: new payment form with rail preview, payments list, payment detail.
- `GET /health`.

Later increments, in order: retry and failure simulation, refunds, reconciliation, settlement, admin dashboard.

## 7. Alternatives Considered

| Option | Description | Verdict |
|---|---|---|
| A. Synchronous in-process pipeline | The request validates, routes and calls the mock rail inline | Rejected. It blocks requests on slow rails, cannot do retry with backoff, can leave a payment in an unknown state after a crash, and poorly simulates asynchronous rail acknowledgement |
| B. State machine with persisted outbox and background worker | The API writes the payment and an outbox row in one transaction and returns 202. A worker submits to the rail | **Chosen.** It matches real-world behaviour, makes idempotency and retry testable, survives crashes, and fits the layered architecture |
| C. Event-sourced ledger | An immutable event log with projections for state, reconciliation and settlement | Rejected. Projection, replay and versioning complexity is too heavy for the MVP. Option B's `payment_events` table captures most of the audit benefit |

## 8. Technical Architecture

### 8.1 Stack
Fixed by `project-manifest.json`.
- Backend: Python 3.12, FastAPI, uv, ruff, mypy, pytest.
- Frontend: React, TypeScript, Vite, ESLint, tsc, vitest.
- Database: SQLite in WAL mode.
- Deployment: local only. Backend on port 8000, frontend on port 3000.
- Layering: Types, Config, Repository, Service, API, UI, with one-way dependencies.
- Money: integer paise only, never floats.

### 8.2 Payment lifecycle
- Payment states: CREATED, SUBMITTED, COMPLETED, FAILED.
- Refund states: REQUESTED, APPROVED, EXECUTED, REJECTED, FAILED.
- `POST /payments` validates the request, checks the idempotency key, routes the payment, writes the Payment (CREATED) and an OutboxMessage in one SQLite transaction, and returns 202.
- An in-process asyncio worker polls the outbox and submits to the mock rail adapter. It records each PaymentAttempt and appends a PaymentEvent for every transition.
- Retries: transient errors retry up to 5 attempts with a 1 second base delay that doubles each time. Exhausting the retries sets FAILED with a reason code. Permanent errors set FAILED immediately.
- Crash recovery: on restart the worker resumes unsent or in-flight outbox rows. The mock rail deduplicates on payment ID, which simulates real rail idempotency.
- Stuck detection: a payment in SUBMITTED for more than 5 minutes is flagged for ops review.
- Insufficient funds is modelled as a permanent failure reason code (for example `INSUFFICIENT_FUNDS`) returned by the mock adapter.

### 8.3 Idempotency
- Unique constraint on `(customer_id, idempotency_key)`, with a stored request hash.
- Same key with the same payload returns the original payment (200).
- Same key with a different payload returns 409.
- Keys are scoped per customer and expire after 24 hours (assumption).
- Two simultaneous requests with the same key create exactly one payment. The other receives the replay.

### 8.4 Refunds
- Only COMPLETED payments can be refunded, and only in full.
- At most one refund per payment (unique constraint). A second request returns 409.
- Admin approves or rejects. A double approval returns 409.
- Execution is a recorded state transition plus a rail-level reversal through the mock adapter. A permanent adapter failure sets the refund to FAILED with a reason code. There is no account credit.

### 8.5 Reconciliation
- A match requires all three of payment ID, rail reference, and exact `amount_paise`.
- Statuses: `matched`, `unmatched_internal` (we have it, the rail does not), `unmatched_external` (the rail has it, we do not), `amount_mismatch`.
- Ops resolves an entry by adding a note and marking it resolved. Nothing is auto-corrected.
- Rail statements come from the same mock adapters. There is no CSV upload.

### 8.6 Settlement
- One combined CSV per business date. The business date is the IST (Asia/Kolkata) calendar day. The daily job runs at 23:59 IST. An admin endpoint triggers a run on demand.
- Each row carries a matched or unmatched indicator. **Interpretation for the approval gate:** mismatched and unmatched rows are included in the file with an unmatched flag, and they do not block the file. The user's wording ("stay out of settlement, they appear with unmatched flag instead of blocking the file") was internally contradictory, and this is the reading that fits "appear with unmatched flag".
- The file includes a row count and checksum.
- The file is append-only once written. A second run for the same date refuses to overwrite the primary file. Late entries go to a separate, also append-only, follow-up file.

### 8.7 Role switch
- The role comes from the `X-Role` and `X-Customer-Id` headers, set by a UI selector. This is demo-only and not a security control.
- Customer: own payments, and refund requests.
- Ops: reconciliation, the unmatched queue and stuck payments.
- Admin: dashboard, refund approval, settlement and simulation controls.

### 8.8 API surface (indicative, finalised in `/design`)
| Area | Endpoints |
|---|---|
| Payments | `POST /payments` (Idempotency-Key header; 202 new, 200 replay, 409 payload mismatch, 422 validation), `GET /payments/{id}` (with events and attempts), `GET /payments` |
| Refunds | `POST /refunds`, `GET /refunds`, `POST /refunds/{id}/approve`, `POST /refunds/{id}/reject` |
| Reconciliation | `POST /reconciliation/run`, `GET /reconciliation/unmatched`, `POST /reconciliation/{id}/resolve` |
| Settlement | `POST /settlement/run`, `GET /settlement/files`, `GET /settlement/files/{id}` |
| Dashboard | `GET /dashboard/summary` |
| Operations | `GET /health` |
| Admin simulation | Endpoints to set mock rail behaviour (success, permanent failure with reason code, transient failure rate) |

`GET /accounts` was removed with the Account entity.

### 8.9 Non-functional requirements
NFR numbering is the planner's. The user referred to "NFR-03" for log masking, and that is the number used below.

| ID | Requirement |
|---|---|
| NFR-01 | `POST /payments` p95 latency is 300 ms or less, because it only writes and enqueues |
| NFR-02 | Throughput of at least 20 payments per second on a laptop (SQLite WAL, single worker) |
| NFR-03 | Beneficiary name and account numbers are masked in all logs |
| NFR-04 | Money is integer paise everywhere. Conversion to and from rupees happens only at the API boundary or in the UI display layer |
| NFR-05 | Every state transition appends a PaymentEvent. The audit trail is `payment_events` plus `requested_by` and `decided_by` |
| NFR-06 | The business date uses IST (Asia/Kolkata) |
| NFR-07 | WCAG 2.1 AA for the UI (section 12) |
| NFR-08 | Code standards per `CLAUDE.md`: TDD, 80% coverage floor, functions under 50 lines, files under 300 lines, static typing with zero `any` |

## 9. Data Model Overview

| Entity | Key fields |
|---|---|
| Customer | id, name, role (customer, ops, admin) |
| Payment | id, customer_id, idempotency_key, request_hash, amount_paise, rail, beneficiary (free text), state, reason_code, created_at |
| PaymentAttempt | id, payment_id, attempt_no, outcome (success, transient, permanent), error_code, at |
| OutboxMessage | id, payment_id, status, next_attempt_at, attempts |
| PaymentEvent | append-only: id, payment_id, type, payload, at |
| Refund | id, payment_id (unique), amount_paise, state, requested_by, decided_by, reason_code |
| RailStatementEntry | id, rail, payment_ref, amount_paise, status, statement_date |
| ReconciliationResult | id, payment_id (nullable), statement_entry_id (nullable), status, resolved, resolution_note |
| SettlementFile | id, business_date, kind (primary or followup), path, row_count, checksum, written_at |

The Account entity, `balance_paise` and all debit and credit logic are removed. Rails are configuration in the Config layer, not a table.

## 10. External Integrations

None. All four rails (UPI, NEFT, RTGS, IMPS) are in-process mock adapters with configurable success, permanent failure and transient-error responses. Reconciliation statements are generated by the same mocks.

## 11. Edge Cases and Constraints

| Scenario | Behaviour |
|---|---|
| Rail returns a permanent failure | Payment goes to FAILED with a reason code. Visible in the customer UI, ops queue and admin dashboard. No notifications |
| Transient error | Retried up to 5 times with doubling backoff, then FAILED |
| Stuck payment | SUBMITTED for more than 5 minutes is flagged for ops review |
| Crash between database write and rail call | The durable outbox lets the worker resume. The mock rail deduplicates on payment ID |
| Duplicate submission (client retry) | Same key and payload returns the original payment. Different payload returns 409 |
| Concurrent same-key requests | Exactly one payment is created. The other gets a replay |
| Double refund approval | 409 |
| Second refund request for a payment | 409 |
| Refund requested for a non-COMPLETED payment | Rejected |
| Reconciliation mismatch | Appears in the unmatched queue. Does not block settlement. Included in the CSV with an unmatched flag |
| Settlement run twice for one date | Primary file is not overwritten. Late entries go to a follow-up file |
| Timezone or cutoff error | Business date is the IST calendar day. Cutoff 23:59 IST |

Constraints:
- No uptime, rate-limit or budget requirements.
- The data is simulated financial data. PCI-DSS and RBI standards are out of scope. Log masking is NFR-03.

## 12. UI Context

Style reference: clean and professional, like a modern banking dashboard. No mockups or brand colours were supplied. The ui-designer agent may invent design tokens in `/design`. `calibration-profile.json` sets the design-score threshold at 8.

### 12.1 Screens
- **Role switcher:** header selector for Customer, Ops and Admin, plus a customer picker.
- **Customer:**
  - New payment form: amount in rupees, beneficiary free text, auto-generated idempotency key. It shows the rail that will be used as the customer types the amount. There is no override.
  - My payments list with status and reason code.
  - Payment detail with the event timeline and attempts.
  - Refund request button on COMPLETED payments.
- **Ops:** reconciliation run and results, unmatched-entries queue with resolve-with-note, stuck-payments list.
- **Admin:**
  - Dashboard: daily volumes per rail, status breakdown, refund queue with approve and reject, settlement reports.
  - Settlement file list and download, plus a run-now trigger.
  - Mock rail simulation controls.

### 12.2 Behaviour
- Devices: desktop-first for ops and admin. Responsive down to mobile for customer screens.
- Accessibility: WCAG 2.1 AA. Keyboard navigation, labelled form fields, status conveyed by text and not by colour alone, sufficient contrast.
- Status updates: poll every 2 seconds while a payment is in a non-terminal state (CREATED or SUBMITTED). No websockets.
- Money display: rupees with Indian digit grouping (for example Rs 1,00,000.50). Convert to and from paise only at the API boundary.

### 12.3 Empty, loading and error states
| Screen | Empty | Loading | Error |
|---|---|---|---|
| Payments list | "No payments yet" with a link to the new payment form | Skeleton rows | Retry banner with the failure message |
| New payment form | n/a | Submit button disabled with a progress label | 422 shows field-level messages (amount below Rs 1, zero or negative amount). 409 shows: "This request was already submitted with different details. Start a new payment." Replay (200) shows: "This payment was already created. Showing the original." and navigates to it |
| Payment detail | n/a | Skeleton timeline | Not-found message and a back link. FAILED shows the reason code as text |
| Unmatched queue | "Nothing to reconcile" | Skeleton rows | Retry banner. Resolving without a note shows a field error |
| Refund queue | "No refunds pending" | Skeleton rows | 409 on double approval shows: "This refund was already decided" |
| Refund request | n/a | Button disabled | 409 shows: "A refund was already requested for this payment" |
| Dashboard | Zero-value tiles with "No activity for this date" | Skeleton tiles | Per-tile retry |
| Settlement files | "No settlement files yet" | Skeleton rows | A repeated run shows: "Primary file for this date already exists. Late entries were written to a follow-up file." |
| Stuck payments | "No stuck payments" | Skeleton rows | Retry banner |

## 13. Open Questions

None blocking. Items for the approver to check:
1. The paise interpretation of the routing table (section 5.3), including rejection of 1 to 99 paise.
2. RTGS starting above Rs 5 lakh, not the earlier-mentioned Rs 2 lakh.
3. The settlement reading: mismatched and unmatched rows are included with an unmatched flag (section 8.6).
4. The NFR numbering (planner's own, with log masking as NFR-03).
5. The user's "PDF" reference for routing conventions could not be located. The table is based on the user's stated answers.

## Assumptions

1. Idempotency keys expire after 24 hours. No expiry preference was given.
2. Amounts of 1 to 99 paise are rejected as below the Rs 1 minimum.
3. Success metric definitions use the planner's bracketed defaults: M1 by automated replay test, M4 against a seeded test corpus, M3 by a daily job at the cutoff.
4. Retry defaults: 5 attempts, 1 second base delay, doubling each time.
5. The stuck threshold is 5 minutes in SUBMITTED.
6. The settlement cutoff is 23:59 IST and the business date is the IST calendar day.
7. The beneficiary is free text. There is no managed beneficiary list.
8. Performance targets (NFR-01, NFR-02) are modest laptop-level demo figures.
9. The role switch uses `X-Role` and `X-Customer-Id` headers and is not a security control.
10. Refunds are full refunds of COMPLETED payments, one per payment.
11. Reconciliation entries are resolved by note and flag only. There is no auto-correction.

## Future Considerations (out of scope)
Partial refunds, notifications, a managed beneficiary list, real rail integration, multi-currency, KYC and fraud checks, websockets for status updates, and fallback to another rail on permanent failure.
