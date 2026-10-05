"""Masking of sensitive values (beneficiary names, account numbers) in text."""

import re
import threading

MAX_REGISTERED = 50_000
_DIGITS = re.compile(r"\d{9,18}")
_registered: dict[str, None] = {}
_pattern: re.Pattern[str] | None = None
_lock = threading.Lock()


def mask_name(name: str) -> str:
    """Mask each word to its first letter: 'Ravi Kumar' -> 'R*** K***'."""
    return " ".join(word[0] + "***" for word in name.split())


def register_sensitive(value: str) -> None:
    """Register a value that must never appear verbatim in logs (oldest evicted at cap)."""
    global _pattern
    value = value.strip()
    if not value:
        return
    with _lock:
        if value in _registered:
            return
        _registered[value] = None
        while len(_registered) > MAX_REGISTERED:
            del _registered[next(iter(_registered))]
        _pattern = None


def _current_pattern() -> re.Pattern[str] | None:
    global _pattern
    with _lock:
        if _pattern is None and _registered:
            names = sorted(_registered, key=len, reverse=True)
            _pattern = re.compile("|".join(re.escape(v) for v in names))
        return _pattern


def mask_text(text: str) -> str:
    """Mask registered values and long digit sequences in text."""
    pattern = _current_pattern()
    if pattern is not None:
        text = pattern.sub(lambda m: mask_name(m.group()), text)
    return _DIGITS.sub(lambda m: "*" * (len(m.group()) - 4) + m.group()[-4:], text)
