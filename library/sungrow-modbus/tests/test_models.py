"""Tests for SungrowSGInverter.

Run against modbus_connection's own in-memory mock (`MockModbusUnit`, via
its `mock_modbus_unit` pytest fixture) - not against a real inverter. This
catches register-plumbing bugs (wrong register space, wrong address,
wrong scale/decode) that a `models.py` typo would otherwise only surface
against real hardware. It is not a substitute for that real-hardware test
- see docs/register_map.md for the plan there.
"""

import pytest
from sungrow_modbus import SungrowSGInverter
from sungrow_modbus import registers as reg
from sungrow_modbus.models import SungrowSGControl


async def test_reads_identity_and_measurements(mock_modbus_unit):
    # Values are Sungrow's raw register words - RegisterSpec.scale is what
    # turns e.g. 2301 into 230.1 V.
    mock_modbus_unit.input[reg.DEVICE_TYPE_CODE.address] = 0x2434  # SG12RT
    mock_modbus_unit.input[reg.PHASE_A_VOLTAGE.address] = 2301
    mock_modbus_unit.input[reg.PHASE_B_VOLTAGE.address] = 2302
    mock_modbus_unit.input[reg.PHASE_C_VOLTAGE.address] = 2303
    # uint32 fields are word_order="little" (confirmed live against a real
    # SG12RT: low word at the first address, high word at the second).
    mock_modbus_unit.input[reg.TOTAL_ACTIVE_POWER.address] = 3456
    mock_modbus_unit.input[reg.TOTAL_ACTIVE_POWER.address + 1] = 0
    mock_modbus_unit.input[reg.DAILY_POWER_YIELD.address] = 123
    mock_modbus_unit.input[reg.TOTAL_POWER_YIELD.address] = 45678
    mock_modbus_unit.input[reg.TOTAL_POWER_YIELD.address + 1] = 0

    inverter = SungrowSGInverter(mock_modbus_unit)
    await inverter.async_update()

    assert inverter.model_name == "SG12RT"
    assert inverter.phase_a_voltage == 230.1
    assert inverter.phase_b_voltage == 230.2
    assert inverter.phase_c_voltage == 230.3
    assert inverter.total_active_power == 3456
    assert inverter.daily_power_yield == 12.3
    assert inverter.total_power_yield == 4567.8


async def test_reads_string_currents_and_meter(mock_modbus_unit):
    mock_modbus_unit.input[reg.STRING_1_CURRENT.address] = 76  # 0.76 A
    mock_modbus_unit.input[reg.STRING_2_CURRENT.address] = 0
    mock_modbus_unit.input[reg.STRING_3_CURRENT.address] = 104  # 1.04 A

    # meter_b_phase_power = -286 W, S32 word_order="little": low word
    # first, two's complement 0xFFFFFEE2 -> low=0xFEE2, high=0xFFFF.
    mock_modbus_unit.input[reg.METER_B_PHASE_POWER.address] = 0xFEE2
    mock_modbus_unit.input[reg.METER_B_PHASE_POWER.address + 1] = 0xFFFF
    mock_modbus_unit.input[reg.TOTAL_EXPORT_ENERGY.address] = 15532
    mock_modbus_unit.input[reg.TOTAL_EXPORT_ENERGY.address + 1] = 3

    inverter = SungrowSGInverter(mock_modbus_unit)
    await inverter.async_update()

    assert inverter.string_1_current == 0.76
    assert inverter.string_2_current == 0.0
    assert inverter.string_3_current == 1.04
    assert inverter.meter_b_phase_power == -286
    assert inverter.total_export_energy == 21214.0


async def test_reads_protocol_version_and_bus_voltage(mock_modbus_unit):
    # 0x01011900 = V1.1.25.0 (Major.Minor.Patch.Build), word_order="little"
    # so the low word (0x1900) sits at the first address.
    mock_modbus_unit.input[reg.PROTOCOL_VERSION.address] = 0x1900
    mock_modbus_unit.input[reg.PROTOCOL_VERSION.address + 1] = 0x0101
    mock_modbus_unit.input[reg.NEGATIVE_VOLTAGE_TO_GROUND.address] = 0
    mock_modbus_unit.input[reg.BUS_VOLTAGE.address] = 6795  # 679.5 V

    inverter = SungrowSGInverter(mock_modbus_unit)
    await inverter.async_update()

    assert inverter.protocol_version == "1.1.25.0"
    assert inverter.negative_voltage_to_ground == 0.0
    assert inverter.bus_voltage == 679.5


