"""Device model for Sungrow SG-series inverters, built on modbus_connection.

Requires Python >=3.12 and the `modbus-connection` package (see
pyproject.toml). This module intentionally has zero Home Assistant imports —
it should be usable from a plain script (see scripts/query.py) or from the
HA integration in custom_components/sungrow_sg.

API SURFACE: confirmed against modbus-connection 4.10.0 actually installed
(`pip install "modbus-connection[tmodbus]"`, Python 3.13) - Component base
class, gauge()/uint32()/coil() field helpers, ModbusConnection.for_unit(),
and the `register_space` class attribute are all real and match this file.
Exercised end-to-end against the package's own in-memory mock in
tests/test_models.py.
"""

from __future__ import annotations

from modbus_connection.model import Component, gauge, int32, string, uint32

from . import registers as reg
from .const import DEVICE_TYPE_CODES, OUTPUT_TYPE_LABELS, WORK_STATE_1_LABELS


class SungrowSGInverter(Component):
    """Sungrow SG5.0RT-SG12RT family string inverter.

    One `Component` instance = one physical inverter reachable at a given
    Modbus unit id. Field addresses come from `registers.py`; do not hardcode
    raw addresses here so the register catalog stays the single place to fix
    if a field turns out wrong on real hardware.
    """

    # All fields below live in Sungrow's "input register" (3x / FC04) space
    # per the official protocol doc - Component defaults to "holding" (4x /
    # FC03), so this MUST be set or every read below silently targets the
    # wrong register file on a real inverter. The writable control registers
    # in registers.py (START_STOP etc.) are holding registers and are not
    # modeled here yet for that reason - they'd need a separate Component.
    register_space = "input"

    # Confirmed live against a real SG12RT (2026-08-30): its 32-bit fields
    # put the LOW word at the first (lower) address and the HIGH word at
    # the second - opposite of uint32()'s "big" default, which decoded
    # total_active_power as ~99 MW and total_power_yield as ~360 GWh on a
    # 12kW inverter. Every uint32() field below passes word_order="little"
    # for that reason.

    device_type_code = gauge(reg.DEVICE_TYPE_CODE.address, scale=1)
    serial_number = string(reg.SERIAL_NUMBER.address, reg.SERIAL_NUMBER.count)
    # "Reserved" in the official SG-string PDF - see registers.py
    # PROTOCOL_VERSION docstring for where this address actually comes
    # from. Packed as Major.Minor.Patch.Build bytes; decode via the
    # protocol_version property below, not this raw field directly.
    protocol_version_raw = uint32(reg.PROTOCOL_VERSION.address, word_order="little")

    nominal_active_power = gauge(
        reg.NOMINAL_ACTIVE_POWER.address,
        scale=reg.NOMINAL_ACTIVE_POWER.scale,
        unit=reg.NOMINAL_ACTIVE_POWER.unit,
    )
    # Raw enum: 0=two-phase, 1=3P4L, 2=3P3L (see registers.py OUTPUT_TYPE).
    output_type = gauge(reg.OUTPUT_TYPE.address, scale=1)

    daily_power_yield = gauge(
        reg.DAILY_POWER_YIELD.address,
        scale=reg.DAILY_POWER_YIELD.scale,
        unit=reg.DAILY_POWER_YIELD.unit,
    )
    total_power_yield = uint32(
        reg.TOTAL_POWER_YIELD.address,
        scale=reg.TOTAL_POWER_YIELD.scale,
        unit=reg.TOTAL_POWER_YIELD.unit,
        word_order="little",
    )
    total_running_time = uint32(
        reg.TOTAL_RUNNING_TIME.address,
        unit=reg.TOTAL_RUNNING_TIME.unit,
        word_order="little",
    )

    internal_temperature = gauge(
        reg.INTERNAL_TEMPERATURE.address,
        scale=reg.INTERNAL_TEMPERATURE.scale,
        unit=reg.INTERNAL_TEMPERATURE.unit,
    )
    total_apparent_power = uint32(
        reg.TOTAL_APPARENT_POWER.address,
        unit=reg.TOTAL_APPARENT_POWER.unit,
        word_order="little",
    )

    mppt_1_voltage = gauge(
        reg.MPPT_1_VOLTAGE.address, scale=reg.MPPT_1_VOLTAGE.scale, unit=reg.MPPT_1_VOLTAGE.unit
    )
    mppt_1_current = gauge(
        reg.MPPT_1_CURRENT.address, scale=reg.MPPT_1_CURRENT.scale, unit=reg.MPPT_1_CURRENT.unit
    )
    mppt_2_voltage = gauge(
        reg.MPPT_2_VOLTAGE.address, scale=reg.MPPT_2_VOLTAGE.scale, unit=reg.MPPT_2_VOLTAGE.unit
    )
    mppt_2_current = gauge(
        reg.MPPT_2_CURRENT.address, scale=reg.MPPT_2_CURRENT.scale, unit=reg.MPPT_2_CURRENT.unit
    )
    # Doc states U32 (unsigned); a community source notes it has observed
    # this returning a signed value in practice on some models. Not yet
    # hardware-tested here for a negative reading (e.g. at night) - if a
    # bogus huge positive value shows up instead of a small negative one,
    # switch this to int32().
    total_dc_power = uint32(
        reg.TOTAL_DC_POWER.address,
        unit=reg.TOTAL_DC_POWER.unit,
        word_order="little",
    )

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
    # Doc states U16 (unsigned); a community source notes these actually
    # decode as signed on real hardware. gauge()'s default signed=True
    # already matches that, so no extra kwarg needed here.
    phase_a_current = gauge(
        reg.PHASE_A_CURRENT.address, scale=reg.PHASE_A_CURRENT.scale, unit=reg.PHASE_A_CURRENT.unit
    )
    phase_b_current = gauge(
        reg.PHASE_B_CURRENT.address, scale=reg.PHASE_B_CURRENT.scale, unit=reg.PHASE_B_CURRENT.unit
    )
    phase_c_current = gauge(
        reg.PHASE_C_CURRENT.address, scale=reg.PHASE_C_CURRENT.scale, unit=reg.PHASE_C_CURRENT.unit
    )

    total_active_power = uint32(
        reg.TOTAL_ACTIVE_POWER.address,
        scale=reg.TOTAL_ACTIVE_POWER.scale,
        unit=reg.TOTAL_ACTIVE_POWER.unit,
        word_order="little",
    )
    total_reactive_power = int32(
        reg.TOTAL_REACTIVE_POWER.address,
        unit=reg.TOTAL_REACTIVE_POWER.unit,
        word_order="little",
    )
    power_factor = gauge(reg.POWER_FACTOR.address, scale=reg.POWER_FACTOR.scale)
    grid_frequency = gauge(
        reg.GRID_FREQUENCY.address, scale=reg.GRID_FREQUENCY.scale, unit=reg.GRID_FREQUENCY.unit
    )

    # Raw status codes - see Sungrow's Appendix 1 (work_state_1) and
    # Appendix 2 (work_state_2, a bitmask: e.g. live-confirmed bit 0 =
    # "running" + bit 17 = "grid connected" both set during normal
    # operation). No lookup table wired in here yet - HA-side code can
    # decode these against the appendix when building sensors.
    work_state_1 = gauge(reg.WORK_STATE_1.address, scale=1)
    work_state_2 = uint32(reg.WORK_STATE_2.address, word_order="little")

    nominal_reactive_power = gauge(
        reg.NOMINAL_REACTIVE_POWER.address,
        scale=reg.NOMINAL_REACTIVE_POWER.scale,
        unit=reg.NOMINAL_REACTIVE_POWER.unit,
    )
    # Doc: "1-20000(0xFFFF: invalid)" - nan=0xFFFF makes an invalid
    # reading decode to None instead of a nonsense 6553.5 kOhm.
    array_insulation_resistance = gauge(
        reg.ARRAY_INSULATION_RESISTANCE.address,
        scale=reg.ARRAY_INSULATION_RESISTANCE.scale,
        unit=reg.ARRAY_INSULATION_RESISTANCE.unit,
        nan=0xFFFF,
    )

    # Per-string current ("combiner board information"). SG12RT has 3
    # physical string inputs (2 on MPPT 1, 1 on MPPT 2 - see registers.py).
    # A model with fewer/more strings would need a different subset here;
    # this class is deliberately SG12RT-specific, not generic SG-series.
    string_1_current = gauge(
        reg.STRING_1_CURRENT.address, scale=reg.STRING_1_CURRENT.scale, unit=reg.STRING_1_CURRENT.unit
    )
    string_2_current = gauge(
        reg.STRING_2_CURRENT.address, scale=reg.STRING_2_CURRENT.scale, unit=reg.STRING_2_CURRENT.unit
    )
    string_3_current = gauge(
        reg.STRING_3_CURRENT.address, scale=reg.STRING_3_CURRENT.scale, unit=reg.STRING_3_CURRENT.unit
    )

    # Grid meter (external CT/smart meter). Doc's own model list excludes
    # SG12RT, but live-confirmed working on this unit - see registers.py.
    # A unit without a meter/CT accessory attached may read zeros here.
    meter_power = int32(
        reg.METER_POWER.address, unit=reg.METER_POWER.unit, word_order="little"
    )
    meter_a_phase_power = int32(
        reg.METER_A_PHASE_POWER.address, unit=reg.METER_A_PHASE_POWER.unit, word_order="little"
    )
    meter_b_phase_power = int32(
        reg.METER_B_PHASE_POWER.address, unit=reg.METER_B_PHASE_POWER.unit, word_order="little"
    )
    meter_c_phase_power = int32(
        reg.METER_C_PHASE_POWER.address, unit=reg.METER_C_PHASE_POWER.unit, word_order="little"
    )
    load_power = int32(
        reg.LOAD_POWER.address, unit=reg.LOAD_POWER.unit, word_order="little"
    )
    daily_export_energy = uint32(
        reg.DAILY_EXPORT_ENERGY.address,
        scale=reg.DAILY_EXPORT_ENERGY.scale,
        unit=reg.DAILY_EXPORT_ENERGY.unit,
        word_order="little",
    )
    total_export_energy = uint32(
        reg.TOTAL_EXPORT_ENERGY.address,
        scale=reg.TOTAL_EXPORT_ENERGY.scale,
        unit=reg.TOTAL_EXPORT_ENERGY.unit,
        word_order="little",
    )
    daily_import_energy = uint32(
        reg.DAILY_IMPORT_ENERGY.address,
        scale=reg.DAILY_IMPORT_ENERGY.scale,
        unit=reg.DAILY_IMPORT_ENERGY.unit,
        word_order="little",
    )
    total_import_energy = uint32(
        reg.TOTAL_IMPORT_ENERGY.address,
        scale=reg.TOTAL_IMPORT_ENERGY.scale,
        unit=reg.TOTAL_IMPORT_ENERGY.unit,
        word_order="little",
    )
    daily_direct_energy_consumption = uint32(
        reg.DAILY_DIRECT_ENERGY_CONSUMPTION.address,
        scale=reg.DAILY_DIRECT_ENERGY_CONSUMPTION.scale,
        unit=reg.DAILY_DIRECT_ENERGY_CONSUMPTION.unit,
        word_order="little",
    )
    total_direct_energy_consumption = uint32(
        reg.TOTAL_DIRECT_ENERGY_CONSUMPTION.address,
        scale=reg.TOTAL_DIRECT_ENERGY_CONSUMPTION.scale,
        unit=reg.TOTAL_DIRECT_ENERGY_CONSUMPTION.unit,
        word_order="little",
    )

    negative_voltage_to_ground = gauge(
        reg.NEGATIVE_VOLTAGE_TO_GROUND.address,
        scale=reg.NEGATIVE_VOLTAGE_TO_GROUND.scale,
        unit=reg.NEGATIVE_VOLTAGE_TO_GROUND.unit,
    )
    bus_voltage = gauge(
        reg.BUS_VOLTAGE.address,
        scale=reg.BUS_VOLTAGE.scale,
        unit=reg.BUS_VOLTAGE.unit,
    )

    # Not wired as writable yet on purpose - see registers.py TODO on the
    # "Control (writable, holding registers)" section. Left commented until
    # confirmed safe on real hw. NIGHT_SVG_SWITCH is also a holding
    # register (like START_STOP/POWER_LIMITATION_*) so it can't join this
    # input-space Component anyway without a second Component - see the
    # register_space comment above.
    # power_limitation_setting = gauge(
    #     reg.POWER_LIMITATION_SETTING.address,
    #     scale=reg.POWER_LIMITATION_SETTING.scale,
    #     unit=reg.POWER_LIMITATION_SETTING.unit,
    #     writable=True,
    # )

    @property
    def model_name(self) -> str:
        """Best-effort model name from the device type code register.

        Returns "unknown" rather than guessing when the code isn't in
        DEVICE_TYPE_CODES - see const.py TODO.
        """
        return DEVICE_TYPE_CODES.get(int(self.device_type_code), "unknown")

    @property
    def protocol_version(self) -> str:
        """Format protocol_version_raw as "Major.Minor.Patch.Build".

        E.g. 0x01011900 -> "1.1.25.0". See registers.py PROTOCOL_VERSION
        docstring for the source of this format and its address.
        """
        raw = int(self.protocol_version_raw)
        major = (raw >> 24) & 0xFF
        minor = (raw >> 16) & 0xFF
        patch = (raw >> 8) & 0xFF
        build = raw & 0xFF
        return f"{major}.{minor}.{patch}.{build}"

    @property
    def work_state_1_label(self) -> str:
        """Human-readable work_state_1 (Appendix 1) - "unknown" if unrecognized."""
        return WORK_STATE_1_LABELS.get(int(self.work_state_1), "unknown")

    @property
    def output_type_label(self) -> str:
        """Human-readable output_type - "unknown" if unrecognized."""
        return OUTPUT_TYPE_LABELS.get(int(self.output_type), "unknown")
