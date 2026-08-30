"""DataUpdateCoordinator for Sungrow SG-series.

STATUS: skeleton. `_async_update_data` needs to call
`inverter.async_update()` on a `sungrow_modbus.SungrowSGInverter` once the
library is installed - see README for the Python 3.12 requirement.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class SungrowSGCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Polls one Sungrow SG-series inverter over a shared modbus unit."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.entry = entry
        # TODO: build a modbus_connection.ModbusConnection for
        # entry.data[CONF_HOST]/[CONF_PORT], call .for_unit(unit_id), and
        # construct a sungrow_modbus.SungrowSGInverter around it here once
        # the library is installable in this dev environment.
        self._inverter = None

    async def _async_update_data(self) -> dict[str, Any]:
        if self._inverter is None:
            raise UpdateFailed(
                "Sungrow device library not wired up yet (scaffold stage)"
            )
        try:
            await self._inverter.async_update()
        except Exception as err:  # noqa: BLE001 - replace with real exception types
            raise UpdateFailed(f"Error communicating with inverter: {err}") from err
        return {
            "phase_a_voltage": self._inverter.phase_a_voltage,
            "phase_b_voltage": self._inverter.phase_b_voltage,
            "phase_c_voltage": self._inverter.phase_c_voltage,
            "total_active_power": self._inverter.total_active_power,
            "daily_power_yield": self._inverter.daily_power_yield,
            "total_power_yield": self._inverter.total_power_yield,
        }
