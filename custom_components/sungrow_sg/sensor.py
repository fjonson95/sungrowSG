"""Sensor platform for Sungrow SG-series.

Every field exposed by `SungrowSGInverter` (see `./sungrow_modbus/models.py`
- a vendored copy of `library/sungrow-modbus/src/sungrow_modbus/models.py`,
see that directory's README.md) is wired here. `model_name`/
`serial_number`/`protocol_version` go into `DeviceInfo` instead of
separate sensor entities - that's what those fields are for in Home
Assistant, and it avoids three redundant diagnostic sensors.
"""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfApparentPower,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_INCLUDE_METER,
    CONF_INCLUDE_MPPT,
    CONF_INCLUDE_STRINGS,
    DEFAULT_INCLUDE_METER,
    DEFAULT_INCLUDE_MPPT,
    DEFAULT_INCLUDE_STRINGS,
    DOMAIN,
    METER_SENSOR_KEYS,
    MPPT_SENSOR_KEYS,
    STRING_SENSOR_KEYS,
    get_toggle,
)
from .coordinator import SungrowSGCoordinator
from .entity import build_device_info
from .sungrow_modbus.const import OUTPUT_TYPE_LABELS, WORK_STATE_1_LABELS

SENSOR_DESCRIPTIONS: tuple[SensorEntityDescription, ...] = (
    # --- AC measurements -----------------------------------------------------
    SensorEntityDescription(
        key="phase_a_voltage",
        translation_key="phase_a_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="phase_b_voltage",
        translation_key="phase_b_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="phase_c_voltage",
        translation_key="phase_c_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="phase_a_current",
        translation_key="phase_a_current",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="phase_b_current",
        translation_key="phase_b_current",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="phase_c_current",
        translation_key="phase_c_current",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="total_active_power",
        translation_key="total_active_power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # total_active_power as a % of nominal_active_power - "how much of
    # this inverter's rated capacity is in use right now". Built for a
    # dashboard bar/gauge card - see docs/register_map.md if you're
    # looking for the underlying registers.
    SensorEntityDescription(
        key="capacity_utilization",
        translation_key="capacity_utilization",
        native_unit_of_measurement="%",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="total_reactive_power",
        translation_key="total_reactive_power",
        device_class=SensorDeviceClass.REACTIVE_POWER,
        native_unit_of_measurement="var",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="total_apparent_power",
        translation_key="total_apparent_power",
        device_class=SensorDeviceClass.APPARENT_POWER,
        native_unit_of_measurement=UnitOfApparentPower.VOLT_AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="power_factor",
        translation_key="power_factor",
        device_class=SensorDeviceClass.POWER_FACTOR,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="grid_frequency",
        translation_key="grid_frequency",
        device_class=SensorDeviceClass.FREQUENCY,
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # --- DC / MPPT -------------------------------------------------------------
    SensorEntityDescription(
        key="mppt_1_voltage",
        translation_key="mppt_1_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="mppt_1_current",
        translation_key="mppt_1_current",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # Calculated (mppt_1_voltage * mppt_1_current) - no direct register,
    # see sungrow_modbus models.py mppt_1_power docstring.
    SensorEntityDescription(
        key="mppt_1_power",
        translation_key="mppt_1_power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="mppt_2_voltage",
        translation_key="mppt_2_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="mppt_2_current",
        translation_key="mppt_2_current",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # Calculated (mppt_2_voltage * mppt_2_current) - no direct register.
    SensorEntityDescription(
        key="mppt_2_power",
        translation_key="mppt_2_power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="total_dc_power",
        translation_key="total_dc_power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="bus_voltage",
        translation_key="bus_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="negative_voltage_to_ground",
        translation_key="negative_voltage_to_ground",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    # --- Per-string current + calculated power ------------------------------------
    # Power is calculated (string_N_current * the MPPT it's wired to's
    # voltage - strings don't have their own voltage register), see
    # sungrow_modbus models.py string_N_power docstrings.
    SensorEntityDescription(
        key="string_1_current",
        translation_key="string_1_current",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="string_1_power",
        translation_key="string_1_power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="string_2_current",
        translation_key="string_2_current",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="string_2_power",
        translation_key="string_2_power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="string_3_current",
        translation_key="string_3_current",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="string_3_power",
        translation_key="string_3_power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # --- Energy yield -----------------------------------------------------------
    SensorEntityDescription(
        key="daily_power_yield",
        translation_key="daily_power_yield",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SensorEntityDescription(
        key="total_power_yield",
        translation_key="total_power_yield",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SensorEntityDescription(
        key="total_running_time",
        translation_key="total_running_time",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.HOURS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    # Cross-checked against iSolarCloud (Sungrow's cloud UI) 2026-08-30:
    # "Daily operating time" / "Yield this month" matched these exactly.
    SensorEntityDescription(
        key="daily_running_time",
        translation_key="daily_running_time",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="monthly_power_yield",
        translation_key="monthly_power_yield",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    # --- Grid meter (external CT/smart meter) -----------------------------------
    SensorEntityDescription(
        key="meter_power",
        translation_key="meter_power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="meter_a_phase_power",
        translation_key="meter_a_phase_power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="meter_b_phase_power",
        translation_key="meter_b_phase_power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="meter_c_phase_power",
        translation_key="meter_c_phase_power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="load_power",
        translation_key="load_power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="daily_export_energy",
        translation_key="daily_export_energy",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SensorEntityDescription(
        key="total_export_energy",
        translation_key="total_export_energy",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SensorEntityDescription(
        key="daily_import_energy",
        translation_key="daily_import_energy",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SensorEntityDescription(
        key="total_import_energy",
        translation_key="total_import_energy",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SensorEntityDescription(
        key="daily_direct_energy_consumption",
        translation_key="daily_direct_energy_consumption",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SensorEntityDescription(
        key="total_direct_energy_consumption",
        translation_key="total_direct_energy_consumption",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    # --- Status / diagnostics ----------------------------------------------------
    SensorEntityDescription(
        key="internal_temperature",
        translation_key="internal_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="work_state_1_label",
        translation_key="work_state_1_label",
        device_class=SensorDeviceClass.ENUM,
        options=sorted({*WORK_STATE_1_LABELS.values(), "unknown"}),
    ),
    SensorEntityDescription(
        key="work_state_2",
        translation_key="work_state_2",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="output_type_label",
        translation_key="output_type_label",
        device_class=SensorDeviceClass.ENUM,
        options=sorted({*OUTPUT_TYPE_LABELS.values(), "unknown"}),
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    # Not ENUM: FAULT_CODE_LABELS (Appendix 4) has ~30 distinct names
    # across hundreds of codes, and both fields are None whenever no
    # fault/alarm is recorded - a plain text/diagnostic sensor fits better
    # than forcing a fixed options list.
    SensorEntityDescription(
        key="fault_alarm_label",
        translation_key="fault_alarm_label",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="fault_alarm_time",
        translation_key="fault_alarm_time",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="nominal_active_power",
        translation_key="nominal_active_power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="nominal_reactive_power",
        translation_key="nominal_reactive_power",
        # No device_class: HA's REACTIVE_POWER device class only allows a
        # native unit of "var", but this field is in kVar (see registers.py).
        native_unit_of_measurement="kVar",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="array_insulation_resistance",
        translation_key="array_insulation_resistance",
        native_unit_of_measurement="kΩ",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    # --- Newly documented in protocol doc V1.1.80 (2026-03-27) ------------------
    SensorEntityDescription(
        key="protocol_no",
        translation_key="protocol_no",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="arm_software_version",
        translation_key="arm_software_version",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="dsp_software_version",
        translation_key="dsp_software_version",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    # Coordinator-side counter, not a Modbus register - see
    # coordinator.py _async_update_data. Counts ModbusTimeoutError
    # specifically (not other ModbusError subclasses), reset at local
    # midnight. TOTAL_INCREASING is the same pattern used for
    # daily_power_yield/daily_running_time above - a value that resets
    # to 0 once a day, not a strictly-ever-increasing counter.
    SensorEntityDescription(
        key="timeout_count_today",
        translation_key="timeout_count_today",
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)


def _enabled_descriptions(
    entry: ConfigEntry,
) -> tuple[SensorEntityDescription, ...]:
    """SENSOR_DESCRIPTIONS filtered by the entry's include_strings/mppt/meter
    toggles - a key not in any of the three optional-group sets is always
    included (the core fields, plus energy yield/status/identity).
    """
    include_mppt = get_toggle(entry, CONF_INCLUDE_MPPT, DEFAULT_INCLUDE_MPPT)
    include_strings = get_toggle(entry, CONF_INCLUDE_STRINGS, DEFAULT_INCLUDE_STRINGS)
    include_meter = get_toggle(entry, CONF_INCLUDE_METER, DEFAULT_INCLUDE_METER)

    def keep(key: str) -> bool:
        if key in MPPT_SENSOR_KEYS:
            return include_mppt
        if key in STRING_SENSOR_KEYS:
            return include_strings
        if key in METER_SENSOR_KEYS:
            return include_meter
        return True

    return tuple(d for d in SENSOR_DESCRIPTIONS if keep(d.key))


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: SungrowSGCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        SungrowSGSensor(coordinator, entry, description)
        for description in _enabled_descriptions(entry)
    )


class SungrowSGSensor(CoordinatorEntity[SungrowSGCoordinator], SensorEntity):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SungrowSGCoordinator,
        entry: ConfigEntry,
        description: SensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = build_device_info(entry, coordinator.data)

    @property
    def native_value(self):
        return self.coordinator.data.get(self.entity_description.key)
