"""Device model for Sungrow SG-series inverters, built on modbus_connection.

Requires Python >=3.12 and the `modbus-connection` package (see
pyproject.toml). This module intentionally has zero Home Assistant imports —
it should be usable from a plain script (see scripts/query.py) or from the
HA integration in custom_components/sungrow_sg.

NOTE ON API SURFACE: this is written against modbus_connection's published
model API (Component base class; gauge()/uint32()/coil() field helpers;
ModbusConnection.for_unit() to get a ModbusUnit) as described in the HA
developer blog "Modernizing Modbus" (2026-07-05) and the package's PyPI
README. The exact field helper names/signatures have NOT been confirmed by
importing the real package in this environment (it requires Python 3.12,
not available here) - re-check against the installed package's actual API
before trusting this to run.
"""

from __future__ import annotations

from modbus_connection.model import Component, coil, gauge, uint32

from . import registers as reg
from .const import DEVICE_TYPE_CODES


class SungrowSGInverter(Component):
    """Sungrow SG5.0RT-SG12RT family string inverter.

    One `Component` instance = one physical inverter reachable at a given
    Modbus unit id. Field addresses come from `registers.py`; do not hardcode
    raw addresses here so the (unverified) register catalog stays the single
    place to fix once confirmed against the official protocol doc.
    """

    device_type_code = gauge(reg.DEVICE_TYPE_CODE.address, scale=1)

    phase_a_voltage = gauge(
        reg.PHASE_A_VOLTAGE.address,
        scale=reg.PHASE_A_VOLTAGE.scale,
        unit=reg.PHASE_A_VOLTAGE.unit,
    )
    phase_b_voltage = gauge(
        reg.PHASE_B_VOLTAGE.address,
        scale=reg.PHASE_B_VOLTAGE.scale,
        unit=reg.PHASE_B_VOLTAGE.unit,
    )
    phase_c_voltage = gauge(
        reg.PHASE_C_VOLTAGE.address,
        scale=reg.PHASE_C_VOLTAGE.scale,
        unit=reg.PHASE_C_VOLTAGE.unit,
    )

    total_active_power = uint32(
        reg.TOTAL_ACTIVE_POWER.address,
        scale=reg.TOTAL_ACTIVE_POWER.scale,
        unit=reg.TOTAL_ACTIVE_POWER.unit,
    )

    daily_power_yield = gauge(
        reg.DAILY_POWER_YIELD.address,
        scale=reg.DAILY_POWER_YIELD.scale,
        unit=reg.DAILY_POWER_YIELD.unit,
    )
    total_power_yield = uint32(
        reg.TOTAL_POWER_YIELD.address,
        scale=reg.TOTAL_POWER_YIELD.scale,
        unit=reg.TOTAL_POWER_YIELD.unit,
    )

    # Not wired as writable yet on purpose - see registers.py TODO on
    # EXPORT_POWER_LIMIT. Left commented until confirmed safe on real hw.
    # export_power_limit = gauge(
    #     reg.EXPORT_POWER_LIMIT.address,
    #     scale=reg.EXPORT_POWER_LIMIT.scale,
    #     unit=reg.EXPORT_POWER_LIMIT.unit,
    #     writable=True,
    # )

    @property
    def model_name(self) -> str:
        """Best-effort model name from the device type code register.

        Returns "unknown" rather than guessing when the code isn't in
        DEVICE_TYPE_CODES - see const.py TODO.
        """
        return DEVICE_TYPE_CODES.get(int(self.device_type_code), "unknown")
