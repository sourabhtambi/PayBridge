import logging

import pytest

from paybridge.config.logging_setup import MaskingFilter, install_masking
from paybridge.lib.masking import mask_name, mask_text, register_sensitive


def _record(msg: str, **extra: object) -> logging.LogRecord:
    rec = logging.LogRecord("t", logging.INFO, "f", 1, msg, None, None)
    rec.__dict__.update(extra)
    return rec


def test_mask_name() -> None:
    assert mask_name("Ravi Kumar") == "R*** K***"


def test_registered_beneficiary_masked_in_message_and_extra() -> None:
    register_sensitive("Ravi Kumar")
    rec = _record("paid Ravi Kumar", who="to Ravi Kumar")
    MaskingFilter().filter(rec)
    assert rec.getMessage() == "paid R*** K***"
    assert rec.who == "to R*** K***"  # type: ignore[attr-defined]


def test_digits_masked_to_last_four() -> None:
    assert mask_text("acct 123456789 and 1234567890123456") == (
        "acct *****6789 and ************3456"
    )
    assert mask_text("short 12345678") == "short 12345678"


def test_blank_not_registered() -> None:
    register_sensitive("  ")
    assert mask_text("a b") == "a b"


def test_traceback_masked() -> None:
    register_sensitive("Asha Rao")
    try:
        raise ValueError("bad Asha Rao 9876543210")
    except ValueError:
        import sys

        rec = _record("failed")
        rec.exc_info = sys.exc_info()
    MaskingFilter().filter(rec)
    assert rec.exc_text is not None
    assert "Asha Rao" not in rec.exc_text and "9876543210" not in rec.exc_text
    assert "A*** R***" in rec.exc_text


def test_existing_exc_text_masked() -> None:
    register_sensitive("Asha Rao")
    rec = _record("x")
    rec.exc_text = "Asha Rao"
    MaskingFilter().filter(rec)
    assert rec.exc_text == "A*** R***"


def test_install_idempotent(caplog: pytest.LogCaptureFixture) -> None:
    original = logging.getLogRecordFactory()
    try:
        install_masking()
        installed = logging.getLogRecordFactory()
        install_masking()
        assert logging.getLogRecordFactory() is installed
        register_sensitive("Meera Nair")
        with caplog.at_level(logging.INFO):
            logging.getLogger("x").info("hi %s", "Meera Nair")
        assert "Meera" not in caplog.text
    finally:
        logging.setLogRecordFactory(original)


def test_uvicorn_access_record_formats_with_masking() -> None:
    original = logging.getLogRecordFactory()
    try:
        install_masking()
        register_sensitive("Kavya Menon")
        rec = logging.getLogRecordFactory()(
            "uvicorn.access",
            logging.INFO,
            "f",
            1,
            '%s - "%s %s HTTP/%s" %d',
            ("127.0.0.1:1", "GET", "/pay/Kavya Menon/1234567890", "1.1", 200),
            None,
        )
        assert isinstance(rec.args, tuple) and len(rec.args) == 5
        out = logging.Formatter("%(message)s").format(rec)
        assert "Kavya" not in out and "1234567890" not in out
        assert "K*** M***" in out and "200" in out
    finally:
        logging.setLogRecordFactory(original)


def test_dict_args_masked_in_place() -> None:
    register_sensitive("Kavya Menon")
    rec = logging.LogRecord("t", logging.INFO, "f", 1, "%(n)s", None, None)
    rec.args = {"n": "Kavya Menon"}
    MaskingFilter().filter(rec)
    assert rec.getMessage() == "K*** M***"


def test_registry_capped_evicts_oldest(monkeypatch: pytest.MonkeyPatch) -> None:
    from paybridge.lib import masking

    monkeypatch.setattr(masking, "MAX_REGISTERED", 2)
    monkeypatch.setattr(masking, "_registered", {})
    monkeypatch.setattr(masking, "_pattern", None)
    for n in ("Aaa Bbb", "Ccc Ddd", "Eee Fff"):
        register_sensitive(n)
    assert mask_text("Aaa Bbb Ccc Ddd Eee Fff") == "Aaa Bbb C*** D*** E*** F***"


def test_pattern_cached_until_registry_changes(monkeypatch: pytest.MonkeyPatch) -> None:
    from paybridge.lib import masking

    monkeypatch.setattr(masking, "_registered", {})
    monkeypatch.setattr(masking, "_pattern", None)
    register_sensitive("Gus Hill")
    mask_text("x")
    first = masking._pattern
    mask_text("y")
    assert masking._pattern is first
    register_sensitive("Gus Hill")  # unchanged
    assert masking._pattern is first
    register_sensitive("Ian Jay")
    mask_text("z")
    assert masking._pattern is not first
