# PayBridge Architecture

## System Overview

```mermaid
graph TB
    Customer-->|HTTP|API
    Ops-->|HTTP|API
    Admin-->|HTTP|API
    API-->|validates|Service
    Service-->|persists|Repository
    Repository-->|reads/writes|SQLite
    Service-->|routes|RailAdapter
    RailAdapter-->|mock|UPI
    RailAdapter-->|mock|NEFT
    RailAdapter-->|mock|RTGS
    RailAdapter-->|mock|IMPS
    Worker-->|polls|Outbox
    Worker-->|submits|RailAdapter
    Scheduler-->|daily 23:59 IST|Settlement
```

## Payment Flow

```mermaid
sequenceDiagram
    Customer->>API: POST /payments
    API->>Service: create_payment()
    Service->>Repository: write Payment + OutboxMessage
    API-->>Customer: 202 Accepted
    Worker->>Outbox: poll
    Worker->>RailAdapter: submit
    RailAdapter-->>Worker: success/failure
    Worker->>Repository: update state + PaymentEvent
```

## Layered Structure
backend/src/paybridge/
├── types/ # Enums, models, errors, ports
├── config/ # Constants, rail settings
├── lib/ # Time, IDs, clock helpers
├── repository/ # Database access only
├── service/ # Business logic only
└── api/ # FastAPI routes only

frontend/src/
├── api/ # HTTP client
├── components/ # Reusable UI
└── pages/ # Screen components

## Key Design Decisions
- **Option B**: State machine with persisted outbox and background worker
- **SQLite WAL mode**: Single writer, sufficient for demo scale
- **Integer paise**: Never floating point, conversion only at API boundary
- **Append-only**: PaymentEvent, settlement files, migrations never mutate
- **Idempotency**: Unique constraint on (customer_id, idempotency_key) with 24h expiry
