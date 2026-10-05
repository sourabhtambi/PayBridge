"""Prefixed identifier generators: prefix plus 12 hex characters."""

from uuid import uuid4


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


def new_payment_id() -> str:
    return _new_id("pay")


def new_refund_id() -> str:
    return _new_id("rfd")


def new_reconciliation_id() -> str:
    return _new_id("rec")


def new_settlement_id() -> str:
    return _new_id("stl")


def new_event_id() -> str:
    return _new_id("evt")


def new_statement_entry_id() -> str:
    return _new_id("rse")
