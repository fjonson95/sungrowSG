"""Constants for the Sungrow SG-series device model.

DEVICE_TYPE_CODES below is read from Appendix 1 ("Adaptive Inverter
Models") of Sungrow's official "Communication Protocol of Residential &
Commercial PV Grid-Connected Inverters" (V1.1.80, 2026-03-27) - see
registers.py module docstring for the source. Also matches two independent
community projects (bohdan-s/SunGather, mvandersteen/SungrowInverter).
0x2434 is live-confirmed against a real SG12RT (2026-08-30). Do not guess
codes beyond what's listed; an unrecognized code should surface as
"unknown model", not be assumed.

Sungrow reuses one model name (e.g. "SG12RT") across multiple regional
variants that each get their own device type code - the doc lists an
"Overseas" default variant and a separate "Australian" variant per power
class, plus "-20"/"-P2" hardware-revision variants. All are mapped to the
same plain model name here since the distinction only matters for the
power-limitation range, which this library doesn't enforce.
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
    0x2438: "SG22RT",
    0x243B: "SG23RT",
    0x2439: "SG25RT",
    # Australian regional variants (distinct device codes, same model names).
    0x2488: "SG3.0RT",
    0x2489: "SG4.0RT",
    0x247D: "SG5.0RT",
    0x247E: "SG6.0RT",
    0x2487: "SG7.0RT",
    0x247F: "SG8.0RT",
    0x2480: "SG10RT",
    0x2481: "SG12RT",
    0x2482: "SG15RT",
    0x2483: "SG17RT",
    0x2484: "SG20RT",
    0x2486: "SG23RT",
    0x2485: "SG25RT",
    # -P2 hardware-revision variants.
    0x244D: "SG3.0RT-P2",
    0x244E: "SG4.0RT-P2",
    0x2440: "SG5.0RT-P2",
    0x2441: "SG6.0RT-P2",
    0x244C: "SG7.0RT-P2",
    0x2442: "SG8.0RT-P2",
    0x2443: "SG10RT-P2",
    0x2444: "SG12RT-P2",
}

DEFAULT_UNIT_ID = 1
DEFAULT_PORT = 502

# work_state_1 (registers.py WORK_STATE_1, doc address 5038) - read
# directly from Appendix 2 "Working State 1" (Table 10) of the official
# protocol doc. Live-confirmed 2026-08-30: a real SG12RT under normal
# daytime operation read 0x0 ("run").
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
    # Added 2026-08-30 from Appendix 2, Table 10 - missed on the first
    # pass through this appendix.
    0x1111: "uninitialized",
}

# work_state_2 (registers.py WORK_STATE_2, doc address 5081-5082) is a
# BITMASK, not an enum like work_state_1 - read from Appendix 3 "Working
# State 2" (Table 11): "The definition corresponding to the state is the
# same as that in Appendix 2" (i.e. bits 0-13 mirror work_state_1's
# states one-for-one, so decoding them individually would just duplicate
# work_state_1_label). The two genuinely new signals are the "total"
# summary bits:
WORK_STATE_2_GRID_CONNECTED_BIT = 17  # "Device is grid-connected running"
WORK_STATE_2_FAULT_BIT = 18  # "Device is in fault stop state"

# output_type (registers.py OUTPUT_TYPE, doc address 5002) - read
# directly from the official protocol doc's field note: "0-two phase;
# 1-3P4L; 2-3P3L". Live-confirmed 2026-08-30: a real 3-phase SG12RT read
# 1 ("three_phase_4l").
OUTPUT_TYPE_LABELS: dict[int, str] = {
    0: "two_phase",
    1: "three_phase_4l",
    2: "three_phase_3l",
}

# FAULT_CODE_LABELS (registers.py FAULT_ALARM_CODE, doc address 5045) -
# read directly from Appendix 4 "Device Fault Code" (Table 12) of the
# V1.1.80 protocol doc. This is a many-values-to-one-name mapping copied
# verbatim from the doc's ranges/lists (e.g. "2, 3, 14, 15" -> "Grid
# Overvoltage"); each disjoint sub-range in a multi-range entry (like
# "532-547, 564-579") is listed as its own tuple below, all mapping to the
# same label. Not hardware-tested (would require forcing a real fault) -
# transcribed from the doc table only. A code missing from this dict
# should surface as "unknown", not raise or guess.
_FAULT_CODE_RANGES: tuple[tuple[tuple[int, ...], str], ...] = (
    ((2, 3, 14, 15), "Grid Overvoltage"),
    ((4, 5), "Grid Undervoltage"),
    ((8,), "Grid Overfrequency"),
    ((9,), "Grid Underfrequency"),
    ((10,), "Grid Power Outage"),
    ((12,), "Excess Leakage Current"),
    ((13,), "Grid Abnormal"),
    ((17,), "Grid Voltage Imbalance"),
    ((28, 29, 208, *range(448, 480)), "PV Reserve Connection Fault"),
    ((*range(532, 548), *range(564, 580)), "PV Reverse Connection Alarm"),
    ((*range(548, 564), *range(580, 596)), "PV Abnormal Alarm"),
    ((37,), "Excessively High Ambient Temperature"),
    ((43,), "Excessively Low Ambient Temperature"),
    ((39,), "Low System Insulation Resistance"),
    ((106,), "Grounding Cable Fault"),
    ((88,), "Electric Arc Fault"),
    ((84,), "Reverse Connection Alarm of the Meter/CT"),
    ((514,), "Meter Communication Abnormal Alarm"),
    ((323,), "Grid Confrontation"),
    ((75,), "Inverter Parallel Communication Alarm"),
    (
        (
            7,
            11,
            16,
            *range(19, 26),
            *range(30, 35),
            36,
            38,
            *range(40, 43),
            *range(44, 51),
            *range(52, 59),
            *range(60, 69),
            85,
            87,
            92,
            93,
            *range(100, 106),
            *range(107, 115),
            *range(116, 125),
            *range(200, 212),
            *range(248, 256),
            *range(300, 323),
            *range(324, 327),
            *range(401, 413),
            *range(600, 604),
            605,
            608,
            612,
            616,
            620,
            *range(622, 625),
            681,
            800,
            802,
            804,
            807,
            *range(1096, 1123),
        ),
        "System Fault",
    ),
    (
        (
            59,
            *range(70, 73),
            74,
            76,
            82,
            83,
            89,
            *range(77, 82),
            *range(216, 219),
            *range(220, 232),
            *range(432, 435),
            *range(500, 514),
            *range(515, 519),
            900,
            901,
            910,
            911,
            635,
            636,
            637,
            638,
            86,
            396,
            397,
            *range(1124, 1128),
        ),
        "System Alarm",
    ),
    (tuple(range(264, 284)), "MPPT Reverse Connection"),
    (tuple(range(332, 364)), "Boost Capacitor Overvoltage Alarm"),
    (tuple(range(364, 396)), "Boost Capacitor Overvoltage Fault"),
    (tuple(range(1548, 1580)), "String Current Reflux"),
    (tuple(range(1600, 1612)), "PV Grounding Fault"),
    ((1616,), "System Hardware Fault"),
    ((1328,), "PV cable-to-ground short circuit"),
)

FAULT_CODE_LABELS: dict[int, str] = {
    code: label for codes, label in _FAULT_CODE_RANGES for code in codes
}
