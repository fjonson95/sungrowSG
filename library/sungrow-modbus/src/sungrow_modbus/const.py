"""Constants for the Sungrow SG-series device model.

DEVICE_TYPE_CODES is intentionally sparse — fill in as models are verified
against Sungrow's official Modbus protocol document. Do not guess codes;
an unrecognized code should surface as "unknown model", not be assumed.
"""

# Manufacturer-assigned device type codes read from the "Device type code"
# register. TODO: verify against Sungrow's official Modbus protocol PDF for
# the SG5.0RT-SG12RT family before relying on these in the integration.
DEVICE_TYPE_CODES: dict[int, str] = {
    # 0x0D03: "SG12RT",  # PLACEHOLDER - verify real code before uncommenting
}

DEFAULT_UNIT_ID = 1
DEFAULT_PORT = 502
