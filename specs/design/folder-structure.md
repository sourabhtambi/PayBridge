# PayBridge Folder Structure

Limits for every file: < 300 lines, every function < 50 lines (split by responsibility; the tree below is already granular for that). Imports flow downward only: types -> config -> repository -> service -> api (backend), types -> config -> service -> api -> ui (frontend). `lib/` is cross-cutting and imports nothing from the layers. Always use absolute imports (`from paybridge.types.enums import Rail`).

## Backend

```
backend/
  pyproject.toml                      uv project; ruff, mypy strict, pytest, coverage floor 80
  src/
    main.py                           shim so `uvicorn src.main:app` works: app = create_app()
    paybridge/
      __init__.py
      lib/                            CROSS-CUTTING (no layer imports)
        clock.py                      SystemClock (implements types.Clock)
        ids.py                        prefixed id generators (pay_, rfd_, rec_, stl_, evt_, rse_)
        timeutil.py                   UTC<->IST, business_date(), ist_day_bounds_utc(), iso_z()
        masking.py                    mask_text/mask_value, sensitive registry, record-factory install
      types/                          LAYER 1
        enums.py                      Role, Rail, PaymentState, RefundState, ReconStatus, AttemptOutcome, OutboxStatus, SettlementKind, SimulationMode, EventType, ReasonCode
        errors.py                     typed domain errors (AmountBelowMinimum, IdempotencyConflict, DuplicateKeyError, NotFound, Forbidden, PaymentNotRefundable, RefundAlreadyExists, RefundAlreadyDecided, ReconAlreadyResolved, PermanentRailError, TransientRailError)
        models.py                     frozen dataclasses for the 9 entities
        money.py                      MIN_AMOUNT_PAISE, rupees_to_paise (Decimal), format helpers
        routing.py                    route_rail + band constants (BRD 5.3)
        state_machine.py              allowed payment/refund transitions, assert_transition
        ports.py                      Clock, RailAdapter, RailLedger, Sleeper, RandomSource Protocols
      config/                         LAYER 2
        settings.py                   Settings from env (paths, CORS origin, busy timeout, poll interval)
        constants.py                  IDEMPOTENCY_TTL_SECONDS, RETRY_*, STUCK_*, OUTBOX_LEASE_SECONDS, BUSINESS_TZ, SETTLEMENT_CUTOFF
        rails.py                      per-rail settings (reference prefix, supported modes)
        logging_setup.py              configure logging + install masking
      repository/                     LAYER 3
        db.py                         Database: connect(), read(), write() (BEGIN IMMEDIATE), pragmas
        schema.py                     DDL strings, triggers, indexes (incl. ux_payments_customer_key)
        migrate.py                    initialize_database(), WAL verification
        seed.py                       idempotent demo users
        customers_repo.py             customers read
        payments_repo.py              insert, get, list, conditional updates, idempotency lookup/release
        attempts_repo.py              attempts insert/list
        outbox_repo.py                insert, claim_due, reset_in_progress, mark_sent/pending
        events_repo.py                append + list only (no update/delete)
        refunds_repo.py               insert, conditional state updates, list
        statements_repo.py            insert-or-ignore entries, list by date
        recon_repo.py                 upsert results, list unmatched, resolve
        settlement_repo.py            insert + list + get (no update/delete)
        stats_queries.py              dashboard aggregates, stuck candidates
        rail_ledger.py                JSONL file ledger (RailLedger impl)
        settlement_store.py           atomic append-only CSV write (tmp + link + chmod 0444)
      service/                        LAYER 4
        identity_service.py           resolve caller from role + customer id
        payment_service.py            create/get/list payments
        idempotency.py                request hash, decide(active, now) -> insert|replay|conflict|release
        simulation_service.py         per-rail mode config + seeded RNG
        rails/
          base.py                     MockRailAdapter shared logic (dedupe, modes, reverse)
          upi.py                      UPI adapter
          imps.py                     IMPS adapter
          neft.py                     NEFT adapter
          rtgs.py                     RTGS adapter
          registry.py                 rail -> adapter map
        retry_policy.py               backoff delays, max attempts
        delivery_service.py           process one outbox message (txn1, rail call, txn2)
        outbox_worker.py              async poll loop, lifecycle start/stop
        recovery_service.py           startup reset of IN_PROGRESS, APPROVED refund sweep
        stuck_service.py              detect + list stuck
        refund_service.py             request/approve/reject/list
        statement_service.py          ledger -> rail_statement_entries
        matching.py                   pure match(payments, entries) -> results
        reconciliation_service.py     run, list unmatched, resolve
        settlement_csv.py             pure CSV build + checksum
        settlement_service.py         run(date), list, read file
        settlement_scheduler.py       23:59 IST loop, catch-up
        dashboard_service.py          summary for a date
      api/                            LAYER 5
        app.py                        create_app(), lifespan (init db, recovery, worker, scheduler), CORS
        container.py                  composition root: builds repos/services from Settings
        deps.py                       get_caller, require_roles, container accessors
        errors.py                     exception handlers -> error envelope
        schemas/
          common.py                   ErrorEnvelope, ListResponse
          payments.py                 CreatePaymentRequest, Payment, PaymentDetail
          refunds.py                  CreateRefundRequest, Refund
          reconciliation.py           run request/response, ReconResult, ResolveRequest
          settlement.py               SettlementFile, run request/response
          simulation.py               SimulationUpdate, SimulationConfig
          dashboard.py                Dashboard, StuckPayment
        routes/
          health.py                   GET /health
          customers.py                GET /customers
          payments.py                 POST/GET /payments, GET /payments/{id}
          refunds.py                  /refunds, approve, reject
          reconciliation.py           run, unmatched, resolve
          settlement.py               run, files, file download
          dashboard.py                GET /dashboard/summary
          ops.py                      GET /ops/stuck-payments
          simulation.py               GET/PUT /admin/simulation
  tests/
    conftest.py                       tmp DB, FakeClock, container factory, masking install
    support/
      fake_clock.py                   FakeClock
      fake_sleeper.py                 manual Sleeper
      seeded_rng.py                   deterministic RandomSource
      factories.py                    payment/refund builders
      corpus.py                       loads specs/test_artefacts recon corpus
    unit/
      test_routing.py                 F001
      test_money.py                   F002-F003
      test_enums_state_machine.py     F004
      test_masking.py                 F128-F131
      test_idempotency_decision.py    TTL boundary, hash
      test_retry_policy.py            delays 1,2,4,8
      test_matching.py                match rules
      test_settlement_csv.py          CSV and checksum
      test_timeutil.py                IST boundaries
    repository/
      test_schema.py                  F006-F009 (tables, WAL, triggers, checks)
      test_seed.py                    F010
      test_payments_repo.py           unique partial index, release
      test_outbox_repo.py             claim, due ordering
      test_rail_ledger.py             dedupe, restart
    service/
      test_payment_service.py         F020-F023
      test_idempotency.py             F024-F028 (incl. expiry)
      test_worker_success.py          F034-F037
      test_simulation.py              F054-F055
      test_retry_flow.py              F056-F060
      test_crash_recovery.py          F061-F064
      test_stuck.py                   F065, F067-F068
      test_refund_service.py          F073-F075, F078-F081
      test_reconciliation.py          F091-F096, F101
      test_settlement.py              F106-F110
      test_scheduler.py               F111
      test_dashboard.py               F119-F122
    api/
      test_health_auth.py             F011-F015
      test_payments_api.py            F029-F033
      test_simulation_api.py          F051-F053
      test_ops_api.py                 F066
      test_refunds_api.py             F076-F077, F082
      test_reconciliation_api.py      F097-F100
      test_settlement_api.py          F112-F114
      test_dashboard_api.py           F123
    integration/
      test_concurrency.py             F026, F075, F080 (threads, file DB)
      test_logging_run.py             F130 end-to-end log capture
      test_performance.py             F132-F134 (marked slow)
```

