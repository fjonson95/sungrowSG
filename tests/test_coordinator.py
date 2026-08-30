"""Tests for SungrowSGCoordinator."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed
from modbus_connection import ModbusTimeoutError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sungrow_sg.const import CONF_UNIT_ID, DOMAIN
from custom_components.sungrow_sg.coordinator import SungrowSGCoordinator

from .conftest import EXPECTED_READINGS, FakeModbusConnectionFactory

ENTRY_DATA = {"host": "10.1.6.206", "port": 502, CONF_UNIT_ID: 1}


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