def _ascii_words(text: str) -> list[int]:
    """Pack ASCII text into 16-bit big-endian register words (2 chars each)."""
    data = text.encode("ascii")
    if len(data) % 2:
        data += b"\x00"
    return [(data[i] << 8) | data[i + 1] for i in range(0, len(data), 2)]


async def test_reads_protocol_no_and_firmware_versions(mock_modbus_unit):
    """Newly documented in protocol doc V1.1.80 (2026-03-27) - previously
    an undocumented "Reserved" ASCII block, see registers.py.
    """
    mock_modbus_unit.input[reg.PROTOCOL_NO.address] = 1
    mock_modbus_unit.input[reg.PROTOCOL_NO.address + 1] = 0
    for i, word in enumerate(_ascii_words("ARM_V11_A")):
        mock_modbus_unit.input[reg.ARM_SOFTWARE_VERSION.address + i] = word
    for i, word in enumerate(_ascii_words("DSP_V11_A")):
        mock_modbus_unit.input[reg.DSP_SOFTWARE_VERSION.address + i] = word

    inverter = SungrowSGInverter(mock_modbus_unit)
    await inverter.async_update()

    assert inverter.protocol_no == 1
    assert inverter.arm_software_version == "ARM_V11_A"
    assert inverter.dsp_software_version == "DSP_V11_A"


async def test_fault_alarm_label_and_time_decode(mock_modbus_unit):
    mock_modbus_unit.input[reg.FAULT_ALARM_YEAR.address] = 2026
    mock_modbus_unit.input[reg.FAULT_ALARM_MONTH.address] = 8
    mock_modbus_unit.input[reg.FAULT_ALARM_DAY.address] = 30
    mock_modbus_unit.input[reg.FAULT_ALARM_HOUR.address] = 14
    mock_modbus_unit.input[reg.FAULT_ALARM_MINUTE.address] = 5
    mock_modbus_unit.input[reg.FAULT_ALARM_SECOND.address] = 9
    mock_modbus_unit.input[reg.FAULT_ALARM_CODE.address] = 8  # Grid Overfrequency

    inverter = SungrowSGInverter(mock_modbus_unit)
    await inverter.async_update()

    assert inverter.fault_alarm_time == "2026-08-30 14:05:09"
    assert inverter.fault_alarm_label == "Grid Overfrequency"


async def test_fault_alarm_no_event_and_unknown_code(mock_modbus_unit):
    # Year=0/code=0 is the "no fault recorded" state - not an all-zero
    # coincidence, it's how a healthy inverter's registers read.
    mock_modbus_unit.input[reg.FAULT_ALARM_YEAR.address] = 0
    mock_modbus_unit.input[reg.FAULT_ALARM_CODE.address] = 0

    inverter = SungrowSGInverter(mock_modbus_unit)
    await inverter.async_update()

    assert inverter.fault_alarm_time is None
    assert inverter.fault_alarm_label is None

    mock_modbus_unit.input[reg.FAULT_ALARM_CODE.address] = 65535  # not in the table
    await inverter.async_update()
    assert inverter.fault_alarm_label == "unknown"


async def test_reads_daily_running_time_and_monthly_yield(mock_modbus_unit):
    """Cross-checked against iSolarCloud (Sungrow's cloud UI) 2026-08-30:
    "Daily operating time"/"Yield this month" matched these exactly.
    """
    mock_modbus_unit.input[reg.DAILY_RUNNING_TIME.address] = 837
    mock_modbus_unit.input[reg.MONTHLY_POWER_YIELD.address] = 17000
    mock_modbus_unit.input[reg.MONTHLY_POWER_YIELD.address + 1] = 0

    inverter = SungrowSGInverter(mock_modbus_unit)
    await inverter.async_update()

    assert inverter.daily_running_time == 837
    assert inverter.monthly_power_yield == 1700.0


