"""
Mock harness that loads sas_dbx.py as an importable module outside Databricks.

sas_dbx.py is a Databricks notebook file: it references `dbutils` as a
runtime-injected global (never imported) and imports the `sas2databricks`
package. Neither exists in a plain pytest environment, so this conftest
stubs both just enough to let the module's top-level code execute safely,
which gives the tests direct access to the real functions defined in the
file (translate_merge_to_join, translate_retain_to_window, etc.) with no
modifications to sas_dbx.py itself.

USAGE
-----
1. Place this file, test_sas_dbx_converter.py, and sas_dbx.py in the same
   directory (or set the SAS_DBX_PATH environment variable to sas_dbx.py's
   location).
2. pip install pytest
3. pytest -v
"""
import importlib.util
import os
import sys
import types

import pytest


class _MockWidgets:
    """Stands in for dbutils.widgets. Returns sensible defaults for every
    widget sas_dbx.py creates, regardless of call order."""

    def __init__(self):
        self._values = {
            "catalog": "test_catalog",
            "schema_prefix": "sas",
            "enable_views": "true",
            "api_style": "dp",
        }

    def text(self, name, default, *_args, **_kwargs):
        self._values.setdefault(name, default)

    def dropdown(self, name, default, *_args, **_kwargs):
        self._values.setdefault(name, default)

    def get(self, name):
        return self._values.get(name, "")


class _MockFS:
    def mkdirs(self, _path):
        return True


class _MockLibrary:
    def restartPython(self):
        # Real Databricks restarts the Python process here. Outside
        # Databricks this is a no-op; the module's re-imports afterward
        # (from sas2databricks import migrate, etc.) just run again safely.
        return None


class _MockNotebook:
    def exit(self, _msg):
        # Real Databricks halts the notebook here via an internal
        # exception. Outside Databricks we let execution fall through --
        # harmless, since the file-scanning loop below it finds zero
        # files in the test environment (no /Volumes/... path exists)
        # and every subsequent block is a no-op on an empty list.
        return None


class _MockDbutils:
    def __init__(self):
        self.widgets = _MockWidgets()
        self.fs = _MockFS()
        self.library = _MockLibrary()
        self.notebook = _MockNotebook()


class _MockMigrateResult:
    def __init__(self, code):
        self.code = code


def _mock_migrate(sas_text, target="dlt", source_path=None):
    """Stand-in for sas2databricks.migrate. The functions under test
    (translate_merge_to_join, parse_sas_datalines, etc.) operate on raw
    SAS text directly and don't need a real conversion to run -- this
    stub only exists so `from sas2databricks import migrate` succeeds."""
    return _MockMigrateResult(code="# stub conversion output\n")


@pytest.fixture(scope="session")
def sas_dbx_module():
    """Load sas_dbx.py with Databricks globals mocked, and hand back the
    live module so tests can call its functions directly."""
    # Try multiple possible locations for sas_dbx.py
    possible_paths = [
        os.environ.get("SAS_DBX_PATH"),
        os.path.join(os.path.dirname(__file__), "sas_dbx.py"),
        os.path.join(os.path.dirname(__file__), "..", "src", "converter", "sas_dbx.py"),
    ]

    path = None
    for p in possible_paths:
        if p and os.path.exists(p):
            path = p
            break

    if not path:
        pytest.skip(
            f"sas_dbx.py not found. Tried: {possible_paths}. "
            f"Place it alongside the test files, or set the SAS_DBX_PATH environment variable."
        )

    fake_pkg = types.ModuleType("sas2databricks")
    fake_pkg.migrate = _mock_migrate
    sys.modules["sas2databricks"] = fake_pkg

    spec = importlib.util.spec_from_file_location("sas_dbx_converter", path)
    module = importlib.util.module_from_spec(spec)
    module.dbutils = _MockDbutils()  # injected before exec, like Databricks does
    sys.modules["sas_dbx_converter"] = module
    spec.loader.exec_module(module)
    return module
