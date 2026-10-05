# Payment Initiation Spec

Parent: `specs/app_spec.md`. Covers `POST /payments`, `GET /payments`, `GET /payments/{id}`.

State naming: PDF PENDING = CREATED; PDF SETTLED = COMPLETED.

## Acceptance Criteria

### AC-01 Customer initiates a payment
- **Scenario 1: valid request**
  - Given a customer with a valid `X-Customer-Id`
  - When they `POST /payments` with beneficiary, `amount_paise` ≥ 100 and an `Idempotency-Key`
  - Then the response is 202 with a new `payment_id`, state `CREATED`, and a routed rail
- **Scenario 2: invalid amount**
  - Given a customer
  - When they submit an amount of 99 paise or less, zero, or negative
  - Then the response is 422 with `AMOUNT_BELOW_MINIMUM` and nothing is persisted
- **Scenario 3: wrong role**
  - Given an ops or admin user
  - When they `POST /payments`
  - Then the response is 403

### AC-09 Creation is audited
- Given a payment is created
- When the transaction commits
- Then a `PAYMENT_CREATED` event with timestamp is appended to `payment_events` in the same transaction as the payment and outbox row
