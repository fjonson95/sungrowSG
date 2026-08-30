# Vendored copy — do not edit directly

This directory is a committed mirror of
`library/sungrow-modbus/src/sungrow_modbus/`, kept here so the integration
doesn't depend on `sungrow-modbus` as a PyPI package (it isn't published
yet — `pip install sungrow-modbus==0.0.1` would just fail, breaking
installs via HACS or a plain `custom_components/` copy).
`custom_components/sungrow_sg/coordinator.py`, `config_flow.py`, and
`sensor.py` import from this local copy (`from .sungrow_modbus import
...`), not from an installed package.

**Edit `library/sungrow-modbus/src/sungrow_modbus/` instead of the files
in this directory.** After changing anything there, re-sync:

```bash
python scripts/sync_vendored_library.py
pytest library/sungrow-modbus/tests
pytest tests
```

The sync script only copies `*.py` files that differ from the library
copy — this `README.md` isn't touched by it, so it's safe to keep
alongside the mirrored source.

Once the library is published to PyPI, this vendored copy can be deleted
and `manifest.json` switched back to a normal `sungrow-modbus>=X`
requirement.
