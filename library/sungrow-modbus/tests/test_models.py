"""Tests for SungrowSGInverter.

Run against modbus_connection's own in-memory mock (`MockModbusUnit`, via
its `mock_modbus_unit` pytest fixture) - not against a real inverter. This
catches register-plumbing bugs (wrong register space, wrong address,
wrong scale/decode) that a `models.py` typo would otherwise only surface
against real hardware. It is not a substitute for that real-hardware test
- see docs/register_map.md for the plan there.
"""

from sungrow_modbus import SungrowSGInverter
from sungrow_modbus import registers as reg


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
    mock_modbus_unit.input[reg.GRID_FREQUENCY.address] = 499
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
    assert inverter.phase_a_current == 4.8
    assert inverter.total_dc_power == 3554
    assert inverter.total_reactive_power == 5
    assert inverter.grid_frequency == 49.9
    assert inverter.work_state_1 == 0
    assert inverter.work_state_1_label == "run"
    assert inverter.work_state_2 == 0x20001
    assert inverter.array_insulation_resistance is None


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
