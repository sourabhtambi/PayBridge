# paybridge package: layer rules

Inherits `/CLAUDE.md` and `backend/CLAUDE.md`. Dependencies flow downward only. Enforced by `tests/architecture/test_layering.py`.

| Layer | Folder | May import |
|---|---|---|
| Types | `types/` | nothing |
| Config | `config/` | types |
| Repository | `repository/` | types, config |
| Service | `service/` | types, config, repository |
| API | `api/` | types, config, service (repositories only in `app.py`, `container.py`, `deps.py`) |

`lib/` holds pure helpers (clock, ids, masking, time) with no layer dependencies.

## Rules
- **Types:** enums, models, state machine, routing, money. Imports no other layer. `float` is forbidden for money.
- **Repository:** SQL only. Money columns are `INTEGER` paise. Payment events and settlement files are append-only (DB triggers); do not add UPDATE or DELETE paths.
- **Service:** business rules and orchestration. Never import from `api/`. Multi-step writes go in one `Database.write()` transaction.
- **API:** validate input, call services, return the envelope. Role checks happen here (customer / ops / admin).
- State changes use `types/state_machine.py`; invalid ones raise `InvalidPaymentStateException`.
- Every state change and routing decision appends a `payment_events` row.
- Known debt: six route files still import repositories (baseline in `tests/architecture/test_layering.py`). Do not add new ones.