async def test_reads_dc_ac_and_status_fields(mock_modbus_unit):
    mock_modbus_unit.input[reg.NOMINAL_ACTIVE_POWER.address] = 120  # 12.0 kW
    mock_modbus_unit.input[reg.MPPT_1_VOLTAGE.address] = 6396
    mock_modbus_unit.input[reg.MPPT_1_CURRENT.address] = 31
    mock_modbus_unit.input[reg.PHASE_A_CURRENT.address] = 48

    # total_dc_power / total_apparent_power / total_reactive_power /
    # total_running_time / work_state_2 are all count=2 - word_order
    # "little" like every other 32-bit field here.
    mock_modbus_unit.input[reg.TOTAL_DC_POWER.address] = 3554
    mock_modbus_unit.input[reg.TOTAL_DC_POWER.address + 1] = 0
    mock_modbus_unit.input[reg.TOTAL_REACTIVE_POWER.address] = 5
    mock_modbus_unit.input[reg.TOTAL_REACTIVE_POWER.address + 1] = 0
    mock_modbus_unit.input[reg.GRID_FREQUENCY.address] = 4999  # scale 0.01Hz
    mock_modbus_unit.input[reg.WORK_STATE_1.address] = 0
    # bit 0 (running) + bit 17 (grid connected) = 0x20001, live-confirmed
    # against a real SG12RT during normal daytime operation.
    mock_modbus_unit.input[reg.WORK_STATE_2.address] = 0x0001
    mock_modbus_unit.input[reg.WORK_STATE_2.address + 1] = 0x0002

    # Doc: array_insulation_resistance 0xFFFF means "invalid" - modeled
    # via gauge(nan=0xFFFF), must decode to None, not 6553.5 kOhm.
    mock_modbus_unit.input[reg.ARRAY_INSULATION_RESISTANCE.address] = 0xFFFF

    inverter = SungrowSGInverter(mock_modbus_unit)
    await inverter.async_update()

    assert inverter.nominal_active_power == 12.0
    assert inverter.mppt_1_voltage == 639.6
    assert inverter.mppt_1_current == 3.1
    assert inverter.mppt_1_power == 1982.8  # 639.6 * 3.1, no direct register
    assert inverter.phase_a_current == 4.8
    assert inverter.total_dc_power == 3554
    assert inverter.total_reactive_power == 5
    assert inverter.grid_frequency == 49.99
    assert inverter.work_state_1 == 0
    assert inverter.work_state_1_label == "run"
    assert inverter.work_state_2 == 0x20001
    assert inverter.is_grid_connected is True
    assert inverter.is_in_fault is False
    assert inverter.array_insulation_resistance is None


async def test_work_state_2_fault_bit_and_before_first_update(mock_modbus_unit):
    assert SungrowSGInverter(mock_modbus_unit).is_grid_connected is None
    assert SungrowSGInverter(mock_modbus_unit).is_in_fault is None

    # bit 18 (fault) set, bit 17 (grid connected) not set - 0x40000.
    mock_modbus_unit.input[reg.WORK_STATE_2.address] = 0x0000
    mock_modbus_unit.input[reg.WORK_STATE_2.address + 1] = 0x0004

    inverter = SungrowSGInverter(mock_modbus_unit)
    await inverter.async_update()

    assert inverter.work_state_2 == 0x40000
    assert inverter.is_grid_connected is False
    assert inverter.is_in_fault is True


async def test_calculated_string_power_uses_the_right_mppt_voltage(mock_modbus_unit):
    """string_1/2 share MPPT 1's voltage, string_3 uses MPPT 2's - not a
    single global voltage (see models.py docstrings on each property).
    """
    mock_modbus_unit.input[reg.MPPT_1_VOLTAGE.address] = 6321  # 632.1 V
    mock_modbus_unit.input[reg.MPPT_2_VOLTAGE.address] = 4875  # 487.5 V
    mock_modbus_unit.input[reg.STRING_1_CURRENT.address] = 298  # 2.98 A
    mock_modbus_unit.input[reg.STRING_2_CURRENT.address] = 0
    mock_modbus_unit.input[reg.STRING_3_CURRENT.address] = 312  # 3.12 A

    inverter = SungrowSGInverter(mock_modbus_unit)
    await inverter.async_update()

    assert inverter.string_1_power == 1883.7  # 632.1 * 2.98 (MPPT 1)
    assert inverter.string_2_power == 0.0
    assert inverter.string_3_power == 1521.0  # 487.5 * 3.12 (MPPT 2)


