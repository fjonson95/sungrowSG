"""sungrow-modbus: backend-neutral device model for Sungrow SG-series inverters.

This package only knows Modbus register semantics — value types, scaling,
units, writability. It does not open connections or know about Home
Assistant; a `modbus_connection.ModbusUnit` is injected by the caller
(either the HA integration in this repo, or a standalone script).
"""

from .models import SungrowSGControl, SungrowSGInverter

__all__ = ["SungrowSGControl", "SungrowSGInverter"]
