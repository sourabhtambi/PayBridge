# Run Settlement

## Command
/run-settlement

## Purpose
Triggers the daily settlement file generation for a given business date.

## Usage
/run-settlement [date]

## Steps
1. Call POST /settlement/run with the given date (defaults to today IST)
2. Verify the settlement CSV was created under data/settlements/
3. Check the file has a row count and SHA256 checksum
4. Confirm append-only — if file exists for date, a follow-up file is created
5. Report matched vs unmatched row counts

## Rules
- Date must be in YYYY-MM-DD format
- Business date is IST calendar day
- Primary file is never overwritten
- Late entries go to follow-up file
