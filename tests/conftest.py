"""Shared fixtures for the Sungrow SG-series integration tests.

Tests never touch a real inverter or open a real socket: every
`ModbusConnection(...)` call the integration makes is monkeypatched to
go through `FakeModbusConnectionFactory` below, which hands out fresh
`modbus_connection.mock.MockModbusConnection` instances (the same
in-memory test double `library/sungrow-modbus`'s own tests use) backed
by one shared register store. That means `SungrowSGCoordinator`/
`SungrowSGInverter` run their real decode logic - only the actual TCP
layer is faked.
"""

from __future__ import annotations

import sys
from collections.abc import Generator

import pytest
import pytest_socket
from modbus_connection.mock import MockModbusConnection, MockModbusUnit

from custom_components.sungrow_sg.sungrow_modbus import registers as reg

if sys.platform == "win32":
    # Windows has no real AF_UNIX socketpair, so asyncio's own internal
    # wakeup pipe (ProactorEventLoop._make_self_pipe) falls back to a
    # real loopback AF_INET pair. pytest-homeassistant-custom-component's
    # own pytest_runtest_setup hook unconditionally calls
    # pytest_socket.disable_socket(allow_unix_socket=True) before every
    # test, expecting that carve-out to cover exactly this wakeup socket
    # - true on Linux/macOS, but pytest_socket._is_unix_socket() is
    # hardcoded to always return False on Windows ("AF_UNIX not
    # supported"), so the carve-out never applies here and every event
    # loop creation gets blocked. No CLI flag reaches this (the plugin
    # calls the pytest_socket API directly, bypassing --allow-hosts).
    # Patched at import time, before the plugin below gets a chance to
    # import pytest_socket itself, so both get the same (patched) module
    # object. Windows-only: on Linux (e.g. CI) AF_UNIX works natively,
    # and this patch would only weaken pytest_socket's real
    # "block tests from touching the internet" guard for no reason.
    pytest_socket._is_unix_socket = lambda family: True

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Make custom_components/sungrow_sg loadable by `hass` in every test."""


class FakeModbusConnectionFactory:
    """Callable stand-in for `ModbusConnection`, patched in as the class
    itself (so `ModbusConnection(params)` calls become `factory(params)`).

    Every call constructs a genuinely fresh `MockModbusConnection` -
    matching production, where config_flow.py's one-shot probe and
    coordinator.py's persistent connection each construct their own
    `ModbusConnection(...)`. A real `ModbusConnection` can't reconnect
    once `close()`'d (confirmed against the actual package: it raises
    `ClientClosedError`), so a naive "always return the same instance"
    fake would make config_flow.py's first (deliberately closed) probe
    attempt permanently break every later one - a bug in the test double,
    not in `_async_try_connect`.

    All connections created here share one persistent `MockModbusUnit`
    (same register store, same fail_requests/read_events state) - "same
    physical inverter, new TCP session," not "state resets on reconnect."
    `connected` reflects the most recently created connection, which is
    always the one the integration is currently holding onto.
    """

    def __init__(self) -> None:
        self._unit: MockModbusUnit | None = None
        self.connections: list[MockModbusConnection] = []

    def __call__(self, *_args: object, **_kwargs: object) -> MockModbusConnection:
        connection = MockModbusConnection()
        if self._unit is None:
            self._unit = connection.for_unit(1)
        else:
            self._unit._conn = connection
            connection._units[1] = self._unit
        self.connections.append(connection)
        return connection

    def for_unit(self, unit_id: int) -> MockModbusUnit:
        assert unit_id == 1, "only unit 1 is modeled in these tests"
        if self._unit is None:
            self()
        assert self._unit is not None
        return self._unit

    @property
    def connected(self) -> bool:
        return bool(self.connections) and self.connections[-1].connected


@pytest.fixture
def mock_connection(
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[FakeModbusConnectionFactory]:
    """Patch the integration so every ModbusConnection(...) call goes
    through one `FakeModbusConnectionFactory` (see its docstring).

    Patched at both call sites - config_flow.py's one-shot probe and
    coordinator.py's persistent polling connection - each constructs its
    own `ModbusConnection`.
    """
    factory = FakeModbusConnectionFactory()

    monkeypatch.setattr(
        "custom_components.sungrow_sg.coordinator.ModbusConnection", factory
    )
    monkeypatch.setattr(
        "custom_components.sungrow_sg.config_flow.ModbusConnection", factory
    )
    yield factory


def _ascii_words(text: str) -> list[int]:
    """Pack ASCII text into 16-bit big-endian register words (2 chars each)."""
    data = text.encode("ascii")
    if len(data) % 2:
        data += b"\x00"
    return [(data[i] << 8) | data[i + 1] for i in range(0, len(data), 2)]


def _write_le32(unit: MockModbusUnit, spec: reg.RegisterSpec, value: int) -> None:
    """Write a little-endian 32-bit register pair (see registers.py word-order note)."""
    raw = value & 0xFFFFFFFF
    unit.input[spec.address] = raw & 0xFFFF
    unit.input[spec.address + 1] = (raw >> 16) & 0xFFFF


# A coherent "typical daytime" snapshot - same shape/magnitudes as a real
# SG12RT live-confirmed against (see docs/register_map.md), with clean
# round numbers instead of the noisy live readings so assertions are
# exact. Every value here is deliberately internally consistent, e.g.
# meter_a + meter_b + meter_c == meter_power.
EXPECTED_READINGS: dict[str, object] = {
    "model_name": "SG12RT",
    "serial_number": "A2322404773",
    "protocol_version": "1.1.25.0",
    "phase_a_voltage": 233.6,
    "phase_b_voltage": 236.6,
    "phase_c_voltage": 234.4,
    "phase_a_current": 4.8,
    "phase_b_current": 4.8,
    "phase_c_current": 4.8,
    "total_active_power": 3370,
    "total_reactive_power": 4,
    "total_apparent_power": 3370,
    "power_factor": 1.0,
    "grid_frequency": 49.9,
    "mppt_1_voltage": 632.1,
    "mppt_1_current": 3.1,
    "mppt_2_voltage": 487.5,
    "mppt_2_current": 3.1,
    "total_dc_power": 3470,
    "bus_voltage": 677.0,
    "negative_voltage_to_ground": 0.0,
    "string_1_current": 2.98,
    "string_2_current": 0.0,
    "string_3_current": 3.12,
    "daily_power_yield": 8.4,
    "total_power_yield": 38258.3,
    "total_running_time": 12228,
    "meter_power": 150,
    "meter_a_phase_power": 200,
    "meter_b_phase_power": -100,
    "meter_c_phase_power": 50,
    "load_power": 3500,
    "daily_export_energy": 1.4,
    "total_export_energy": 21214.1,
    "daily_import_energy": 1.6,
    "total_import_energy": 26036.4,
    "daily_direct_energy_consumption": 0.0,
    "total_direct_energy_consumption": 0.0,
    "internal_temperature": 44.7,
    "nominal_active_power": 12.0,
    "nominal_reactive_power": 6.0,
    "array_insulation_resistance": 1748,
    "work_state_1_label": "run",
    "work_state_2": 0x20001,
    "output_type_label": "three_phase_4l",
}


def populate_realistic_readings(unit: MockModbusUnit) -> None:
    """Fill a MockModbusUnit so it decodes to exactly EXPECTED_READINGS."""
    unit.input[reg.DEVICE_TYPE_CODE.address] = 0x2434  # SG12RT
    for i, word in enumerate(_ascii_words("A2322404773")):
        unit.input[reg.SERIAL_NUMBER.address + i] = word
    _write_le32(unit, reg.PROTOCOL_VERSION, 0x01011900)  # V1.1.25.0

    unit.input[reg.NOMINAL_ACTIVE_POWER.address] = 120  # 12.0 kW
    unit.input[reg.OUTPUT_TYPE.address] = 1  # 3P4L

    unit.input[reg.DAILY_POWER_YIELD.address] = 84
    _write_le32(unit, reg.TOTAL_POWER_YIELD, 382583)
    _write_le32(unit, reg.TOTAL_RUNNING_TIME, 12228)

    unit.input[reg.INTERNAL_TEMPERATURE.address] = 447
    _write_le32(unit, reg.TOTAL_APPARENT_POWER, 3370)

    unit.input[reg.MPPT_1_VOLTAGE.address] = 6321
    unit.input[reg.MPPT_1_CURRENT.address] = 31
    unit.input[reg.MPPT_2_VOLTAGE.address] = 4875
    unit.input[reg.MPPT_2_CURRENT.address] = 31
    _write_le32(unit, reg.TOTAL_DC_POWER, 3470)

    unit.input[reg.PHASE_A_VOLTAGE.address] = 2336
    unit.input[reg.PHASE_B_VOLTAGE.address] = 2366
    unit.input[reg.PHASE_C_VOLTAGE.address] = 2344
    unit.input[reg.PHASE_A_CURRENT.address] = 48
    unit.input[reg.PHASE_B_CURRENT.address] = 48
    unit.input[reg.PHASE_C_CURRENT.address] = 48

    _write_le32(unit, reg.TOTAL_ACTIVE_POWER, 3370)
    _write_le32(unit, reg.TOTAL_REACTIVE_POWER, 4)
    unit.input[reg.POWER_FACTOR.address] = 1000
    unit.input[reg.GRID_FREQUENCY.address] = 499

    unit.input[reg.WORK_STATE_1.address] = 0x0  # run
    _write_le32(unit, reg.WORK_STATE_2, 0x20001)  # running + grid connected
    unit.input[reg.NOMINAL_REACTIVE_POWER.address] = 60
    unit.input[reg.ARRAY_INSULATION_RESISTANCE.address] = 1748

    unit.input[reg.STRING_1_CURRENT.address] = 298
    unit.input[reg.STRING_2_CURRENT.address] = 0
    unit.input[reg.STRING_3_CURRENT.address] = 312

    _write_le32(unit, reg.METER_POWER, 150)
    _write_le32(unit, reg.METER_A_PHASE_POWER, 200)
    _write_le32(unit, reg.METER_B_PHASE_POWER, -100)
    _write_le32(unit, reg.METER_C_PHASE_POWER, 50)
    _write_le32(unit, reg.LOAD_POWER, 3500)
    _write_le32(unit, reg.DAILY_EXPORT_ENERGY, 14)
    _write_le32(unit, reg.TOTAL_EXPORT_ENERGY, 212141)
    _write_le32(unit, reg.DAILY_IMPORT_ENERGY, 16)
    _write_le32(unit, reg.TOTAL_IMPORT_ENERGY, 260364)
    _write_le32(unit, reg.DAILY_DIRECT_ENERGY_CONSUMPTION, 0)
    _write_le32(unit, reg.TOTAL_DIRECT_ENERGY_CONSUMPTION, 0)

    unit.input[reg.NEGATIVE_VOLTAGE_TO_GROUND.address] = 0
    unit.input[reg.BUS_VOLTAGE.address] = 6770


@pytest.fixture
def populated_mock_connection(
    mock_connection: FakeModbusConnectionFactory,
) -> FakeModbusConnectionFactory:
    """`mock_connection`, pre-loaded with a coherent reading (see EXPECTED_READINGS)."""
    populate_realistic_readings(mock_connection.for_unit(1))
    return mock_connection
