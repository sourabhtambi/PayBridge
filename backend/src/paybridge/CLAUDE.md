# paybridge package: layer rules

Inherits `/CLAUDE.md` and `backend/CLAUDE.md`. Dependencies flow downward only. Enforced by `tests/architecture/test_layering.py`.

| Layer | Folder | May import |
|---|---|---|
| Types | `types/` | nothing |
| Domain | `domain/` | types |
| Config | `config/` | types, domain |
| Repository | `repository/` | types, domain, config |
| Service | `service/` | types, domain, config, repository |
| API | `api/` | types, domain, config, service (repositories only in `app.py`, `container.py`, `deps.py`) |

`lib/` holds pure helpers (clock, ids, masking, time) with no layer dependencies.

## Rules
- **Types:** enums, models, errors, ports. Imports no other layer. `float` is forbidden for money.
- **Domain:** pure business rules: routing, state machine, money, idempotency hashing. Imports only `types` and the standard library; no I/O.
- **Repository:** SQL only. Money columns are `INTEGER` paise. Payment events and settlement files are append-only (DB triggers); do not add UPDATE or DELETE paths.
- **Service:** business rules and orchestration. Never import from `api/`. Multi-step writes go in one `Database.write()` transaction.
- **API:** validate input, call services, return the envelope. Role checks happen here (customer / ops / admin).
- State changes use `domain/state_machine.py`; invalid ones raise `InvalidPaymentStateException`.
- Every state change and routing decision appends a `payment_events` row.
- Known debt: six route files still import repositories (baseline in `tests/architecture/test_layering.py`). Do not add new ones.
