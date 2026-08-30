"""Tests for the Sungrow SG-series binary_sensor platform."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sungrow_sg.const import CONF_UNIT_ID, DOMAIN

from .conftest import EXPECTED_READINGS, FakeModbusConnectionFactory

ENTRY_DATA = {"host": "10.1.6.206", "port": 502, CONF_UNIT_ID: 1}


async def _setup_entry(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, data=ENTRY_DATA)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_binary_sensors_reflect_current_state(
    hass: HomeAssistant, populated_mock_connection: FakeModbusConnectionFactory
) -> None:
    entry = await _setup_entry(hass)
    entity_registry = er.async_get(hass)

    for key in ("is_grid_connected", "is_in_fault"):
        unique_id = f"{entry.entry_id}_{key}"
        entity_id = entity_registry.async_get_entity_id(
            "binary_sensor", DOMAIN, unique_id
        )
        assert entity_id is not None, f"no binary_sensor entity for {key!r}"
        state = hass.states.get(entity_id)
        assert state.state == ("on" if EXPECTED_READINGS[key] else "off")


async def test_binary_sensors_are_diagnostic_category(
    hass: HomeAssistant, populated_mock_connection: FakeModbusConnectionFactory
) -> None:
    entry = await _setup_entry(hass)
    entity_registry = er.async_get(hass)

    for key in ("is_grid_connected", "is_in_fault"):
        entry_reg = entity_registry.async_get(
            entity_registry.async_get_entity_id(
                "binary_sensor", DOMAIN, f"{entry.entry_id}_{key}"
            )
        )
        assert entry_reg.entity_category == "diagnostic"
