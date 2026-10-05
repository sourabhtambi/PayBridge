# Rail Adapters Spec

Parent: `specs/app_spec.md`. Four in-process mock adapters (UPI, IMPS, NEFT, RTGS) driven by an outbox worker. Simulation is set via `PUT /admin/simulation/{rail}` (admin only).

## Acceptance Criteria

### AC-05 Transient failures are retried
- **Scenario 1: retry then success**
  - Given an adapter that returns a transient error then succeeds
  - When the worker processes the payment
  - Then it is retried with exponential backoff (1s base, doubling) and ends COMPLETED
- **Scenario 2: retries exhausted**
  - Given an adapter that is always transient
  - When 5 attempts have failed
  - Then the payment is FAILED with reason code `RETRIES_EXHAUSTED`

### AC-05 Permanent failures fail immediately
- Given an adapter in `permanent_failure` mode with a reason code
- When the worker submits the payment
- Then it is FAILED on the first attempt with that reason code and no retry

### AC-04 Lifecycle is enforced
- **Scenario 1: valid path**
  - Given a payment in CREATED
  - When the worker submits it and the rail succeeds
  - Then it moves CREATED → SUBMITTED → COMPLETED
- **Scenario 2: invalid transition**
  - Given a payment in COMPLETED or FAILED
  - When a move to SUBMITTED or COMPLETED is attempted
  - Then `InvalidPaymentStateException` is raised

### AC-05 Crash recovery
- Given a crash after the rail accepted a payment
- When the worker restarts
- Then the outbox row is resumed and the rail deduplicates on payment ID, so the payment completes exactly once

### AC-09 Attempts are audited
- Given each submission attempt
- When it finishes
- Then a `payment_attempts` row and a `payment_events` row are written
