"""Number platform for Sungrow SG-series.

Writable holding registers: power limitation (percent or absolute kW) and
feed-in power limit (absolute kW or percent) - see
`sungrow_modbus/models.py`'s `SungrowSGControl` docstring for the safety
caveats, same as switch.py.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SungrowSGCoordinator
from .entity import build_device_info


@dataclass(frozen=True, kw_only=True)
class SungrowSGNumberEntityDescription(NumberEntityDescription):
    """Adds the coordinator.data key and the write callback per number -
    same reasoning as switch.py's SungrowSGSwitchEntityDescription: each
    control has its own coordinator method, not a single generic "write
    raw value" path.
    """

    async_set_value: Callable[[SungrowSGCoordinator, float], Awaitable[None]]


NUMBER_DESCRIPTIONS: tuple[SungrowSGNumberEntityDescription, ...] = (
    SungrowSGNumberEntityDescription(
        key="power_limitation_setting",
        translation_key="power_limitation_setting",
        native_unit_of_measurement="%",
        # Doc's own note ("See Appendix 6") implies a model-specific
        # range not confirmed for SG12RT - see registers.py
        # POWER_LIMITATION_SETTING. 0-100 is a conservative UI bound;
        # the inverter's own firmware is the real authority and will
        # reject an out-of-range write regardless of this limit.
        native_min_value=0,
        native_max_value=100,
        native_step=0.1,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
        async_set_value=(
            lambda coordinator, value: coordinator.async_set_power_limitation_setting(
                value
            )
        ),
    ),
    # Doc chapter 3.1.3 "Setting Power Limitation Value" - absolute-kW
    # alternative to the percentage above. Only takes effect once
    # power_limitation_switch is on (chapter 3.1.2's precondition applies
    # here too) - this entity doesn't enforce that itself.
    SungrowSGNumberEntityDescription(
        key="power_limitation_adjustment",
        translation_key="power_limitation_adjustment",
        native_unit_of_measurement="kW",
        # No documented upper bound beyond "the inverter's max active
        # power" (model-specific, see Appendix 1) - a generous but not
        # unbounded UI ceiling; the inverter's firmware is the real limit.
        native_min_value=0,
        native_max_value=50,
        native_step=0.1,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
        async_set_value=(
            lambda coordinator,
            value: coordinator.async_set_power_limitation_adjustment(value)
        ),
    ),
    # Feed-in power limit family (doc chapter 3.1) - a separate control
    # point at the grid connection, not the inverter's own AC output; see
    # registers.py FEED_IN_POWER_LIMIT_* docstring. Requires an external
    # smart meter to be meaningful.
    SungrowSGNumberEntityDescription(
        key="feed_in_power_limit_value",
        translation_key="feed_in_power_limit_value",
        native_unit_of_measurement="kW",
        native_min_value=0,
        native_max_value=50,
        native_step=0.01,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
        async_set_value=(
            lambda coordinator, value: coordinator.async_set_feed_in_power_limit_value(
                value
            )
        ),
    ),
    SungrowSGNumberEntityDescription(
        key="feed_in_power_limit_ratio",
        translation_key="feed_in_power_limit_ratio",
        native_unit_of_measurement="%",
        native_min_value=0,
        native_max_value=100,
        native_step=0.1,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
        async_set_value=(
            lambda coordinator, value: coordinator.async_set_feed_in_power_limit_ratio(
                value
            )
        ),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: SungrowSGCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        SungrowSGNumber(coordinator, entry, description)
        for description in NUMBER_DESCRIPTIONS
    )


class SungrowSGNumber(CoordinatorEntity[SungrowSGCoordinator], NumberEntity):
    _attr_has_entity_name = True
    entity_description: SungrowSGNumberEntityDescription

    def __init__(
        self,
        coordinator: SungrowSGCoordinator,
        entry: ConfigEntry,
        description: SungrowSGNumberEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = build_device_info(entry, coordinator.data)

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data.get(self.entity_description.key)

    async def async_set_native_value(self, value: float) -> None:
        await self.entity_description.async_set_value(self.coordinator, value)
