"""Elli Charger over local Modbus TCP or EEBUS."""

from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_CONNECTION, CONNECTION_EEBUS
from .coordinator import ElliConfigEntry, ElliCoordinator
from .eebus import EebusCoordinator

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.SWITCH,
]


async def async_setup_entry(hass: HomeAssistant, entry: ElliConfigEntry) -> bool:
    if entry.data.get(CONF_CONNECTION) == CONNECTION_EEBUS:
        coordinator = EebusCoordinator(hass, entry)
    else:
        coordinator = ElliCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ElliConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        if isinstance(entry.runtime_data, EebusCoordinator):
            await entry.runtime_data.async_shutdown()
        else:
            await entry.runtime_data.charger.close()
    return unloaded


async def _async_reload(hass: HomeAssistant, entry: ElliConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
