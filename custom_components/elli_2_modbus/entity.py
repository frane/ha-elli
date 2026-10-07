"""Base entity for the Elli Charger 2 (Modbus) integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import ElliCoordinator


class ElliEntity(CoordinatorEntity[ElliCoordinator]):
    """Common device info and unique id."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: ElliCoordinator, key: str) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.unique_id}_{key}"
        self._attr_translation_key = key
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id)},
            name=entry.title,
            manufacturer=MANUFACTURER,
            model=MODEL,
            hw_version=f"Modbus layout {coordinator.info.layout_version}",
        )
