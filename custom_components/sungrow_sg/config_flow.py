"""Config flow for Sungrow SG-series."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry, OptionsFlow
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from modbus_connection import ModbusError, ModbusTcpParams
from modbus_connection.tmodbus import ModbusConnection

from .const import (
    CONF_INCLUDE_METER,
    CONF_INCLUDE_MPPT,
    CONF_INCLUDE_STRINGS,
    CONF_UNIT_ID,
    DEFAULT_INCLUDE_METER,
    DEFAULT_INCLUDE_MPPT,
    DEFAULT_INCLUDE_STRINGS,
    DEFAULT_PORT,
    DEFAULT_UNIT_ID,
    DOMAIN,
    get_toggle,
)
from .sungrow_modbus import SungrowSGInverter

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Optional(CONF_UNIT_ID, default=DEFAULT_UNIT_ID): int,
        vol.Optional(CONF_INCLUDE_STRINGS, default=DEFAULT_INCLUDE_STRINGS): bool,
        vol.Optional(CONF_INCLUDE_MPPT, default=DEFAULT_INCLUDE_MPPT): bool,
        vol.Optional(CONF_INCLUDE_METER, default=DEFAULT_INCLUDE_METER): bool,
    }
)


class SungrowSGConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Sungrow SG-series."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(
                f"{user_input[CONF_HOST]}:{user_input[CONF_PORT]}:"
                f"{user_input[CONF_UNIT_ID]}"
            )
            self._abort_if_unique_id_configured()

            try:
                await self._async_try_connect(user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title=f"Sungrow SG ({user_input[CONF_HOST]})",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def _async_try_connect(self, user_input: dict[str, Any]) -> None:
        """Probe the inverter with one real Modbus read.

        Opens its own short-lived `ModbusConnection` (separate from the
        one `SungrowSGCoordinator` builds for actual polling) and reads
        `device_type_code` - the cheapest read-only register in the
        catalog. Raises `CannotConnect` on any Modbus-level failure
        (unreachable host, wrong port, wrong unit id, timeout - see
        `ModbusError` and its subclasses in `modbus_connection`).
        """
        connection = ModbusConnection(
            ModbusTcpParams(host=user_input[CONF_HOST], port=user_input[CONF_PORT])
        )
        try:
            inverter = SungrowSGInverter(
                connection.for_unit(user_input[CONF_UNIT_ID])
            )
            await inverter.async_update()
        except ModbusError as err:
            raise CannotConnect from err
        else:
            _LOGGER.debug(
                "Connected to %s (device_type_code=0x%04X, model=%s)",
                user_input[CONF_HOST],
                int(inverter.device_type_code),
                inverter.model_name,
            )
        finally:
            await connection.close()

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> SungrowSGOptionsFlow:
        return SungrowSGOptionsFlow()


class SungrowSGOptionsFlow(OptionsFlow):
    """Let the strings/MPPT/meter sensor groups be changed after setup.

    No connection re-probe here on purpose - only the sensor groups
    change, not host/port/unit_id (there's no step to edit those; add a
    reconfigure flow separately if that's ever needed). __init__.py
    registers an update listener that reloads the config entry whenever
    options change - HA does NOT do that on its own, it only fires
    update listeners (see ConfigEntries.async_update_entry's docstring).
    """

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_INCLUDE_STRINGS,
                    default=get_toggle(
                        self.config_entry, CONF_INCLUDE_STRINGS, DEFAULT_INCLUDE_STRINGS
                    ),
                ): bool,
                vol.Optional(
                    CONF_INCLUDE_MPPT,
                    default=get_toggle(
                        self.config_entry, CONF_INCLUDE_MPPT, DEFAULT_INCLUDE_MPPT
                    ),
                ): bool,
                vol.Optional(
                    CONF_INCLUDE_METER,
                    default=get_toggle(
                        self.config_entry, CONF_INCLUDE_METER, DEFAULT_INCLUDE_METER
                    ),
                ): bool,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)


class CannotConnect(Exception):
    """Error to indicate we cannot connect."""
