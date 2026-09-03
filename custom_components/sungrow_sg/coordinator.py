"""DataUpdateCoordinator for Sungrow SG-series.

Builds one `modbus_connection.tmodbus.ModbusConnection` +
`sungrow_modbus.SungrowSGInverter` per config entry and polls it. The
connection is created once in `__init__` and reused across polls -
`ModbusConnection` connects on demand and manages its own reconnects (see
the modbus-connection docs); we don't open/close a socket per poll.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util
from modbus_connection import ModbusError, ModbusTcpParams, ModbusTimeoutError
from modbus_connection.tmodbus import ModbusConnection

from .const import (
    CONF_INCLUDE_METER,
    CONF_INCLUDE_MPPT,
    CONF_INCLUDE_STRINGS,
    CONF_UNIT_ID,
    DEFAULT_INCLUDE_METER,
    DEFAULT_INCLUDE_MPPT,
    DEFAULT_INCLUDE_STRINGS,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    get_toggle,
    restricted_field_names,
)
from .sungrow_modbus import SungrowSGControl, SungrowSGInverter

_LOGGER = logging.getLogger(__name__)

# A transient Modbus TCP timeout (a dropped packet, a brief network blip)
# shouldn't immediately mark every entity unavailable - retry a few times,
# spaced out, before giving up. See _async_update_data.
_UPDATE_RETRY_ATTEMPTS = 3
_UPDATE_RETRY_DELAY_SECONDS = 10


def _is_enabled(value: Any, *, on: int) -> bool | None:
    """None before the first poll; otherwise whether the raw register
    value equals its "on" enum code (e.g. 0xCF for start_stop, 0xAA for
    the two enable/disable switches).
    """
    return None if value is None else int(value) == on


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
        # Counts every ModbusTimeoutError attempt specifically (not other
        # ModbusError subclasses, and not just full-poll UpdateFailed
        # events - a retry that eventually succeeds still counts), reset
        # at local midnight. See _async_update_data.
        self._timeout_count = 0
        self._timeout_count_day = dt_util.now().date()
        self._connection = ModbusConnection(
            ModbusTcpParams(host=entry.data[CONF_HOST], port=entry.data[CONF_PORT])
        )
        unit = self._connection.for_unit(entry.data[CONF_UNIT_ID])
        self._inverter = SungrowSGInverter(unit)
        # Separate Component sharing the same unit: SungrowSGControl's
        # fields live in the holding register space (writable), while
        # SungrowSGInverter's are all input (read-only) - see
        # SungrowSGControl's docstring for why they can't be one Component.
        self._control = SungrowSGControl(unit)
        # Only actually poll the registers the enabled sensor groups need -
        # e.g. a unit with no CT/meter accessory can otherwise read zeros
        # or garbage on the meter block for no benefit (see
        # sungrow_modbus registers.py METER_POWER docstring).
        self._inverter.restrict_fields(
            restricted_field_names(
                include_mppt=get_toggle(entry, CONF_INCLUDE_MPPT, DEFAULT_INCLUDE_MPPT),
                include_strings=get_toggle(
                    entry, CONF_INCLUDE_STRINGS, DEFAULT_INCLUDE_STRINGS
                ),
                include_meter=get_toggle(
                    entry, CONF_INCLUDE_METER, DEFAULT_INCLUDE_METER
                ),
            )
        )

    async def _async_update_data(self) -> dict[str, Any]:
        # Reset the daily timeout counter on the first poll of a new
        # local day - checked unconditionally (not just on failure) so a
        # quiet day correctly shows 0 instead of carrying over
        # yesterday's count until the next failure happens to occur.
        today = dt_util.now().date()
        if today != self._timeout_count_day:
            self._timeout_count = 0
            self._timeout_count_day = today

        # A single dropped poll (e.g. one Modbus TCP timeout) shouldn't
        # flip every entity to unavailable - retry a couple of times
        # first. Only give up and let UpdateFailed propagate (which is
        # what actually marks entities unavailable) after
        # _UPDATE_RETRY_ATTEMPTS straight failures.
        last_err: ModbusError | None = None
        for attempt in range(1, _UPDATE_RETRY_ATTEMPTS + 1):
            try:
                await self._inverter.async_update()
                await self._control.async_update()
            except ModbusError as err:
                last_err = err
                if isinstance(err, ModbusTimeoutError):
                    self._timeout_count += 1
                _LOGGER.debug(
                    "Modbus read failed (attempt %d/%d): %s",
                    attempt,
                    _UPDATE_RETRY_ATTEMPTS,
                    err,
                )
                if attempt < _UPDATE_RETRY_ATTEMPTS:
                    await asyncio.sleep(_UPDATE_RETRY_DELAY_SECONDS)
                continue
            else:
                break
        else:
            raise UpdateFailed(
                f"Error communicating with inverter after {_UPDATE_RETRY_ATTEMPTS} "
                f"attempts: {last_err}"
            ) from last_err

        inverter = self._inverter
        control = self._control
        return {
            "timeout_count_today": self._timeout_count,
            # Writable controls (holding registers). start_stop/
            # power_limitation_switch/night_svg_switch come back from the
            # register as raw enum ints (0xCF/0xCE, 0xAA/0x55) - turned
            # into plain bools here so switch.py doesn't need to know the
            # magic numbers, matching what SungrowSGControl.write()
            # accepts on the way in (see models.py _validate_start_stop).
            "start_stop_is_running": _is_enabled(control.start_stop, on=0xCF),
            "power_limitation_enabled": _is_enabled(
                control.power_limitation_switch, on=0xAA
            ),
            "power_limitation_setting": control.power_limitation_setting,
            "power_limitation_adjustment": control.power_limitation_adjustment,
            "feed_in_power_limit_enabled": _is_enabled(
                control.feed_in_power_limit_switch, on=0xAA
            ),
            "feed_in_power_limit_value": control.feed_in_power_limit_value,
            "feed_in_power_limit_ratio": control.feed_in_power_limit_ratio,
            "night_svg_enabled": _is_enabled(control.night_svg_switch, on=0xAA),
            # Identification - used for DeviceInfo (model/sw_version/
            # serial_number), not exposed as separate sensor entities.
            "model_name": inverter.model_name,
            "serial_number": inverter.serial_number,
            "protocol_version": inverter.protocol_version,
            # Newly documented in the V1.1.80 protocol doc (2026-03-27) -
            # meaning of "protocol_no" beyond the register table itself is
            # undocumented, exposed as-is as a diagnostic sensor.
            "protocol_no": inverter.protocol_no,
            "arm_software_version": inverter.arm_software_version,
            "dsp_software_version": inverter.dsp_software_version,
            # AC measurements
            "phase_a_voltage": inverter.phase_a_voltage,
            "phase_b_voltage": inverter.phase_b_voltage,
            "phase_c_voltage": inverter.phase_c_voltage,
            "phase_a_current": inverter.phase_a_current,
            "phase_b_current": inverter.phase_b_current,
            "phase_c_current": inverter.phase_c_current,
            "total_active_power": inverter.total_active_power,
            "capacity_utilization": inverter.capacity_utilization,
            "total_reactive_power": inverter.total_reactive_power,
            "total_apparent_power": inverter.total_apparent_power,
            "power_factor": inverter.power_factor,
            "grid_frequency": inverter.grid_frequency,
            # DC / MPPT
            "mppt_1_voltage": inverter.mppt_1_voltage,
            "mppt_1_current": inverter.mppt_1_current,
            "mppt_1_power": inverter.mppt_1_power,
            "mppt_2_voltage": inverter.mppt_2_voltage,
            "mppt_2_current": inverter.mppt_2_current,
            "mppt_2_power": inverter.mppt_2_power,
            "total_dc_power": inverter.total_dc_power,
            "bus_voltage": inverter.bus_voltage,
            "negative_voltage_to_ground": inverter.negative_voltage_to_ground,
            # Per-string current + calculated power (no direct register -
            # see sungrow_modbus models.py string_N_power docstrings)
            "string_1_current": inverter.string_1_current,
            "string_1_power": inverter.string_1_power,
            "string_2_current": inverter.string_2_current,
            "string_2_power": inverter.string_2_power,
            "string_3_current": inverter.string_3_current,
            "string_3_power": inverter.string_3_power,
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
            "daily_running_time": inverter.daily_running_time,
            "monthly_power_yield": inverter.monthly_power_yield,
            "work_state_1_label": inverter.work_state_1_label,
            "work_state_2": inverter.work_state_2,
            "is_grid_connected": inverter.is_grid_connected,
            "is_in_fault": inverter.is_in_fault,
            "output_type_label": inverter.output_type_label,
            "fault_alarm_time": inverter.fault_alarm_time,
            "fault_alarm_label": inverter.fault_alarm_label,
        }

    async def async_shutdown(self) -> None:
        """Stop polling and close the shared Modbus connection."""
        await super().async_shutdown()
        await self._connection.close()

    async def _async_write_control(self, field: str, value: Any) -> None:
        """Write one SungrowSGControl field, then refresh so entities
        reflect the confirmed new state (not an optimistic guess) - see
        registers.py's "do not touch until confirmed" caution on these.

        Raises HomeAssistantError (not a raw ModbusError/ValueError) so
        switch/number entities show the user a real error instead of an
        unhandled-exception log entry.
        """
        try:
            await self._control.write(field, value)
        except (ModbusError, ValueError) as err:
            raise HomeAssistantError(
                f"Failed to write {field} to the inverter: {err}"
            ) from err
        await self.async_request_refresh()

    async def async_set_start_stop(self, *, running: bool) -> None:
        await self._async_write_control("start_stop", running)

    async def async_set_power_limitation_enabled(self, *, enabled: bool) -> None:
        await self._async_write_control("power_limitation_switch", enabled)

    async def async_set_power_limitation_setting(self, percent: float) -> None:
        await self._async_write_control("power_limitation_setting", percent)

    async def async_set_power_limitation_adjustment(self, kw: float) -> None:
        await self._async_write_control("power_limitation_adjustment", kw)

    async def async_set_feed_in_power_limit_enabled(self, *, enabled: bool) -> None:
        await self._async_write_control("feed_in_power_limit_switch", enabled)

    async def async_set_feed_in_power_limit_value(self, kw: float) -> None:
        await self._async_write_control("feed_in_power_limit_value", kw)

    async def async_set_feed_in_power_limit_ratio(self, percent: float) -> None:
        await self._async_write_control("feed_in_power_limit_ratio", percent)

    async def async_set_night_svg_enabled(self, *, enabled: bool) -> None:
        await self._async_write_control("night_svg_switch", enabled)
