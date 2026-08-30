"""Binary sensor platform for Sungrow SG-series.

Two states decoded from work_state_2 (registers.py WORK_STATE_2, a
bitmask - see Appendix 3 "Working State 2" of the protocol doc), not
exposed as their own sensors: is_grid_connected (bit 17, "Device is
grid-connected running") and is_in_fault (bit 18, "Device is in fault
stop state"). The rest of work_state_2's bits mirror work_state_1_label
one-for-one per the doc ("The definition corresponding to the state is
the same as that in Appendix 2"), so decoding them individually here
would just duplicate that sensor.
"""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SungrowSGCoordinator
from .entity import build_device_info

BINARY_SENSOR_DESCRIPTIONS: tuple[BinarySensorEntityDescription, ...] = (
    BinarySensorEntityDescription(
        key="is_grid_connected",
        translation_key="is_grid_connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    BinarySensorEntityDescription(
        key="is_in_fault",
        translation_key="is_in_fault",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: SungrowSGCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        SungrowSGBinarySensor(coordinator, entry, description)
        for description in BINARY_SENSOR_DESCRIPTIONS
    )


class SungrowSGBinarySensor(CoordinatorEntity[SungrowSGCoordinator], BinarySensorEntity):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SungrowSGCoordinator,
        entry: ConfigEntry,
        description: BinarySensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = build_device_info(entry, coordinator.data)

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.data.get(self.entity_description.key)
