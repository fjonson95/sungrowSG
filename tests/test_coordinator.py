"""Tests for SungrowSGCoordinator."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed
from modbus_connection import ModbusTimeoutError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sungrow_sg.const import (
    CONF_INCLUDE_METER,
    CONF_INCLUDE_MPPT,
    CONF_INCLUDE_STRINGS,
    CONF_UNIT_ID,
    DOMAIN,
)
from custom_components.sungrow_sg.coordinator import SungrowSGCoordinator

from .conftest import EXPECTED_READINGS, FakeModbusConnectionFactory

# include_meter=True here (its own default is False) so this file's main
# test can assert against the full EXPECTED_READINGS, which includes
# meter data. test_restrict_fields_* below cover the toggles themselves.
ENTRY_DATA = {
    "host": "10.1.6.206",
    "port": 502,
    CONF_UNIT_ID: 1,
    CONF_INCLUDE_STRINGS: True,
    CONF_INCLUDE_MPPT: True,
    CONF_INCLUDE_METER: True,
}


async def test_update_data_returns_every_expected_field(
    hass: HomeAssistant, populated_mock_connection: FakeModbusConnectionFactory
) -> None:
    """Every key coordinator.py hardcodes decodes to the right value.

    This is the test that would have caught a typo'd dict key or a
    forgotten field in coordinator.py's `_async_update_data` - the
    return statement there hand-lists ~40 keys, exactly the kind of
    spot a copy-paste mistake hides in.
    """
    entry = MockConfigEntry(domain=DOMAIN, data=ENTRY_DATA)
    entry.add_to_hass(hass)
    coordinator = SungrowSGCoordinator(hass, entry)

    data = await coordinator._async_update_data()

    assert data == EXPECTED_READINGS


async def test_update_failure_marks_coordinator_unsuccessful(
    hass: HomeAssistant, mock_connection: FakeModbusConnectionFactory
) -> None:
    """A ModbusError from the inverter becomes UpdateFailed, not a crash."""
    mock_connection.for_unit(1).fail_requests(ModbusTimeoutError("simulated timeout"))
    entry = MockConfigEntry(domain=DOMAIN, data=ENTRY_DATA)
    entry.add_to_hass(hass)
    coordinator = SungrowSGCoordinator(hass, entry)

    await coordinator.async_refresh()

    assert coordinator.last_update_success is False
    assert isinstance(coordinator.last_exception, UpdateFailed)


async def test_shutdown_closes_the_connection(
    hass: HomeAssistant, populated_mock_connection: FakeModbusConnectionFactory
) -> None:
    """async_shutdown closes the underlying ModbusConnection, not just the poller."""
    entry = MockConfigEntry(domain=DOMAIN, data=ENTRY_DATA)
    entry.add_to_hass(hass)
    coordinator = SungrowSGCoordinator(hass, entry)
    await coordinator.async_refresh()
    assert coordinator.last_update_success is True

    await coordinator.async_shutdown()

    assert populated_mock_connection.connected is False


async def test_meter_excluded_by_default(
    hass: HomeAssistant, populated_mock_connection: FakeModbusConnectionFactory
) -> None:
    """include_meter defaults to False - its fields aren't even read."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"host": "10.1.6.206", "port": 502, CONF_UNIT_ID: 1},
    )
    entry.add_to_hass(hass)
    coordinator = SungrowSGCoordinator(hass, entry)

    data = await coordinator._async_update_data()

    assert data["meter_power"] is None
    assert data["load_power"] is None
    assert data["total_export_energy"] is None
    # Groups left at their own defaults (strings/mppt on) still populate.
    assert data["string_1_current"] == EXPECTED_READINGS["string_1_current"]
    assert data["mppt_1_voltage"] == EXPECTED_READINGS["mppt_1_voltage"]


async def test_strings_and_mppt_excluded_still_reads_core_fields(
    hass: HomeAssistant, populated_mock_connection: FakeModbusConnectionFactory
) -> None:
    """Turning off strings/MPPT/meter leaves the always-on fields intact."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "host": "10.1.6.206",
            "port": 502,
            CONF_UNIT_ID: 1,
            CONF_INCLUDE_STRINGS: False,
            CONF_INCLUDE_MPPT: False,
            CONF_INCLUDE_METER: False,
        },
    )
    entry.add_to_hass(hass)
    coordinator = SungrowSGCoordinator(hass, entry)

    data = await coordinator._async_update_data()

    assert data["string_1_current"] is None
    assert data["string_1_power"] is None  # calculated field, None-guarded
    assert data["mppt_1_voltage"] is None
    assert data["mppt_1_power"] is None
    assert data["meter_power"] is None
    assert data["phase_a_voltage"] == EXPECTED_READINGS["phase_a_voltage"]
    assert data["total_active_power"] == EXPECTED_READINGS["total_active_power"]
    assert data["model_name"] == EXPECTED_READINGS["model_name"]


async def test_strings_without_mppt_still_reads_mppt_voltage_for_string_power(
    hass: HomeAssistant, populated_mock_connection: FakeModbusConnectionFactory
) -> None:
    """Strings need their MPPT's voltage to calculate power even when
    MPPT sensors themselves are excluded (restricted_field_names() in
    const.py reads mppt_1/2_voltage whenever strings are included).
    """
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "host": "10.1.6.206",
            "port": 502,
            CONF_UNIT_ID: 1,
            CONF_INCLUDE_STRINGS: True,
            CONF_INCLUDE_MPPT: False,
            CONF_INCLUDE_METER: False,
        },
    )
    entry.add_to_hass(hass)
    coordinator = SungrowSGCoordinator(hass, entry)

    data = await coordinator._async_update_data()

    assert data["mppt_1_current"] is None  # MPPT sensors themselves off
    assert data["string_1_current"] == EXPECTED_READINGS["string_1_current"]
    assert data["string_1_power"] == EXPECTED_READINGS["string_1_power"]
