# sungrow-modbus

Fristående, Home Assistant-oberoende bibliotek som modellerar Sungrow
SG-seriens strängväxelriktare (fokus SG12RT) mot `modbus_connection.model`.

Skriv aldrig direkt mot pymodbus/tmodbus här — all transport går via en
`modbus_connection.ModbusUnit` som injiceras utifrån. Det är det som gör
biblioteket återanvändbart både i Home Assistant-integrationen i det här
repot och i fristående skript (se `scripts/query.py` i repo-roten).

## Status

Registerkartan i `registers.py` är läst direkt ur Sungrows officiella
protokolldokument (senast V1.1.80) och live-testad mot en riktig SG12RT
— se `docs/register_map.md` i repo-roten för fullständig
adress-för-adress-dokumentation, inklusive vad som är
hårdvarubekräftat kontra bara PDF-verifierat.

Testkörning:

```bash
pip install -e .[dev]
pytest tests
ruff check .
```
