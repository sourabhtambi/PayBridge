# Routing Agent

## Purpose
Validates and enforces payment rail routing rules for PayBridge.

## Responsibilities
- Verify routing decisions follow configured rail bands
- Ensure amounts are integer paise with no floating point
- Validate routing decisions are logged as PaymentEvents
- Check invalid amounts are rejected with correct error codes

## Rules
- UPI: 100 to 10,000,000 paise inclusive
- IMPS: 10,000,001 to 20,000,000 paise inclusive
- NEFT: 20,000,001 to 50,000,000 paise inclusive
- RTGS: 50,000,001 and above
- Amounts below 100 paise rejected with AMOUNT_BELOW_MINIMUM
- No fallback to another rail on permanent failure
