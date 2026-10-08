"""EEBUS connection (elli-eebus): coordinator and base entity."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from ellieebus import ElliEebus, ElliError, ElliStatus
from pyeebus.spine import SpineError
from pyeebus.usecases import DataNotAvailable

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator

from .const import CONF_SKI, DOMAIN, EEBUS_NAME, EEBUS_SETUP_WAIT, MANUFACTURER

_LOGGER = logging.getLogger(__name__)


def state_dir(hass: HomeAssistant, ski: str) -> Path:
    """Where our EEBUS identity (certificate) for this wallbox is kept."""
    return Path(hass.config.path(".storage", DOMAIN, ski))


async def async_get_zeroconf(hass: HomeAssistant) -> Any:
    """Home Assistant's shared zeroconf instance (needed so the wallbox finds us)."""
    from homeassistant.components import zeroconf

    return await zeroconf.async_get_async_instance(hass)


async def async_create_client(hass: HomeAssistant, ski: str, host: str, port: int) -> ElliEebus:
    zc = await async_get_zeroconf(hass)
    return ElliEebus(ski, state_dir=state_dir(hass, ski), host=host, port=port, local_port=0,
                     name=EEBUS_NAME, zeroconf=zc, announce=zc is not None)


class EebusCoordinator(DataUpdateCoordinator[ElliStatus]):
    """Push based: the wallbox reports changes, nothing is polled."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(hass, _LOGGER, config_entry=entry, name=DOMAIN)
        self.client: ElliEebus | None = None
        self._unsub = None
        self.target_power: float | None = None  # W the user wants while the limit is on

    async def _async_setup(self) -> None:
        data = self.config_entry.data
        self.client = await async_create_client(self.hass, data[CONF_SKI], data[CONF_HOST], data[CONF_PORT])
        self._unsub = self.client.add_listener(self.async_set_updated_data)
        await self.client.start()
        try:
            await self.client.wait_connected(EEBUS_SETUP_WAIT)
            await asyncio.sleep(1)  # first data
        except TimeoutError:
            _LOGGER.warning("Elli wallbox %s did not connect yet, retrying in the background",
                            data[CONF_HOST])

    async def _async_update_data(self) -> ElliStatus:
        assert self.client is not None
        return self.client.status()

    async def async_shutdown(self) -> None:
        if self._unsub:
            self._unsub()
            self._unsub = None
        if self.client is not None:
            client, self.client = self.client, None
            await client.stop()
        await super().async_shutdown()

    # control
    async def _call(self, coro) -> None:
        try:
            await coro
        except ValueError as err:
            raise ServiceValidationError(str(err)) from err
        except (ElliError, DataNotAvailable) as err:
            raise HomeAssistantError(f"Wallbox not ready: {err}") from err
        except (SpineError, TimeoutError) as err:
            raise HomeAssistantError(f"Wallbox rejected the command: {err!r}") from err
        self.async_set_updated_data(self.client.status())

    @property
    def limit_active(self) -> bool:
        return bool(self.data and self.data.power_limit_active)

    def default_target(self) -> float:
        d = self.data
        if d and d.power_limit_active and d.power_limit:
            return d.power_limit
        return (d.max_power or d.nominal_max_power or 11000.0) if d else 11000.0

    async def async_set_target_power(self, watts: float) -> None:
        self.target_power = watts
        if self.limit_active:
            await self._call(self.client.set_power_limit(watts))
        else:
            self.async_update_listeners()

    async def async_set_limit_active(self, active: bool) -> None:
        if active:
            await self._call(self.client.set_power_limit(self.target_power or self.default_target()))
        else:
            await self._call(self.client.clear_power_limit())

    async def async_set_failsafe(self, watts: float | None = None, seconds: float | None = None) -> None:
        await self._call(self.client.set_failsafe(watts, seconds))


class EebusEntity(CoordinatorEntity[EebusCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: EebusCoordinator, key: str) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        status = coordinator.data
        self._attr_unique_id = f"{entry.unique_id}_{key}"
        self._attr_translation_key = key
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id)},
            name=entry.title,
            manufacturer=(status.brand if status and status.brand else MANUFACTURER),
            model="Charger (EEBUS)",
            serial_number=status.serial if status else None,
            sw_version=status.software if status else None,
        )

    @property
    def available(self) -> bool:
        return super().available and bool(self.coordinator.data and self.coordinator.data.connected)
