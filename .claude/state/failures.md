# Failure Log
<!-- Append-only. Used for pattern detection → learned rules extraction. -->
<!-- When 2+ entries share the same Category, extract a Learned Rule to .claude/state/learned-rules.md -->

<!-- ENTRY FORMAT (copy this for each new failure):

## Group {ID} — Failure #{N}
- **Date:** {ISO 8601}
- **Category:** {lint_format | type_error | test_failure | import_error | coverage_drop | api_check_fail | playwright_fail | design_score_low | docker_fail | architecture_drift}
- **Story:** {story ID}
- **Attempt 1:**
  - Error: {error message with file:line if available}
  - Fix: {what was tried}
  - Result: FAIL — {why it failed}
- **Attempt 2:**
  - Error: {error message}
  - Fix: {what was tried}
  - Result: FAIL — {why it failed}
- **Attempt 3:**
  - Error: {error message}
  - Fix: {what was tried}
  - Result: FAIL — 3 attempts exhausted
- **Escalation:** User notified. Marked BLOCKED. Skipped to next group.
- **Pattern:** {describe the recurring pattern if visible}

-->

## Group D — Failure #1
- **Date:** 2026-10-04
- **Category:** architecture_drift (init.sh startup bug; index.html skip link missing per contract wording)
- **Story:** E1-S4
- **Attempt:** 1 of 3
- **Detail:** init.sh `(cd backend && uv run ... & echo $! > ../.run/backend.pid)` backgrounds the whole list so echo runs from repo root; init.sh exits 1. Skip link rendered by React, not index.html. D-PW-01 ArrowDown on <select> is a macOS Chromium platform artifact (accepted, not a defect).
