"""Constants for the Elli Charger integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "elli"

DEFAULT_NAME: Final = "Elli Wallbox"
DEFAULT_PORT: Final = 502
DEFAULT_UNIT_ID: Final = 1
DEFAULT_SCAN_INTERVAL: Final = 5  # s, well below the 15 s default watchdog
MIN_SCAN_INTERVAL: Final = 2
MAX_SCAN_INTERVAL: Final = 60

CONF_UNIT_ID: Final = "unit_id"

MANUFACTURER: Final = "Elli"
MODEL: Final = "Charger 2"
WATCHDOG_MAX_SECONDS: Final = 65

# EEBUS
CONF_CONNECTION: Final = "connection"
CONNECTION_MODBUS: Final = "modbus"
CONNECTION_EEBUS: Final = "eebus"
CONF_SKI: Final = "ski"
DEFAULT_EEBUS_PORT: Final = 4711
EEBUS_NAME: Final = "home-assistant"  # how we appear in the wallbox's list of EEBUS devices
EEBUS_PAIR_TIMEOUT: Final = 30  # s to wait for the wallbox after the user paired
EEBUS_SETUP_WAIT: Final = 15  # s to wait for the first data when the entry is set up
