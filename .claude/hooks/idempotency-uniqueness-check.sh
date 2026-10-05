#!/bin/bash
# Idempotency Uniqueness Check
# Blocks any code that bypasses the idempotency check on payment creation

echo "Running idempotency uniqueness check..."

# Check that create_payment always goes through idempotency check
if grep -r "INSERT INTO payments" backend/src --include="*.py" | grep -v "idempotency"; then
  echo "ERROR: Payment insert found without idempotency check"
  exit 1
fi

echo "Idempotency check passed"
exit 0
