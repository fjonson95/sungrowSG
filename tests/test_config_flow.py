"""Tests for the Sungrow SG-series config flow."""

from __future__ import annotations

from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from modbus_connection import ModbusTimeoutError

from custom_components.sungrow_sg.const import CONF_UNIT_ID, DOMAIN

from .conftest import FakeModbusConnectionFactory, populate_realistic_readings

USER_INPUT = {"host": "10.1.6.206", "port": 502, CONF_UNIT_ID: 1}


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
    assert result["title"] == "Sungrow SG (10.1.6.206)"
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
