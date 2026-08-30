"""Config flow for Sungrow SG-series.

STATUS: skeleton. The connectivity check in `async_step_user` needs to be
wired up once `modbus_connection` / `sungrow_modbus` are actually
installable in the HA dev environment (Python >=3.12) - see repo README.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.data_entry_flow import FlowResult

from .const import CONF_UNIT_ID, DEFAULT_PORT, DEFAULT_UNIT_ID, DOMAIN

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

            # TODO: actually probe the inverter here via
            # sungrow_modbus.SungrowSGInverter over a modbus_connection
            # ModbusConnection.for_unit(), and set errors["base"] =
            # "cannot_connect" on failure. Left unimplemented until the
            # library is installable in this dev environment.
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
        """Placeholder connectivity probe.

        Raises CannotConnect on failure once implemented. Currently a
        no-op so the flow is exercisable end-to-end before the device
        library is wired in.
        """
        return None


class CannotConnect(Exception):
    """Error to indicate we cannot connect."""
