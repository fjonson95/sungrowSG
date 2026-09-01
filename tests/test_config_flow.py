"""Tests for the Sungrow SG-series config flow."""

from __future__ import annotations

from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from modbus_connection import ModbusTimeoutError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sungrow_sg.const import (
    CONF_INCLUDE_METER,
    CONF_INCLUDE_MPPT,
    CONF_INCLUDE_STRINGS,
    CONF_UNIT_ID,
    DOMAIN,
)

from .conftest import FakeModbusConnectionFactory, populate_realistic_readings

# include_meter=True here (its own default is False) so this file's tests
# exercise the full sensor set, matching test_coordinator.py/test_sensor.py.
USER_INPUT = {
    "host": "10.1.6.206",
    "port": 502,
    CONF_UNIT_ID: 1,
    CONF_INCLUDE_STRINGS: True,
    CONF_INCLUDE_MPPT: True,
    CONF_INCLUDE_METER: True,
}


async def test_user_flow_success(
    hass: HomeAssistant, mock_connection: FakeModbusConnectionFactory
) -> None:
    """A reachable inverter creates a config entry."""
    populate_realistic_readings(mock_connection.for_unit(1))

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Sungrow SG"  # default name - no IP in it
    assert result["data"] == USER_INPUT


async def test_user_flow_with_custom_name(
    hass: HomeAssistant, mock_connection: FakeModbusConnectionFactory
) -> None:
    """A custom name becomes the entry title, not a data field - keeps
    entry.data limited to the actual Modbus connection parameters.
    """
    populate_realistic_readings(mock_connection.for_unit(1))

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {**USER_INPUT, CONF_NAME: "Garage"}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Garage"
    assert CONF_NAME not in result["data"]
    assert result["data"] == USER_INPUT


async def test_user_flow_cannot_connect(
    hass: HomeAssistant, mock_connection: FakeModbusConnectionFactory
) -> None:
    """An inverter that never answers shows the cannot_connect error, not a crash."""
    mock_connection.for_unit(1).fail_requests(ModbusTimeoutError("simulated timeout"))

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "cannot_connect"}


async def test_user_flow_recovers_after_cannot_connect(
    hass: HomeAssistant, mock_connection: FakeModbusConnectionFactory
) -> None:
    """Fixing the problem and resubmitting the same form succeeds."""
    unit = mock_connection.for_unit(1)
    unit.fail_requests(ModbusTimeoutError("simulated timeout"))

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    assert result["errors"] == {"base": "cannot_connect"}

    unit.fail_requests(None)
    populate_realistic_readings(unit)

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_user_flow_aborts_on_duplicate(
    hass: HomeAssistant, mock_connection: FakeModbusConnectionFactory
) -> None:
    """The same host/port/unit_id can't be configured twice."""
    populate_realistic_readings(mock_connection.for_unit(1))

    first = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    await hass.config_entries.flow.async_configure(first["flow_id"], USER_INPUT)
    await hass.async_block_till_done()

    second = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    second = await hass.config_entries.flow.async_configure(
        second["flow_id"], USER_INPUT
    )

    assert second["type"] is FlowResultType.ABORT
    assert second["reason"] == "already_configured"


async def test_user_flow_fills_in_sensor_group_defaults(
    hass: HomeAssistant, mock_connection: FakeModbusConnectionFactory
) -> None:
    """Omitting the toggles falls back to strings=on, mppt=on, meter=off."""
    populate_realistic_readings(mock_connection.for_unit(1))
    minimal_input = {"host": "10.1.6.207", "port": 502, CONF_UNIT_ID: 1}

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], minimal_input
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_INCLUDE_STRINGS] is True
    assert result["data"][CONF_INCLUDE_MPPT] is True
    assert result["data"][CONF_INCLUDE_METER] is False


async def test_options_flow_updates_sensor_group_toggles(
    hass: HomeAssistant, populated_mock_connection: FakeModbusConnectionFactory
) -> None:
    """The options flow (gear icon) can change the toggles after setup."""
    entry = MockConfigEntry(domain=DOMAIN, data=USER_INPUT)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_INCLUDE_STRINGS: False,
            CONF_INCLUDE_MPPT: False,
            CONF_INCLUDE_METER: False,
        },
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_INCLUDE_STRINGS] is False
    assert entry.options[CONF_INCLUDE_MPPT] is False
    assert entry.options[CONF_INCLUDE_METER] is False


async def test_options_flow_renames_the_entry(
    hass: HomeAssistant, populated_mock_connection: FakeModbusConnectionFactory
) -> None:
    """The name can be changed after setup too, not just at creation -
    updates entry.title directly, not entry.options (matches the initial
    user step keeping CONF_NAME out of entry.data).
    """
    entry = MockConfigEntry(domain=DOMAIN, data=USER_INPUT, title="Sungrow SG")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "Garage",
            CONF_INCLUDE_STRINGS: True,
            CONF_INCLUDE_MPPT: True,
            CONF_INCLUDE_METER: True,
        },
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.title == "Garage"
    assert CONF_NAME not in entry.options
