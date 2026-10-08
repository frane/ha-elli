"""Number entities: charging current, failsafe current, watchdog timeout."""

from __future__ import annotations

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.const import EntityCategory, UnitOfElectricCurrent, UnitOfPower, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN, WATCHDOG_MAX_SECONDS
from .coordinator import ElliConfigEntry, ElliCoordinator
from .eebus import EebusCoordinator, EebusEntity
from .entity import ElliEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ElliConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    if isinstance(coordinator, EebusCoordinator):
        async_add_entities(
            [
                PowerLimitNumber(coordinator),
                FailsafePowerNumber(coordinator),
                FailsafeDurationNumber(coordinator),
            ]
        )
        return
    async_add_entities(
        [
            ChargingCurrentNumber(coordinator),
            FailsafeCurrentNumber(coordinator),
            WatchdogTimeoutNumber(coordinator),
        ]
    )


class ChargingCurrentNumber(ElliEntity, NumberEntity):
    """Target charging current. Applied while charging is enabled."""

    _attr_device_class = NumberDeviceClass.CURRENT
    _attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
    _attr_native_step = 0.1
    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator: ElliCoordinator) -> None:
        super().__init__(coordinator, "charging_current")
        self._attr_native_min_value = coordinator.info.min_current
        self._attr_native_max_value = coordinator.info.max_current

    @property
    def native_value(self) -> float | None:
        return self.coordinator.target_current

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_set_target_current(value)


class FailsafeCurrentNumber(ElliEntity, NumberEntity):
    """Current used when Modbus communication is lost (0 = stop charging)."""

    _attr_device_class = NumberDeviceClass.CURRENT
    _attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
    _attr_native_min_value = 0
    _attr_native_step = 1
    _attr_mode = NumberMode.BOX
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: ElliCoordinator) -> None:
        super().__init__(coordinator, "failsafe_current")
        self._attr_native_max_value = coordinator.info.max_current

    @property
    def native_value(self) -> float:
        return self.coordinator.data.failsafe_current

    async def async_set_native_value(self, value: float) -> None:
        if 0 < value < self.coordinator.info.min_current:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="failsafe_out_of_range",
                translation_placeholders={
                    "min": f"{self.coordinator.info.min_current:g}"
                },
            )
        await self.coordinator.async_set_failsafe_current(value)


class WatchdogTimeoutNumber(ElliEntity, NumberEntity):
    """Fall back to failsafe current after this time without Modbus traffic."""

    _attr_device_class = NumberDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_native_min_value = 0
    _attr_native_max_value = WATCHDOG_MAX_SECONDS
    _attr_native_step = 1
    _attr_mode = NumberMode.BOX
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: ElliCoordinator) -> None:
        super().__init__(coordinator, "watchdog_timeout")

    @property
    def native_value(self) -> float:
        return self.coordinator.data.watchdog_timeout

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_set_watchdog_timeout(value)


class PowerLimitNumber(EebusEntity, NumberEntity):
    """Charging power limit (EEBUS LPC). Applied while the limit switch is on."""

    _attr_device_class = NumberDeviceClass.POWER
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_native_step = 100
    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator: EebusCoordinator) -> None:
        super().__init__(coordinator, "power_limit")
        status = coordinator.data
        self._attr_native_min_value = (status.min_power if status and status.min_power else 0)
        self._attr_native_max_value = (
            status.max_power or status.nominal_max_power if status and (status.max_power or status.nominal_max_power)
            else 22000
        )

    @property
    def native_value(self) -> float | None:
        return self.coordinator.target_power or self.coordinator.default_target()

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_set_target_power(value)


class FailsafePowerNumber(EebusEntity, NumberEntity):
    """Power the wallbox allows when Home Assistant is gone (missing heartbeat)."""

    _attr_device_class = NumberDeviceClass.POWER
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_native_min_value = 0
    _attr_native_max_value = 22000
    _attr_native_step = 100
    _attr_mode = NumberMode.BOX
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: EebusCoordinator) -> None:
        super().__init__(coordinator, "failsafe_power")

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data.failsafe_power

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_set_failsafe(watts=value)


class FailsafeDurationNumber(EebusEntity, NumberEntity):
    """How long the failsafe power applies at least (2 to 24 h)."""

    _attr_device_class = NumberDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.HOURS
    _attr_native_min_value = 2
    _attr_native_max_value = 24
    _attr_native_step = 0.5
    _attr_mode = NumberMode.BOX
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: EebusCoordinator) -> None:
        super().__init__(coordinator, "failsafe_duration")

    @property
    def native_value(self) -> float | None:
        seconds = self.coordinator.data.failsafe_duration
        return None if seconds is None else seconds / 3600

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_set_failsafe(seconds=value * 3600)
