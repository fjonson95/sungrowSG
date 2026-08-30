"""Register catalog for Sungrow SG-series inverters (SG5.0RT-SG12RT family).

STATUS: SKELETON / UNVERIFIED.

Every entry below is a placeholder shape, not a confirmed address. Before
trusting any of this against a real inverter:

1. Pull Sungrow's official "Communication Protocol of Residential Hybrid
   Inverter / String Inverter (Modbus)" document for the SG5.0RT-SG12RT
   family (available from Sungrow's installer portal / your installer).
2. Cross-check against community-verified maps, e.g.
   https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant
   (note: that project targets the SH-hybrid family, not SG string
   inverters — registers overlap but are NOT identical, so treat it as a
   cross-check, not a source of truth for SG12RT).
3. Confirm on your own SG12RT with a Modbus scanner before wiring a
   register into `models.py`.

Naming follows Sungrow's own register references where known (e.g. a
manufacturer doc entry "5000: Device type code" becomes DEVICE_TYPE_CODE
below with manufacturer_ref="5000"). `address` is the zero-based Modbus
address actually sent on the wire — Sungrow docs are usually 1-based /
40001-style, so double check the offset when transcribing.

Each entry records:
    address           zero-based Modbus register address
    function           "input" (FC04) or "holding" (FC03/06/16)
    manufacturer_ref   the address as printed in Sungrow's doc, for
                        cross-referencing during verification
    count              number of 16-bit registers
    scale              multiply raw value by this to get the real value
    unit               physical unit, if any
    writable           whether the integration should expose a write path
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class RegisterSpec:
    address: int
    function: str  # "input" | "holding"
    manufacturer_ref: str
    count: int = 1
    scale: float = 1.0
    unit: str | None = None
    writable: bool = False
    verified: bool = False


# --- Identification -------------------------------------------------------
# TODO(verify): confirm address + encoding against the official doc.
DEVICE_TYPE_CODE = RegisterSpec(
    address=4999, function="input", manufacturer_ref="5000", count=1
)
SERIAL_NUMBER = RegisterSpec(
    address=4989, function="input", manufacturer_ref="4990-4999", count=10
)

# --- AC measurements --------------------------------------------------------
# TODO(verify): these follow the common SG-series layout seen across
# community projects, but have NOT been confirmed against an official doc
# or a real SG12RT in this project.
PHASE_A_VOLTAGE = RegisterSpec(
    address=5018, function="input", manufacturer_ref="5019", scale=0.1, unit="V"
)
PHASE_B_VOLTAGE = RegisterSpec(
    address=5020, function="input", manufacturer_ref="5021", scale=0.1, unit="V"
)
PHASE_C_VOLTAGE = RegisterSpec(
    address=5022, function="input", manufacturer_ref="5023", scale=0.1, unit="V"
)
TOTAL_ACTIVE_POWER = RegisterSpec(
    address=5030,
    function="input",
    manufacturer_ref="5031-5032",
    count=2,
    scale=1.0,
    unit="W",
)

# --- Energy -----------------------------------------------------------------
DAILY_POWER_YIELD = RegisterSpec(
    address=5002, function="input", manufacturer_ref="5003", scale=0.1, unit="kWh"
)
TOTAL_POWER_YIELD = RegisterSpec(
    address=5003,
    function="input",
    manufacturer_ref="5004-5005",
    count=2,
    scale=0.1,
    unit="kWh",
)

# --- Control (writable) ------------------------------------------------------
# TODO(verify): start/stop and export-limit registers vary by firmware and
# region on Sungrow inverters. Do not implement writes until confirmed on
# real hardware — a wrong register here can disconnect the inverter from
# the grid.
EXPORT_POWER_LIMIT = RegisterSpec(
    address=5006,
    function="holding",
    manufacturer_ref="5007",
    scale=0.1,
    unit="%",
    writable=True,
)
