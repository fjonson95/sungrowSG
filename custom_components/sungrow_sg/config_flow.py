"""Config flow for Sungrow SG-series."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.data_entry_flow import FlowResult
from modbus_connection import ModbusError, ModbusTcpParams
from modbus_connection.tmodbus import ModbusConnection
from sungrow_modbus import SungrowSGInverter

from .const import CONF_UNIT_ID, DEFAULT_PORT, DEFAULT_UNIT_ID, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Optional(CONF_UNIT_ID, default=DEFAULT_UNIT_ID): int,
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


class CannotConnect(Exception):
    """Error to indicate we cannot connect."""
