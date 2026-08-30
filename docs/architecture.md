# Arkitektur

Följer mönstret från Home Assistants "Modernizing Modbus"-blogg
(2026-07-05): https://developers.home-assistant.io/blog/2026/07/05/modernizing-modbus/

```
scripts/query.py            <- fristående CLI, pratar direkt mot biblioteket
library/sungrow-modbus/      <- HA-oberoende: registerkunskap + modbus_connection.model
custom_components/sungrow_sg/ <- HA-integration: config_flow, coordinator, entiteter
```

- `custom_components/sungrow_sg` öppnar ALDRIG en egen Modbus-anslutning.
  Den ber kärnintegrationen `modbus` om en unit via
  `modbus_connection.ModbusConnection(...).for_unit(unit_id)`, vilket delar
  och serialiserar anslutningen med andra integrationer på samma buss
  (t.ex. Modbus Manager om den körs mot samma inverter).
- Referensimplementationer att luta sig mot:
  - Bibliotek: https://github.com/Tom-Bom-badil/trovis-modbus/
  - HA-integration: `trovis557x` i Home Assistant core
  - HACS-mall: `integration_blueprint`
