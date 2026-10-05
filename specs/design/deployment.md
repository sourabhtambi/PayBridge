# PayBridge Deployment

Local-only. No cloud, no containers required, no external services.

## Environments

| Env | Purpose | Backend | Frontend | Data |
|---|---|---|---|---|
| dev | Day-to-day work | `cd backend && uv run uvicorn src.main:app --port 8000 --reload` | `cd frontend && npm run dev -- --port 3000` | `data/paybridge.db`, `data/rail_ledger.jsonl`, `data/settlement/` |
| test | pytest / vitest / Playwright | In-process app with `tmp_path` DB, ledger and settlement dir; `FakeClock`, seeded RNG, fake sleeper. Playwright runs against servers started by `init.sh` on a throwaway data dir (`PAYBRIDGE_DATA_DIR`) | Vite on 3000 | Created per test run, deleted afterwards |
| demo | Showing the product | `init.sh` (seeded users, SystemClock, default simulation = success) | Vite on 3000 | Fresh `data/` dir; reset with `rm -rf data/` |

Ports: backend 8000, frontend 3000 (CORS allows only `http://localhost:3000`). Health: `http://localhost:8000/health` (init.sh and manifest poll it, 5 retries with backoff).

## Configuration and secrets

There are no secrets. Configuration is by environment variables read once into `config/settings.py` (`Settings`), with safe local defaults:

| Variable | Default | Meaning |
|---|---|---|
| `PAYBRIDGE_DATA_DIR` | `./data` | Base directory for DB, ledger and settlement files |
| `PAYBRIDGE_DB_PATH` | `<data>/paybridge.db` | SQLite file |
| `PAYBRIDGE_RAIL_LEDGER_PATH` | `<data>/rail_ledger.jsonl` | Simulated rail storage |
| `PAYBRIDGE_SETTLEMENT_DIR` | `<data>/settlement` | Append-only CSVs |
| `PAYBRIDGE_CORS_ORIGIN` | `http://localhost:3000` | Allowed origin |
| `PAYBRIDGE_SQLITE_BUSY_TIMEOUT_MS` | `10000` | busy_timeout |
| `PAYBRIDGE_WORKER_POLL_INTERVAL` | `0.5` | Seconds between outbox polls |
| `VITE_API_BASE_URL` | `http://localhost:8000` | Frontend API base |

Business constants (TTL 86400, 5 attempts, 1 s base delay, 300 s stuck threshold, 23:59 IST cutoff) live in `config/constants.py`, not env. `.env.example` lists the variables above with defaults and contains no secret values. The `X-Role` / `X-Customer-Id` headers are a demo role switch and are NOT a security control; the service must never be exposed beyond localhost.

## CI steps (local script or any runner; order matters)

1. Backend: `cd backend && uv sync --frozen`
2. `uv run ruff check .` (and `ruff format --check .`)
3. `uv run mypy src/` (strict, zero errors)
4. `uv run pytest -x -q --cov=paybridge --cov-fail-under=80` (excludes `-m slow` perf test on the fast path; the perf test `tests/integration/test_performance.py` runs in a separate step)
5. Architecture check: `.claude/hooks/check-architecture.sh`
6. Frontend: `cd frontend && npm ci`
7. `npm run lint` (eslint, no `any`), `npm run typecheck` (tsc), `npm test` (vitest)
8. `init.sh` (start servers on a clean data dir, health check)
9. Playwright E2E and axe-core: `npx playwright test` from repo root `e2e/`
10. Perf: `uv run pytest -m slow tests/integration/test_performance.py` (F132-F134)
11. Teardown: stop PIDs in `.run/*.pid`

## Infrastructure as code

`init.sh` is the IaC: installs dependencies (`uv sync`, `npm ci`), creates `data/`, starts both servers, polls health. Database schema is created idempotently at app startup (`initialize_database`, `CREATE ... IF NOT EXISTS`, WAL verified). Optional: a `docker-compose.yml` with two services (backend on 8000, frontend on 3000) and a named volume for `data/` may be added; it is not required and not part of acceptance.

## Backup and rollback

- Database backup: `sqlite3 data/paybridge.db ".backup 'backups/paybridge-<timestamp>.db'"` (or `VACUUM INTO`). Do not copy only the main file while WAL is active.
- Settlement files are append-only (mode 0444, never overwritten, no delete in the repository). They and `rail_ledger.jsonl` (append-only) are copied with the backup: `cp -p data/settlement/* backups/settlement-<timestamp>/`.
- Rollback of code: `git revert`/checkout the previous tag, stop servers, restore the matching DB backup, restart with `init.sh`. Schema changes are additive (new columns/tables with defaults); there are no destructive migrations in v1.
- If a restore would drop a settlement `settlement_files` row but its file exists, the next settlement run adopts the existing file (recomputed checksum) instead of overwriting it.
- Demo reset: stop servers, `rm -rf data/`, run `init.sh`. This deletes all payments and settlement files; never done in a shared environment.
