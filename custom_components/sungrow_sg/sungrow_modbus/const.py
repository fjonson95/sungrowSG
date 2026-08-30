"""Constants for the Sungrow SG-series device model.

DEVICE_TYPE_CODES below is read directly from Appendix 6 ("Device
Information") of Sungrow's official "Communication Protocol of PV
Grid-Connected String Inverters" (V1.1.37 EN) - see registers.py module
docstring for the source. Also matches two independent community projects
(bohdan-s/SunGather, mvandersteen/SungrowInverter). Still NOT verified
against a real inverter - see docs/register_map.md. Do not guess codes
beyond what's listed; an unrecognized code should surface as "unknown
model", not be assumed.
"""

# Manufacturer-assigned device type codes read from the "Device type code"
# register (see registers.py DEVICE_TYPE_CODE, address 5000).
DEVICE_TYPE_CODES: dict[int, str] = {
    0x243D: "SG3.0RT",
    0x243E: "SG4.0RT",
    0x2430: "SG5.0RT",
    0x2431: "SG6.0RT",
    0x243C: "SG7.0RT",
    0x2432: "SG8.0RT",
    0x2433: "SG10RT",
    0x2434: "SG12RT",
    0x2435: "SG15RT",
    0x2436: "SG17RT",
    0x2437: "SG20RT",
}

DEFAULT_UNIT_ID = 1
DEFAULT_PORT = 502

# work_state_1 (registers.py WORK_STATE_1, doc address 5038) - read
# directly from Appendix 1 of the official protocol doc. Live-confirmed
# 2026-08-30: a real SG12RT under normal daytime operation read 0x0
# ("run").
WORK_STATE_1_LABELS: dict[int, str] = {
    0x0000: "run",
    0x8000: "stop",
    0x1300: "key_stop",
    0x1500: "emergency_stop",
    0x1400: "standby",
    0x1200: "initial_standby",
    0x1600: "starting",
    0x9100: "alarm_run",
    0x8100: "derating_run",
    0x8200: "dispatch_run",
    0x5500: "fault",
    0x2500: "communication_fault",
}

# output_type (registers.py OUTPUT_TYPE, doc address 5002) - read
# directly from the official protocol doc's field note: "0-two phase;
# 1-3P4L; 2-3P3L". Live-confirmed 2026-08-30: a real 3-phase SG12RT read
# 1 ("three_phase_4l").
OUTPUT_TYPE_LABELS: dict[int, str] = {
    0: "two_phase",
    1: "three_phase_4l",
    2: "three_phase_3l",
}
