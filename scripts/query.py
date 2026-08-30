#!/usr/bin/env python3
"""Fristående CLI för att läsa av en Sungrow SG-inverter över Modbus TCP.

Kräver Python >=3.12 och `modbus-connection` + `sungrow-modbus` installerade
(`pip install -e library/sungrow-modbus[dev]` i en 3.12-venv). Används för
att verifiera register mot en riktig inverter innan de låses fast i
`registers.py` (se docs/register_map.md).

Status: skelett - importerna nedan kommer faila tills library/sungrow-modbus
faktiskt är installerat i en 3.12-miljö.
"""

from __future__ import annotations

import argparse
import asyncio

from modbus_connection import ModbusConnection, ModbusTcpParams

from sungrow_modbus import SungrowSGInverter


async def main(host: str, port: int, unit_id: int) -> None:
    conn = ModbusConnection(ModbusTcpParams(host=host, port=port))
    inverter = SungrowSGInverter(conn.for_unit(unit_id))
    await inverter.async_update()
    print(f"phase_a_voltage:   {inverter.phase_a_voltage}")
    print(f"phase_b_voltage:   {inverter.phase_b_voltage}")
    print(f"phase_c_voltage:   {inverter.phase_c_voltage}")
    print(f"total_active_power:{inverter.total_active_power}")
    print(f"daily_power_yield: {inverter.daily_power_yield}")
    print(f"total_power_yield: {inverter.total_power_yield}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("host")
    parser.add_argument("--port", type=int, default=502)
    parser.add_argument("--unit-id", type=int, default=1)
    args = parser.parse_args()
    asyncio.run(main(args.host, args.port, args.unit_id))
