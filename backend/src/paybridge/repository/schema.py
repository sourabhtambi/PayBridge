"""DDL for the nine tables, indexes and append-only triggers (see data-models.md)."""

_RAILS = "('UPI','IMPS','NEFT','RTGS')"
_RECON = "('matched','unmatched_internal','unmatched_external','amount_mismatch')"
_EVENTS = (
    "('PAYMENT_CREATED','PAYMENT_SUBMITTED','PAYMENT_RETRY_SCHEDULED','PAYMENT_COMPLETED',"
    "'PAYMENT_FAILED','PAYMENT_FLAGGED_STUCK','REFUND_REQUESTED','REFUND_APPROVED',"
    "'REFUND_REJECTED','REFUND_EXECUTED','REFUND_FAILED','PAYMENT_REFUNDED')"
)

STATEMENTS: tuple[str, ...] = (
    """CREATE TABLE IF NOT EXISTS customers (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL CHECK (length(name) >= 1),
  role TEXT NOT NULL CHECK (role IN ('customer','ops','admin')),
  created_at TEXT NOT NULL)""",
    f"""CREATE TABLE IF NOT EXISTS payments (
  id TEXT PRIMARY KEY,
  customer_id TEXT NOT NULL REFERENCES customers(id),
  idempotency_key TEXT NOT NULL CHECK (length(idempotency_key) BETWEEN 1 AND 128),
  request_hash TEXT NOT NULL,
  amount_paise INTEGER NOT NULL CHECK (amount_paise >= 100),
  rail TEXT NOT NULL CHECK (rail IN {_RAILS}),
  beneficiary TEXT NOT NULL CHECK (length(beneficiary) BETWEEN 1 AND 140),
  state TEXT NOT NULL CHECK (state IN ('CREATED','SUBMITTED','COMPLETED','FAILED','REFUNDED')),
  reason_code TEXT,
  rail_reference TEXT,
  submitted_at TEXT,
  completed_at TEXT,
  stuck_flagged_at TEXT,
  idempotency_released_at TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  CHECK (state <> 'COMPLETED' OR (rail_reference IS NOT NULL AND completed_at IS NOT NULL)),
  CHECK (state <> 'FAILED' OR reason_code IS NOT NULL))""",
    """CREATE UNIQUE INDEX IF NOT EXISTS ux_payments_customer_key
  ON payments(customer_id, idempotency_key) WHERE idempotency_released_at IS NULL""",
    """CREATE INDEX IF NOT EXISTS ix_payments_customer_created
  ON payments(customer_id, created_at DESC, id DESC)""",
    "CREATE INDEX IF NOT EXISTS ix_payments_created ON payments(created_at DESC, id DESC)",
    "CREATE INDEX IF NOT EXISTS ix_payments_state_submitted ON payments(state, submitted_at)",
    """CREATE INDEX IF NOT EXISTS ix_payments_completed_at
  ON payments(completed_at) WHERE state = 'COMPLETED'""",
    """CREATE TABLE IF NOT EXISTS payment_attempts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  payment_id TEXT NOT NULL REFERENCES payments(id),
  attempt_no INTEGER NOT NULL CHECK (attempt_no BETWEEN 1 AND 5),
  outcome TEXT NOT NULL CHECK (outcome IN ('success','transient','permanent')),
  error_code TEXT,
  at TEXT NOT NULL,
  UNIQUE (payment_id, attempt_no))""",
    """CREATE TABLE IF NOT EXISTS outbox_messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  payment_id TEXT NOT NULL UNIQUE REFERENCES payments(id),
  status TEXT NOT NULL CHECK (status IN ('PENDING','IN_PROGRESS','SENT')),
  next_attempt_at TEXT NOT NULL,
  attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts BETWEEN 0 AND 5),
  claimed_at TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL)""",
    "CREATE INDEX IF NOT EXISTS ix_outbox_due ON outbox_messages(status, next_attempt_at)",
    f"""CREATE TABLE IF NOT EXISTS payment_events (
  id TEXT PRIMARY KEY,
  payment_id TEXT NOT NULL REFERENCES payments(id),
  type TEXT NOT NULL CHECK (type IN {_EVENTS}),
  payload TEXT NOT NULL DEFAULT '{{}}' CHECK (json_valid(payload)),
  at TEXT NOT NULL)""",
    "CREATE INDEX IF NOT EXISTS ix_events_payment ON payment_events(payment_id)",
    """CREATE TRIGGER IF NOT EXISTS trg_payment_events_no_update BEFORE UPDATE ON payment_events
BEGIN SELECT RAISE(ABORT, 'payment_events is append-only'); END""",
    """CREATE TRIGGER IF NOT EXISTS trg_payment_events_no_delete BEFORE DELETE ON payment_events
BEGIN SELECT RAISE(ABORT, 'payment_events is append-only'); END""",
    """CREATE TABLE IF NOT EXISTS refunds (
  id TEXT PRIMARY KEY,
  payment_id TEXT NOT NULL UNIQUE REFERENCES payments(id),
  amount_paise INTEGER NOT NULL CHECK (amount_paise >= 100),
  state TEXT NOT NULL
    CHECK (state IN ('REQUESTED','APPROVED','EXECUTED','REJECTED','FAILED')),
  requested_by TEXT NOT NULL REFERENCES customers(id),
  decided_by TEXT REFERENCES customers(id),
  reason_code TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL)""",
    "CREATE INDEX IF NOT EXISTS ix_refunds_state ON refunds(state)",
    f"""CREATE TABLE IF NOT EXISTS rail_statement_entries (
  id TEXT PRIMARY KEY,
  rail TEXT NOT NULL CHECK (rail IN {_RAILS}),
  payment_ref TEXT NOT NULL,
  payment_id TEXT,
  amount_paise INTEGER NOT NULL CHECK (amount_paise >= 0),
  status TEXT CHECK (status IS NULL OR status IN {_RECON}),
  statement_date TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE (rail, payment_ref, statement_date))""",
    """CREATE INDEX IF NOT EXISTS ix_statement_date
  ON rail_statement_entries(statement_date)""",
    f"""CREATE TABLE IF NOT EXISTS reconciliation_results (
  id TEXT PRIMARY KEY,
  statement_date TEXT NOT NULL,
  rail TEXT NOT NULL CHECK (rail IN {_RAILS}),
  status TEXT NOT NULL CHECK (status IN {_RECON}),
  payment_id TEXT REFERENCES payments(id),
  statement_entry_id TEXT REFERENCES rail_statement_entries(id),
  payment_ref TEXT,
  payment_amount_paise INTEGER,
  statement_amount_paise INTEGER,
  resolved INTEGER NOT NULL DEFAULT 0 CHECK (resolved IN (0,1)),
  resolution_note TEXT,
  resolved_by TEXT REFERENCES customers(id),
  resolved_at TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  CHECK (payment_id IS NOT NULL OR statement_entry_id IS NOT NULL),
  CHECK (resolved = 0 OR resolution_note IS NOT NULL))""",
    """CREATE UNIQUE INDEX IF NOT EXISTS ux_recon_key ON reconciliation_results(
  statement_date, rail, COALESCE(payment_id,''), COALESCE(statement_entry_id,''))""",
    "CREATE INDEX IF NOT EXISTS ix_recon_queue ON reconciliation_results(resolved, status)",
    """CREATE TABLE IF NOT EXISTS settlement_files (
  id TEXT PRIMARY KEY,
  business_date TEXT NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('primary','followup')),
  sequence INTEGER NOT NULL,
  path TEXT NOT NULL UNIQUE,
  row_count INTEGER NOT NULL CHECK (row_count >= 0),
  checksum TEXT NOT NULL,
  written_at TEXT NOT NULL,
  CHECK ((kind = 'primary') = (sequence = 0)),
  UNIQUE (business_date, sequence))""",
    """CREATE TRIGGER IF NOT EXISTS trg_settlement_files_no_update
BEFORE UPDATE ON settlement_files
BEGIN SELECT RAISE(ABORT, 'settlement_files is append-only'); END""",
    """CREATE TRIGGER IF NOT EXISTS trg_settlement_files_no_delete
BEFORE DELETE ON settlement_files
BEGIN SELECT RAISE(ABORT, 'settlement_files is append-only'); END""",
)
