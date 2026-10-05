#!/bin/bash
# Amount Precision Check
# Blocks any floating point usage for payment amounts

echo "Running amount precision check..."

# Check for float usage in payment amounts
if grep -r "float\|decimal\|0\." backend/src --include="*.py" | grep -i "amount" | grep -v "paise\|#\|test"; then
  echo "ERROR: Floating point detected in amount handling"
  exit 1
fi

echo "Amount precision check passed"
exit 0
