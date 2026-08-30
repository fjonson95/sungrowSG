"""Tests for SungrowSGInverter.

These are meant to run against modbus_connection's in-process test server
(TCP), per the library's own pytest plugin - not against a real inverter,
and not against mocks. Fill in the fixture once modbus_connection is
installed and its testing API is confirmed; this is a placeholder shape.
"""

import pytest

from sungrow_modbus import SungrowSGInverter


@pytest.mark.skip(
    reason=(
        "Scaffold placeholder - wire up modbus_connection's in-process "
        "test server fixture here once the library is installed and its "
        "testing API (pytest plugin) is confirmed."
    )
)
async def test_reads_phase_voltages():
    # Expected shape, to fill in:
    #
    # async with modbus_connection.testing.tcp_server(unit=1) as server:
    #     server.set_register(SungrowSGInverter... )
    #     conn = ModbusConnection(ModbusTcpParams(host=server.host, port=server.port))
    #     inverter = SungrowSGInverter(conn.for_unit(1))
    #     await inverter.async_update()
    #     assert inverter.phase_a_voltage == pytest.approx(230.0)
    raise NotImplementedError
