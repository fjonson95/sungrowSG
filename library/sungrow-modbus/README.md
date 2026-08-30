# sungrow-modbus

Fristående, Home Assistant-oberoende bibliotek som modellerar Sungrow
SG-seriens strängväxelriktare (fokus SG12RT) mot `modbus_connection.model`.

Skriv aldrig direkt mot pymodbus/tmodbus här — all transport går via en
`modbus_connection.ModbusUnit` som injiceras utifrån. Det är det som gör
biblioteket återanvändbart både i Home Assistant-integrationen i det här
repot och i fristående skript (se `scripts/query.py` i repo-roten).

## Status

Skelett. Registeradresserna i `registers.py` är **inte verifierade** mot
Sungrows officiella Modbus-protokolldokument — se `docs/register_map.md`
i repo-roten.
