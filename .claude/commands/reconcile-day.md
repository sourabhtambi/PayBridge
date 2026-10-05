# Reconcile Day

## Command
/reconcile-day

## Purpose
Runs reconciliation for a given business date and reports unmatched entries.

## Usage
/reconcile-day [date]

## Steps
1. Call POST /reconciliation/run for the given date
2. Fetch GET /reconciliation/unmatched to list unmatched entries
3. Report counts by status: matched, unmatched_internal, unmatched_external, amount_mismatch
4. Flag any entries needing ops review
5. Confirm mismatches do not block settlement

## Rules
- Ops must resolve entries manually with a note
- No auto-correction of data
- Unmatched entries appear in settlement CSV with unmatched_flag=TRUE
