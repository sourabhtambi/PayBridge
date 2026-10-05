import json
from pathlib import Path
from typing import Any

CORPUS_PATH = Path(__file__).resolve().parents[3] / "specs/test_artefacts/recon_corpus.json"


def load_corpus() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(CORPUS_PATH.read_text())
    return data
