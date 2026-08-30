"""Tests for the Sungrow SG-series switch platform."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sungrow_sg.const import CONF_UNIT_ID, DOMAIN
from custom_components.sungrow_sg.sungrow_modbus import registers as reg

from .conftest import (
    EXPECTED_READINGS,
    FakeModbusConnectionFactory,
    populate_realistic_readings,
)

ENTRY_DATA = {"host": "10.1.6.206", "port": 502, CONF_UNIT_ID: 1}


async def _setup_entry(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, data=ENTRY_DATA)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_switches_reflect_current_state(
    hass: HomeAssistant, populated_mock_connection: FakeModbusConnectionFactory
) -> None:
    entry = await _setup_entry(hass)
    entity_registry = er.async_get(hass)

    expected = {
        "start_stop": EXPECTED_READINGS["start_stop_is_running"],
        "power_limitation_switch": EXPECTED_READINGS["power_limitation_enabled"],
        "night_svg_switch": EXPECTED_READINGS["night_svg_enabled"],
    }
    for key, is_on in expected.items():
        unique_id = f"{entry.entry_id}_{key}"
        entity_id = entity_registry.async_get_entity_id("switch", DOMAIN, unique_id)
        assert entity_id is not None, f"no switch entity for {key!r}"
        state = hass.states.get(entity_id)
        assert state.state == ("on" if is_on else "off")


async def test_turning_off_start_stop_writes_the_stop_code(
    hass: HomeAssistant, populated_mock_connection: FakeModbusConnectionFactory
) -> None:
    """start_stop begins the test data set as running (True/"on")."""
    entry = await _setup_entry(hass)
    entity_registry = er.async_get(hass)
    entity_id = entity_registry.async_get_entity_id(
        "switch", DOMAIN, f"{entry.entry_id}_start_stop"
    )
    events = []
    populated_mock_connection.for_unit(1).on_write(events.append)

    await hass.services.async_call(
        "switch", "turn_off", {"entity_id": entity_id}, blocking=True
    )

    assert events[-1].values == [0xCE]
    assert hass.states.get(entity_id).state == "off"


async def test_turning_on_start_stop_writes_the_start_code(
    hass: HomeAssistant, mock_connection: FakeModbusConnectionFactory
) -> None:
    """Same as the "off" test above but starting from a stopped inverter -
    a second async_call in the same test would collide with
    DataUpdateCoordinator's 10s request-refresh debounce (only the first
    of two rapid async_request_refresh() calls runs immediately), so this
    is deliberately its own test with its own fresh setup rather than a
    second step chained onto the "off" test.
    """
    unit = mock_connection.for_unit(1)
    populate_realistic_readings(unit)
    unit.holding[reg.START_STOP.address] = 0xCE  # start stopped, not running

    entry = await _setup_entry(hass)
    entity_registry = er.async_get(hass)
    entity_id = entity_registry.async_get_entity_id(
        "switch", DOMAIN, f"{entry.entry_id}_start_stop"
    )
    assert hass.states.get(entity_id).state == "off"
    events = []
    unit.on_write(events.append)

    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": entity_id}, blocking=True
    )

    assert events[-1].values == [0xCF]
    assert hass.states.get(entity_id).state == "on"


async def test_turning_on_power_limitation_switch_writes_enable(
    hass: HomeAssistant, populated_mock_connection: FakeModbusConnectionFactory
) -> None:
    entry = await _setup_entry(hass)
    entity_registry = er.async_get(hass)
    entity_id = entity_registry.async_get_entity_id(
        "switch", DOMAIN, f"{entry.entry_id}_power_limitation_switch"
    )
    events = []
    populated_mock_connection.for_unit(1).on_write(events.append)

    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": entity_id}, blocking=True
    )

    assert events[-1].values == [0xAA]
    assert events[-1].address == reg.POWER_LIMITATION_SWITCH.address
    assert hass.states.get(entity_id).state == "on"


async def test_turning_on_feed_in_power_limit_switch_writes_enable(
    hass: HomeAssistant, populated_mock_connection: FakeModbusConnectionFactory
) -> None:
    entry = await _setup_entry(hass)
    entity_registry = er.async_get(hass)
    entity_id = entity_registry.async_get_entity_id(
        "switch", DOMAIN, f"{entry.entry_id}_feed_in_power_limit_switch"
    )
    events = []
    populated_mock_connection.for_unit(1).on_write(events.append)

    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": entity_id}, blocking=True
    )

    assert events[-1].values == [0xAA]
    assert events[-1].address == reg.FEED_IN_POWER_LIMIT_SWITCH.address
    assert hass.states.get(entity_id).state == "on"


async def test_power_limitation_and_night_svg_are_config_category(
    hass: HomeAssistant, populated_mock_connection: FakeModbusConnectionFactory
) -> None:
    """start_stop is a primary control (not hidden); the other two are
    configuration-category, matching their lower everyday relevance.
    """
    entry = await _setup_entry(hass)
    entity_registry = er.async_get(hass)

    def category(key: str) -> str | None:
        entry_reg = entity_registry.async_get(
            entity_registry.async_get_entity_id(
                "switch", DOMAIN, f"{entry.entry_id}_{key}"
            )
        )
        return entry_reg.entity_category

    assert category("start_stop") is None
    assert category("power_limitation_switch") == "config"
    assert category("feed_in_power_limit_switch") == "config"
    assert category("night_svg_switch") == "config"
