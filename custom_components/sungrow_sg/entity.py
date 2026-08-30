"""Shared entity helpers for the Sungrow SG-series integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN


def build_device_info(entry: ConfigEntry, coordinator_data: dict) -> DeviceInfo:
    """One DeviceInfo shared by every platform (sensor/switch/number) for
    this config entry - same physical inverter, not one device per platform.

    Populated from the inverter's own identification registers -
    coordinator_data is already filled by the time any platform's
    async_setup_entry runs (the first refresh is awaited in __init__.py
    before platforms are forwarded).
    """
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.title,
        manufacturer="Sungrow",
        model=coordinator_data.get("model_name"),
        sw_version=coordinator_data.get("protocol_version"),
        serial_number=coordinator_data.get("serial_number"),
    )
