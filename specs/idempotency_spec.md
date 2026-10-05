# Idempotency Spec

Parent: `specs/app_spec.md`. Uniqueness is on `(customer_id, idempotency_key)` with a stored request hash.

## Acceptance Criteria

### AC-02 Replay returns the original payment
- **Scenario 1: same key, same payload**
  - Given a payment created with key X
  - When the same customer submits key X with the same payload
  - Then the response is 200 with the original `payment_id` and no new payment row exists
- **Scenario 2: same key, different payload**
  - Given a payment created with key X
  - When key X is submitted with a different amount or beneficiary
  - Then the response is 409 `IDEMPOTENCY_KEY_CONFLICT` and nothing changes
- **Scenario 3: concurrent submissions**
  - Given two simultaneous requests with the same key
  - When both are processed
  - Then exactly one payment is created and the other receives the replay
- **Scenario 4: scope per customer**
  - Given two different customers using the same key string
  - When each submits
  - Then two separate payments are created
- **Scenario 5: expiry**
  - Given a key older than 24 hours
  - When it is submitted again
  - Then its uniqueness is released and a new payment is created
- **Scenario 6: database guarantee**
  - Given a direct insert of a second active payment with the same customer and key
  - When the insert runs
  - Then the database rejects it (partial unique index)
