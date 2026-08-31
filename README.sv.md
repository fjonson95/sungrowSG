<img src="custom_components/sungrow_sg/brand/icon@2x.png" alt="" width="96" height="96" align="right">

**Svenska** | [English](README.md)

# Sungrow SG-serien för Home Assistant

[![CI](https://github.com/fjonson95/sungrowSG/actions/workflows/ci.yml/badge.svg)](https://github.com/fjonson95/sungrowSG/actions/workflows/ci.yml)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Home Assistant-integration för Sungrow SG-seriens strängväxelriktare
(SG5.0RT–SG25RT, RT-familjen — utvecklad och livetestad mot en SG12RT)
över Modbus TCP. Ingen molntjänst, ingen datalogger-mellanhand — pratar
direkt med invertern på ditt lokala nätverk.

## Funktioner

- **55 sensorer**: AC-mätvärden (fas­spänning/ström, effekt, frekvens),
  DC/MPPT (spänning, ström, beräknad effekt per MPPT och per sträng),
  energiproduktion (dagens/månadens/totalt), elmätarblock
  (export/import/husbehov, kräver extern CT/smart-mätare), diagnostik
  (temperatur, isolationsresistans, driftstatus, felkoder från Sungrows
  Appendix 4-tabell, firmware-versioner) och en beräknad
  kapacitetsutnyttjande-sensor (aktuell effekt som % av märkeffekt, för
  stapel-/gauge-kort).
- **2 binärsensorer**: nätansluten, fel.
- **Skrivbara kontroller** (switch/number-entiteter): start/stopp,
  effektbegränsning (på/av + nivå i % eller absolut kW), separat
  nätinmatningsbegränsning (på/av + kW/%, kräver extern smart-mätare),
  Night SVG.
- **Konfigurerbara sensorgrupper** — välj bort strängar, MPPT eller
  elmätare vid installation eller senare via Alternativ, om du inte vill
  ha dem (t.ex. ingen mätare inkopplad). Avstängda sensorer städas bort
  ur entity-registret, inte bara dolda.
- Egen enhet i enhetsregistret (modell, serienummer, protokollversion),
  UI-konfiguration (config flow, ingen YAML).

## Installation

### Via HACS (rekommenderas)

1. HACS → tre punkter uppe till höger → **Anpassade förråd**.
2. Lägg till `https://github.com/fjonson95/sungrowSG` som typ **Integration**.
3. Sök upp "Sungrow SG-series" i HACS och installera.
4. Starta om Home Assistant.

### Manuellt

Kopiera `custom_components/sungrow_sg/` till din `config/custom_components/`-
mapp och starta om Home Assistant.

## Konfiguration

Inställningar → Enheter & tjänster → Lägg till integration → "Sungrow
SG-series". Du behöver:

- **Host** — invertern IP-adress.
- **Port** — Modbus TCP-port (standard `502`).
- **Unit ID** — Modbus-enhets-id (standard `1`).
- Togglar för strängsensorer, MPPT-sensorer och elmätare (kan ändras
  senare via Alternativ på den konfigurerade enheten).

## Support och verifierat mot

Registerkartan är läst direkt ur Sungrows officiella "Communication
Protocol of Residential & Commercial PV Grid-Connected Inverters"
(V1.1.80) samt live-testad mot en riktig SG12RT — se
[`docs/register_map.md`](docs/register_map.md) för fullständig
adress-för-adress-dokumentation, inklusive vad som är hårdvarubekräftat
kontra bara PDF-verifierat.

**Skrivbara register** (start/stopp, effektbegränsning, nätinmatnings-
begränsning, Night SVG) har adress/skala/enum-värden avlästa ur
dokumentet och läsverifierade live, men **ingen skrivning har körts mot
en riktig inverter ännu**. Testa försiktigt själv och rapportera gärna
resultatet i ett issue.

## Projektstruktur

```
scripts/query.py              <- fristående CLI mot biblioteket, ingen HA behövs
library/sungrow-modbus/       <- HA-oberoende: registerkunskap + modbus_connection.model
custom_components/sungrow_sg/ <- HA-integrationen (vendorar biblioteket ovan, se dess README)
docs/register_map.md          <- fullständig registerkarta med källhänvisningar
docs/architecture.md          <- kort teknisk översikt
```

Se [`docs/architecture.md`](docs/architecture.md) för mer.

## Utveckling

```bash
# Bibliotek (Python 3.12+)
pip install -e library/sungrow-modbus[dev]
pytest library/sungrow-modbus/tests
ruff check library/sungrow-modbus

# HA-integration (Python 3.13, pytest-homeassistant-custom-component)
pip install -r requirements_test.txt
pytest tests
ruff check custom_components tests
```

Efter en ändring i `library/sungrow-modbus/src/sungrow_modbus/`, synka
den vendorade kopian innan commit:

```bash
python scripts/sync_vendored_library.py
```

## Licens

[MIT](LICENSE)
