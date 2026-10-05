# Settlement Spec

Parent: `specs/app_spec.md`. One CSV per IST business date. Daily job at 23:59 IST; admin can trigger `POST /settlement/run`.

## Acceptance Criteria

### AC-07 Daily file generation
- **Scenario 1: contents**
  - Given COMPLETED payments within the IST calendar day
  - When the daily job runs
  - Then one CSV row per payment is written with a matched or unmatched indicator, plus a row count and checksum footer
- **Scenario 2: unmatched rows**
  - Given a payment that failed reconciliation
  - When the file is generated
  - Then it is included with an unmatched flag and does not block the file
- **Scenario 3: empty day**
  - Given no COMPLETED payments for the date
  - When the job runs
  - Then an empty primary file is still written

### AC-07 Append-only and immutable
- **Scenario 1: no overwrite**
  - Given a primary file already exists for the date
  - When a second run is triggered
  - Then the primary file is unchanged and late entries go to a separate follow-up file
- **Scenario 2: write-once**
  - Given an existing file path
  - When a write is attempted
  - Then it is refused, and the database rejects UPDATE and DELETE on `settlement_files`

### AC-07 Schedule
- Given the current time in IST
- When the next run is computed
- Then it is 23:59 IST, and the scheduler fires at most once per day

### AC-10 Admin access
- Given an admin
- When they call `GET /settlement/files` or download a file
- Then files are listed; ops and customers receive 403
