"""Tests for the Sungrow SG-series number platform."""

from __future__ import annotations

import pytest
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


async def test_power_limitation_setting_reflects_current_value(
    hass: HomeAssistant, populated_mock_connection: FakeModbusConnectionFactory
) -> None:
    entry = await _setup_entry(hass)
    entity_registry = er.async_get(hass)
    entity_id = entity_registry.async_get_entity_id(
        "number", DOMAIN, f"{entry.entry_id}_power_limitation_setting"
    )
    assert entity_id is not None

    state = hass.states.get(entity_id)
    assert float(state.state) == EXPECTED_READINGS["power_limitation_setting"]
    assert state.attributes["min"] == 0
    assert state.attributes["max"] == 100


async def test_setting_the_value_writes_the_scaled_register(
    hass: HomeAssistant, populated_mock_connection: FakeModbusConnectionFactory
) -> None:
    entry = await _setup_entry(hass)
    entity_registry = er.async_get(hass)
    entity_id = entity_registry.async_get_entity_id(
        "number", DOMAIN, f"{entry.entry_id}_power_limitation_setting"
    )
    events = []
    populated_mock_connection.for_unit(1).on_write(events.append)

    await hass.services.async_call(
        "number",
        "set_value",
        {"entity_id": entity_id, "value": 42.5},
        blocking=True,
    )

    assert events[-1].values == [425]
    assert hass.states.get(entity_id).state == "42.5"


async def test_power_limitation_setting_is_config_category(
    hass: HomeAssistant, populated_mock_connection: FakeModbusConnectionFactory
) -> None:
    entry = await _setup_entry(hass)
    entity_registry = er.async_get(hass)
    entry_reg = entity_registry.async_get(
        entity_registry.async_get_entity_id(
            "number", DOMAIN, f"{entry.entry_id}_power_limitation_setting"
        )
    )
    assert entry_reg.entity_category == "config"


@pytest.mark.parametrize(
    ("key", "value", "raw"),
    [
        ("power_limitation_adjustment", 8.4, 84),
        ("feed_in_power_limit_value", 12.0, 1200),
        ("feed_in_power_limit_ratio", 75.5, 755),
    ],
)
async def test_absolute_and_feed_in_numbers_write_the_scaled_register(
    hass: HomeAssistant,
    populated_mock_connection: FakeModbusConnectionFactory,
    key: str,
    value: float,
    raw: int,
) -> None:
    entry = await _setup_entry(hass)
    entity_registry = er.async_get(hass)
    entity_id = entity_registry.async_get_entity_id(
        "number", DOMAIN, f"{entry.entry_id}_{key}"
    )
    assert entity_id is not None, f"no number entity for {key!r}"
    events = []
    populated_mock_connection.for_unit(1).on_write(events.append)

    await hass.services.async_call(
        "number",
        "set_value",
        {"entity_id": entity_id, "value": value},
        blocking=True,
    )

    assert events[-1].values == [raw]
