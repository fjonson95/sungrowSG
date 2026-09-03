# Arkitektur

Följer mönstret från Home Assistants "Modernizing Modbus"-blogg
(2026-07-05): https://developers.home-assistant.io/blog/2026/07/05/modernizing-modbus/

```
scripts/query.py            <- fristående CLI, pratar direkt mot biblioteket
library/sungrow-modbus/      <- HA-oberoende: registerkunskap + modbus_connection.model
custom_components/sungrow_sg/ <- HA-integration: config_flow, coordinator, entiteter
```

- `custom_components/sungrow_sg` bygger en egen `ModbusConnection`
  (`modbus_connection.tmodbus`, ett TCP-klientbibliotek, inte HA:s
  kärnintegration `modbus`) i `coordinator.py`, en per config entry,
  återanvänd över alla polls. `SungrowSGInverter` (läsning) och
  `SungrowSGControl` (skrivning) delar samma `ModbusUnit` via
  `connection.for_unit(unit_id)` - se `coordinator.py`.
- `SungrowSGCoordinator._async_update_data` retryar upp till 3 gånger
  (10s mellanrum) på `ModbusError` innan `UpdateFailed` propagerar - en
  enskild tappad TCP-timeout ska inte direkt slå ut alla entiteter till
  `unavailable`. Ett dygnsräknat antal `ModbusTimeoutError` exponeras
  som en diagnostisk sensor (`timeout_count_today`) - ren
  coordinator-state, inget Modbus-register.
- Referensimplementationer att luta sig mot:
  - Bibliotek: https://github.com/Tom-Bom-badil/trovis-modbus/
  - HA-integration: `trovis557x` i Home Assistant core
  - HACS-mall: `integration_blueprint`
