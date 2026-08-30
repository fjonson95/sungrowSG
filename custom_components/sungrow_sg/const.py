"""Constants for the Sungrow SG-series integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

DOMAIN = "sungrow_sg"

CONF_UNIT_ID = "unit_id"
DEFAULT_UNIT_ID = 1
DEFAULT_PORT = 502
DEFAULT_SCAN_INTERVAL = 30  # seconds

# Optional sensor groups - not every SG12RT installation has strings worth
# graphing separately, or a CT/smart meter attached (see
# sungrow_modbus registers.py METER_POWER docstring: an inverter without
# one may just read zeros there). Chosen in config_flow.py, editable
# later via its OptionsFlow.
CONF_INCLUDE_STRINGS = "include_strings"
CONF_INCLUDE_MPPT = "include_mppt"
CONF_INCLUDE_METER = "include_meter"
DEFAULT_INCLUDE_STRINGS = True
DEFAULT_INCLUDE_MPPT = True
DEFAULT_INCLUDE_METER = False

# SungrowSGInverter (sungrow_modbus.models) field names always read,
# regardless of which optional groups below are enabled.
CORE_FIELDS: frozenset[str] = frozenset(
    {
        "device_type_code",
        "serial_number",
        "protocol_version_raw",
        "nominal_active_power",
        "output_type",
        "daily_power_yield",
        "total_power_yield",
        "total_running_time",
        "internal_temperature",
        "total_apparent_power",
        "total_dc_power",
        "phase_a_voltage",
        "phase_b_voltage",
        "phase_c_voltage",
        "phase_a_current",
        "phase_b_current",
        "phase_c_current",
        "total_active_power",
        "total_reactive_power",
        "power_factor",
        "grid_frequency",
        "work_state_1",
        "work_state_2",
        "nominal_reactive_power",
        "array_insulation_resistance",
        "negative_voltage_to_ground",
        "bus_voltage",
    }
)

# mppt_1/2_voltage are needed whenever strings are included too - strings
# on the same MPPT are wired in parallel and share that MPPT's voltage
# (see sungrow_modbus models.py string_N_power docstrings), so
# restricted_field_names() below reads them even with include_mppt off.
MPPT_VOLTAGE_FIELDS: frozenset[str] = frozenset({"mppt_1_voltage", "mppt_2_voltage"})
MPPT_FIELDS: frozenset[str] = MPPT_VOLTAGE_FIELDS | frozenset(
    {"mppt_1_current", "mppt_2_current"}
)
STRING_FIELDS: frozenset[str] = frozenset(
    {"string_1_current", "string_2_current", "string_3_current"}
)
METER_FIELDS: frozenset[str] = frozenset(
    {
        "meter_power",
        "meter_a_phase_power",
        "meter_b_phase_power",
        "meter_c_phase_power",
        "load_power",
        "daily_export_energy",
        "total_export_energy",
        "daily_import_energy",
        "total_import_energy",
        "daily_direct_energy_consumption",
        "total_direct_energy_consumption",
    }
)

# Sensor entity keys (sensor.py SENSOR_DESCRIPTIONS) per optional group -
# includes the calculated power sensors, which aren't SungrowSGInverter
# Component fields (they're plain Python properties) and so aren't part
# of the *_FIELDS sets above.
MPPT_SENSOR_KEYS: frozenset[str] = frozenset(
    {
        "mppt_1_voltage",
        "mppt_1_current",
        "mppt_1_power",
        "mppt_2_voltage",
        "mppt_2_current",
        "mppt_2_power",
    }
)
STRING_SENSOR_KEYS: frozenset[str] = frozenset(
    {
        "string_1_current",
        "string_2_current",
        "string_3_current",
        "string_1_power",
        "string_2_power",
        "string_3_power",
    }
)
METER_SENSOR_KEYS: frozenset[str] = METER_FIELDS


def get_toggle(entry: ConfigEntry, key: str, default: bool) -> bool:
    """Read an include_* toggle: entry.options overrides entry.data.

    Options flow writes to entry.options; entries created (or never
    reconfigured via options) before that still work off entry.data.
    """
    if key in entry.options:
        return bool(entry.options[key])
    return bool(entry.data.get(key, default))


def restricted_field_names(
    *, include_mppt: bool, include_strings: bool, include_meter: bool
) -> set[str]:
    """SungrowSGInverter field names to keep via Component.restrict_fields()."""
    names = set(CORE_FIELDS)
    if include_mppt:
        names |= MPPT_FIELDS
    if include_strings:
        names |= STRING_FIELDS
        names |= MPPT_VOLTAGE_FIELDS
    if include_meter:
        names |= METER_FIELDS
    return names
