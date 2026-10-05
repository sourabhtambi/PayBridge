# PayBridge

A payments routing, reconciliation and settlement hub for a simulated bank. It puts four rails (UPI, IMPS, NEFT, RTGS) behind one platform that handles amount-based routing, idempotent payment creation, retry with backoff, refunds, reconciliation and a daily settlement CSV. All rails are mock adapters, and money is stored as integer paise.

Built entirely by Claude Code agents. See `CLAUDE.md` and `specs/` for the rules and acceptance criteria.

## Prerequisites

- Python 3.12+ and [uv](https://docs.astral.sh/uv/)
- Node.js 20+ and npm
- `curl` (used by the startup health checks)

## Run locally

```bash
bash init.sh
```

This installs backend and frontend dependencies, starts both servers and waits for them to be healthy.

| Service | URL |
|---|---|
| Backend (FastAPI) | http://localhost:8000 (health: `/health`) |
| Frontend (React) | http://localhost:3000 |

Logs and PID files are written to `.run/`. Data is stored in `backend/data/` (SQLite database and settlement CSVs). To reset, stop the servers and delete `backend/data/paybridge.db`.

## Tests

```bash
# Backend (pytest, coverage floor 80%)
cd backend && uv run pytest -q
uv run ruff check . && uv run mypy src/

# Frontend (Vitest with coverage)
cd frontend && npm test
npm run lint && npm run typecheck

# Playwright e2e (backend and frontend must already be running via init.sh)
cd frontend && npx playwright install chromium   # first time only
npm run e2e
```

Add `-- --headed` to `npm run e2e` to watch the browser.

## Seed data

The database is seeded on startup with:

- **5 users:** 3 customers (`cus_001` Asha Verma, `cus_002` Rohan Mehta, `cus_003` Priya Nair), 1 ops analyst (`ops_001`) and 1 admin (`adm_001`). Pick a role and customer from the selector in the app header. There is no real login: the role is sent in the `X-Role` and `X-Customer-Id` headers, which is demo-only.
- **4 mock rails:** UPI, IMPS, NEFT and RTGS, all defaulting to success. An admin can switch each rail to permanent failure or a transient-error rate from the Simulation page.
- Beneficiaries are free text, so there is no beneficiary list to seed.

Routing (inclusive upper bounds): UPI up to Rs 1,00,000, IMPS up to Rs 2,00,000, NEFT up to Rs 5,00,000, RTGS above that.
