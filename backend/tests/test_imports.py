"""Tests guarding the import graph of the application packages.

The schema layer used to import a constant from the AI layer, which closed a
cycle between :mod:`app.schemas` and :mod:`app.ai`.  Depending on which module
was imported first, that cycle made the package unimportable.  These tests
pin the import order that used to fail.
"""

import ast
import importlib
import subprocess
import sys
from pathlib import Path

#: Modules that must be importable on their own, in a fresh interpreter.
IMPORTABLE_MODULES = [
    "app.core.constants",
    "app.schemas",
    "app.schemas.ai",
    "app.ai",
    "app.ai.analyzer",
    "app.ai.parsing",
    "app.ai.factory",
    "app.core.csv_export",
    "app.api.admin_reviews",
    "app.api.auth",
    "main",
]

#: Import orders that used to raise ``ImportError`` because of the cycle.
IMPORT_ORDERS = [
    ["app.schemas", "app.ai", "app.core.csv_export"],
    ["app.ai", "app.schemas", "app.core.csv_export"],
    ["app.schemas.ai", "app.ai.factory"],
    ["app.ai.parsing", "app.schemas.ai"],
]


def _run_fresh_interpreter(module_names: list[str]) -> subprocess.CompletedProcess[str]:
    """Import the given modules in a brand new interpreter.

    Running in a subprocess guarantees that no module from the test session is
    already in ``sys.modules``, which is exactly the situation in which an
    import cycle surfaces.

    Args:
        module_names: The modules to import, in the given order.

    Returns:
        The completed process holding the interpreter output.
    """
    backend_root = Path(__file__).resolve().parent.parent
    program = "; ".join(f"import {name}" for name in module_names) + "; print('OK')"
    return subprocess.run(
        [sys.executable, "-c", program],
        capture_output=True,
        text=True,
        cwd=backend_root,
        check=False,
    )


def test_every_module_imports_in_a_fresh_interpreter() -> None:
    """All application modules import together without an import error."""
    result = _run_fresh_interpreter(IMPORTABLE_MODULES)

    assert result.returncode == 0, f"import failed:\n{result.stderr}"


def test_import_order_does_not_raise() -> None:
    """Importing the schema and AI layers in either order works.

    The two orders are checked in one interpreter each, because the failure
    only shows up when a module is imported before its partner has finished
    initialising.
    """
    for module_names in IMPORT_ORDERS:
        result = _run_fresh_interpreter(module_names)

        assert result.returncode == 0, f"import {module_names} failed:\n{result.stderr}"


def test_schema_layer_does_not_import_the_ai_layer() -> None:
    """The schema layer must not depend on the AI layer.

    A dependency from the schemas to the AI package is what closed the import
    cycle, so the direction is asserted explicitly rather than left to the
    import-order tests above.
    """
    module = importlib.import_module("app.schemas.ai")
    tree = ast.parse(Path(str(module.__file__)).read_text(encoding="utf-8"))

    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
        elif isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)

    assert not [name for name in imported if name == "app.ai" or name.startswith("app.ai.")], (
        "app.schemas.ai must not import anything from app.ai"
    )


def test_language_code_limit_is_shared_by_both_layers() -> None:
    """Both layers read the limit from the same shared constant."""
    from app.ai import parsing
    from app.core import constants
    from app.schemas import ai

    assert parsing.MAX_LANGUAGE_CODE_LENGTH == constants.MAX_LANGUAGE_CODE_LENGTH == ai.MAX_LANGUAGE_CODE_LENGTH
