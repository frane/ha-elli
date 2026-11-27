"""Polling coordinator for the Elli Charger integration."""

from __future__ import annotations

from datetime import timedelta
import logging

from elli2modbus import ChargerInfo, ChargerStatus, ElliCharger, ModbusError

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_UNIT_ID, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

type ElliConfigEntry = ConfigEntry[ElliCoordinator]


class ElliCoordinator(DataUpdateCoordinator[ChargerStatus]):
    """Polls the wallbox, and keeps its Modbus watchdog fed.

    The Elli resets the watchdog on writes only, not on reads. While the watchdog
    is on, every poll therefore writes the current Home Assistant wants back to
    register 261. That also undoes a failsafe the wallbox fell into: once tripped,
    it reports the failsafe current in 261 until something writes again.

    An energy manager limiting the wallbox over EEBUS (e.g. a pause, 0 A) shows in
    261 as well. So what Home Assistant wants is remembered across restarts instead
    of being read back from 261: a pause of the energy manager must not become
    Home Assistant's own setting, which the watchdog would then keep writing.
    """

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
        # Whether Home Assistant wants charging allowed; None until the first poll.
        self.charging_wanted: bool | None = None
        self._store: Store[dict] = Store(hass, 1, f"{DOMAIN}.{entry.entry_id}")

    async def _async_setup(self) -> None:
        if stored := await self._store.async_load():
            self.charging_wanted = stored.get("charging_wanted")
            self.target_current = stored.get("target_current")
        try:
            self.info = await self.charger.read_info()
        except ModbusError as err:
            raise UpdateFailed(f"Wallbox not reachable: {err}") from err

    async def _async_update_data(self) -> ChargerStatus:
        try:
            status = await self.charger.read_status()
        except ModbusError as err:
            raise UpdateFailed(f"Error reading wallbox: {err}") from err
        if self.target_current is None or self.charging_wanted is None:
            # first start: take over what the wallbox does now, and remember it
            if self.target_current is None:
                self.target_current = status.current_limit or self.info.max_current
            if self.charging_wanted is None:
                self.charging_wanted = status.charging_allowed
            self._save()
        if status.watchdog_timeout:
            status = await self._feed_watchdog(status)
        return status

    async def _feed_watchdog(self, status: ChargerStatus) -> ChargerStatus:
        """Write the wanted current again: a write is what resets the watchdog."""
        wanted = (self.target_current or self.info.max_current) if self.charging_wanted else 0
        try:
            if wanted:
                await self.charger.set_current(wanted)
            else:
                await self.charger.stop()
        except (ModbusError, ValueError) as err:
            _LOGGER.warning("Could not refresh the wallbox watchdog: %s", err)
            return status
        if status.current_limit != wanted:
            if status.current_limit == status.failsafe_current:
                _LOGGER.info(
                    "Wallbox was on its failsafe current (%s A); restored %s A",
                    status.failsafe_current,
                    wanted,
                )
            try:
                status = await self.charger.read_status()
            except ModbusError as err:
                raise UpdateFailed(f"Error reading wallbox: {err}") from err
        return status

    @property
    def charging_enabled(self) -> bool:
        """Whether Home Assistant allows charging (an energy manager may still pause it)."""
        if self.charging_wanted is not None:
            return self.charging_wanted
        return bool(self.data and self.data.charging_allowed)

    def _wanted(self) -> dict:
        return {"charging_wanted": self.charging_wanted, "target_current": self.target_current}

    def _save(self) -> None:
        self._store.async_delay_save(self._wanted, 1)

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
        if self.charging_wanted is None:
            self.charging_wanted = self.charging_enabled
        await self._store.async_save(self._wanted())
        if self.charging_wanted:
            await self._call(self.charger.set_current(amps))
        else:
            self.async_update_listeners()

    async def async_set_charging(self, enabled: bool) -> None:
        self.charging_wanted = enabled
        await self._store.async_save(self._wanted())
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
