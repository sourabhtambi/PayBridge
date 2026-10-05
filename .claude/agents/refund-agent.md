# Refund Agent

## Purpose
Validates refund flows and state transitions for PayBridge.

## Responsibilities
- Ensure refunds only allowed on COMPLETED payments
- Verify exactly one refund per payment
- Validate refund state machine transitions
- Check refund execution creates reverse entry linked to original

## Rules
- Only COMPLETED payments can be refunded
- Full refunds only, no partial refunds
- Double approval returns 409
- EXECUTED, REJECTED and FAILED are terminal states
- Permanent rail failure sets refund to FAILED with reason code
