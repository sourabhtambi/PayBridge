# TDD Discipline Document

## Approach
PayBridge follows strict red-green-refactor TDD. Every feature starts with a failing test before any implementation code is written.

## Red-Green-Refactor Cycle
1. **Red**: Write a failing test that describes the desired behaviour
2. **Green**: Write the minimum code to make the test pass
3. **Refactor**: Clean up without breaking tests

## Worked Example: AC-02 Idempotency Replay

### Red — failing test first
```python
def test_idempotency_replay_returns_original():
    # This test fails because create_payment doesn't exist yet
    payment1 = create_payment(key="key-001", amount=10000)
    payment2 = create_payment(key="key-001", amount=10000)
    assert payment1.id == payment2.id
```

### Green — minimum code to pass
```python
def create_payment(key: str, amount: int) -> Payment:
    existing = db.get_by_idempotency_key(key)
    if existing:
        return existing
    return db.insert(Payment(key=key, amount=amount))
```

### Refactor — clean up
- Extract idempotency check into IdempotencyManager
- Add payload hash comparison for conflict detection
- Add 24-hour expiry logic

## Coverage
- Floor: 80% enforced by pytest-cov
- All AC-NN identifiers have at least one corresponding test
- Architecture tests enforce layering rules

## Test Files
- backend/tests/unit/ — unit tests per layer
- backend/tests/architecture/ — layering enforcement
- frontend/src/ — component tests with vitest
- e2e/ — Playwright end-to-end tests
