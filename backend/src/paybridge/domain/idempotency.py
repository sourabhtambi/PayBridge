"""Request hashing for idempotent payment creation."""

import hashlib
import json


def request_hash(amount_paise: int, beneficiary: str) -> str:
    canonical = json.dumps(
        {"amount_paise": amount_paise, "beneficiary": beneficiary},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode()).hexdigest()
