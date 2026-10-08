"""Binary sensors."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from elli2modbus import ChargerStatus
from ellieebus import ElliStatus

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import ElliConfigEntry, ElliCoordinator
from .eebus import EebusCoordinator, EebusEntity
from .entity import ElliEntity


@dataclass(frozen=True, kw_only=True)
class ElliBinaryDescription(BinarySensorEntityDescription):
    value_fn: Callable[[ChargerStatus], bool]


BINARY_SENSORS = (
    ElliBinaryDescription(
        key="vehicle_connected",
        device_class=BinarySensorDeviceClass.PLUG,
        value_fn=lambda d: d.vehicle_connected,
    ),
    ElliBinaryDescription(
        key="charging",
        device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
        value_fn=lambda d: d.charging,
    ),
    ElliBinaryDescription(
        key="problem",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda d: d.problem,
    ),
)


@dataclass(frozen=True, kw_only=True)
class EebusBinaryDescription(BinarySensorEntityDescription):
    value_fn: Callable[[ElliStatus], bool | None]
    optional: bool = False


EEBUS_BINARY_SENSORS = (
    EebusBinaryDescription(
        key="connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.connected,
    ),
    EebusBinaryDescription(
        key="problem",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda d: None if d.operating_state is None
        else d.operating_state not in ("normalOperation", "standby"),
    ),
    EebusBinaryDescription(
        key="vehicle_connected",
        device_class=BinarySensorDeviceClass.PLUG,
        optional=True,
        value_fn=lambda d: d.vehicle_connected,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ElliConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    if isinstance(coordinator, EebusCoordinator):
        status = coordinator.data
        async_add_entities(
            EebusBinarySensor(coordinator, d)
            for d in EEBUS_BINARY_SENSORS
            if not d.optional or (status is not None and d.value_fn(status) is not None)
        )
        return
    async_add_entities(ElliBinarySensor(coordinator, d) for d in BINARY_SENSORS)


class ElliBinarySensor(ElliEntity, BinarySensorEntity):
    entity_description: ElliBinaryDescription

    def __init__(
        self, coordinator: ElliCoordinator, description: ElliBinaryDescription
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool:
        return self.entity_description.value_fn(self.coordinator.data)


class EebusBinarySensor(EebusEntity, BinarySensorEntity):
    entity_description: EebusBinaryDescription

    def __init__(self, coordinator: EebusCoordinator, description: EebusBinaryDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def available(self) -> bool:
        if self.entity_description.key == "connected":
            return self.coordinator.last_update_success
        return super().available

    @property
    def is_on(self) -> bool | None:
        return self.entity_description.value_fn(self.coordinator.data)