@pytest.mark.parametrize(
    ("power_w", "nominal_raw", "expected_percent"),
    [
        (3370, 120, 28.1),  # 3.37kW / 12.0kW - typical daytime reading
        (-5, 120, 0.0),  # briefly negative (S32) - clamped to 0, not negative
        (13200, 120, 100.0),  # 110% overload - clamped to 100, not shown over
    ],
)
async def test_capacity_utilization_scales_and_clamps(
    mock_modbus_unit, power_w, nominal_raw, expected_percent
):
    mock_modbus_unit.input[reg.NOMINAL_ACTIVE_POWER.address] = nominal_raw
    raw = power_w & 0xFFFFFFFF
    mock_modbus_unit.input[reg.TOTAL_ACTIVE_POWER.address] = raw & 0xFFFF
    mock_modbus_unit.input[reg.TOTAL_ACTIVE_POWER.address + 1] = raw >> 16

    inverter = SungrowSGInverter(mock_modbus_unit)
    await inverter.async_update()

    assert inverter.capacity_utilization == expected_percent


async def test_capacity_utilization_is_none_without_both_inputs(mock_modbus_unit):
    assert SungrowSGInverter(mock_modbus_unit).capacity_utilization is None


async def test_calculated_power_is_none_without_both_inputs(mock_modbus_unit):
    """No TypeError from None * None - before the first async_update(),
    and after restrict_fields() excludes an underlying field.
    """
    inverter = SungrowSGInverter(mock_modbus_unit)
    assert inverter.mppt_1_power is None
    assert inverter.string_1_power is None

    mock_modbus_unit.input[reg.MPPT_1_VOLTAGE.address] = 6321
    mock_modbus_unit.input[reg.MPPT_1_CURRENT.address] = 31
    inverter.restrict_fields(["mppt_1_voltage"])  # mppt_1_current excluded
    await inverter.async_update()

    assert inverter.mppt_1_voltage == 632.1
    assert inverter.mppt_1_current is None
    assert inverter.mppt_1_power is None


async def test_work_state_and_output_type_labels_fall_back_to_unknown(mock_modbus_unit):
    mock_modbus_unit.input[reg.WORK_STATE_1.address] = 0x1234  # not in Appendix 1
    mock_modbus_unit.input[reg.OUTPUT_TYPE.address] = 1  # 3P4L

    inverter = SungrowSGInverter(mock_modbus_unit)
    await inverter.async_update()

    assert inverter.work_state_1_label == "unknown"
    assert inverter.output_type_label == "three_phase_4l"


async def test_unrecognized_device_type_code_is_unknown(mock_modbus_unit):
    mock_modbus_unit.input[reg.DEVICE_TYPE_CODE.address] = 0xFFFF

    inverter = SungrowSGInverter(mock_modbus_unit)
    await inverter.async_update()

    assert inverter.model_name == "unknown"


async def test_reads_target_the_input_register_space(mock_modbus_unit):
    """SungrowSGInverter must read FC04 (input), not the Component default
    of FC03 (holding) - see the `register_space` comment in models.py.
    """
    inverter = SungrowSGInverter(mock_modbus_unit)
    await inverter.async_update()

    assert mock_modbus_unit.read_events
    assert all(
        event.register_type == "input" for event in mock_modbus_unit.read_events
    )


# --- SungrowSGControl (writable holding registers) ------------------------------


async def test_control_reads_target_the_holding_register_space(mock_modbus_unit):
    """SungrowSGControl must read FC03 (holding), not FC04 (input) - the
    opposite of SungrowSGInverter, and the whole reason it's a separate
    Component (register_space is a class attribute, can't mix per-field).
    """
    control = SungrowSGControl(mock_modbus_unit)
    await control.async_update()

    assert mock_modbus_unit.read_events
    assert all(
        event.register_type == "holding" for event in mock_modbus_unit.read_events
    )


