# Evaluator Report - Group A (E1-S1, types and config layer)

Date: 2026-10-05
VERDICT: FAIL (F004 only, re-check: wrapper signature does not match the literal spec step). F001, F002, F003, F005 PASS.

Mode: local, unit-level (no HTTP/UI surface, so no API, Playwright or design layers). Single pass, no production code edited, no git operations.

## Tool results
- pytest -q --cov: 55 passed. Coverage 96.55% (floor 80%). Only gap: types/ports.py 0% (Protocol declarations, nothing executable).
- Contract command (4 test files only): 48 passed. Note: it exits non-zero in this repo because pytest-cov's fail-under (80%) is applied to the 4-file subset (51%). The tests themselves pass. Contract command should add --no-cov.
- ruff check: pass. ruff format --check: 22 files formatted. mypy src/: Success, 16 files, exit 0.

## Per-feature
- F001 PASS. Probed all 8 boundaries: 100, 10000000 -> UPI; 10000001, 20000000 -> IMPS; 20000001, 50000000 -> NEFT; 50000001, 10^12 -> RTGS. route_rail(99) raises AmountBelowMinimum.
- F002 PASS. validate_amount raises AmountBelowMinimum with code AMOUNT_BELOW_MINIMUM for 0, -1, 1, 99; validate_amount(100) returns 100.
- F003 PASS. rupees_to_paise('1,00,000.50') == 10000050, type int. '1.005', 'abc', '', '-5', '1e3' raise ValidationError (VALIDATION_ERROR). Uses Decimal; grep of money.py finds no float( and no float literal.
- F004 FAIL. Enum sets exactly match: PaymentState {CREATED, SUBMITTED, COMPLETED, FAILED}; RefundState {REQUESTED, APPROVED, EXECUTED, REJECTED, FAILED}; ReconStatus {matched, unmatched_internal, unmatched_external, amount_mismatch}; Role {customer, ops, admin}. Behaviour is correct: COMPLETED->SUBMITTED False, FAILED->COMPLETED False, CREATED->SUBMITTED, SUBMITTED->COMPLETED, SUBMITTED->FAILED True. But features.json F004 steps call is_valid_transition and folder-structure.md names assert_transition. Neither exists; the module exposes only is_valid_payment_transition / is_valid_refund_transition / assert_payment_transition / assert_refund_transition. The literal step raises AttributeError. Suggested fix: add the spec-named functions (or align the specs to the per-entity names), whichever the user prefers. failure_layer recorded as "api" because the allowed set has no unit value.
- F005 PASS. mypy exit 0; the *_paise float-annotation grep over backend/src returns nothing; every *_paise field in models.py is int. Only float in src is ports.py (Sleeper.sleep seconds, RandomSource.random), not money.

## Contract checks
- Layering PASS: types/ imports nothing from config/repository/service/api/lib; config/ imports only types; lib/ imports no layer package; no relative imports.
- Folder structure: all 18 required files exist.

## Items for the user to review
1. Inferred refund transitions (not stated in data-models.md or BRD excerpts I could find): REQUESTED -> {APPROVED, REJECTED}; APPROVED -> {EXECUTED, FAILED}; EXECUTED, REJECTED, FAILED terminal. The only spec source is the state list and the E4 refund features. Please confirm, notably whether APPROVED -> FAILED is intended and whether FAILED should be retryable.
2. Stub ports RailAdapter, RailLedger and RailLedgerEntry in types/ports.py and models.py. Design docs name the ports but give no signatures. Generator-chosen shapes: RailLedger.find(entry_type Literal["PAYMENT","REVERSAL"], payment_id) and record(entry); RailAdapter async submit/reverse(payment_id, amount_paise) -> RailLedgerEntry. Later stories (rail adapters, ledger) are bound to these, so please confirm before they build on them.
3. Observation: route_rail(10**12 + 1) does not raise, so there is no upper bound. The spec lists no maximum error, so I did not fail it.

## Re-check after F004 self-heal (2026-10-05)
- pytest -q --cov: 59 passed, coverage 96.41%. ruff check pass, ruff format --check pass (22 files), mypy src/ pass (16 files).
- Contract pytest command (with --no-cov): 52 passed, exits 0 (the coverage-subset problem is fixed).
- F001, F002, F003, F005 re-confirmed PASS (8 boundary rails, AMOUNT_BELOW_MINIMUM for 0/-1/1/99 and 100 accepted, '1,00,000.50' -> int 10000050, '1.005'/'abc' rejected, no float in money.py, no float *_paise, mypy clean).
- F004 still FAIL. is_valid_transition and assert_transition now exist, but the signature is (entity, current, target). The literal step is_valid_transition(COMPLETED, SUBMITTED) raises TypeError (missing argument 'target'). With entity='payment' the behaviour is correct (COMPLETED->SUBMITTED False, FAILED->COMPLETED False, the three allowed transitions True, assert_transition raises InvalidTransition). Enum sets match exactly.
- Fix options: make the wrapper infer the entity from the state type (is_valid_transition(current, target)), which matches the spec step, or change the F004 step text to include the entity. No further self-heal was run.

# Group B / E1-S2 (SQLite schema and repositories), single pass 2026-10-05

Mode: local, unit-level (no UI/API/Playwright). No production code edited, no git operations.

## Tool results
- pytest -q --cov: 82 passed, coverage 95.45% (floor 80). Gaps: config/settings.py 0%, refunds_repo.py 65%, migrate.py 82%.
- ruff check: pass. mypy src/: pass (32 files).
- ruff format --check: FAIL, 7 files would be reformatted: repository/{payments,recon,refunds,settlement,statements}_repo.py, tests/repository/test_payments_repo.py, tests/repository/test_schema.py. The group-B contract's typing check names only ruff check, so this did not fail any feature, but it is a lint-hygiene gap to fix (run ruff format).

## Per-feature (probes on fresh file DBs)
- F006 PASS. All nine tables exist, journal_mode=wal, pragmas synchronous=1, foreign_keys=1, busy_timeout=10000. initialize_database twice is safe. All 10 named indexes and the 4 triggers exist.
- F007 PASS. Same (customer, key) raises DuplicateKeyError; second refund for one payment raises DuplicateKeyError. Same key for another customer succeeds; after release_idempotency a new payment with the key succeeds.
- F008 PASS. EventsRepo public methods are only append and list_for_payment. Raw UPDATE and DELETE raise IntegrityError "payment_events is append-only"; the row is still present.
- F009 PASS. amount_paise is INTEGER in payments and refunds, with no REAL/FLOAT/DOUBLE column anywhere. 99, 0 and -1 are rejected; 100 is accepted. A refund of 99 is rejected. Table CHECKs for COMPLETED (needs reference and completed_at) and FAILED (needs reason) reject violations and accept conforming rows. An unknown customer_id fails on the foreign key.
- F010 PASS. Seeding twice gives 5 rows: customer x3, ops x1, admin x1, ids cus_001..003, ops_001, adm_001. The second run adds no rows and leaves created_at unchanged. A bogus role is rejected.

## Layering and typing greps
- sqlite3.connect appears only in db.py. Repository, config, types and lib import nothing from service or api. No `type: ignore` or `Any` in repository/. Largest file is schema.py at 135 lines.

## Not checked
- Contract items not probed: settlement_files triggers and CHECKs (triggers exist), rail_statement_entries amount 0/-1, payment_events json_valid, and the remaining UNIQUE constraints.
- refunds_repo.py has 65% coverage (get/get_for_payment/list_by_state untested).

## Verdict
PASS for F006-F010 (features.json updated). F004 (E1-S1) is unchanged and out of scope.

# Group C / E1-S3 (identity, health, customers, CORS), single pass 2026-10-05

Mode: local, API only (no UI/Playwright). No production code edited, no git operations, no self-heal. E2-S1 not evaluated.

## Tool results
- pytest -q --cov: 109 passed, coverage 98.50% (floor 80). ruff check pass. ruff format --check pass (60 files). mypy src/ pass (44 files).

## Live start (FAIL)
- `uv run uvicorn src.main:app --port 8765` -> "Failed to spawn: uvicorn". pyproject.toml lists only fastapi; uvicorn is absent from .venv. The manifest start command and init.sh:20 cannot boot the API. Live curl probes were therefore impossible. Detail in specs/reviews/eval-failures-005.json. Fix: add uvicorn to dependencies and uv sync.

## In-process probes (fastapi TestClient on a temp DB, default env, lifespan run)
- GET /health -> 200 application/json {status:ok, database:ok}; with X-Role bogus -> 200 (C-API-01, C-API-04 behaviour OK).
- GET /customers -> 200, total 5, ids adm_001, cus_001..003, ops_001, each with only id, name, role; roles customer x3, ops, admin. X-Role bogus -> 200 (C-API-02, 05 OK).
- CORS default env: Origin 3000 gets Allow-Origin http://localhost:3000; Origin 5173 gets none. Preflight OPTIONS 200, Allow-Headers include X-Role, X-Customer-Id, Idempotency-Key (C-API-03 OK).
- Guard on /admin/simulation (admin-only route registered in api/routes/simulation.py): no role 401, superuser 401, customer without id 401, customer cus_999 401 (all UNAUTHENTICATED envelope, no fields key), customer cus_001 403 FORBIDDEN, ops 403, admin 200.
- Settings default cors_origin http://localhost:3000; PAYBRIDGE_* names used in settings.py; no os.environ/getenv outside settings.py; no fastapi/starlette or api imports in service/ or repository/.

## Contract deviations (non-blocking, noted)
- api/schemas/common.py is missing (api/schemas/ does not exist) though listed in files_must_exist.
- Contract-named tests/api/test_health_auth.py does not exist; equivalent tests are in tests/api/test_e1_s3.py (9 tests). It uses the real /admin/simulation route rather than a test-only one.
- /admin/simulation is registered (contract said no placeholder required, not forbidden).
- No leftover *.db files outside .mypy_cache. Settings.from_env env-injection probe not run (signature takes no argument).

## Verdict
- F011 FAIL, F015 FAIL (failure_layer api): live boot impossible, behaviour otherwise correct in-process.
- F012, F013, F014 PASS (verified in-process, as the contract specifies for 401/403 rules).
- features.json updated for F011-F015 only.

# E1-S3 re-check (uvicorn added), 2026-10-05

Mode: local. No production edits, no git operations, no self-heal. Server started via `uv run uvicorn src.main:app --port 8791`, stopped afterwards (no process left).

## Live probes (real HTTP)
- GET /health -> 200 {"status":"ok","database":"ok"}; X-Role bogus -> 200.
- GET /customers -> 200, total 5 (adm_001, cus_001..003, ops_001), fields id/name/role.
- /admin/simulation: no role 401, superuser 401, customer without id 401, customer cus_999 401 (UNAUTHENTICATED envelope), customer cus_001 403, ops 403 (FORBIDDEN), admin 200.
- CORS: Origin 3000 -> Allow-Origin http://localhost:3000; Origin 5173 -> no Allow-Origin. Preflight 200, Allow-Headers include Idempotency-Key, X-Customer-Id, X-Role.

## Tools
- pytest --cov: 109 passed, 98.50% coverage. ruff check pass. ruff format --check pass (60 files). mypy src/ pass (44 files).

## Verdict
F011 PASS, F015 PASS (features.json updated, failure fields cleared). F012-F014 remain PASS. Prior non-blocking contract deviations (missing api/schemas/common.py, test file naming) unchanged.

# Evaluator Report - Story E1-S4 (frontend foundation, F016-F019)

Date: 2026-10-05
VERDICT: FAIL (F017, F019 pass; F016, F018 not fully verified)

## Static / unit
- [PASS] npm test (vitest --coverage): 14/14 pass, 99.6% stmts, 96.25% branch
- [PASS] npm run lint, npm run typecheck: clean
- [PASS] Backend /health ok, GET /customers returns 5 items

## Playwright (single run, headless Chromium, cached build 1243 via playwright-core 1.57)
- [PASS] F016 Role select in banner, options exactly Customer/Ops/Admin, Tab leaves select
- [FAIL] F016 ArrowDown/ArrowUp did not change value (type-ahead did). Likely macOS Chromium popup behavior, but not verified; needs re-check
- [PASS] F017 picker absent for Ops/Admin, visible for Customer, populated from live /customers. Note: lists all 5 customers incl. Admin and Ops Analyst, labels "Name (id)"; getByLabel('Customer') matches 2 selects (Role label text contains "Customer"), so contract locator is ambiguous
- [PASS] F018 customer role: X-Role=customer, X-Customer-Id cus_002 / cus_003 on /customers; localStorage key paybridge.session persists role and customer across reload; admin restored with no picker
- [FAIL] F018 ops/admin: no API request issued on nav click or reload, so headers unobservable; Payments click issues no /payments request either
- [PASS] F019 nav: Customer=[Payments], Ops=[Reconciliation, Stuck payments], Admin=[Dashboard, Settlement, Simulation]
- Screenshots: specs/reviews/screenshots/e1-s4/ (design critic not run, per instruction)

# E1-S4 re-check 2 (F016-F019), 2026-10-05

Mode: local. Backend :8000 and frontend :3000 started, then stopped. Single Playwright run (@playwright/test, headless Chromium). No production edits, no git operations, no self-heal, no critic.

## Tools
- npm test: 16/16 pass, 99.66% stmts, 96.77% branch. npm run lint clean. npm run typecheck clean.

## Results
- F016 PASS by user acceptance: arrow-key behaviour in headless Chromium on macOS is a test-environment limit; not re-tested. (Earlier run verified select in banner, options Customer/Ops/Admin, Tab.)
- F017 PASS: picker absent for Ops/Admin, present for Customer with 5 options from live /customers ("Name (id)" incl. Admin and Ops Analyst).
- F019 PASS: Customer=[Payments]; Ops=[Reconciliation, Stuck payments]; Admin=[Dashboard, Settlement, Simulation].
- F018 FAIL (left false): customer role verified (headers, localStorage key paybridge.session persists role+customer across reload; Admin reload restores with no picker). Ops/admin: clicking Reconciliation/Dashboard issues 0 requests to localhost:8000, so contract D-PW-03 waitForRequest steps cannot be satisfied. Supplementary evidence only: apiRequest called in the real browser under ops and admin sends X-Role ops/admin. The vitest suite covers apiRequest for customer only and authHeaders for admin, so the unit-test route does not fully cover the contract either. To pass: add a unit test for apiRequest under ops/admin, or amend the contract step (or have those views make a request).
- Observation: after switching to Ops/Admin the stored customerId (cus_001) is still sent as X-Customer-Id on apiRequest; the contract only requires it for Customer, but it is stale identity leakage worth reviewing.
- Observation: Payments click triggers 2 requests to :8000 (not inspected further).
- Observation: getByLabel('Role') exact fails because the label wraps the select (name includes options); getByRole('combobox',{name}) works. getByLabel('Customer') remains ambiguous.

## Config note (not fixed)
frontend/playwright.config.ts baseURL is http://localhost:5173 but the dev server is on 3000 (also no frontend/e2e dir exists).

## Verdict
F016 PASS (accepted), F017 PASS, F019 PASS, F018 FAIL (failure_layer browser). features.json updated for F016-F019.

---
# E2-S1 (F020-F023) - 2026-10-05
Mode: local, service-level probes on temp SQLite DBs (customers seeded via seed_customers). No UI, no production edits, no git, no self-heal.

## Tools
- pytest --cov: 116 passed, 98.57% total (payment_service.py 100%). ruff check clean. ruff format --check clean (64 files). mypy src/ clean (46 files).

## Results
- F020 PASS: 150000 paise -> state CREATED, rail UPI, 1 PENDING outbox row, 1 PAYMENT_CREATED event.
- F021 PASS: OutboxRepo.insert patched to raise -> create_payment raised; payments, payment_events, outbox_messages all 0 rows.
- F022 PASS: 10,000,001 -> IMPS; 50,000,001 -> RTGS (boundaries 10,000,000 -> UPI, 50,000,000 -> NEFT also checked).
- F023 PASS: 99 paise (AmountBelowMinimum), empty / whitespace / 141-char beneficiary (ValidationError) all rejected with messages naming the field; 0 rows written; 140 chars accepted.

## Observations
- Validation errors carry only a message string naming the field, no structured field attribute. Acceptable for the service layer.
- Coverage gaps outside this story: refunds_repo.py 65%, migrate.py 82%.

## Verdict
F020, F021, F022, F023 PASS. features.json updated.

---
# E2-S2 (F024-F028) - 2026-10-05
Mode: local, service-level probes on temp SQLite DBs, FakeClock. No UI, no production edits, no git, no self-heal.

## Tools
- pytest --cov: 122 passed, 98.59% total (payment_service.py, idempotency.py 100%). ruff check clean. ruff format --check clean (64 files). mypy src/ clean (46 files).

## Results
- F024 PASS: same key+payload -> same id, first replay=False, second replay=True, 1 payment row.
- F025 PASS: changed amount and changed beneficiary each raise IdempotencyConflict; row count stays 1.
- F026 PASS: 20 threads, same key, 5 trials: each 1 row, 1 created, 19 replays, 0 errors, 1 distinct id.
- F027 PASS: same key for cus_001 and cus_002 -> 2 rows, distinct ids, both replay=False.
- F028 PASS: at 23h59m59s still replay; at 24h01m new id, replay=False, 2 rows; original row differs only in idempotency_released_at (None -> new now); new row has it NULL.

## Verdict
F024-F028 PASS. features.json updated.

## E2-S4 (F034-F037) - 2026-10-05
- pytest --cov: 125 passed, 98.63% total. ruff check: pass. mypy src/: pass.
- ruff format --check: FAIL - backend/src/paybridge/repository/outbox_repo.py:52 (long SQL line). Quality-gate defect, not tied to a feature step.
- F034 PASS: temp DB, one cycle -> COMPLETED, one attempt "success", events SUBMITTED then COMPLETED.
- F035 PASS: all 4 adapters return identical rail_ref on repeat submit. Note: all rails returned "UPI-PAY-pay_x" for the same payment id (ledger appears keyed by payment id, not rail); not a spec violation.
- F036 PASS: lifespan driven directly with warnings=error: worker task running inside, done after exit, no pending tasks. Live uvicorn boot on a free port: /health 200, clean shutdown. Existing test only checks /health, it does not assert the task state.
- F037 PASS: two cycles (1, then 0 rows), adapter called once, outbox SENT.
- Verdict: features PASS; sprint needs `ruff format` on outbox_repo.py before merge.

## E2-S3 (F029-F033) - 2026-10-05
- pytest --cov: 131 passed, 98.96% total. ruff check, ruff format --check (69 files), mypy src/ (49 files): all clean.
- Live uvicorn probe on a free port (temp data dir, server stopped afterwards):
- F029 PASS: POST as customer -> 202, id, state CREATED, rail UPI, amount_paise.
- F030 PASS: replay -> 200 + Idempotent-Replay: true, same id; changed payload -> 409 IDEMPOTENCY_KEY_CONFLICT; amount 99 -> 422 with fields[].field=amount_paise; missing key -> 422 (field Idempotency-Key).
- F031 PASS: GET own payment has events and attempts arrays; other customer -> 404; ops and admin -> 200.
- F032 PASS: customer sees only own, newest first (list shape is {items,total}); ?state= filters; ops/admin see both customers; ?customer_id= filters for admin, ignored for customers.
- F033 PASS: POST as ops and admin -> 403 FORBIDDEN.
- Extras: unknown payment 404, no X-Role 401, bad ?state= 422, all in the error envelope.
- Verdict: F029-F033 PASS. features.json updated.

## E3-S1 (F038-F042) - 2026-10-05
- vitest: 30 passed. eslint: clean. tsc --noEmit: clean.
- One Playwright run (chromium, live backend, temp data dir), spec frontend/e2e/e3-s1.spec.ts, screenshots in specs/reviews/screenshots/e3-s1/.
- F038 PASS: labelled fields, Idempotency-Key header is a UUID matching the form key, new key shown after successful submit and return to form.
- F039 PASS: 1,00,000 UPI; 100000.50 IMPS; 200000.01 NEFT; 500000.01 RTGS; 0.99 no rail.
- F040 PASS: mocked 422 shows 'Amount must be at least Rs 1' beside amount; 0 and -5 show a client-side error.
- F041 FAIL (browser): 409 message OK; live 202 navigates to /payments/{id}. For 200 replay, URL changes but form unmounts (no payment detail route yet, blank page), so the replay message is never visible (06-200.png). Likely resolved by a detail page (E3-S2) or by carrying the notice across navigation.
- F042 PASS: button disabled with 'Submitting...' while pending; live request body amount_paise = 10000050 (integer).
- Servers stopped.

## E3-S1 re-check after F041 fix - 2026-10-05
- npm test exit 0, eslint clean, tsc clean. One Playwright run: 1 passed, but the 200-notice assertion in e3-s1.spec.ts is wrapped in .catch (not a real assertion).
- Screenshot 06-200.png (fresh) shows a blank page: notice NOT visible on /payments/pay_mock. F041 still FAIL (browser).
- Likely cause: takeFlash() (read+remove) called in useState initializer in FlashBanner; React StrictMode double-invokes it in dev, second call returns null. Fix: read in useEffect/useRef-guarded, or remove-on-unmount/next navigation instead of on read; and make the spec assertion strict.
- F038, F039, F040, F042 still PASS; F041 409 and 202 OK. Servers stopped.

## E3-S2 (F043-F046) - 2026-10-05
- npm test exit 0: 35 passed, coverage 99.86% stmts / 96.12% branch. eslint clean, tsc clean.
- Live backend (cus_001 seeded incl. a replay -> 200, same id, no duplicate; plus cus_002 payment; worker completed all). Playwright e2e/e3-s2-live.spec.ts (added by evaluator): live list shows only cus_001 rows (5, cus_002 payment/amount absent), Rs 1,00,000.50 / Rs 5,00,000.00 / Rs 2,500.00, caption "My payments", Enter on row link -> /payments/{id}. Mocked-API variant: CREATED/SUBMITTED/COMPLETED/FAILED badges, reason code INSUFFICIENT_FUNDS, Tab order between row links, empty state + link /payments/new, skeleton rows, 500 banner "Request failed: 500" then Retry refetches. Screenshots in specs/reviews/screenshots/e3-s2/.
- F043-F046 PASS (app behaviour). No live FAILED payment could be produced, so FAILED reason code is verified with mocks only.
- DEFECT in generator's e2e/e3-s2.spec.ts (2 tests FAIL, test-only, not app): route glob "**/payments" also intercepts the page navigation to /payments (fulfills HTML with JSON); error test uses n++===0 which breaks under StrictMode double fetch (dev). Fix: route "http://localhost:8000/payments" and switch to a flag, as in e3-s2-live.spec.ts.
- Servers stopped.

## E3-S3 (F047-F050) - 2026-10-05
- npm test exit 0: 7 files, 40 tests passed, coverage 99.88% stmts / 95.45% branch. eslint clean, tsc clean.
- ONE Playwright invocation (e3-s2.spec.ts, e3-s3.spec.ts, plus evaluator-added e3-s3-live.spec.ts): 6/6 passed. e3-s2.spec.ts now passes (earlier test defect fixed), F043-F046 unchanged.
- F047 PASS: live COMPLETED payment shows fields and Attempts table; out-of-order mocked events render chronologically (CREATED, SUBMITTED, FAILED); 2 attempt rows.
- F048 PASS: SUBMITTED -> COMPLETED within 5s, then no further GET /payments/{id} for 4.5s.
- F049 PASS: FAILED shows 'Payment failed. Reason code: INSUFFICIENT_FUNDS'; live and mocked 404 show 'Payment not found' and 'Back to payments' -> /payments.
- F050 PASS: skeleton shown while pending (note: skeleton is a single card, not timeline-shaped); no horizontal scroll at 375px on live detail and 404.
- Limit: no live FAILED payment producible (mock only). Screenshots in specs/reviews/screenshots/e3-s3/. Servers stopped.

## Re-check: F004, F041, layering moves
- F004 PASS: 2-arg is_valid_transition(COMPLETED,SUBMITTED)=False, (CREATED,SUBMITTED)=True, (FAILED,COMPLETED)=False; assert_transition raises InvalidTransition.
- F041 PASS: e3-s1 live spec asserts replay notice visible on /payments/{id} (hard expect, no catch) under dev StrictMode.
- Backend: pytest 131 passed, cov 99.06%; ruff check, ruff format --check, mypy clean. Frontend: npm test exit 0, lint, typecheck clean.
- Playwright: 1 invocation, 5/5 passed (e3-s1, s2, s3). Reused running servers on :8000/:3000 (not stopped). No regressions.

## E4-S1 (F051-F055) - 2026-10-05
- Backend: pytest 142 passed, cov 99.02%; ruff check, ruff format --check, mypy clean.
- Live (uvicorn :8765, temp data dir, stopped): GET admin -> 200, 4 rails all success; ops/customer GET and PUT -> 403; unknown rail BOGUS -> 404; rate 1.5 and -0.1 -> 422; permanent_failure without/invalid reason_code -> 422; valid INSUFFICIENT_FUNDS -> 200 echo; transient without rate -> 422; invalid mode -> 422; state reflected in GET.
- Adapter (script, seeded): permanent -> PermanentRailError reason_code INSUFFICIENT_FUNDS; transient 1.0 -> 100/100 errors; 0.0 -> 0/100.
- F051-F055 PASS. Note: rail path segment is case-sensitive uppercase (/admin/simulation/upi -> 404, /UPI -> 200); stories do not specify case. No UI checked.

## E4-S2 (F056-F060) - 2026-10-05
- Backend: pytest 145 passed, cov 99.05%; ruff check, ruff format --check, mypy clean.
- Probe (scripted adapter, FakeClock, temp DBs, clock advanced 1s per poll so early re-processing would show as extra adapter calls): 
- F056 PASS: 2 transient then success -> COMPLETED, attempts transient, transient, success (3 adapter calls).
- F057 PASS: next_attempt_at deltas 1, 2, 4, 8s after failures 1-4 (5th attempt succeeded).
- F058 PASS: 5 transient -> FAILED, RETRIES_EXHAUSTED, exactly 5 attempts/adapter calls; no retry scheduled after 5th.
- F059 PASS: permanent INSUFFICIENT_FUNDS -> FAILED immediately, 1 attempt (outcome permanent).
- F060 PASS: 2-then-success run has 2 PAYMENT_RETRY_SCHEDULED; permanent run has exactly 1 PAYMENT_FAILED (exhaustion run also 1 PAYMENT_FAILED + 4 RETRY_SCHEDULED).
- Limit: worker-level only (no live HTTP/UI). Servers on :8000/:3000 untouched.

## E4-S3 (F061-F064) - 2026-10-05
- Backend: pytest 147 passed, cov 99.05%; ruff check, ruff format --check, mypy clean.
- Probe (scripted adapter spy, FakeClock, temp DBs):
- F061 PASS: CREATED payment + IN_PROGRESS row -> COMPLETED, row SENT.
- F062 PASS: crash (CancelledError) after ledger accept, before DB update -> SUBMITTED/IN_PROGRESS; fresh worker -> COMPLETED, same rail_reference, ledger has 1 entry, 1 success attempt.
- F063 PASS: future next_attempt_at -> untouched (0 processed, 0 adapter calls) at t and t+29s; processed at t+30s.
- F064 PASS: 10 payments, worker task cancelled mid-batch (4 SENT, #5 accepted by rail but IN_PROGRESS, 5 PENDING); fresh worker -> 10 COMPLETED, 10 attempts each exactly 1 success, 10 SENT rows, 1 ledger entry per payment. Adapter submit calls 5+6=11 (crashed payment re-submitted once, deduped by rail).
- Limit: rail ledger is in-memory, so crash is simulated in-process (task cancel), not an OS-level kill; live HTTP/UI not checked. Servers on :8000/:3000 untouched.

## E4-S4 stuck payment detection (2026-10-05) - PASS (F065-F068)
- pytest 150 passed, cov 99.09%; ruff check, ruff format --check, mypy src/ clean.
- Live probe (uvicorn, temp PAYBRIDGE_DATA_DIR): ops/admin 200, customer 403, no role 401.
- SUBMITTED rows aged 299s/300s not flagged, 301s flagged; age_seconds present.
- 4 calls: exactly one PAYMENT_FLAGGED_STUCK per payment; payment moved to FAILED/COMPLETED drops out of list.
- Note: submitted_at must be second-precision Z (ms-precision rows from outside the app cause 500 in parse_iso_z); app writes second precision, so not a defect.

## E4-S5 (F069-F072) single-pass evaluation 2026-10-05
- npm test exit 0: 10 files / 50 tests pass, coverage 99.9% stmts / 95.64% branch; lint and typecheck clean.
- Playwright (1 invocation, 4 tests): e2e/e4-s5.spec.ts 2/2 pass; e2e/e4-s5-steps.spec.ts F071 pass, F069/F072 test failed on my ambiguous locator (substring label match), not an app defect.
- F070 PASS (rate 2 -> field error, 0 PUTs). F071 PASS (columns, empty message, 500 retry banner). F069/F072 left passes=false (unverified live: PUT body for 0.3, per-control label/keyboard toggle); unit tests cover labels, PUT and confirmation.
- Screenshots: specs/reviews/screenshots/e4-s5/ (stuck-list, stuck-empty, stuck-error; simulation shots not captured due to failure order).

## E4-S5 re-check 2026-10-05 - F069, F072 PASS
- Playwright (1 invocation) e2e/e4-s5-steps.spec.ts: 2/2 pass (F069/F072 test, F071 test) after locator fix (radio role, exact names).
- F069 PASS: UPI transient 0.3 saved, PUT body and confirmation verified. F072 PASS: controls found by label, keyboard toggle works.
- Screenshots: specs/reviews/screenshots/e4-s5/simulation.png, simulation-saved.png. All E4-S5 features (F069-F072) now pass.

## E5-S1 refund request endpoint (F073-F077) single-pass evaluation 2026-10-05 - PASS
- Supersedes any earlier E5-S1 entry/feature edits (those were judged from test assertions only; none found in this file).
- Backend: pytest 159 passed, cov 99.14%; ruff check, ruff format --check, mypy src/ clean.
- Live probe (uvicorn :8791, temp PAYBRIDGE_DATA_DIR, stopped afterwards; :8000/:3000 untouched):
- F073 PASS: customer owner, COMPLETED payment -> 201 REQUESTED, amount 12345 = payment, requested_by cus_001; REFUND_REQUESTED event present.
- F074 PASS: CREATED, SUBMITTED, FAILED -> 422 PAYMENT_NOT_REFUNDABLE (states forced via sqlite on temp db).
- F075 PASS: duplicate -> 409 REFUND_ALREADY_EXISTS; 10 concurrent -> one 201, nine 409, 1 refund row, 1 event.
- F076 PASS: other customer -> 404; ops and admin POST -> 403; no headers 401; unknown payment 404.
- F077 PASS: customers see only own (2 vs 1); admin sees all 3; ?state=REQUESTED -> 2 REQUESTED only, APPROVED (set via sqlite) -> 1; invalid state -> 422.
- Notes: ops GET /refunds returns 200 (all refunds; story silent on ops). Non-COMPLETED states and APPROVED refund were set by direct DB edits, not via app flows. No UI checked.

## E5-S2 (F078-F082) - 2026-10-05 - PASS
- Gates: pytest 171 passed, cov 99.34%; ruff check/format clean; mypy clean.
- Live (uvicorn, temp data dir): approve 200 EXECUTED decided_by adm_001, events REFUND_REQUESTED/APPROVED/EXECUTED; reject 200 REJECTED/REJECTED_BY_ADMIN, payment COMPLETED; 4 concurrent approvals -> one 200, three 409; decided refund 409 REFUND_ALREADY_DECIDED; unknown 404; customer/ops 403 on both; permanent_failure LIMIT_EXCEEDED -> refund FAILED, payment COMPLETED, re-approve 409.
- Observations: (1) transient reversal error yields 500 and leaves refund APPROVED (per caller note). (2) F081 text cites REVERSAL_REJECTED, which PUT /admin/simulation rejects with 422 (not in reason-code enum); verified with LIMIT_EXCEEDED. Spec/feature wording mismatch.

## E5-S3 (F083-F086) - 2026-10-05 - PASS (UI), with infra caveat
- npm test exit 0 (54 tests, coverage 99.75% stmts), lint 0, typecheck 0.
- Playwright (1 invocation): e5-s3.spec.ts + added e5-s3-live.spec.ts, 6/6 pass. Screenshots in specs/reviews/screenshots/e5-s3/.
- Live GET /payments/{id} (cus_001, pay_f0dd627a03e7) returns `"refund": null`; list also includes `refund`. Shape {id,state,reason_code} per source. Live refund states EXECUTED/REJECTED/FAILED verified via mocked responses only (no refunds exist in live DB).
- Caveat: backend process on :8000 (started 08:33) predates refunds.py (08:59): live POST /refunds returns 404, openapi lacks /refunds. Restart backend before true end-to-end refund creation.
- Observations: mockup refund-state styling skipped; 422 message not handled.

## E5-S4 (F087-F090) - 2026-10-05 - PASS (story), F019 REGRESSION
- npm test exit 0 (62 tests, 99.77% stmts; RefundQueue.tsx 100/100/100/100), lint 0, typecheck 0.
- Playwright (1 invocation, 4 tests pass): e5-s4.spec.ts + added e5-s4-live.spec.ts. Live: cus_001 payments created via POST /payments, worker -> COMPLETED, POST /refunds 201, admin UI approve -> EXECUTED, reject -> REJECTED; GET /payments shows refund.state EXECUTED/REJECTED. Empty and 500 retry banner screenshotted. Screenshots: specs/reviews/screenshots/e5-s4/.
- F090 skeleton and aria-name details covered by unit tests (not in browser run); button names "Approve/Reject refund for payment <id>" verified in browser.
- F019 FAIL (regression): admin nav now Dashboard, Refunds, Settlement, Simulation (NavBar.test asserts this). F019/E1-S4 say "no other items". Set passes=false. Fix: update F019/E1-S4 wording to include Refunds (spec decision) or remove the nav item.

## E6-S1 (F091-F096) - 2026-10-05 - PASS
- Gates: pytest 178 passed, cov 99.38%; ruff check/format clean; mypy clean (57 files).
- Independent probes on temp DBs (service layer, raw-SQL mutations): F091 3 entries w/ correct rail/ref/amount/date; F092 all matched; F093 +1 and -1 paise -> exactly one amount_mismatch; F094 one unmatched_internal + one unmatched_external; F096 re-run x3 -> no duplicate rows (unique index ux_recon_key); F095 corpus flagged set == anomaly set exactly (3/3, 4 clean not flagged), using own loader.
- Extra: wrong ref or wrong rail on entry -> unmatched_internal + unmatched_external pair (not mismatch).
- Notes: statements derive from COMPLETED payments (steps F091 say "complete payments, generate statement" - accepted). Corpus is hand-authored and independent of matcher but thin (7 payments, one anomaly per type; no ref/rail-mismatch or duplicate cases). Re-run after the statement changes adds new rows and leaves stale ones (out of scope).

## E6-S2 (F097-F101) - 2026-10-05 - PASS
- Gates: pytest 191 passed, cov 99.41%; ruff check/format clean; mypy clean (58 files).
- Live (uvicorn :18734, temp PAYBRIDGE_DATA_DIR, stopped after): run as ops/admin 200 with counts for all 4 statuses; re-run same date no new rows; malformed (20261005, 2026-13-45), missing, future date -> 422. Unmatched: excludes matched/resolved; status/rail/combined/statement_date filters correct; status=matched -> []; bogus status/rail -> 422. Resolve: matched 422, blank/whitespace/501-char/missing note 422, 500-char ok, unknown id 404, second resolve 409, ops->ops_001, admin->adm_001; payments table byte-identical before/after, amount columns unchanged. Roles: customer 403 (even with invalid body), no/unknown X-Role 401, on all 3 endpoints.
- Observation: resolved_by hard-coded ops_001/adm_001. Contract says "resolved_by = caller id". Caller has no id for ops/admin (identity is role header only, one seeded user each), so output matches contract today; would diverge if multiple ops users existed.
- Setup note: anomaly rows were seeded by raw SQL into the temp DB (a real run on a clean DB yields only matched). Tampering entries then re-running regenerated statements and left stale matched rows (same known E6-S1 behavior).
- Scope: repo has no commits so git diff unavailable; could not verify touched-file list by diff. All mtimes fall in same window. Unexpected modified files exist beyond the stated list (e.g. payments_repo, payment_service, outbox_worker, idempotency, matching, refund_service, rail_adapters, state_machine, simulation, tests/service/test_payment_service.py, test_outbox_worker.py), but may be from earlier sprints.

## E6-S3 (F102-F105) - 2026-10-05
- Servers restarted via init.sh (left running). npm test exit 0 (14 files, 69 tests, 99.81% stmts); lint 0; typecheck 0.
- Playwright (1 invocation): e6-s3.spec.ts PASS (ops nav exactly Reconciliation + Stuck payments); e6-s3-live.spec.ts live run+resolve PASS (real payment, seeded orphan entry, run today -> counts 5/0/1/0, row resolved via dialog, empty-note error shown, backend unmatched total decremented); mocked states/focus test FAIL due to evaluator's wrong skeleton selector (app uses data-testid skeleton-row), aborted before 500-banner/focus steps.
- F102, F103, F104 pass. F105 left false: skeleton confirmed (screenshot 20-loading.png) and unit tests cover banner/focus, but browser check incomplete.
- Observation: UI is JS-rendered React, not following the E6-S3 mockup.
- Screenshots: specs/reviews/screenshots/e6-s3/

## E6-S3 re-check (2026-10-05) - F105 PASS
Single run of e2e/e6-s3-live.spec.ts: 2/2 passed. Live run+resolve (note-required error, unmatched count drops by 1, API total matches). Mocked: skeleton rows with .skel attached during 3s delay then empty state; 500 shows alert "Something went wrong" + Retry button (visibility only, retry click not exercised); dialog Tab x8 stays inside dialog, Escape closes, focus returns to trigger.

## E7-S1 (F106-F110) - 2026-10-05 - PASS
- Gates: pytest 196 passed, cov 99.44%; ruff check/format clean; mypy clean (59 files).
- Probes on temp DBs/data dirs (service layer): F106 IST bounds exact (18:29:59Z on 10-04 in; 18:30:00Z out; 10-03 18:30:00Z in, 10-03 18:29:59Z out), one combined file, header columns correct. F107 amount_mismatch and no-recon (unmatched_internal) rows flagged true, matched false, file written. F108 footer row_count + sha256 over data rows only equals recomputed and stored record (kind primary). F109 rerun returns None, bytes unchanged, file mode 0444, write-open denied. F110 late payment -> followup-1 with exactly that row, primary hash unchanged; rerun -> None, no new file; second late -> followup-2. settlement_files rows = files on disk. Empty day writes a 0-row primary (e3b0... checksum).
- Observations: (1) orphan final file adoption not implemented (crash between link and DB insert would leave file with no row; next run would hit FileExistsError via os.link, not tested). (2) Service not wired to API/scheduler (E7-S2). (3) payments_repo.list_completed_on (used by StatementService and ReconciliationService) filters on UTC date prefix; settlement uses IST days. Payments completed 18:30Z-24:00Z belong to the next IST day in settlement but to the earlier statement/recon date. The recon route's future-date check uses IST business_date, so inconsistent. Settlement still finds recon status (looked up by payment_id, not date), so no wrong row now, but recon for IST date D misses payments completed in the first 5.5h IST of D. Needs a spec decision before E7-S2.

## E7-S2 (F111-F114) + IST fix re-check (F091-F101) - 2026-10-05 - PASS
- Gates: pytest 203 passed, cov 99.34%; ruff check/format clean; mypy clean (61 files).
- Live (uvicorn temp port + temp PAYBRIDGE_DATA_DIR, stopped): IST window recon for D=2026-10-04: payments completed 2026-10-03T18:30:00Z and 2026-10-04T18:29:59Z included (2 statement entries, 2 matched); 10-03T18:29:59Z and 10-04T18:30:00Z excluded. F091-F101 still pass (suite + this probe).
- Settlement: POST run 201 primary (CSV rows A,B; footer row_count/sha256 match), repeat 200 {file:null,"Primary file ... already exists"}, late payment -> 200 followup (1 row), repeat -> 200 null. Future/malformed date 422; no body -> today IST primary 201. GET list has id/business_date/kind/row_count/checksum/written_at; GET file text/csv; unknown 404. ops 403, customer(cus_001) 403, no role 401 on all 3 endpoints (customer without valid X-Customer-Id is 401, consistent with other routes).
- Scheduler under FakeClock via app lifespan (poll 0.05s): no run at 15:30 IST; one primary for 2026-10-04 after 23:59 IST; +1 min no second; next day 05:00 IST no run; next 23:59 -> 2026-10-05 primary.
- ISSUE (test hygiene, not a story failure): tests/service/test_outbox_worker.py::test_lifespan_starts_and_stops_worker uses Settings.from_env() with no PAYBRIDGE_DATA_DIR, so it creates/opens relative data/paybridge.db (confirmed in a scratch cwd; no other test creates data/). Running pytest from backend/ opens the real backend/data DB (initialize + seed_customers, and the scheduler is live: a run at 23:59 IST would write settlement files there). The real DB mtime was unchanged by my pytest run. Fix: use Settings(db_path=tmp_path/...) or monkeypatch PAYBRIDGE_DATA_DIR.

## E7-S3 Settlement files screen (F115-F118) - 2026-10-05 - PASS
- Servers restarted via init.sh. npm test exit 0 (77 tests, 99.82% stmt coverage), lint and typecheck clean. Backend pytest 203 passed; paybridge.db mtime unchanged by the run.
- Playwright: 1 invocation, 4 tests passed (live admin: payment completed, Run now POST with X-Role admin, status shown, list row has date/kind/rows/checksum, link name, downloaded 2026-10-05-primary.csv has `# row_count`/`# sha256` footer matching list; mocked loading skeleton, empty, 500 alert+retry, repeated-run message, link names; ops/customer nav lacks Settlement). Screenshots in specs/reviews/screenshots/e7-s3/. Spec: frontend/e2e/e7-s3.spec.ts.
- Omitted mockup business-date input and Written column: no F115-F118 step or acceptance criterion requires them (minor mockup deviation).
- Note: evaluator's pre-test curl POST /settlement/run wrote today's primary file (stl_005a6524decc) in the dev DB; the live UI run then returned the backend message "followup written". The repeated-run text in F116 was verified via mock only; the live backend message differs from the spec text.

## E8-S1 Dashboard summary API (F119-F123) - 2026-10-05 - PASS
- Gates: pytest 209 passed, cov 99.49%; ruff check/format clean; mypy clean (62 files).
- Live (uvicorn :8765, temp PAYBRIDGE_DATA_DIR, stopped; rows seeded via sqlite): date=2026-10-04 -> UPI 4/335000 (includes 10-03T18:30:00Z and 10-04T18:29:59Z; excludes 10-04T18:30:00Z and 10-03T18:29:59Z), IMPS 1/12345, NEFT 1/50000, RTGS 0/0; status_counts CREATED 3, SUBMITTED 1, COMPLETED 1, FAILED 1; settlement_files only that date's file; 10-03 and 10-05 windows pick up the excluded edge rows. All four rails and four states always present. Empty date (2026-01-01) 200 with all zeros, settlement_files []. No date -> today IST (2026-10-05). Malformed (abc, 2026-13-45, empty, 20261004) and future (2026-10-06, 2099) 422 VALIDATION_ERROR. ops 403, customer 403, no role 401, unknown role 401.
- Contract note: neither story E8-S1 nor api-contracts.md (Dashboard `pending_refunds[]`, no date param semantics) scopes pending_refunds to the date; generator's all-REQUESTED-regardless-of-date reading is consistent with the spec, which is silent. Consequence: an empty date still lists REQUESTED refunds from other days (F122 step says "all counts and totals 0", which holds; the list is not a count/total). Worth a spec clarification, not a failure.

## E8-S2 Admin dashboard (F124-F127) + F019 + F087-F090 regression - 2026-10-05 - PARTIAL
- Servers restarted via init.sh. npm test exit 0 (83 tests, 99.84% stmt cov), lint and typecheck clean.
- Playwright: 1 invocation, 12 tests, 11 passed, 1 failed. Passed: e8-s2.spec.ts (tiles Rs 1,00,000.50, status counts, mocked approve -> EXECUTED and "0 pending", link to /refunds, single tile Retry), e5-s4 (3), e7-s3 (4), live /refunds reject regression. Added frontend/e2e/e8-s2-live.spec.ts.
- FAIL (evaluator spec, not an app defect by diagnosis): live dashboard test asserted status_counts.CREATED == 1 from an API snapshot; the other live specs ran in parallel (5 workers) and had a payment in CREATED at snapshot time, UI later read 0. Test aborted before live approve, date picker, empty-date and ops/customer nav steps. Rail counts per tile matched the live API before the abort. Not re-run per hard limit.
- Verdict: F124 pass, F126 pass (mock-based browser approve + pending decrement; live approve from tile NOT verified). F125 and F127 left false (no browser evidence for empty date message / IST date default). F019 pass: admin nav exactly Dashboard, Settlement, Simulation (3 specs), config shows exact ops/customer lists; ops verified earlier in e6-s3, customer by config only. F087-F090 still pass.
- Observations: each tile calls /dashboard/summary separately (~5 identical requests per load; ActivityBanner adds one); RefundQueue not reused per component-map (dashboard re-implements it).
- Screenshots: specs/reviews/screenshots/e8-s2/ (01 live today only, 04 refunds route).

## E8-S2 re-check (2026-10-05)
Single run of e2e/e8-s2-live.spec.ts: 2/2 passed (live backend, summary frozen from one real API response). Verified: tiles match real response (F125), zeros and "No activity for this date" on 2026-01-01 (F125), approve from dashboard tile -> POST /approve as admin -> UI EXECUTED and API refund.state EXECUTED (F126), date input defaults to today IST with max=today (F127), ops/customer nav (F019), /refunds regression. F125, F126, F127 PASS. Screenshots: specs/reviews/screenshots/e8-s2/. Note: 10 summary calls on load (informational, not asserted).

## E9-S1 Sensitive data masking (F128-F131) - 2026-10-05 - FAIL
- Gates: pytest 217 passed, cov 99.50%; ruff check/format clean; mypy clean.
- Live (uvicorn :8791, temp data dir, stopped): 2 payments with names + 13-digit numbers completed by worker, refund requested+approved (EXECUTED), 422 sent. Raw names/numbers absent from log (grep 0), BUT every request raised "--- Logging error ---" (16 of 16): MaskingFilter sets record.args=None, uvicorn.access formatter unpacks args (TypeError). Access log is lost in the real server. Real defect.
- Risk 1 confirmed: registry is in-memory, filled only in create_payment. After restart a fresh process logs "Zorblax Quimby" verbatim in message and traceback (digits are still masked). Live forced-exception not possible (DB CHECK constraint on state); shown in-process.
- Risk 4: production code has only 2 log call sites (settlement schedule exception, unhandled-error handler); worker/refund log nothing, so F130 passes trivially and the integration test does not exercise real masking of those flows.
- Risk 2: registry is an unbounded set; mask_text rebuilds a regex of all names per log record (20k names: ~17ms/record). Risk 3: install_masking idempotent (verified); register_sensitive/mask_text not locked (race test: 0 errors in 2 writers + 1 reader, so no observed failure, but unlocked).
- features.json: F128-F131 left passes=false with failure reasons.

## E9-S1 re-check after self-heal (F128-F131) - 2026-10-05 - PASS
- Gates: pytest 223 passed, cov 99.51%; ruff check/format clean; mypy clean (64 files).
- Live (a) uvicorn on free port, temp data dir: 2 payments (names + 13-digit numbers) completed, refund requested+approved (EXECUTED), 422 sent. 0 "Logging error"; 7 access-log lines present in standard uvicorn format; raw names/numbers absent (grep 0).
- Live (b) restarted on same data dir (app wrapped with a route raising RuntimeError containing the stored name): startup-loaded beneficiaries masked in traceback ("Z*** Q*** 4***") and "unhandled error" record; 0 Logging errors. Restart risk resolved.
- (c) access log format intact after restart (GET/500/200 lines).
- Limitations (not failures): integer %d args not masked (known); a percent-encoded name in a URL path (%20) is not matched by the registry, so "Zorblax%20Quimby" stayed in the access line (digits masked). Real API carries no names in URLs. Production code still has only 2 log call sites, so F130 is mostly guarded by unit/integration tests.
- features.json: F128-F131 passes=true, failure fields cleared.

## E9-S2 Performance (F132-F134) - 2026-10-05 - PASS
- Gates: pytest 225 passed, cov 99.51%; ruff check/format clean; mypy src/ clean (64 files); mypy on tests/integration/test_performance.py clean.
- Live: real uvicorn (free ports, temp data dirs, stopped after), 200 POST /payments as cus_001, unique keys, urllib client.
  - Paced 20/s x 10s: 200x 202, p50 8.5 / p95 15.8 / p99 20.4 / max 21.4 ms; 200 rows, all COMPLETED, drain 0.5s.
  - Burst 20 parallel: 200x 202 in 0.4s, p50 6.8 / p95 140.3 / p99 226.5 / max 379.7 ms; 200 rows, all COMPLETED, drain 2.0s.
  - Server logs: 0 matches for 'database is locked', 'Logging error', Traceback; 200 access lines each.
- Caveat: single run each, localhost, tiny payload; burst tail (max 380ms) shows contention but p95 is under 300ms.
- features.json: F132-F134 passes=true.

## E9-S3 (F135-F138) evaluation 2026-10-05
- npm test exit 0 (99.84% stmts), lint 0, typecheck 0. One playwright invocation: 6/7 pass.
- F135 PASS: serious+critical filtered, tags wcag2a/aa/21a/21aa, no excludes; non-vacuity confirmed (injected img-no-alt and low-contrast detected: image-alt, color-contrast). Caveats: /stuck-payments scanned in empty state (0 rows); reconciliation unmatched rows are route-mocked.
- F136 FAIL: spec defect. URL regex matches /payments/new so id="new"; getByText("new") fails. App did navigate to detail. Keyboard flow itself uses only Tab/type/Enter.
- F137 PASS: 36 token-pair tests; spot-checked pairs absent from list (text-secondary/bg 7.46, link/sunken 5.94, placeholder/sunken 4.66, etc.) all >= 4.5.
- F138 PASS with gap: spec covers payments list, detail state/refund, dashboard status+rail tiles. Not covered by spec: new-payment rail preview, settlement kind badges, reconciliation/stuck statuses (plain text). Sanity spec e2e/e9-s3-eval-sanity.spec.ts verified rail preview and settlement badges have text.

## E9-S3 F136 + F018 final check 2026-10-05
- npm test exit 0 (17 files, 123 tests, 99.84% stmts), lint 0, typecheck 0. Playwright invoked once (e9-s3-a11y.spec.ts): 5/5 pass.
- F136 PASS: URL assertion is now /\/payments\/(?!new$)[A-Za-z0-9_-]+$/; flow uses only keyboard.press/type/Tab/Enter (no click/mouse), reaches detail for the created id, then opens detail from the list via focused link + Enter.
- F018 PASS (closed on USER decision, unit-level evidence): client.test.ts has it.each asserting fetch headers toEqual {X-Role: customer, X-Customer-Id: cus_007}, {X-Role: ops}, {X-Role: admin}; all pass. Original browser step D-PW-03 (API request after clicking Reconciliation/Dashboard) is still NOT satisfied in the browser: those views issue no request.
- Observation: an ops session carrying a stored customerId still sends X-Customer-Id (test asserts this behaviour for ops/cus_009).
