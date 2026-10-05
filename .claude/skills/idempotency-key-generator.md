# Idempotency Key Generator

## Purpose
Generates and validates idempotency keys for payment creation.

## Rules
- Keys are UUID v4 format
- Scoped per customer_id
- Same key + same payload = return original payment (200)
- Same key + different payload = reject with 409
- Keys expire after 24 hours and can be reused
- Concurrent requests with same key create exactly one payment
