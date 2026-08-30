"""Tests for the Sungrow SG-series sensor platform."""

from __future__ import annotations

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sungrow_sg.const import CONF_UNIT_ID, DOMAIN
from custom_components.sungrow_sg.sensor import SENSOR_DESCRIPTIONS

from .conftest import EXPECTED_READINGS, FakeModbusConnectionFactory

ENTRY_DATA = {"host": "10.1.6.206", "port": 502, CONF_UNIT_ID: 1}


async def _setup_entry(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, data=ENTRY_DATA)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_all_descriptions_create_an_entity_with_the_right_state(
    hass: HomeAssistant, populated_mock_connection: FakeModbusConnectionFactory
) -> None:
    """Every SENSOR_DESCRIPTIONS entry becomes a real entity with the expected state.

    Looks entities up by unique_id (deterministic: f"{entry_id}_{key}"),
    not by guessing a translated entity_id - the translation strings are
    a separate concern from whether the wiring itself is correct.
    """
    entry = await _setup_entry(hass)
    entity_registry = er.async_get(hass)

    assert len(SENSOR_DESCRIPTIONS) == 42

    for description in SENSOR_DESCRIPTIONS:
        unique_id = f"{entry.entry_id}_{description.key}"
        entity_id = entity_registry.async_get_entity_id("sensor", DOMAIN, unique_id)
        assert entity_id is not None, f"no entity registered for {description.key!r}"

        state = hass.states.get(entity_id)
        assert state is not None, f"{description.key!r} has no state"

        expected = EXPECTED_READINGS[description.key]
        if isinstance(expected, float):
            assert float(state.state) == pytest.approx(expected)
        else:
            assert state.state == str(expected)


async def test_identity_fields_go_to_device_info_not_separate_sensors(
    hass: HomeAssistant, populated_mock_connection: FakeModbusConnectionFactory
) -> None:
    """model_name/serial_number/protocol_version are DeviceInfo, not sensors."""
    entry = await _setup_entry(hass)

    device_registry = dr.async_get(hass)
    device = device_registry.async_get_device(identifiers={(DOMAIN, entry.entry_id)})
    assert device is not None
    assert device.manufacturer == "Sungrow"
    assert device.model == EXPECTED_READINGS["model_name"]
    assert device.sw_version == EXPECTED_READINGS["protocol_version"]
    assert device.serial_number == EXPECTED_READINGS["serial_number"]

    entity_registry = er.async_get(hass)
    for leaked_key in ("model_name", "serial_number", "protocol_version"):
        unique_id = f"{entry.entry_id}_{leaked_key}"
        assert (
            entity_registry.async_get_entity_id("sensor", DOMAIN, unique_id) is None
        ), f"{leaked_key!r} should not be its own sensor entity"


async def test_enum_sensors_report_valid_options(
    hass: HomeAssistant, populated_mock_connection: FakeModbusConnectionFactory
) -> None:
    """work_state_1_label/output_type_label are real ENUM sensors, not raw codes."""
    entry = await _setup_entry(hass)
    entity_registry = er.async_get(hass)

    for key in ("work_state_1_label", "output_type_label"):
        unique_id = f"{entry.entry_id}_{key}"
        entity_id = entity_registry.async_get_entity_id("sensor", DOMAIN, unique_id)
        assert entity_id is not None
        state = hass.states.get(entity_id)
        assert state.attributes["device_class"] == "enum"
        assert state.state in state.attributes["options"]


async def test_diagnostic_entities_are_categorized(
    hass: HomeAssistant, populated_mock_connection: FakeModbusConnectionFactory
) -> None:
    """The diagnostic-only fields (nameplate ratings, raw bitmask, etc.)
    are actually registered under the diagnostic category, not left
    cluttering the main entity list.
    """
    entry = await _setup_entry(hass)
    entity_registry = er.async_get(hass)

    diagnostic_keys = {
        d.key for d in SENSOR_DESCRIPTIONS if d.entity_category is not None
    }
    assert diagnostic_keys == {
        "bus_voltage",
        "negative_voltage_to_ground",
        "total_running_time",
        "output_type_label",
        "nominal_active_power",
        "nominal_reactive_power",
        "array_insulation_resistance",
        "work_state_2",
    }

    for key in diagnostic_keys:
        unique_id = f"{entry.entry_id}_{key}"
        entry_reg = entity_registry.async_get(
            entity_registry.async_get_entity_id("sensor", DOMAIN, unique_id)
        )
        assert entry_reg.entity_category == "diagnostic"


async def test_unload_entry_closes_the_connection(
    hass: HomeAssistant, populated_mock_connection: FakeModbusConnectionFactory
) -> None:
    """Unloading the config entry shuts the coordinator (and its Modbus
    connection) down, not just the sensor platform.
    """
    entry = await _setup_entry(hass)

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert populated_mock_connection.connected is False
