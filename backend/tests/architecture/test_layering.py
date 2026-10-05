"""Structural tests enforcing the layered architecture (NFR-08).

Layer order (low to high): types -> config -> repository -> service -> api.
Imports are read from the AST, so comments and strings never cause false hits.
"""

import ast
from pathlib import Path

import pytest

PACKAGE = "paybridge"
SRC_ROOT = Path(__file__).resolve().parents[2] / "src" / PACKAGE

# Layers above the key are forbidden imports for it.
LAYERS = ("types", "config", "repository", "service", "api")

# Known api -> repository violations (routes holding business logic; see
# claude-progress.txt "clean-code review"). Ratchet: new entries must not be
# added, and an entry must be deleted once its file is fixed.
API_REPOSITORY_BASELINE = frozenset(
    {
        "api/routes/customers.py",
        "api/routes/dashboard.py",
        "api/routes/payments.py",
        "api/routes/reconciliation.py",
        "api/routes/refunds.py",
        "api/routes/settlement.py",
    }
)
# Composition root: wires repositories into services, so it may import them.
API_COMPOSITION_ROOT = frozenset({"api/app.py", "api/container.py", "api/deps.py"})


def _imported_modules(path: Path) -> set[str]:
    modules: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            modules.add(node.module)
            modules.update(f"{node.module}.{alias.name}" for alias in node.names)
    return modules


def _layer_files(layer: str) -> list[Path]:
    return sorted((SRC_ROOT / layer).rglob("*.py"))


def _imports_layer(path: Path, layer: str) -> list[str]:
    prefix = f"{PACKAGE}.{layer}"
    return sorted(
        m for m in _imported_modules(path) if m == prefix or m.startswith(prefix + ".")
    )


def _violations(source_layer: str, forbidden: tuple[str, ...]) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for path in _layer_files(source_layer):
        hits = [m for layer in forbidden for m in _imports_layer(path, layer)]
        if hits:
            found[path.relative_to(SRC_ROOT).as_posix()] = hits
    return found


def test_layer_directories_exist() -> None:
    for layer in LAYERS:
        assert _layer_files(layer), f"no python files found for layer {layer!r}"


def test_api_does_not_import_repository_directly() -> None:
    """NFR-08: api must go through services, not repositories."""
    violating = set(_violations("api", ("repository",)))
    new = violating - API_REPOSITORY_BASELINE - API_COMPOSITION_ROOT
    assert not new, f"new api -> repository imports: {sorted(new)}"


def test_api_repository_baseline_is_not_stale() -> None:
    """Ratchet: once a file is fixed, remove it from the baseline."""
    violating = set(_violations("api", ("repository",)))
    stale = API_REPOSITORY_BASELINE - violating
    assert not stale, f"fixed files still in baseline, remove them: {sorted(stale)}"


def test_service_does_not_import_api() -> None:
    assert _violations("service", ("api",)) == {}


def test_types_does_not_import_any_other_layer() -> None:
    assert _violations("types", ("config", "repository", "service", "api")) == {}


@pytest.mark.parametrize(
    ("layer", "forbidden"),
    [
        ("config", ("repository", "service", "api")),
        ("repository", ("service", "api")),
    ],
)
def test_lower_layers_do_not_import_upward(layer: str, forbidden: tuple[str, ...]) -> None:
    assert _violations(layer, forbidden) == {}


def test_import_scanner_detects_violations(tmp_path: Path) -> None:
    """Guards the guard: the scanner must actually flag a bad import."""
    bad = tmp_path / "bad.py"
    bad.write_text("from paybridge.api.app import create_app\nimport paybridge.service.x\n")
    assert _imports_layer(bad, "api") == ["paybridge.api.app", "paybridge.api.app.create_app"]
    assert _imports_layer(bad, "service") == ["paybridge.service.x"]
    assert _imports_layer(bad, "repository") == []
