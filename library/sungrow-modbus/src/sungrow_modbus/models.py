"""Device model for Sungrow SG-series inverters, built on modbus_connection.

Requires Python >=3.12 and the `modbus-connection` package (see
pyproject.toml). This module intentionally has zero Home Assistant imports —
it should be usable from a plain script (see scripts/query.py) or from the
HA integration in custom_components/sungrow_sg.

FIELDS: addresses/types/scales come from `registers.py`, which is verified
against Sungrow's official "Communication Protocol of Residential &
Commercial PV Grid-Connected Inverters" (V1.1.80, 2026-03-27) - see that
module's docstring for the full source chain. Do not hand-edit an
address/type here without updating `registers.py` first.

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
from .const import (
    DEVICE_TYPE_CODES,
    FAULT_CODE_LABELS,
    OUTPUT_TYPE_LABELS,
    WORK_STATE_1_LABELS,
    WORK_STATE_2_FAULT_BIT,
    WORK_STATE_2_GRID_CONNECTED_BIT,
)


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
    # Packed as Major.Minor.Patch.Build bytes; decode via the
    # protocol_version property below, not this raw field directly.
    protocol_version_raw = uint32(reg.PROTOCOL_VERSION.address, word_order="little")
    # Undocumented beyond the register table itself - see registers.py
    # PROTOCOL_NO docstring.
    protocol_no = uint32(reg.PROTOCOL_NO.address, word_order="little")
    arm_software_version = string(
        reg.ARM_SOFTWARE_VERSION.address, reg.ARM_SOFTWARE_VERSION.count
    )
    dsp_software_version = string(
        reg.DSP_SOFTWARE_VERSION.address, reg.DSP_SOFTWARE_VERSION.count
    )

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

    # Doc (V1.1.80) lists this as S32, not U32 - a production inverter can
    # legitimately export negative "active power" briefly (e.g. absorbing
    # from the grid during certain fault/standby transitions), so this must
    # be signed like total_reactive_power below or it would wrap to a huge
    # positive value instead.
    total_active_power = int32(
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

    # Fault/alarm timestamp + code (doc 5039-5045) - "valid only when the
    # device work state is fault (0x5500) or alarm (0x9100)" per the doc,
    # so these are stale/meaningless whenever work_state_1 isn't one of
    # those two. Decode via fault_alarm_time/fault_alarm_label below, not
    # these raw fields directly.
    fault_alarm_year = gauge(reg.FAULT_ALARM_YEAR.address, scale=1)
    fault_alarm_month = gauge(reg.FAULT_ALARM_MONTH.address, scale=1)
    fault_alarm_day = gauge(reg.FAULT_ALARM_DAY.address, scale=1)
    fault_alarm_hour = gauge(reg.FAULT_ALARM_HOUR.address, scale=1)
    fault_alarm_minute = gauge(reg.FAULT_ALARM_MINUTE.address, scale=1)
    fault_alarm_second = gauge(reg.FAULT_ALARM_SECOND.address, scale=1)
    fault_alarm_code = gauge(reg.FAULT_ALARM_CODE.address, scale=1)

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
    daily_running_time = gauge(
        reg.DAILY_RUNNING_TIME.address, scale=1, unit=reg.DAILY_RUNNING_TIME.unit
    )
    monthly_power_yield = uint32(
        reg.MONTHLY_POWER_YIELD.address,
        scale=reg.MONTHLY_POWER_YIELD.scale,
        unit=reg.MONTHLY_POWER_YIELD.unit,
        word_order="little",
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
        """Human-readable work_state_1 (Appendix 2) - "unknown" if unrecognized."""
        return WORK_STATE_1_LABELS.get(int(self.work_state_1), "unknown")

    @property
    def is_grid_connected(self) -> bool | None:
        """work_state_2 (Appendix 3) bit 17 - "Device is grid-connected
        running". None before the first read.
        """
        state = self.work_state_2
        if state is None:
            return None
        return bool(int(state) & (1 << WORK_STATE_2_GRID_CONNECTED_BIT))

    @property
    def is_in_fault(self) -> bool | None:
        """work_state_2 (Appendix 3) bit 18 - "Device is in fault stop
        state". None before the first read.
        """
        state = self.work_state_2
        if state is None:
            return None
        return bool(int(state) & (1 << WORK_STATE_2_FAULT_BIT))

    @property
    def output_type_label(self) -> str:
        """Human-readable output_type - "unknown" if unrecognized."""
        return OUTPUT_TYPE_LABELS.get(int(self.output_type), "unknown")

    @property
    def fault_alarm_label(self) -> str | None:
        """Human-readable fault_alarm_code (Appendix 4) - None when no
        fault/alarm is recorded (code 0), "unknown" if the code isn't in
        FAULT_CODE_LABELS. Per the doc this register is only meaningful
        while work_state_1 reads fault (0x5500) or alarm (0x9100) - a
        nonzero code left over from a past event may still be readable
        outside those states, so check work_state_1_label too if you need
        "is this fault currently active" rather than "most recent fault".
        """
        code = self.fault_alarm_code
        if code is None or int(code) == 0:
            return None
        return FAULT_CODE_LABELS.get(int(code), "unknown")

    @property
    def fault_alarm_time(self) -> str | None:
        """fault_alarm_year/month/.../second combined as "YYYY-MM-DD
        HH:MM:SS" - None if the year field hasn't been read yet or reads
        0 (no fault/alarm recorded). Same "only valid during fault/alarm
        work state" caveat as fault_alarm_label.
        """
        year = self.fault_alarm_year
        if year is None or int(year) == 0:
            return None
        return (
            f"{int(year):04d}-{int(self.fault_alarm_month):02d}-"
            f"{int(self.fault_alarm_day):02d} {int(self.fault_alarm_hour):02d}:"
            f"{int(self.fault_alarm_minute):02d}:{int(self.fault_alarm_second):02d}"
        )

    # --- Calculated power (no direct register - V * I) ---------------------------
    # None whenever either input is None: before the first async_update(),
    # or when restrict_fields() has excluded the underlying voltage/current
    # (see coordinator.py) - never raise TypeError on None * None.
    @property
    def mppt_1_power(self) -> float | None:
        """mppt_1_voltage * mppt_1_current, in W."""
        if self.mppt_1_voltage is None or self.mppt_1_current is None:
            return None
        return round(self.mppt_1_voltage * self.mppt_1_current, 1)

    @property
    def mppt_2_power(self) -> float | None:
        """mppt_2_voltage * mppt_2_current, in W."""
        if self.mppt_2_voltage is None or self.mppt_2_current is None:
            return None
        return round(self.mppt_2_voltage * self.mppt_2_current, 1)

    # Strings don't have their own voltage register - strings on the same
    # MPPT are wired in parallel and share that MPPT's voltage (see
    # registers.py STRING_1/2/3_CURRENT docstring). SG12RT: strings 1-2 are
    # on MPPT 1, string 3 is on MPPT 2 (Appendix 6 "String/MPPT" = "2;1").
    @property
    def string_1_power(self) -> float | None:
        """mppt_1_voltage * string_1_current, in W (string 1 is on MPPT 1)."""
        if self.mppt_1_voltage is None or self.string_1_current is None:
            return None
        return round(self.mppt_1_voltage * self.string_1_current, 1)

    @property
    def string_2_power(self) -> float | None:
        """mppt_1_voltage * string_2_current, in W (string 2 is on MPPT 1)."""
        if self.mppt_1_voltage is None or self.string_2_current is None:
            return None
        return round(self.mppt_1_voltage * self.string_2_current, 1)

    @property
    def string_3_power(self) -> float | None:
        """mppt_2_voltage * string_3_current, in W (string 3 is on MPPT 2)."""
        if self.mppt_2_voltage is None or self.string_3_current is None:
            return None
        return round(self.mppt_2_voltage * self.string_3_current, 1)

    @property
    def capacity_utilization(self) -> float | None:
        """total_active_power as a percentage of nominal_active_power -
        "how much of this inverter's rated capacity is being used right
        now". nominal_active_power is read from the inverter itself
        (kW), not hardcoded, so this works for any SG-series model, not
        just SG12RT.

        Clamped to [0, 100]: total_active_power is signed (can briefly
        read slightly negative during fault/standby transitions - see
        registers.py TOTAL_ACTIVE_POWER) and a >100% overload reading is
        possible on models that support overload running, but a
        "utilization" percentage isn't meant to display either.
        """
        power = self.total_active_power
        nominal = self.nominal_active_power
        if power is None or nominal is None or nominal == 0:
            return None
        percent = (power / (nominal * 1000)) * 100
        return round(min(max(percent, 0.0), 100.0), 1)


def _validate_start_stop(value: object) -> int:
    """True starts the inverter (0xCF), False stops it (0xCE).

    Strict `isinstance(value, bool)` on purpose: `bool(0xCE)` is `True`
    (206 is truthy), so accepting any truthy/falsy value here would let a
    caller who passes the raw "stop" code by mistake silently get
    "start" instead - the exact kind of inversion that must never happen
    on a grid-tied inverter's start/stop control.
    """
    if not isinstance(value, bool):
        # ValueError, not TypeError: matches modbus_connection's own
        # convention for "this value is invalid for this field" (see
        # write_register_field's docstring on scaling failures).
        raise ValueError(  # noqa: TRY004
            f"start_stop must be a bool (True=start, False=stop), got {value!r}"
        )
    return 0xCF if value else 0xCE


def _validate_enable_disable(value: object) -> int:
    """0xAA = enable, 0x55 = disable - shared shape for
    POWER_LIMITATION_SWITCH and NIGHT_SVG_SWITCH. Same strict-bool
    reasoning as `_validate_start_stop`.
    """
    if not isinstance(value, bool):
        raise ValueError(  # noqa: TRY004 - see _validate_start_stop
            f"must be a bool (True=enable, False=disable), got {value!r}"
        )
    return 0xAA if value else 0x55


class SungrowSGControl(Component):
    """Writable Sungrow SG-series holding registers: start/stop, power
    limitation (switch + %, or switch + absolute kW), feed-in power limit
    (switch + %, or switch + absolute kW - a separate control point at the
    grid connection, see registers.py FEED_IN_POWER_LIMIT_* docstring),
    Night SVG.

    A separate `Component` from `SungrowSGInverter` on purpose:
    `register_space` is a class attribute, and these registers live in
    the holding space (FC03/06/16) while every `SungrowSGInverter` field
    is input (FC04) - see that class's `register_space` docstring. Build
    both `Component`s around `ModbusConnection.for_unit(...)`'s SAME
    `ModbusUnit` (calling `for_unit()` again for the same unit id returns
    the cached instance) so they share one connection.

    STATUS: address/scale/enum values are read directly from the
    official protocol doc (see registers.py START_STOP/
    POWER_LIMITATION_*/NIGHT_SVG_SWITCH docstrings) and cross-checked
    live by *reading* each register against a real SG12RT - but no write
    has been sent to real hardware yet. A wrong value here can disconnect
    the inverter from the grid or stop production; the strict bool
    validators above are a safety net, not a substitute for testing
    cautiously against real hardware before relying on this.
    """

    register_space = "holding"

    start_stop = gauge(reg.START_STOP.address, scale=1, writable=_validate_start_stop)
    power_limitation_switch = gauge(
        reg.POWER_LIMITATION_SWITCH.address, scale=1, writable=_validate_enable_disable
    )
    # No documented min/max found for this one (the doc's note "See
    # Appendix 6" implies a model-specific range, unconfirmed for
    # SG12RT) - relies on the inverter's own firmware to reject an
    # out-of-range write rather than a guessed client-side limit that
    # might be wrong in either direction.
    power_limitation_setting = gauge(
        reg.POWER_LIMITATION_SETTING.address,
        scale=reg.POWER_LIMITATION_SETTING.scale,
        unit=reg.POWER_LIMITATION_SETTING.unit,
        writable=True,
    )
    night_svg_switch = gauge(
        reg.NIGHT_SVG_SWITCH.address, scale=1, writable=_validate_enable_disable
    )
    # Alternative to power_limitation_setting's percentage - doc chapter
    # 3.1.3 "Setting Power Limitation Value". Still requires
    # power_limitation_switch=True first (same precondition as the
    # percentage method, chapter 3.1.2) - this field doesn't enforce that
    # itself, same as power_limitation_setting above.
    power_limitation_adjustment = gauge(
        reg.POWER_LIMITATION_ADJUSTMENT.address,
        scale=reg.POWER_LIMITATION_ADJUSTMENT.scale,
        unit=reg.POWER_LIMITATION_ADJUSTMENT.unit,
        writable=True,
    )
    feed_in_power_limit_switch = gauge(
        reg.FEED_IN_POWER_LIMIT_SWITCH.address,
        scale=1,
        writable=_validate_enable_disable,
    )
    feed_in_power_limit_value = gauge(
        reg.FEED_IN_POWER_LIMIT_VALUE.address,
        scale=reg.FEED_IN_POWER_LIMIT_VALUE.scale,
        unit=reg.FEED_IN_POWER_LIMIT_VALUE.unit,
        writable=True,
    )
    feed_in_power_limit_ratio = gauge(
        reg.FEED_IN_POWER_LIMIT_RATIO.address,
        scale=reg.FEED_IN_POWER_LIMIT_RATIO.scale,
        unit=reg.FEED_IN_POWER_LIMIT_RATIO.unit,
        writable=True,
    )
