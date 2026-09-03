"""Tests for SungrowSGCoordinator."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from freezegun import freeze_time
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import UpdateFailed
from modbus_connection import ModbusTimeoutError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sungrow_sg.const import (
    CONF_INCLUDE_METER,
    CONF_INCLUDE_MPPT,
    CONF_INCLUDE_STRINGS,
    CONF_UNIT_ID,
    DOMAIN,
)
from custom_components.sungrow_sg.coordinator import SungrowSGCoordinator
from custom_components.sungrow_sg.sungrow_modbus import registers as reg

from .conftest import EXPECTED_READINGS, FakeModbusConnectionFactory

# include_meter=True here (its own default is False) so this file's main
# test can assert against the full EXPECTED_READINGS, which includes
# meter data. test_restrict_fields_* below cover the toggles themselves.
ENTRY_DATA = {
    "host": "10.1.6.206",
    "port": 502,
    CONF_UNIT_ID: 1,
    CONF_INCLUDE_STRINGS: True,
    CONF_INCLUDE_MPPT: True,
    CONF_INCLUDE_METER: True,
}


async def test_update_data_returns_every_expected_field(
    hass: HomeAssistant, populated_mock_connection: FakeModbusConnectionFactory
) -> None:
    """Every key coordinator.py hardcodes decodes to the right value.

    This is the test that would have caught a typo'd dict key or a
    forgotten field in coordinator.py's `_async_update_data` - the
    return statement there hand-lists ~40 keys, exactly the kind of
    spot a copy-paste mistake hides in.
    """
    entry = MockConfigEntry(domain=DOMAIN, data=ENTRY_DATA)
    entry.add_to_hass(hass)
    coordinator = SungrowSGCoordinator(hass, entry)

    data = await coordinator._async_update_data()

    assert data == EXPECTED_READINGS


async def test_update_failure_marks_coordinator_unsuccessful(
    hass: HomeAssistant, mock_connection: FakeModbusConnectionFactory
) -> None:
    """A ModbusError that persists across all retry attempts becomes
    UpdateFailed, not a crash - only then does the coordinator (and so
    every entity) actually go unavailable.
    """
    mock_connection.for_unit(1).fail_requests(ModbusTimeoutError("simulated timeout"))
    entry = MockConfigEntry(domain=DOMAIN, data=ENTRY_DATA)
    entry.add_to_hass(hass)
    coordinator = SungrowSGCoordinator(hass, entry)

    with patch(
        "custom_components.sungrow_sg.coordinator.asyncio.sleep", new=AsyncMock()
    ) as mock_sleep:
        await coordinator.async_refresh()

    assert coordinator.last_update_success is False
    assert isinstance(coordinator.last_exception, UpdateFailed)
    # 3 attempts, 10s apart -> 2 sleeps, not 3 (no point waiting after the
    # last attempt).
    assert mock_sleep.call_count == 2
    assert mock_sleep.call_args_list[0].args == (10,)


async def test_update_recovers_after_a_transient_failure(
    hass: HomeAssistant, populated_mock_connection: FakeModbusConnectionFactory
) -> None:
    """A timeout on the first attempt that clears before the retry limit
    is reached must NOT mark the coordinator unsuccessful - this is the
    whole point of retrying before giving up.
    """
    unit = populated_mock_connection.for_unit(1)
    unit.fail_requests(ModbusTimeoutError("simulated timeout"))
    entry = MockConfigEntry(domain=DOMAIN, data=ENTRY_DATA)
    entry.add_to_hass(hass)
    coordinator = SungrowSGCoordinator(hass, entry)

    async def clear_failure_after_first_sleep(*_args: object) -> None:
        unit.fail_requests(None)

    with patch(
        "custom_components.sungrow_sg.coordinator.asyncio.sleep",
        new=AsyncMock(side_effect=clear_failure_after_first_sleep),
    ) as mock_sleep:
        await coordinator.async_refresh()

    assert coordinator.last_update_success is True
    assert mock_sleep.call_count == 1  # succeeded on the 2nd attempt


async def test_timeout_count_increments_per_failed_attempt(
    hass: HomeAssistant, populated_mock_connection: FakeModbusConnectionFactory
) -> None:
    """timeout_count_today counts every failed attempt within a poll, not
    just full-poll failures - a poll that fails twice then succeeds on
    its 3rd attempt should still count 2.
    """
    unit = populated_mock_connection.for_unit(1)
    unit.fail_requests(ModbusTimeoutError("simulated timeout"))
    entry = MockConfigEntry(domain=DOMAIN, data=ENTRY_DATA)
    entry.add_to_hass(hass)
    coordinator = SungrowSGCoordinator(hass, entry)

    sleeps = 0

    async def clear_failure_after_second_sleep(*_args: object) -> None:
        nonlocal sleeps
        sleeps += 1
        if sleeps >= 2:
            unit.fail_requests(None)

    with patch(
        "custom_components.sungrow_sg.coordinator.asyncio.sleep",
        new=AsyncMock(side_effect=clear_failure_after_second_sleep),
    ):
        await coordinator.async_refresh()

    assert coordinator.last_update_success is True
    assert coordinator.data["timeout_count_today"] == 2


async def test_timeout_count_resets_at_local_midnight(
    hass: HomeAssistant, populated_mock_connection: FakeModbusConnectionFactory
) -> None:
    """The counter is a per-day tally, not a running total since startup."""
    unit = populated_mock_connection.for_unit(1)
    entry = MockConfigEntry(domain=DOMAIN, data=ENTRY_DATA)
    entry.add_to_hass(hass)

    with freeze_time("2026-09-01 12:00:00"):
        coordinator = SungrowSGCoordinator(hass, entry)
        unit.fail_requests(ModbusTimeoutError("simulated timeout"))
        with patch(
            "custom_components.sungrow_sg.coordinator.asyncio.sleep", new=AsyncMock()
        ):
            await coordinator.async_refresh()
        assert coordinator.last_update_success is False  # all 3 attempts failed

        unit.fail_requests(None)
        await coordinator.async_refresh()
        assert coordinator.data["timeout_count_today"] == 3

    # +2 UTC days, not +1 - a naive "next day" UTC timestamp can still
    # land on the same local calendar day depending on the test
    # environment's timezone (dt_util.now() is local-zone-aware, by
    # design - see the reset check's comment above).
    with freeze_time("2026-09-03 12:00:00"):
        await coordinator.async_refresh()
        assert coordinator.data["timeout_count_today"] == 0


async def test_shutdown_closes_the_connection(
    hass: HomeAssistant, populated_mock_connection: FakeModbusConnectionFactory
) -> None:
    """async_shutdown closes the underlying ModbusConnection, not just the poller."""
    entry = MockConfigEntry(domain=DOMAIN, data=ENTRY_DATA)
    entry.add_to_hass(hass)
    coordinator = SungrowSGCoordinator(hass, entry)
    await coordinator.async_refresh()
    assert coordinator.last_update_success is True

    await coordinator.async_shutdown()

    assert populated_mock_connection.connected is False


async def test_fault_alarm_decodes_when_a_fault_is_recorded(
    hass: HomeAssistant, populated_mock_connection: FakeModbusConnectionFactory
) -> None:
    """The default fixture data has no fault recorded (fault_alarm_label is
    None) - this checks the actual decode path when one is, end to end
    through the coordinator (not just the library, see test_models.py).
    """
    unit = populated_mock_connection.for_unit(1)
    unit.input[reg.FAULT_ALARM_YEAR.address] = 2026
    unit.input[reg.FAULT_ALARM_MONTH.address] = 8
    unit.input[reg.FAULT_ALARM_DAY.address] = 30
    unit.input[reg.FAULT_ALARM_HOUR.address] = 14
    unit.input[reg.FAULT_ALARM_MINUTE.address] = 5
    unit.input[reg.FAULT_ALARM_SECOND.address] = 9
    unit.input[reg.FAULT_ALARM_CODE.address] = 8  # Grid Overfrequency

    entry = MockConfigEntry(domain=DOMAIN, data=ENTRY_DATA)
    entry.add_to_hass(hass)
    coordinator = SungrowSGCoordinator(hass, entry)

    data = await coordinator._async_update_data()

    assert data["fault_alarm_time"] == "2026-08-30 14:05:09"
    assert data["fault_alarm_label"] == "Grid Overfrequency"


async def test_meter_excluded_by_default(
    hass: HomeAssistant, populated_mock_connection: FakeModbusConnectionFactory
) -> None:
    """include_meter defaults to False - its fields aren't even read."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"host": "10.1.6.206", "port": 502, CONF_UNIT_ID: 1},
    )
    entry.add_to_hass(hass)
    coordinator = SungrowSGCoordinator(hass, entry)

    data = await coordinator._async_update_data()

    assert data["meter_power"] is None
    assert data["load_power"] is None
    assert data["total_export_energy"] is None
    # Groups left at their own defaults (strings/mppt on) still populate.
    assert data["string_1_current"] == EXPECTED_READINGS["string_1_current"]
    assert data["mppt_1_voltage"] == EXPECTED_READINGS["mppt_1_voltage"]