## Frontend

```
frontend/
  package.json                        scripts: dev, build, test, lint, typecheck
  vite.config.ts                      port 3000, vitest config
  tsconfig.json                       strict, noImplicitAny, no `any`
  eslint.config.js                    @typescript-eslint/no-explicit-any = error, import layer rules
  index.html                          root + skip link
  src/
    main.tsx                          entry: wires session provider, client config, router
    types/                            LAYER 1
      domain.ts                       Role, Rail, PaymentState, RefundState, ReconStatus, Payment, Refund, ...
      api.ts                          request/response and error envelope types
    config/                           LAYER 2
      env.ts                          API base URL (http://localhost:8000)
      constants.ts                    poll interval 2000 ms, role/storage keys, nav definitions
      routes.ts                       route path constants
    service/                          LAYER 3 (pure logic, no fetch)
      money.ts                        parseRupeesToPaise (string, no float), formatPaise Indian grouping
      railPreview.ts                  rail for typed rupee amount (BRD 5.3 bands)
      validation.ts                   amount/beneficiary/note validators
      format.ts                       dates, state labels, reason code text
      navigation.ts                   nav items per role (E1-S4)
      errorMessages.ts                API error code -> user message map (exact BRD strings)
    api/                              LAYER 4
      client.ts                       fetch wrapper: headers from injected session getter, error envelope parsing
      customers.ts                    GET /customers
      payments.ts                     create, get, list
      refunds.ts                      create, list, approve, reject
      reconciliation.ts               run, unmatched, resolve
      settlement.ts                   run, files, download URL
      dashboard.ts                    summary
      ops.ts                          stuck payments
      simulation.ts                   get, put
    ui/                               LAYER 5 (highest)
      App.tsx                         routes and shell
      state/
        SessionContext.tsx            role + customer selection, localStorage persistence
      hooks/
        useResource.ts                load/error/refetch state machine
        usePolling.ts                 interval polling with stop condition
      components/
        AppShell.tsx                  header + nav + main landmark
        RoleSwitcher.tsx              Role select and customer picker
        NavBar.tsx                    role-aware links
        StateBadge.tsx                text badge for payment/refund state
        Skeleton.tsx                  skeleton rows/timeline/tiles (aria-busy)
        RetryBanner.tsx               error banner with retry (role=alert)
        EmptyState.tsx                empty message with optional link
        Dialog.tsx                    focus-trapped modal, returns focus
        FieldError.tsx                linked error text for inputs
        MoneyText.tsx                 formatted rupee amount
        RefundQueue.tsx               shared refund approve/reject list (E5-S4, E8-S2)
      pages/
        NewPaymentPage.tsx            /payments/new
        PaymentsListPage.tsx          /payments
        PaymentDetailPage.tsx         /payments/:id (timeline, attempts, refund request)
        ReconciliationPage.tsx        /reconciliation (run form, queue, resolve dialog)
        StuckPaymentsPage.tsx         /stuck-payments
        DashboardPage.tsx             /dashboard
        SettlementPage.tsx            /settlement
        SimulationPage.tsx            /simulation
      styles/
        tokens.css                    design tokens (contrast >= 4.5:1)
        global.css                    base styles
    tests/                            setup.ts, test-utils.tsx (colocated *.test.ts(x) beside sources)
```

Frontend layer rule: `service/` never imports `api/` or `ui/`; `api/` never imports `ui/`. The `ui` layer injects the session getter into `api/client.ts` at startup (dependency injection) so `api` stays below `ui`.

## Repo root (existing)

```
e2e/                  Playwright specs (E9-S3, /test)
sprint-contracts/     per-sprint contracts
specs/                BRD, stories, design, features.json (only registry)
init.sh               bootstrap + start servers
data/                 runtime only, git-ignored: paybridge.db, rail_ledger.jsonl, settlement/
```
