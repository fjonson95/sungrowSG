<img src="custom_components/sungrow_sg/brand/icon@2x.png" alt="" width="96" height="96" align="right">

**English** | [Svenska](README.sv.md)

# Sungrow SG-series for Home Assistant

[![CI](https://github.com/fjonson95/sungrowSG/actions/workflows/ci.yml/badge.svg)](https://github.com/fjonson95/sungrowSG/actions/workflows/ci.yml)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Home Assistant integration for Sungrow SG-series string inverters
(SG5.0RT–SG25RT, the RT family — developed and live-tested against an
SG12RT) over Modbus TCP. No cloud service, no datalogger middleman —
talks directly to the inverter on your local network.

## Features

- **55 sensors**: AC measurements (phase voltage/current, power,
  frequency), DC/MPPT (voltage, current, calculated power per MPPT and
  per string), energy yield (daily/monthly/total), grid meter block
  (export/import/house load, requires an external CT/smart meter),
  diagnostics (temperature, insulation resistance, work state, fault
  codes from Sungrow's Appendix 4 table, firmware versions), and a
  calculated capacity-utilization sensor (current power as a % of rated
  power, for dashboard bar/gauge cards).
- **2 binary sensors**: grid-connected, fault.
- **Writable controls** (switch/number entities): start/stop, power
  limitation (on/off + level as % or absolute kW), a separate feed-in
  power limit (on/off + kW/%, requires an external smart meter), Night
  SVG.
- **Configurable sensor groups** — opt out of strings, MPPT, or the grid
  meter at setup or later via Options, if you don't have/want them (e.g.
  no meter installed). Disabled sensors are actually removed from the
  entity registry, not just hidden.
- A proper device in the device registry (model, serial number,
  protocol version), UI configuration (config flow, no YAML).

## Installation

### Via HACS (recommended)

1. HACS → three-dot menu (top right) → **Custom repositories**.
2. Add `https://github.com/fjonson95/sungrowSG` as type **Integration**.
3. Search for "Sungrow SG-series" in HACS and install.
4. Restart Home Assistant.

### Manual

Copy `custom_components/sungrow_sg/` into your `config/custom_components/`
directory and restart Home Assistant.

## Configuration

Settings → Devices & services → Add integration → "Sungrow SG-series".
You'll need:

- **Host** — the inverter's IP address.
- **Port** — Modbus TCP port (default `502`).
- **Unit ID** — Modbus unit id (default `1`).
- Toggles for string sensors, MPPT sensors, and the grid meter (can be
  changed later via Options on the configured device).

## Verified against

The register map is read directly from Sungrow's official
"Communication Protocol of Residential & Commercial PV Grid-Connected
Inverters" (V1.1.80) and live-tested against a real SG12RT — see
[`docs/register_map.md`](docs/register_map.md) for the full
address-by-address documentation, including what's hardware-confirmed
versus only PDF-verified.

**Writable registers** (start/stop, power limitation, feed-in power
limit, Night SVG) have their address/scale/enum values read from the
doc and read-verified live, but **no write has been sent to a real
inverter yet**. Test carefully yourself and consider reporting the
result in an issue.

## Project structure

```
scripts/query.py              <- standalone CLI against the library, no HA needed
library/sungrow-modbus/       <- HA-independent: register knowledge + modbus_connection.model
custom_components/sungrow_sg/ <- the HA integration (vendors the library above, see its README)
docs/register_map.md          <- full register map with source citations
docs/architecture.md          <- short technical overview
```

See [`docs/architecture.md`](docs/architecture.md) for more.

## Development

```bash
# Library (Python 3.12+)
pip install -e library/sungrow-modbus[dev]
pytest library/sungrow-modbus/tests
ruff check library/sungrow-modbus

# HA integration (Python 3.13, pytest-homeassistant-custom-component)
pip install -r requirements_test.txt
pytest tests
ruff check custom_components tests
```

After changing anything under
`library/sungrow-modbus/src/sungrow_modbus/`, sync the vendored copy
before committing:

```bash
python scripts/sync_vendored_library.py
```

## License

[MIT](LICENSE)
