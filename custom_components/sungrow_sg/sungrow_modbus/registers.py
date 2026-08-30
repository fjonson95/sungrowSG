"""Register catalog for Sungrow SG-series inverters (SG5.0RT-SG12RT family).

STATUS: verified against Sungrow's official "Communication Protocol of PV
Grid-Connected String Inverters" (V1.1.37 EN), AND spot-checked live
against a real SG12RT over Modbus TCP (2026-08-30): serial_number,
device_type_code (0x2434), phase voltages, daily/total power yield and
total active power all read back plausible values matching the inverter's
own label / display. Not every field in this file has been individually
read off the real device yet - only the ones wired into models.py so far
(see docs/register_map.md for what's still outstanding, e.g. the
holding/write registers).

IMPORTANT - word order on 32-bit (U32/S32) fields:
    The doc doesn't state byte/word order for multi-register values.
    Confirmed live: this inverter (over Modbus TCP) puts the LOW word at
    the first (lower) address and the HIGH word at the second - the
    opposite of the common "big-endian" convention. Decoding
    total_active_power and total_power_yield with word order "big" (the
    modbus_connection default) produced ~99 MW and ~360 GWh on a 12kW
    inverter; switching to "little" gave correct values. Every count=2
    (U32/S32) field's consumer must pass word_order="little" - see
    models.py.

    Only address (see below) and this word-order gotcha have been
    hardware-confirmed - everything else here still traces back to the
    PDF/community cross-reference, not a live read.

Source: bohdan-s/Sungrow-Inverter mirrors the official PDF at
https://github.com/bohdan-s/Sungrow-Inverter/blob/main/Modbus%20Information/Communication%20Protocol%20of%20PV%20Grid-Connected%20String%20Inverters_V1.1.37_EN.pdf
Every field/address/datatype/scale/unit below was read directly from that
document's register tables (section 3.1 "Running information", section
"a) Parameter setting") and Appendix 6 (device type codes).

IMPORTANT - the address offset gotcha:
    The document's own table lists addresses as 1-based "reference
    numbers" (e.g. "Device type code: 5000"), NOT the 0-based address you
    put on the wire. The doc says so explicitly ("Visit all registers by
    subtracting 1 from the register address") and then proves it with
    worked hex examples:
        - "acquire data from address 5000" -> PC sends 0x1387 = 4999
        - "acquire SN ... from address starting from 4990" -> sends
          0x137D = 4989
        - "read data from address 5000 of 4x [holding] type" -> sends
          0x1387 = 4999 (the -1 rule applies to holding registers too)
    This is independently confirmed by bohdan-s/SunGather's actual client
    code (SungrowClient.py in the separate `SungrowClient` PyPI package),
    which stores the document address in its yaml but does
    `register['address'] - 1` before calling pymodbus's
    read_input_registers/read_holding_registers.

    So: `address` below is the real 0-based Modbus PDU address (doc
    address minus 1) - the value to actually pass to a Modbus client.
    `manufacturer_ref` keeps the document's own number for
    cross-referencing against the PDF/community sources, which mostly
    quote the document numbers directly.

Each entry records:
    address           zero-based Modbus register address (doc address - 1)
    function           "input" (FC04) or "holding" (FC03/06/16)
    manufacturer_ref   the address as printed in Sungrow's doc
    count              number of 16-bit registers
    scale              multiply raw value by this to get the real value
    unit               physical unit, if any
    writable           whether the integration should expose a write path
    verified           address/datatype/scale/unit read directly from the
                        official PDF (see module docstring for the file)
    cross_referenced   also matches bohdan-s/SunGather and
                        mvandersteen/SungrowInverter (once their own -1
                        offset is applied)

Not yet done: reading these off a real SG12RT (see docs/register_map.md).
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
    cross_referenced: bool = False


# --- Identification ---------------------------------------------------------
# PROTOCOL_VERSION: marked "Reserved" for doc address 4952-4953 in the
# official SG-string-inverter PDF this file is otherwise built on (see
# module docstring) - that specific field comes from other Sungrow
# documentation (the SH-hybrid protocol doc documents the same address
# as "protocol_version", format 0x01015300 = V1.1.53
# Major.Minor.Patch.Build; "Logger forwarding not supported" per that
# source, i.e. some data-logger/gateway setups don't relay it). Live
# tested 2026-08-30 on this SG12RT with word_order="little" (same
# convention as every other count=2 field here): decoded to a plausible
# 0x01011900 = V1.1.25, one point below the V1.1.37 PDF this file is
# built on - consistent with an inverter running slightly older
# firmware than the latest protocol doc.
PROTOCOL_VERSION = RegisterSpec(
    address=4951,
    function="input",
    manufacturer_ref="4952-4953",
    count=2,
    verified=True,
)
SERIAL_NUMBER = RegisterSpec(
    address=4989,
    function="input",
    manufacturer_ref="4990-4999",
    count=10,
    verified=True,
    cross_referenced=True,
)
DEVICE_TYPE_CODE = RegisterSpec(
    address=4999,
    function="input",
    manufacturer_ref="5000",
    verified=True,
    cross_referenced=True,
)
NOMINAL_ACTIVE_POWER = RegisterSpec(
    address=5000,
    function="input",
    manufacturer_ref="5001",
    scale=0.1,
    unit="kW",
    verified=True,
    cross_referenced=True,
)
OUTPUT_TYPE = RegisterSpec(
    address=5001,
    function="input",
    manufacturer_ref="5002",
    verified=True,
    cross_referenced=True,
)

# --- Energy -------------------------------------------------------------------
DAILY_POWER_YIELD = RegisterSpec(
    address=5002,
    function="input",
    manufacturer_ref="5003",
    scale=0.1,
    unit="kWh",
    verified=True,
    cross_referenced=True,
)
# Generic total-yield register (no extra decimal precision). For the RT
# family the doc's own table points at TOTAL_POWER_YIELD (below, doc
# address 5144) as the higher-precision register - kept here for
# reference / fallback only.
TOTAL_POWER_YIELD_LEGACY = RegisterSpec(
    address=5003,
    function="input",
    manufacturer_ref="5004-5005",
    count=2,
    unit="kWh",
    verified=True,
    cross_referenced=True,
)
TOTAL_RUNNING_TIME = RegisterSpec(
    address=5005,
    function="input",
    manufacturer_ref="5006-5007",
    count=2,
    unit="h",
    verified=True,
    cross_referenced=True,
)

# --- Status / temperature ------------------------------------------------------
INTERNAL_TEMPERATURE = RegisterSpec(
    address=5007,
    function="input",
    manufacturer_ref="5008",
    scale=0.1,
    unit="°C",
    verified=True,
    cross_referenced=True,
)
TOTAL_APPARENT_POWER = RegisterSpec(
    address=5008,
    function="input",
    manufacturer_ref="5009-5010",
    count=2,
    unit="VA",
    verified=True,
    cross_referenced=True,
)

# --- DC / MPPT measurements -----------------------------------------------------
# SG12RT has 2 MPPT trackers (Appendix 6 in the official doc lists SG12RT
# / device code 0x2434 with 2 MPPTs). MPPT_3 exists in the register map
# for larger SG-series models but does not apply to SG12RT.
MPPT_1_VOLTAGE = RegisterSpec(
    address=5010, function="input", manufacturer_ref="5011", scale=0.1, unit="V", verified=True, cross_referenced=True
)
MPPT_1_CURRENT = RegisterSpec(
    address=5011, function="input", manufacturer_ref="5012", scale=0.1, unit="A", verified=True, cross_referenced=True
)
MPPT_2_VOLTAGE = RegisterSpec(
    address=5012, function="input", manufacturer_ref="5013", scale=0.1, unit="V", verified=True, cross_referenced=True
)
MPPT_2_CURRENT = RegisterSpec(
    address=5013, function="input", manufacturer_ref="5014", scale=0.1, unit="A", verified=True, cross_referenced=True
)
TOTAL_DC_POWER = RegisterSpec(
    address=5016,
    function="input",
    manufacturer_ref="5017-5018",
    count=2,
    unit="W",
    verified=True,
    cross_referenced=True,
)

# --- AC measurements --------------------------------------------------------
PHASE_A_VOLTAGE = RegisterSpec(
    address=5018, function="input", manufacturer_ref="5019", scale=0.1, unit="V", verified=True, cross_referenced=True
)
PHASE_B_VOLTAGE = RegisterSpec(
    address=5019, function="input", manufacturer_ref="5020", scale=0.1, unit="V", verified=True, cross_referenced=True
)
PHASE_C_VOLTAGE = RegisterSpec(
    address=5020, function="input", manufacturer_ref="5021", scale=0.1, unit="V", verified=True, cross_referenced=True
)
PHASE_A_CURRENT = RegisterSpec(
    address=5021, function="input", manufacturer_ref="5022", scale=0.1, unit="A", verified=True, cross_referenced=True
)
PHASE_B_CURRENT = RegisterSpec(
    address=5022, function="input", manufacturer_ref="5023", scale=0.1, unit="A", verified=True, cross_referenced=True
)
PHASE_C_CURRENT = RegisterSpec(
    address=5023, function="input", manufacturer_ref="5024", scale=0.1, unit="A", verified=True, cross_referenced=True
)
TOTAL_ACTIVE_POWER = RegisterSpec(
    address=5030,
    function="input",
    manufacturer_ref="5031-5032",
    count=2,
    unit="W",
    verified=True,
    cross_referenced=True,
)
TOTAL_REACTIVE_POWER = RegisterSpec(
    address=5032,
    function="input",
    manufacturer_ref="5033-5034",
    count=2,
    unit="Var",
    verified=True,
    cross_referenced=True,
)
POWER_FACTOR = RegisterSpec(
    address=5034, function="input", manufacturer_ref="5035", scale=0.001, verified=True, cross_referenced=True
)
GRID_FREQUENCY = RegisterSpec(
    address=5035, function="input", manufacturer_ref="5036", scale=0.1, unit="Hz", verified=True, cross_referenced=True
)

# --- Work state / diagnostics ------------------------------------------------
WORK_STATE_1 = RegisterSpec(
    address=5037, function="input", manufacturer_ref="5038", verified=True, cross_referenced=True
)
NOMINAL_REACTIVE_POWER = RegisterSpec(
    address=5048,
    function="input",
    manufacturer_ref="5049",
    scale=0.1,
    unit="kVar",
    verified=True,
    cross_referenced=True,
)
ARRAY_INSULATION_RESISTANCE = RegisterSpec(
    address=5070,
    function="input",
    manufacturer_ref="5071",
    unit="kΩ",
    verified=True,
    cross_referenced=True,
)
WORK_STATE_2 = RegisterSpec(
    address=5080,
    function="input",
    manufacturer_ref="5081-5082",
    count=2,
    verified=True,
    cross_referenced=True,
)
NEGATIVE_VOLTAGE_TO_GROUND = RegisterSpec(
    address=5145,
    function="input",
    manufacturer_ref="5146",
    scale=0.1,
    unit="V",
    verified=True,
)
BUS_VOLTAGE = RegisterSpec(
    address=5146,
    function="input",
    manufacturer_ref="5147",
    scale=0.1,
    unit="V",
    verified=True,
)

# Precise total-yield register for the RT family (doc explicitly lists
# SG12RT under this entry's "valid for inverters" list).
TOTAL_POWER_YIELD = RegisterSpec(
    address=5143,
    function="input",
    manufacturer_ref="5144-5145",
    count=2,
    scale=0.1,
    unit="kWh",
    verified=True,
    cross_referenced=True,
)

# --- Per-string current ("Combiner board information") -----------------------
# NOTE: Sungrow SG string inverters do not report per-string VOLTAGE - only
# per-string CURRENT. Strings on the same MPPT are wired in parallel, so
# they share one voltage (MPPT_1_VOLTAGE / MPPT_2_VOLTAGE above); there is
# no such thing as "string voltage" in this protocol, doc-confirmed and
# not a gap in this file.
#
# Appendix 6 lists SG12RT's "String/MPPT" as "2;1": MPPT 1 has 2 strings,
# MPPT 2 has 1 string, so 3 physical string-current registers total
# (STRING_1/2_CURRENT on MPPT 1, STRING_3_CURRENT on MPPT 2). The doc
# warns: "If the value of string/MPPT is 1, it indicates that no string
# information (7013-7036) is uploaded" - not the case for SG12RT.
# Live-confirmed 2026-08-30: reads back plausible non-garbage amperages.
STRING_1_CURRENT = RegisterSpec(
    address=7012, function="input", manufacturer_ref="7013", scale=0.01, unit="A", verified=True, cross_referenced=True
)
STRING_2_CURRENT = RegisterSpec(
    address=7013, function="input", manufacturer_ref="7014", scale=0.01, unit="A", verified=True, cross_referenced=True
)
STRING_3_CURRENT = RegisterSpec(
    address=7014, function="input", manufacturer_ref="7015", scale=0.01, unit="A", verified=True, cross_referenced=True
)

# --- Grid meter (external CT/smart meter, e.g. for export limiting) ----------
# The doc's own "Valid for inverters" list on this block only names
# SG5KTL-MT/SG6KTL-MT/SG8KTL-M/SG10KTL-M/SG10KTL-MT/SG12KTL-M/SG15KTL-M/
# SG17KTL-M/SG20KTL-M - NOT the RT family SG12RT belongs to. Despite that,
# live-tested 2026-08-30 against a real SG12RT and got fully plausible,
# internally consistent values (meter_a/b/c_phase_power summed to exactly
# meter_power; daily/total export+import were sane magnitudes relative to
# total_power_yield). Treat as working on this unit; a differently
# configured SG12RT without a CT/meter accessory attached may read zeros
# or garbage here instead of raising an error.
METER_POWER = RegisterSpec(
    address=5082, function="input", manufacturer_ref="5083-5084", count=2, unit="W", verified=True, cross_referenced=True
)
METER_A_PHASE_POWER = RegisterSpec(
    address=5084, function="input", manufacturer_ref="5085-5086", count=2, unit="W", verified=True, cross_referenced=True
)
METER_B_PHASE_POWER = RegisterSpec(
    address=5086, function="input", manufacturer_ref="5087-5088", count=2, unit="W", verified=True, cross_referenced=True
)
METER_C_PHASE_POWER = RegisterSpec(
    address=5088, function="input", manufacturer_ref="5089-5090", count=2, unit="W", verified=True, cross_referenced=True
)
LOAD_POWER = RegisterSpec(
    address=5090, function="input", manufacturer_ref="5091-5092", count=2, unit="W", verified=True, cross_referenced=True
)
DAILY_EXPORT_ENERGY = RegisterSpec(
    address=5092, function="input", manufacturer_ref="5093-5094", count=2, scale=0.1, unit="kWh", verified=True, cross_referenced=True
)
TOTAL_EXPORT_ENERGY = RegisterSpec(
    address=5094, function="input", manufacturer_ref="5095-5096", count=2, scale=0.1, unit="kWh", verified=True, cross_referenced=True
)
DAILY_IMPORT_ENERGY = RegisterSpec(
    address=5096, function="input", manufacturer_ref="5097-5098", count=2, scale=0.1, unit="kWh", verified=True, cross_referenced=True
)
TOTAL_IMPORT_ENERGY = RegisterSpec(
    address=5098, function="input", manufacturer_ref="5099-5100", count=2, scale=0.1, unit="kWh", verified=True, cross_referenced=True
)
DAILY_DIRECT_ENERGY_CONSUMPTION = RegisterSpec(
    address=5100, function="input", manufacturer_ref="5101-5102", count=2, scale=0.1, unit="kWh", verified=True, cross_referenced=True
)
TOTAL_DIRECT_ENERGY_CONSUMPTION = RegisterSpec(
    address=5102, function="input", manufacturer_ref="5103-5104", count=2, scale=0.1, unit="kWh", verified=True, cross_referenced=True
)

# --- Control (writable, holding registers) ------------------------------------
# Address/scale/unit read directly from the official doc's "a) Parameter
# setting address definition (holding register, Address type: 4X)" table
# - same -1 offset rule applies to holding registers (see module
# docstring: example (d) reads doc address 5000 by sending wire 0x1387 =
# 4999 with function code 0x03).
#
# Still do NOT wire these into models.py as writable until confirmed on
# real hardware - a wrong register/value here can disconnect the inverter
# from the grid. See docs/register_map.md.
START_STOP = RegisterSpec(
    address=5005,
    function="holding",
    manufacturer_ref="5006",
    writable=True,
    verified=True,
)
POWER_LIMITATION_SWITCH = RegisterSpec(
    address=5006,
    function="holding",
    manufacturer_ref="5007",
    writable=True,
    verified=True,
)
POWER_LIMITATION_SETTING = RegisterSpec(
    address=5007,
    function="holding",
    manufacturer_ref="5008",
    scale=0.1,
    unit="%",
    writable=True,
    verified=True,
)
# Doc-confirmed for SG12RT explicitly ("Valid for inverters" lists it by
# name). Live-tested 2026-08-30: read back 0x55 (Disable) - a sane
# installed-default state, not garbage.
NIGHT_SVG_SWITCH = RegisterSpec(
    address=5034,
    function="holding",
    manufacturer_ref="5035",
    writable=True,
    verified=True,
)
