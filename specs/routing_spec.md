# Routing Spec

Parent: `specs/app_spec.md`. Rules live in `types/routing.py`. Amounts are integer paise; upper bounds are inclusive.

## Acceptance Criteria

### AC-03 Rail selection by amount
- **Scenario 1: band boundaries**
  - Given an amount in paise
  - When routing is applied
  - Then 100–10,000,000 → UPI; 10,000,001–20,000,000 → IMPS; 20,000,001–50,000,000 → NEFT; 50,000,001 and above → RTGS
- **Scenario 2: every amount maps to exactly one rail**
  - Given the amounts 10,000,000 and 10,000,001
  - When routed
  - Then they route to UPI and IMPS respectively
- **Scenario 3: below minimum**
  - Given an amount under 100 paise
  - When routing is requested
  - Then validation fails with `AMOUNT_BELOW_MINIMUM` and no rail is chosen
- **Scenario 4: no fallback**
  - Given a payment routed to a rail that fails permanently
  - When the failure is recorded
  - Then the payment becomes FAILED and is not re-routed to another rail

### AC-03 Routing decision is logged with reason
- Given a payment is routed
- When it is created
- Then the `PAYMENT_CREATED` event payload contains `rail` and `reason`, for example `amount 20000001 paise > 20000000 and <= 50000000: NEFT`

### AC-09 Routing decision is persisted
- Given a routing decision
- When it is made
- Then it is stored as an append-only `payment_events` row with timestamp
