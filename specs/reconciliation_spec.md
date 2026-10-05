# Reconciliation Spec

Parent: `specs/app_spec.md`. Matching rule in `service/matching.py`. Statements come from the same mock adapters; no CSV upload.

## Acceptance Criteria

### AC-06 Matching
- **Scenario 1: matched**
  - Given a COMPLETED payment and a rail statement entry with the same payment ID, rail reference and exact `amount_paise`
  - When reconciliation runs
  - Then the result is `matched`
- **Scenario 2: amount mismatch**
  - Given identical payment ID and reference but amounts differing by 1 paise
  - When reconciliation runs
  - Then the result is `amount_mismatch`
- **Scenario 3: unmatched internal**
  - Given a COMPLETED payment with no statement entry
  - When reconciliation runs
  - Then the result is `unmatched_internal`
- **Scenario 4: unmatched external**
  - Given a statement entry with no payment
  - When reconciliation runs
  - Then the result is `unmatched_external`
- **Scenario 5: seeded corpus**
  - Given the seeded test corpus
  - When reconciliation runs
  - Then 100% of seeded anomalies are flagged and nothing else

### AC-06 Idempotent runs
- Given reconciliation already ran for a date
- When it runs again
- Then results are not duplicated

### AC-10 Unmatched queue and resolution
- **Scenario 1: ops views the queue**
  - Given unmatched entries exist
  - When ops calls `GET /reconciliation/unmatched`
  - Then they are listed and can be filtered; a customer receives 403
- **Scenario 2: resolve with a note**
  - Given an unmatched entry
  - When ops resolves it with a note
  - Then it is marked resolved and no payment data is changed; a missing note returns 422