async def test_strings_and_mppt_excluded_still_reads_core_fields(
    hass: HomeAssistant, populated_mock_connection: FakeModbusConnectionFactory
) -> None:
    """Turning off strings/MPPT/meter leaves the always-on fields intact."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "host": "10.1.6.206",
            "port": 502,
            CONF_UNIT_ID: 1,
            CONF_INCLUDE_STRINGS: False,
            CONF_INCLUDE_MPPT: False,
            CONF_INCLUDE_METER: False,
        },
    )
    entry.add_to_hass(hass)
    coordinator = SungrowSGCoordinator(hass, entry)

    data = await coordinator._async_update_data()

    assert data["string_1_current"] is None
    assert data["string_1_power"] is None  # calculated field, None-guarded
    assert data["mppt_1_voltage"] is None
    assert data["mppt_1_power"] is None
    assert data["meter_power"] is None
    assert data["phase_a_voltage"] == EXPECTED_READINGS["phase_a_voltage"]
    assert data["total_active_power"] == EXPECTED_READINGS["total_active_power"]
    assert data["model_name"] == EXPECTED_READINGS["model_name"]


async def test_strings_without_mppt_still_reads_mppt_voltage_for_string_power(
    hass: HomeAssistant, populated_mock_connection: FakeModbusConnectionFactory
) -> None:
    """Strings need their MPPT's voltage to calculate power even when
    MPPT sensors themselves are excluded (restricted_field_names() in
    const.py reads mppt_1/2_voltage whenever strings are included).
    """
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "host": "10.1.6.206",
            "port": 502,
            CONF_UNIT_ID: 1,
            CONF_INCLUDE_STRINGS: True,
            CONF_INCLUDE_MPPT: False,
            CONF_INCLUDE_METER: False,
        },
    )
    entry.add_to_hass(hass)
    coordinator = SungrowSGCoordinator(hass, entry)

    data = await coordinator._async_update_data()

    assert data["mppt_1_current"] is None  # MPPT sensors themselves off
    assert data["string_1_current"] == EXPECTED_READINGS["string_1_current"]
    assert data["string_1_power"] == EXPECTED_READINGS["string_1_power"]


# --- Writable controls (holding registers) --------------------------------------


async def _setup_coordinator(hass: HomeAssistant) -> SungrowSGCoordinator:
    entry = MockConfigEntry(domain=DOMAIN, data=ENTRY_DATA)
    entry.add_to_hass(hass)
    coordinator = SungrowSGCoordinator(hass, entry)
    await coordinator.async_refresh()
    return coordinator


async def test_async_set_start_stop_writes_the_right_raw_value(
    hass: HomeAssistant, populated_mock_connection: FakeModbusConnectionFactory
) -> None:
    coordinator = await _setup_coordinator(hass)
    events = []
    populated_mock_connection.for_unit(1).on_write(events.append)

    await coordinator.async_set_start_stop(running=False)

    assert events[-1].values == [0xCE]
    assert coordinator.data["start_stop_is_running"] is False


async def test_async_set_power_limitation_enabled_writes_the_right_raw_value(
    hass: HomeAssistant, populated_mock_connection: FakeModbusConnectionFactory
) -> None:
    coordinator = await _setup_coordinator(hass)
    events = []
    populated_mock_connection.for_unit(1).on_write(events.append)

    await coordinator.async_set_power_limitation_enabled(enabled=True)

    assert events[-1].values == [0xAA]
    assert coordinator.data["power_limitation_enabled"] is True


async def test_async_set_power_limitation_setting_scales_correctly(
    hass: HomeAssistant, populated_mock_connection: FakeModbusConnectionFactory
) -> None:
    coordinator = await _setup_coordinator(hass)
    events = []
    populated_mock_connection.for_unit(1).on_write(events.append)

    await coordinator.async_set_power_limitation_setting(75.5)

    assert events[-1].values == [755]
    assert coordinator.data["power_limitation_setting"] == 75.5


async def test_async_set_night_svg_enabled_writes_the_right_raw_value(
    hass: HomeAssistant, populated_mock_connection: FakeModbusConnectionFactory
) -> None:
    coordinator = await _setup_coordinator(hass)
    events = []
    populated_mock_connection.for_unit(1).on_write(events.append)

    await coordinator.async_set_night_svg_enabled(enabled=True)

    assert events[-1].values == [0xAA]
    assert coordinator.data["night_svg_enabled"] is True


async def test_async_set_power_limitation_adjustment_scales_correctly(
    hass: HomeAssistant, populated_mock_connection: FakeModbusConnectionFactory
) -> None:
    coordinator = await _setup_coordinator(hass)
    events = []
    populated_mock_connection.for_unit(1).on_write(events.append)

    await coordinator.async_set_power_limitation_adjustment(8.4)

    assert events[-1].values == [84]
    assert coordinator.data["power_limitation_adjustment"] == 8.4


async def test_async_set_feed_in_power_limit_enabled_writes_the_right_raw_value(
    hass: HomeAssistant, populated_mock_connection: FakeModbusConnectionFactory
) -> None:
    coordinator = await _setup_coordinator(hass)
    events = []
    populated_mock_connection.for_unit(1).on_write(events.append)

    await coordinator.async_set_feed_in_power_limit_enabled(enabled=True)

    assert events[-1].values == [0xAA]
    assert coordinator.data["feed_in_power_limit_enabled"] is True


async def test_async_set_feed_in_power_limit_value_scales_correctly(
    hass: HomeAssistant, populated_mock_connection: FakeModbusConnectionFactory
) -> None:
    coordinator = await _setup_coordinator(hass)
    events = []
    populated_mock_connection.for_unit(1).on_write(events.append)

    await coordinator.async_set_feed_in_power_limit_value(12.0)

    assert events[-1].values == [1200]
    assert coordinator.data["feed_in_power_limit_value"] == 12.0


async def test_async_set_feed_in_power_limit_ratio_scales_correctly(
    hass: HomeAssistant, populated_mock_connection: FakeModbusConnectionFactory
) -> None:
    coordinator = await _setup_coordinator(hass)
    events = []
    populated_mock_connection.for_unit(1).on_write(events.append)

    await coordinator.async_set_feed_in_power_limit_ratio(75.5)

    assert events[-1].values == [755]
    assert coordinator.data["feed_in_power_limit_ratio"] == 75.5


async def test_write_failure_raises_home_assistant_error(
    hass: HomeAssistant, populated_mock_connection: FakeModbusConnectionFactory
) -> None:
    """A failed write must surface as HomeAssistantError (so the frontend
    shows a real error), not an unhandled ModbusError.
    """
    coordinator = await _setup_coordinator(hass)
    populated_mock_connection.for_unit(1).fail_write(
        reg.START_STOP.address, ModbusTimeoutError("simulated timeout")
    )

    with pytest.raises(HomeAssistantError):
        await coordinator.async_set_start_stop(running=False)
