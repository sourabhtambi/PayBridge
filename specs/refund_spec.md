# Refund Spec

Parent: `specs/app_spec.md`. Full refunds of COMPLETED payments only; one refund per payment. Refund states: REQUESTED → APPROVED → EXECUTED, or REJECTED / FAILED.

## Acceptance Criteria

### AC-08 Customer requests a refund
- **Scenario 1: request**
  - Given a customer's own COMPLETED payment
  - When they `POST /refunds` with its `payment_id`
  - Then a refund in REQUESTED is created, linked to the original payment, with the full amount
- **Scenario 2: not refundable**
  - Given a payment that is CREATED, SUBMITTED or FAILED
  - When a refund is requested
  - Then the response is 422
- **Scenario 3: duplicate**
  - Given a payment that already has a refund
  - When a second refund is requested
  - Then the response is 409

### AC-08 Execution moves the payment to REFUNDED
- **Scenario 1: approve**
  - Given a REQUESTED refund
  - When an admin approves it and the rail reversal succeeds
  - Then the refund is EXECUTED and the original payment moves COMPLETED → REFUNDED
- **Scenario 2: permanent reversal failure**
  - Given the rail reversal fails permanently
  - When the admin approves
  - Then the refund is FAILED with a reason code and the payment stays COMPLETED
- **Scenario 3: reject**
  - Given a REQUESTED refund
  - When an admin rejects it
  - Then it is REJECTED with `REJECTED_BY_ADMIN` and the payment stays COMPLETED
- **Scenario 4: double decision**
  - Given an already decided refund
  - When approve or reject is called again
  - Then the response is 409

### AC-04 Refund state rules
- Given a payment in COMPLETED
- When moving to REFUNDED
- Then it is the only allowed exit from COMPLETED; any other invalid transition raises `InvalidPaymentStateException`

### AC-09 Refund is audited
- Given a refund request, approval, rejection or execution
- When it happens
- Then `REFUND_REQUESTED`, `REFUND_APPROVED`, `REFUND_REJECTED` or `REFUND_EXECUTED` is appended to `payment_events`, followed by `PAYMENT_REFUNDED` when the payment moves to REFUNDED

### AC-10 Refund queue
- Given an admin or ops user
- When they `GET /refunds` or open the dashboard
- Then pending (REQUESTED) refunds are listed; a customer sees only their own
