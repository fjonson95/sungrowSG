"""Tests for the Sungrow SG-series sensor platform."""

from __future__ import annotations

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sungrow_sg.const import (
    CONF_INCLUDE_METER,
    CONF_INCLUDE_MPPT,
    CONF_INCLUDE_STRINGS,
    CONF_UNIT_ID,
    DOMAIN,
    METER_SENSOR_KEYS,
    MPPT_SENSOR_KEYS,
    STRING_SENSOR_KEYS,
)
from custom_components.sungrow_sg.sensor import SENSOR_DESCRIPTIONS

from .conftest import EXPECTED_READINGS, FakeModbusConnectionFactory

# include_meter=True here (its own default is False) so this file's main
# test can assert against every entry in SENSOR_DESCRIPTIONS, meter
# sensors included. test_sensor_groups_can_be_excluded below covers the
# toggles themselves.
ENTRY_DATA = {
    "host": "10.1.6.206",
    "port": 502,
    CONF_UNIT_ID: 1,
    CONF_INCLUDE_STRINGS: True,
    CONF_INCLUDE_MPPT: True,
    CONF_INCLUDE_METER: True,
}


async def _setup_entry(
    hass: HomeAssistant, data: dict | None = None
) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, data=data or ENTRY_DATA)
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

    assert len(SENSOR_DESCRIPTIONS) == 54

    for description in SENSOR_DESCRIPTIONS:
        unique_id = f"{entry.entry_id}_{description.key}"
        entity_id = entity_registry.async_get_entity_id("sensor", DOMAIN, unique_id)
        assert entity_id is not None, f"no entity registered for {description.key!r}"

        state = hass.states.get(entity_id)
        assert state is not None, f"{description.key!r} has no state"

        expected = EXPECTED_READINGS[description.key]
        if expected is None:
            assert state.state == "unknown"
        elif isinstance(expected, float):
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
        "protocol_no",
        "arm_software_version",
        "dsp_software_version",
        "daily_running_time",
        "fault_alarm_label",
        "fault_alarm_time",
    }

    for key in diagnostic_keys:
        unique_id = f"{entry.entry_id}_{key}"
        entry_reg = entity_registry.async_get(
            entity_registry.async_get_entity_id("sensor", DOMAIN, unique_id)
        )
        assert entry_reg.entity_category == "diagnostic"


async def test_sensor_groups_can_be_excluded(
    hass: HomeAssistant, populated_mock_connection: FakeModbusConnectionFactory
) -> None:
    """Turning a group off in config_flow means no entity for it at all -
    not just a hidden/unavailable one.
    """
    entry = await _setup_entry(
        hass,
        data={
            "host": "10.1.6.206",
            "port": 502,
            CONF_UNIT_ID: 1,
            CONF_INCLUDE_STRINGS: False,
            CONF_INCLUDE_MPPT: False,
            CONF_INCLUDE_METER: False,
        },
    )
    entity_registry = er.async_get(hass)

    excluded_keys = MPPT_SENSOR_KEYS | STRING_SENSOR_KEYS | METER_SENSOR_KEYS
    for key in excluded_keys:
        unique_id = f"{entry.entry_id}_{key}"
        assert (
            entity_registry.async_get_entity_id("sensor", DOMAIN, unique_id) is None
        ), f"{key!r} should not exist with its group excluded"

    # A core sensor is still there.
    core_unique_id = f"{entry.entry_id}_phase_a_voltage"
    assert (
        entity_registry.async_get_entity_id("sensor", DOMAIN, core_unique_id)
        is not None
    )


async def test_changing_options_reloads_and_updates_sensors(
    hass: HomeAssistant, populated_mock_connection: FakeModbusConnectionFactory
) -> None:
    """The options flow actually takes effect - __init__.py's update
    listener must reload the entry, since HA doesn't do that on its own
    (see the comment on it in __init__.py).

    Checks live state, not the entity registry: HA doesn't purge a
    registry entry just because a reload no longer recreates it. Instead
    the state machine keeps a "restored" placeholder showing
    `unavailable` for it - the registry entry (and that placeholder)
    persisting is normal, expected HA behavior, not a sign the toggle
    didn't take effect.
    """
    entry = await _setup_entry(hass)  # ENTRY_DATA: all three groups on
    entity_registry = er.async_get(hass)
    mppt_unique_id = f"{entry.entry_id}_mppt_1_voltage"
    mppt_entity_id = entity_registry.async_get_entity_id(
        "sensor", DOMAIN, mppt_unique_id
    )
    state = hass.states.get(mppt_entity_id)
    assert state is not None
    assert state.state not in ("unavailable", "unknown")

    result = await hass.config_entries.options.async_init(entry.entry_id)
    await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_INCLUDE_STRINGS: True,
            CONF_INCLUDE_MPPT: False,
            CONF_INCLUDE_METER: True,
        },
    )
    await hass.async_block_till_done()

    state = hass.states.get(mppt_entity_id)
    assert state is None or state.state == "unavailable"


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
