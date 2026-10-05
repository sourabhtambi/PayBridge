# Routing Rule Evaluator

## Purpose
Evaluates payment amounts against routing rules and returns the correct rail.

## Rules
- Amount must be integer paise, never float
- UPI: 100 to 10,000,000 paise inclusive
- IMPS: 10,000,001 to 20,000,000 paise inclusive
- NEFT: 20,000,001 to 50,000,000 paise inclusive
- RTGS: 50,000,001 and above, no cap
- Below 100 paise: reject with AMOUNT_BELOW_MINIMUM
- No customer override of routing decision
