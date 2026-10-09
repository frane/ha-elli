"""Polling coordinator for the Elli Charger integration."""

from __future__ import annotations

from datetime import timedelta
import logging

from elli2modbus import ChargerInfo, ChargerStatus, ElliCharger, ModbusError

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_UNIT_ID, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

type ElliConfigEntry = ConfigEntry[ElliCoordinator]


class ElliCoordinator(DataUpdateCoordinator[ChargerStatus]):
    """Polls the wallbox. Polling also keeps the Modbus watchdog alive."""

    config_entry: ElliConfigEntry
    info: ChargerInfo

    def __init__(self, hass: HomeAssistant, entry: ElliConfigEntry) -> None:
        interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=interval),
        )
        self.charger = ElliCharger(
            entry.data[CONF_HOST], entry.data[CONF_PORT], entry.data[CONF_UNIT_ID]
        )
        # Current the user wants while charging is enabled. Register 261 may
        # report less (internal limits), so it is tracked separately.
        self.target_current: float | None = None

    async def _async_setup(self) -> None:
        try:
            self.info = await self.charger.read_info()
        except ModbusError as err:
            raise UpdateFailed(f"Wallbox not reachable: {err}") from err

    async def _async_update_data(self) -> ChargerStatus:
        try:
            status = await self.charger.read_status()
        except ModbusError as err:
            raise UpdateFailed(f"Error reading wallbox: {err}") from err
        if self.target_current is None:
            self.target_current = status.current_limit or self.info.max_current
        return status

    @property
    def charging_enabled(self) -> bool:
        return bool(self.data and self.data.charging_allowed)

    async def _call(self, coro) -> None:
        try:
            await coro
        except ValueError as err:
            raise ServiceValidationError(str(err)) from err
        except ModbusError as err:
            raise HomeAssistantError(f"Wallbox rejected the command: {err}") from err
        # Refresh right away (not debounced) so entities follow at once.
        await self.async_refresh()

    async def async_set_target_current(self, amps: float) -> None:
        """Store the target; apply it immediately while charging is enabled."""
        self.target_current = amps
        if self.charging_enabled:
            await self._call(self.charger.set_current(amps))
        else:
            self.async_update_listeners()

    async def async_set_charging(self, enabled: bool) -> None:
        if enabled:
            await self._call(
                self.charger.set_current(self.target_current or self.info.max_current)
            )
        else:
            await self._call(self.charger.stop())

    async def async_set_failsafe_current(self, amps: float) -> None:
        await self._call(self.charger.set_failsafe_current(amps))

    async def async_set_watchdog_timeout(self, seconds: float) -> None:
        await self._call(self.charger.set_watchdog_timeout(seconds))
