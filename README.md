# sungrowSG — Sungrow SG-serien som riktig Home Assistant-integration

Egen Modbus-integration för Sungrow strängväxelriktare (SG-serien, i första hand
SG12RT), byggd enligt den nya arkitekturen som beskrivs i Home Assistants
utvecklarblogg ["Modernizing Modbus"](https://developers.home-assistant.io/blog/2026/07/05/modernizing-modbus/)
(juli 2026).

Projektet är uppdelat i två delar, enligt mönstret `trovis-modbus` (bibliotek)
+ `trovis557x` (HA-integration):

- **`library/sungrow-modbus/`** — fristående, HA-oberoende Python-paket som
  modellerar Sungrow SG-enheter mot `modbus_connection.model`
  (register, skalning, enheter, coils). Publiceras separat på PyPI när det är
  moget, testas med `modbus_connection`s pytest-plugin mot riktiga
  in-process Modbus-servrar (ingen mockning).
- **`custom_components/sungrow_sg/`** — HACS-distribuerad Home Assistant-
  integration som "vendorar" biblioteket, ber kärnintegrationen `modbus` om
  en unit (delad, serialiserad anslutning — ingen egen socket), och
  exponerar entiteter via config flow + device registry.

## Status

Tidigt skelett. Registerkartan för SG12RT (`docs/register_map.md`) är
**inte verifierad** — den är ihopsatt av kända Sungrow-register från
community-projekt (t.ex. `mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant`)
och måste stämmas av mot Sungrows officiella Modbus-protokolldokument för
SG5.0RT–SG12RT-familjen innan något litas på i produktion.

`modbus-connection` kräver Python ≥3.12. Denna dev-miljö har bara 3.10
installerat lokalt — sätt upp en 3.12-venv (eller kör i HA:s devcontainer)
innan biblioteket faktiskt installeras och testas skarpt.

## Varför en egen integration (i korthet)

Se den fulla diskussionen i projektanteckningarna, men kort: riktig enhet i
enhetsregistret, UI-konfiguration istället för YAML/mallar, delad
Modbus-anslutning utan buskonflikter med t.ex. Modbus Manager, och möjlighet
att bidra tillbaka till communityn om SG12RT-stödet blir bra.

## Nästa steg

1. Hämta/verifiera SG12RT-registerkartan mot Sungrows officiella dokument.
2. Fylla i `library/sungrow-modbus/src/sungrow_modbus/registers.py` med
   verifierade adresser.
3. Sätta upp Python 3.12-miljö och installera `modbus-connection` på riktigt.
4. Skriva tester i `library/sungrow-modbus/tests/`.
5. Bygga config_flow + coordinator + sensor-platform i
   `custom_components/sungrow_sg/` och testa mot en riktig SG12RT på LAN.
