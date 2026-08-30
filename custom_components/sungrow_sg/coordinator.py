"""DataUpdateCoordinator for Sungrow SG-series.

Builds one `modbus_connection.tmodbus.ModbusConnection` +
`sungrow_modbus.SungrowSGInverter` per config entry and polls it. The
connection is created once in `__init__` and reused across polls -
`ModbusConnection` connects on demand and manages its own reconnects (see
the modbus-connection docs); we don't open/close a socket per poll.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from modbus_connection import ModbusError, ModbusTcpParams
from modbus_connection.tmodbus import ModbusConnection
from sungrow_modbus import SungrowSGInverter

from .const import CONF_UNIT_ID, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class SungrowSGCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Polls one Sungrow SG-series inverter over a shared modbus unit."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self._connection = ModbusConnection(
            ModbusTcpParams(host=entry.data[CONF_HOST], port=entry.data[CONF_PORT])
        )
        self._inverter = SungrowSGInverter(
            self._connection.for_unit(entry.data[CONF_UNIT_ID])
        )

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            await self._inverter.async_update()
        except ModbusError as err:
            raise UpdateFailed(f"Error communicating with inverter: {err}") from err

        inverter = self._inverter
        return {
            # Identification - used for DeviceInfo (model/sw_version/
            # serial_number), not exposed as separate sensor entities.
            "model_name": inverter.model_name,
            "serial_number": inverter.serial_number,
            "protocol_version": inverter.protocol_version,
            # AC measurements
            "phase_a_voltage": inverter.phase_a_voltage,
            "phase_b_voltage": inverter.phase_b_voltage,
            "phase_c_voltage": inverter.phase_c_voltage,
            "phase_a_current": inverter.phase_a_current,
            "phase_b_current": inverter.phase_b_current,
            "phase_c_current": inverter.phase_c_current,
            "total_active_power": inverter.total_active_power,
            "total_reactive_power": inverter.total_reactive_power,
            "total_apparent_power": inverter.total_apparent_power,
            "power_factor": inverter.power_factor,
            "grid_frequency": inverter.grid_frequency,
            # DC / MPPT
            "mppt_1_voltage": inverter.mppt_1_voltage,
            "mppt_1_current": inverter.mppt_1_current,
            "mppt_2_voltage": inverter.mppt_2_voltage,
            "mppt_2_current": inverter.mppt_2_current,
            "total_dc_power": inverter.total_dc_power,
            "bus_voltage": inverter.bus_voltage,
            "negative_voltage_to_ground": inverter.negative_voltage_to_ground,
            # Per-string current
            "string_1_current": inverter.string_1_current,
            "string_2_current": inverter.string_2_current,
            "string_3_current": inverter.string_3_current,
            # Energy yield
            "daily_power_yield": inverter.daily_power_yield,
            "total_power_yield": inverter.total_power_yield,
            "total_running_time": inverter.total_running_time,
            # Grid meter (external CT/smart meter)
            "meter_power": inverter.meter_power,
            "meter_a_phase_power": inverter.meter_a_phase_power,
            "meter_b_phase_power": inverter.meter_b_phase_power,
            "meter_c_phase_power": inverter.meter_c_phase_power,
            "load_power": inverter.load_power,
            "daily_export_energy": inverter.daily_export_energy,
            "total_export_energy": inverter.total_export_energy,
            "daily_import_energy": inverter.daily_import_energy,
            "total_import_energy": inverter.total_import_energy,
            "daily_direct_energy_consumption": inverter.daily_direct_energy_consumption,
            "total_direct_energy_consumption": inverter.total_direct_energy_consumption,
            # Status / diagnostics
            "internal_temperature": inverter.internal_temperature,
            "nominal_active_power": inverter.nominal_active_power,
            "nominal_reactive_power": inverter.nominal_reactive_power,
            "array_insulation_resistance": inverter.array_insulation_resistance,
            "work_state_1_label": inverter.work_state_1_label,
            "work_state_2": inverter.work_state_2,
            "output_type_label": inverter.output_type_label,
        }

    async def async_shutdown(self) -> None:
        """Stop polling and close the shared Modbus connection."""
        await super().async_shutdown()
        await self._connection.close()
