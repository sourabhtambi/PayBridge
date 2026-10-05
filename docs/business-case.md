# PayBridge Business Case

## Problem
Banks managing multiple payment rails (UPI, NEFT, RTGS, IMPS) face manual reconciliation, duplicate payment risks, no unified status view, and delayed settlement files produced by hand.

## Target Users
- **Customers**: Initiate payments, track status, request refunds
- **Ops Analysts**: Run reconciliation, manage unmatched entries, review stuck payments
- **Admins**: View volumes, approve refunds, trigger settlement, control simulation

## Value Proposition
PayBridge consolidates all payment rails behind one hub with automatic routing, idempotent creation, retry handling, reconciliation, and daily settlement — eliminating manual work and duplicate payment risk.

## Domain Rules
1. Routing: UPI ≤ ₹1,00,000 | IMPS ₹1,00,001–₹2,00,000 | NEFT ₹2,00,001–₹5,00,000 | RTGS > ₹5,00,000
2. Idempotency: same key + same payload = original payment returned; same key + different payload = 409
3. Retry: transient failures retry up to 5 times with exponential backoff (1s base, doubling)
4. Settlement: append-only CSV generated at 23:59 IST; second run creates follow-up file
5. Refunds: full refunds only on COMPLETED payments; one refund per payment
6. Money: always stored as integer paise; never floating point

## Success Metrics
- Zero duplicate payments
- 100% correct rail routing
- Daily settlement file by 23:59 IST
- All unmatched reconciliation entries flagged
- Refund flow verified end to end
