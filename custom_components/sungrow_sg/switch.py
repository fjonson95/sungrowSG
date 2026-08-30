"""Switch platform for Sungrow SG-series.

Three writable holding-register controls - see
`sungrow_modbus/models.py`'s `SungrowSGControl` docstring for the safety
caveats: a wrong value here can disconnect the inverter from the grid or
stop production. Address/enum values are read directly from the official
protocol doc and read back correctly against a real SG12RT, but writing
has not been tested against real hardware yet.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SungrowSGCoordinator
from .entity import build_device_info


@dataclass(frozen=True, kw_only=True)
class SungrowSGSwitchEntityDescription(SwitchEntityDescription):
    """Adds the coordinator.data key and the write callback per switch -
    each control has its own coordinator method (see coordinator.py),
    not a single generic "write raw enum" path, so a bug in one switch's
    wiring can't silently affect another.
    """

    data_key: str
    async_set_state: Callable[[SungrowSGCoordinator, bool], Awaitable[None]]


SWITCH_DESCRIPTIONS: tuple[SungrowSGSwitchEntityDescription, ...] = (
    SungrowSGSwitchEntityDescription(
        key="start_stop",
        translation_key="start_stop",
        data_key="start_stop_is_running",
        async_set_state=lambda coordinator, value: coordinator.async_set_start_stop(
            running=value
        ),
    ),
    SungrowSGSwitchEntityDescription(
        key="power_limitation_switch",
        translation_key="power_limitation_switch",
        data_key="power_limitation_enabled",
        entity_category=EntityCategory.CONFIG,
        async_set_state=(
            lambda coordinator,
            value: coordinator.async_set_power_limitation_enabled(enabled=value)
        ),
    ),
    SungrowSGSwitchEntityDescription(
        key="feed_in_power_limit_switch",
        translation_key="feed_in_power_limit_switch",
        data_key="feed_in_power_limit_enabled",
        entity_category=EntityCategory.CONFIG,
        async_set_state=(
            lambda coordinator,
            value: coordinator.async_set_feed_in_power_limit_enabled(enabled=value)
        ),
    ),
    SungrowSGSwitchEntityDescription(
        key="night_svg_switch",
        translation_key="night_svg_switch",
        data_key="night_svg_enabled",
        entity_category=EntityCategory.CONFIG,
        async_set_state=(
            lambda coordinator, value: coordinator.async_set_night_svg_enabled(
                enabled=value
            )
        ),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: SungrowSGCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        SungrowSGSwitch(coordinator, entry, description)
        for description in SWITCH_DESCRIPTIONS
    )


class SungrowSGSwitch(CoordinatorEntity[SungrowSGCoordinator], SwitchEntity):
    _attr_has_entity_name = True
    entity_description: SungrowSGSwitchEntityDescription

    def __init__(
        self,
        coordinator: SungrowSGCoordinator,
        entry: ConfigEntry,
        description: SungrowSGSwitchEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = build_device_info(entry, coordinator.data)

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.data.get(self.entity_description.data_key)

    async def async_turn_on(self, **kwargs: object) -> None:
        await self.entity_description.async_set_state(self.coordinator, True)

    async def async_turn_off(self, **kwargs: object) -> None:
        await self.entity_description.async_set_state(self.coordinator, False)
