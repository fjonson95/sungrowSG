"""Test setup.

Skips the whole suite with a clear message if `modbus_connection` isn't
installed (e.g. running under Python <3.12, or before the dependency is
actually installed). This keeps `pytest` runnable in this repo's scaffold
state without a misleading collection error.

The `mock_modbus_connection`/`mock_modbus_unit` fixtures used in
test_models.py come from `modbus_connection`'s own pytest plugin
(registered automatically via its `pytest11` entry point - no wiring
needed here). They're an in-memory `MockModbusUnit`, not a real socket
server: good enough to catch register-plumbing bugs (wrong register
space, wrong address, wrong scale) without needing real hardware, but not
a substitute for testing against an actual inverter.
"""

import pytest

modbus_connection = pytest.importorskip(
    "modbus_connection",
    reason=(
        "modbus-connection not installed (requires Python >=3.12). "
        "See README.md: set up a 3.12+ venv and "
        "`pip install -e library/sungrow-modbus[dev]`."
    ),
)
