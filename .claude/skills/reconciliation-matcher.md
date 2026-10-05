# Reconciliation Matcher

## Purpose
Matches outbound payments against inbound rail statement entries.

## Rules
- Match requires: payment_id + rail_reference + exact amount_paise
- Statuses: matched, unmatched_internal, unmatched_external, amount_mismatch
- Mismatches never block settlement file generation
- Ops resolves by adding a note — no auto-correction
- Unmatched entries appear in CSV with unmatched_flag=TRUE
