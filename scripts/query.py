#!/usr/bin/env python3
"""Fristående CLI för att läsa av en Sungrow SG-inverter över Modbus TCP.

Kräver Python >=3.12 och `modbus-connection` + `sungrow-modbus` installerade
(`pip install -e library/sungrow-modbus[dev]` i en 3.12+-venv). Används för
att verifiera register mot en riktig inverter innan de låses fast i
`registers.py` (se docs/register_map.md).

Read-only - läser bara input-registren SungrowSGInverter exponerar just nu.
Rör inte de skrivbara holding-registren (start/stopp,
effektbegränsning) mot en riktig inverter utan att veta vad de gör.
"""

from __future__ import annotations

import argparse
import asyncio

from modbus_connection import ModbusTcpParams
from modbus_connection.tmodbus import ModbusConnection

from sungrow_modbus import SungrowSGInverter


async def main(host: str, port: int, unit_id: int) -> None:
    conn = ModbusConnection(ModbusTcpParams(host=host, port=port))
    inverter = SungrowSGInverter(conn.for_unit(unit_id))
    await inverter.async_update()
    print(f"serial_number:     {inverter.serial_number!r}")
    print(f"device_type_code:  {hex(int(inverter.device_type_code))}")
    print(f"model_name:        {inverter.model_name}")
    print(f"protocol_version:  {inverter.protocol_version}")
    print(f"bus_voltage:       {inverter.bus_voltage}")
    print(f"negative_voltage_to_ground:{inverter.negative_voltage_to_ground}")
    print(f"nominal_active_power:{inverter.nominal_active_power}")
    print(f"output_type:       {inverter.output_type}")
    print(f"total_running_time:{inverter.total_running_time}")
    print(f"internal_temperature:{inverter.internal_temperature}")
    print(f"total_apparent_power:{inverter.total_apparent_power}")
    print(f"mppt_1_voltage:    {inverter.mppt_1_voltage}")
    print(f"mppt_1_current:    {inverter.mppt_1_current}")
    print(f"mppt_2_voltage:    {inverter.mppt_2_voltage}")
    print(f"mppt_2_current:    {inverter.mppt_2_current}")
    print(f"total_dc_power:    {inverter.total_dc_power}")
    print(f"phase_a_voltage:   {inverter.phase_a_voltage}")
    print(f"phase_b_voltage:   {inverter.phase_b_voltage}")
    print(f"phase_c_voltage:   {inverter.phase_c_voltage}")
    print(f"phase_a_current:   {inverter.phase_a_current}")
    print(f"phase_b_current:   {inverter.phase_b_current}")
    print(f"phase_c_current:   {inverter.phase_c_current}")
    print(f"total_active_power:{inverter.total_active_power}")
    print(f"total_reactive_power:{inverter.total_reactive_power}")
    print(f"power_factor:      {inverter.power_factor}")
    print(f"grid_frequency:    {inverter.grid_frequency}")
    print(f"work_state_1:      {inverter.work_state_1}")
    print(f"work_state_2:      {inverter.work_state_2}")
    print(f"nominal_reactive_power:{inverter.nominal_reactive_power}")
    print(f"array_insulation_resistance:{inverter.array_insulation_resistance}")
    print(f"daily_power_yield: {inverter.daily_power_yield}")
    print(f"total_power_yield: {inverter.total_power_yield}")
    print(f"string_1_current:  {inverter.string_1_current}")
    print(f"string_2_current:  {inverter.string_2_current}")
    print(f"string_3_current:  {inverter.string_3_current}")
    print(f"meter_power:       {inverter.meter_power}")
    print(f"meter_a_phase_power:{inverter.meter_a_phase_power}")
    print(f"meter_b_phase_power:{inverter.meter_b_phase_power}")
    print(f"meter_c_phase_power:{inverter.meter_c_phase_power}")
    print(f"load_power:        {inverter.load_power}")
    print(f"daily_export_energy:{inverter.daily_export_energy}")
    print(f"total_export_energy:{inverter.total_export_energy}")
    print(f"daily_import_energy:{inverter.daily_import_energy}")
    print(f"total_import_energy:{inverter.total_import_energy}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("host")
    parser.add_argument("--port", type=int, default=502)
    parser.add_argument("--unit-id", type=int, default=1)
    args = parser.parse_args()
    asyncio.run(main(args.host, args.port, args.unit_id))
