"""Test setup.

Skips the whole suite with a clear message if `modbus_connection` isn't
installed (e.g. running under Python <3.12, or before the dependency is
actually installed). This keeps `pytest` runnable in this repo's scaffold
state without a misleading collection error.
"""

import pytest

modbus_connection = pytest.importorskip(
    "modbus_connection",
    reason=(
        "modbus-connection not installed (requires Python >=3.12). "
        "See README.md: set up a 3.12 venv and `pip install -e .[dev]`."
    ),
)
