# Backend (Python 3.12, FastAPI, SQLite)

Inherits `/CLAUDE.md`. Module rules below; per-layer rules are in `src/paybridge/CLAUDE.md`.

## Commands
- Test: `uv run pytest -x -q` (coverage floor 80%, enforced by `addopts`)
- Lint / types: `uv run ruff check --fix .` | `uv run mypy src/`

## Rules
- **Money is integer paise.** Never `float` for amounts, fees or refunds. `Decimal` only to parse rupee text in `types/money.py`.
- Convert rupees ↔ paise only at the API boundary; the domain, service and DB layers see paise.
- Full type hints everywhere; `mypy src/` must be clean. No untyped `dict` payloads where a dataclass fits.
- FastAPI routes stay thin: parse, call a service, map errors. No business logic or SQL in routes.
- Domain errors derive from `DomainError` (stable `code`); the API maps them to the error envelope.
- Never log beneficiary names or account numbers raw; use `lib/masking.py`.
- Tests: TDD (red first). Tag tests with the PDF AC id, e.g. `# AC-02`. Architecture tests live in `tests/architecture/`.
- Functions < 50 lines, files < 300 lines.
