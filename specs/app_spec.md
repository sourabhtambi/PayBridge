# PayBridge Application Spec

## Overview
PayBridge is a payments routing, reconciliation and settlement hub consolidating UPI, NEFT, RTGS and IMPS behind one platform.

## Acceptance Criteria

### AC-01 Payment Initiation
Given a customer submits beneficiary, amount and narration
When the request is valid
Then the system assigns a payment_id, accepts an idempotency_key, and sets state to CREATED

### AC-02 Idempotency
Given a payment was created with idempotency_key X
When the same key is submitted again with the same payload
Then the original payment_id is returned without creating a duplicate

### AC-03 Rail Routing
Given a payment amount
When routing is applied
Then UPI for ≤ ₹1,00,000 | IMPS for ₹1,00,001–₹2,00,000 | NEFT for ₹2,00,001–₹5,00,000 | RTGS for > ₹5,00,000

### AC-04 Payment Lifecycle
Given a payment exists
When state transitions occur
Then only CREATED→SUBMITTED→COMPLETED/FAILED are valid; invalid transitions raise InvalidPaymentStateException

### AC-05 Retry on Failure
Given a rail adapter returns a transient failure
When the retry policy runs
Then payment is retried up to 5 times with exponential backoff; permanent failures set FAILED with reason code

### AC-06 Reconciliation
Given outbound payment records and inbound rail statements
When reconciliation runs
Then matched entries are marked matched; unmatched entries are flagged for ops review

### AC-07 Settlement File
Given all COMPLETED payments for the day
When the daily job runs at 23:59 IST
Then an append-only CSV is generated with matched/unmatched indicators

### AC-08 Refunds
Given a COMPLETED payment
When a customer requests a refund
Then a reverse entry is created linked to the original and state moves to REFUNDED

### AC-09 Audit Trail
Given any state transition or routing decision
When it occurs
Then it is persisted as an immutable PaymentEvent with timestamp and actor

### AC-10 Ops Dashboard
Given an ops/admin user
When they view the dashboard
Then they see daily volumes by rail and status, unmatched queue, and refund queue

## Feature Specs
- See specs/stories/ for per-feature Given-When-Then criteria
- See specs/brd/brd.md for full business requirements