async def test_control_reads_current_values(mock_modbus_unit):
    mock_modbus_unit.holding[reg.START_STOP.address] = 0xCF
    mock_modbus_unit.holding[reg.POWER_LIMITATION_SWITCH.address] = 0x55
    mock_modbus_unit.holding[reg.POWER_LIMITATION_SETTING.address] = 500  # 50.0%
    mock_modbus_unit.holding[reg.NIGHT_SVG_SWITCH.address] = 0x55
    mock_modbus_unit.holding[reg.POWER_LIMITATION_ADJUSTMENT.address] = 84  # 8.4 kW
    mock_modbus_unit.holding[reg.FEED_IN_POWER_LIMIT_SWITCH.address] = 0x55
    mock_modbus_unit.holding[reg.FEED_IN_POWER_LIMIT_VALUE.address] = 1200  # 12.00 kW
    mock_modbus_unit.holding[reg.FEED_IN_POWER_LIMIT_RATIO.address] = 1000  # 100.0%

    control = SungrowSGControl(mock_modbus_unit)
    await control.async_update()

    assert int(control.start_stop) == 0xCF
    assert int(control.power_limitation_switch) == 0x55
    assert control.power_limitation_setting == 50.0
    assert int(control.night_svg_switch) == 0x55
    assert control.power_limitation_adjustment == 8.4
    assert int(control.feed_in_power_limit_switch) == 0x55
    assert control.feed_in_power_limit_value == 12.0
    assert control.feed_in_power_limit_ratio == 100.0


@pytest.mark.parametrize(
    ("field", "value", "raw"),
    [
        ("start_stop", True, 0xCF),
        ("start_stop", False, 0xCE),
        ("power_limitation_switch", True, 0xAA),
        ("power_limitation_switch", False, 0x55),
        ("night_svg_switch", True, 0xAA),
        ("night_svg_switch", False, 0x55),
        ("feed_in_power_limit_switch", True, 0xAA),
        ("feed_in_power_limit_switch", False, 0x55),
    ],
)
async def test_control_writes_encode_the_right_enum_value(
    mock_modbus_unit, field, value, raw
):
    control = SungrowSGControl(mock_modbus_unit)
    events = []
    mock_modbus_unit.on_write(events.append)

    await control.write(field, value)

    assert len(events) == 1
    assert events[0].values == [raw]


@pytest.mark.parametrize(
    "field",
    [
        "start_stop",
        "power_limitation_switch",
        "night_svg_switch",
        "feed_in_power_limit_switch",
    ],
)
@pytest.mark.parametrize("bad_value", [0xCF, 0xAA, 1, 0, "start", "true", None])
async def test_control_rejects_anything_that_is_not_a_real_bool(
    mock_modbus_unit, field, bad_value
):
    """The strict isinstance(value, bool) check is the whole safety net:
    bool(0xCE) is True, so a raw register code passed by mistake must be
    rejected outright, not silently coerced into the wrong command.
    """
    control = SungrowSGControl(mock_modbus_unit)

    with pytest.raises(ValueError, match="must be a bool"):
        await control.write(field, bad_value)


async def test_control_power_limitation_setting_write_scales_correctly(
    mock_modbus_unit,
):
    control = SungrowSGControl(mock_modbus_unit)
    events = []
    mock_modbus_unit.on_write(events.append)

    await control.write("power_limitation_setting", 75.5)

    assert events[0].values == [755]


@pytest.mark.parametrize(
    ("field", "value", "raw"),
    [
        ("power_limitation_adjustment", 8.4, 84),
        ("feed_in_power_limit_value", 12.0, 1200),
        ("feed_in_power_limit_ratio", 75.5, 755),
    ],
)
async def test_control_absolute_and_feed_in_writes_scale_correctly(
    mock_modbus_unit, field, value, raw
):
    control = SungrowSGControl(mock_modbus_unit)
    events = []
    mock_modbus_unit.on_write(events.append)

    await control.write(field, value)

    assert events[0].values == [raw]
