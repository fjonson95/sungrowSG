"""The Sungrow SG-series integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import (
    CONF_INCLUDE_METER,
    CONF_INCLUDE_MPPT,
    CONF_INCLUDE_STRINGS,
    DEFAULT_INCLUDE_METER,
    DEFAULT_INCLUDE_MPPT,
    DEFAULT_INCLUDE_STRINGS,
    DOMAIN,
    METER_SENSOR_KEYS,
    MPPT_SENSOR_KEYS,
    STRING_SENSOR_KEYS,
    get_toggle,
)
from .coordinator import SungrowSGCoordinator

PLATFORMS = ["sensor", "binary_sensor", "switch", "number"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = SungrowSGCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    # sensor.py's _enabled_descriptions() only stops *creating* entities
    # for a toggled-off group - it doesn't touch ones a previous, more
    # permissive config already registered. Without this they'd linger
    # forever as "unavailable" registry entries instead of actually
    # disappearing. Runs on every setup (not just after an options
    # change) so it also cleans up strays left over from before this
    # existed.
    _async_prune_disabled_sensors(hass, entry)
    # HA only *fires* update listeners on an options change - it doesn't
    # reload the entry on its own. Reloading re-runs this function, which
    # picks up the new include_strings/mppt/meter toggles (new
    # restrict_fields() set, new filtered sensor list).
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


def _async_prune_disabled_sensors(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove entity_registry entries for sensor keys the current
    include_strings/mppt/meter toggles exclude.
    """
    excluded: set[str] = set()
    if not get_toggle(entry, CONF_INCLUDE_MPPT, DEFAULT_INCLUDE_MPPT):
        excluded |= MPPT_SENSOR_KEYS
    if not get_toggle(entry, CONF_INCLUDE_STRINGS, DEFAULT_INCLUDE_STRINGS):
        excluded |= STRING_SENSOR_KEYS
    if not get_toggle(entry, CONF_INCLUDE_METER, DEFAULT_INCLUDE_METER):
        excluded |= METER_SENSOR_KEYS
    if not excluded:
        return

    entity_registry = er.async_get(hass)
    for key in excluded:
        entity_id = entity_registry.async_get_entity_id(
            "sensor", DOMAIN, f"{entry.entry_id}_{key}"
        )
        if entity_id is not None:
            entity_registry.async_remove(entity_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator: SungrowSGCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_shutdown()
    return unload_ok
