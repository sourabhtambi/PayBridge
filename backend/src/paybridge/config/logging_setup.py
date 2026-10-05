"""Logging filter that masks sensitive data in records."""

import logging
import traceback
from typing import Any

from paybridge.lib.masking import mask_text

_STANDARD = set(logging.makeLogRecord({}).__dict__) | {"message", "asctime"}


class MaskingFilter(logging.Filter):
    """Masks message, extra string fields and exception tracebacks."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = mask_text(record.msg)
        if isinstance(record.args, tuple):
            record.args = tuple(mask_text(a) if isinstance(a, str) else a for a in record.args)
        elif isinstance(record.args, dict):
            record.args = {
                k: mask_text(v) if isinstance(v, str) else v for k, v in record.args.items()
            }
        for key, value in list(record.__dict__.items()):
            if key not in _STANDARD and isinstance(value, str):
                setattr(record, key, mask_text(value))
        if record.exc_info and record.exc_info[0] is not None:
            record.exc_text = mask_text("".join(traceback.format_exception(*record.exc_info)))
            record.exc_info = None
        elif record.exc_text:
            record.exc_text = mask_text(record.exc_text)
        return True


def install_masking() -> None:
    """Mask every record at creation via the record factory (idempotent)."""
    previous = logging.getLogRecordFactory()
    if getattr(previous, "masking", False):
        return
    masker = MaskingFilter()

    def factory(*args: Any, **kwargs: Any) -> logging.LogRecord:  # noqa: ANN401
        record = previous(*args, **kwargs)
        masker.filter(record)
        return record

    factory.masking = True  # type: ignore[attr-defined]
    logging.setLogRecordFactory(factory)
