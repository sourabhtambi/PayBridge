# Post-Mortem: Idempotency Key Expiry Design

## Date
2026-10-04

## Summary
During the /design phase, the idempotency expiry mechanism was undefined. A plain unique index on the payment row would permanently block key reuse, which contradicted the 24-hour expiry requirement.

## Timeline
- /brd: idempotency keys expire after 24 hours — agreed
- /design: agent flagged that a unique index alone would block reuse permanently
- Resolution: added idempotency_released_at column with a partial unique index

## Root Cause
The BRD specified 24-hour expiry but did not specify the release mechanism. The design agent caught this gap before code generation.

## Resolution
- Added idempotency_released_at column to payments table
- Partial unique index: unique on (customer_id, idempotency_key) where idempotency_released_at IS NULL
- Release happens lazily inside the create transaction — no background sweeper needed
- F028 spec updated to reflect the new column

## Lesson Learned
Expiry requirements need a release mechanism defined at design time, not just a TTL value. This is now encoded in the idempotency-key-generator skill.

## Environment-First Resolution
Issue was caught during /design review before any code was written. No rollback needed. Spec updated first, then code generated from updated spec — following Spec-Is-Truth rule.
