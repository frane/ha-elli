"""Config flow."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from elli2modbus import ElliCharger, ModbusConnectionError, ModbusError
from ellieebus import ElliEebus
from pyeebus.ship import is_ski_valid, normalize_ski
from pyeebus.ship.mdns import ShipMdns, ShipService
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import selector
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from .const import (
    CONF_CONNECTION,
    CONF_SKI,
    CONF_UNIT_ID,
    CONNECTION_EEBUS,
    CONNECTION_MODBUS,
    DEFAULT_EEBUS_PORT,
    FIRST_GEN_EEBUS_PORT,
    EEBUS_NAME,
    EEBUS_PAIR_TIMEOUT,
    DEFAULT_NAME,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_UNIT_ID,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)
from .coordinator import ElliConfigEntry
from .eebus import async_create_client, async_get_zeroconf

_LOGGER = logging.getLogger(__name__)

DISCOVERY_SECONDS = 3
MAX_FOUND = 5  # one menu entry (async_step_found_N) each


def _connection_schema(defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_HOST, default=defaults.get(CONF_HOST, vol.UNDEFINED)): str,
            vol.Required(CONF_PORT, default=defaults.get(CONF_PORT, DEFAULT_PORT)): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=65535)
            ),
            vol.Required(
                CONF_UNIT_ID, default=defaults.get(CONF_UNIT_ID, DEFAULT_UNIT_ID)
            ): vol.All(vol.Coerce(int), vol.Range(min=0, max=255)),
        }
    )


async def _validate(data: dict[str, Any]) -> str | None:
    """Return an error key, or None if the wallbox answered."""
    charger = ElliCharger(data[CONF_HOST], data[CONF_PORT], data[CONF_UNIT_ID])
    try:
        await charger.read_info()
    except ModbusConnectionError:
        return "cannot_connect"
    except ModbusError:
        return "modbus_error"
    except Exception:  # noqa: BLE001
        _LOGGER.exception("Unexpected error validating wallbox")
        return "unknown"
    finally:
        await charger.close()
    return None


async def _async_discover(hass: HomeAssistant) -> list[ShipService]:
    """Elli wallboxes announcing EEBUS (SHIP) on the network."""
    try:
        zc = await async_get_zeroconf(hass)
        if zc is None:
            return []
        mdns = ShipMdns(zeroconf=zc)
        try:
            await mdns.browse()
            await asyncio.sleep(DISCOVERY_SECONDS)
        finally:
            await mdns.close()
    except Exception:  # noqa: BLE001
        _LOGGER.debug("EEBUS discovery failed", exc_info=True)
        return []
    return [s for s in mdns.services.values() if s.brand.lower().startswith("elli")]


def _service_host(service: ShipService) -> str:
    return service.addresses[0] if service.addresses else service.host


def _unique_id(data: dict[str, Any]) -> str:
    return f"{data[CONF_HOST].strip().lower()}:{data[CONF_PORT]}:{data[CONF_UNIT_ID]}"


def _eebus_schema(defaults: dict[str, Any], with_ski: bool = True) -> vol.Schema:
    schema = {
        vol.Required(CONF_HOST, default=defaults.get(CONF_HOST, vol.UNDEFINED)): str,
        vol.Required(CONF_PORT, default=defaults.get(CONF_PORT, DEFAULT_EEBUS_PORT)): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=65535)
        ),
    }
    if with_ski:
        schema[vol.Required(CONF_SKI, default=defaults.get(CONF_SKI, vol.UNDEFINED))] = str
    return vol.Schema(schema)


class ElliConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._eebus: dict[str, Any] = {}
        self._modbus: dict[str, Any] = {}
        self._found: list[ShipService] = []
        self._modbus_ok = False
        self._client: ElliEebus | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Wallboxes found on the network first, manual setup as a fallback."""
        configured = {e.unique_id for e in self._async_current_entries()} | {
            str(e.data.get(CONF_HOST, "")).strip().lower() for e in self._async_current_entries()
        }
        self._found = [
            s for s in await _async_discover(self.hass)
            if s.ski not in configured and _service_host(s).lower() not in configured
        ][:MAX_FOUND]
        if not self._found:
            return await self.async_step_manual()
        manual = "Manuell einrichten" if self.hass.config.language.startswith("de") else "Set up manually"
        options = {f"found_{i}": f"{s.brand.capitalize()} {s.model} ({_service_host(s)})".replace("  ", " ")
                   for i, s in enumerate(self._found)}
        return self.async_show_menu(step_id="user", menu_options={**options, "manual": manual})

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        return self.async_show_menu(step_id="manual", menu_options=["modbus", "eebus"])

    async def _async_pick(self, index: int) -> ConfigFlowResult:
        s = self._found[index]
        return await self._async_discovered(_service_host(s), s.port, s.ski, s.brand, user=True)

    async def async_step_found_0(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return await self._async_pick(0)

    async def async_step_found_1(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return await self._async_pick(1)

    async def async_step_found_2(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return await self._async_pick(2)

    async def async_step_found_3(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return await self._async_pick(3)

    async def async_step_found_4(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return await self._async_pick(4)

    # --- Modbus ---------------------------------------------------------------

    async def async_step_modbus(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            user_input[CONF_HOST] = user_input[CONF_HOST].strip()
            await self.async_set_unique_id(_unique_id(user_input))
            self._abort_if_unique_id_configured()
            if (error := await _validate(user_input)) is None:
                name = user_input.pop(CONF_NAME, DEFAULT_NAME)
                return self.async_create_entry(
                    title=name, data={CONF_CONNECTION: CONNECTION_MODBUS, **user_input}
                )
            errors["base"] = error

        schema = vol.Schema(
            {vol.Required(CONF_NAME, default=DEFAULT_NAME): str}
        ).extend(_connection_schema(user_input or {}).schema)
        return self.async_show_form(step_id="modbus", data_schema=schema, errors=errors)

    # --- EEBUS ----------------------------------------------------------------

    async def async_step_eebus(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            ski = normalize_ski(user_input[CONF_SKI])
            if not is_ski_valid(ski):
                errors[CONF_SKI] = "invalid_ski"
            else:
                await self.async_set_unique_id(ski)
                self._abort_if_unique_id_configured()
                self._eebus = {
                    CONF_NAME: user_input.get(CONF_NAME, DEFAULT_NAME),
                    CONF_HOST: user_input[CONF_HOST].strip(),
                    CONF_PORT: user_input[CONF_PORT],
                    CONF_SKI: ski,
                }
                return await self.async_step_pair()
        schema = vol.Schema(
            {vol.Required(CONF_NAME, default=DEFAULT_NAME): str}
        ).extend(_eebus_schema(user_input or {}).schema)
        return self.async_show_form(step_id="eebus", data_schema=schema, errors=errors)

    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> ConfigFlowResult:
        props = discovery_info.properties
        ski = normalize_ski(str(props.get("ski", "")))
        if not is_ski_valid(ski):
            return self.async_abort(reason="not_supported")
        return await self._async_discovered(
            discovery_info.host, discovery_info.port, ski, str(props.get("brand", "Elli"))
        )

    async def _async_discovered(
        self, host: str, port: int | None, ski: str, brand: str, user: bool = False
    ) -> ConfigFlowResult:
        await self.async_set_unique_id(ski, raise_on_progress=not user)
        self._abort_if_unique_id_configured(updates={CONF_HOST: host})
        # The same wallbox may already be set up over Modbus.
        if any(str(e.data.get(CONF_HOST, "")).strip().lower() == host.lower() for e in self._async_current_entries()):
            return self.async_abort(reason="already_configured")
        self._eebus = {
            CONF_NAME: DEFAULT_NAME,
            CONF_HOST: host,
            CONF_PORT: port or DEFAULT_EEBUS_PORT,
            CONF_SKI: ski,
        }
        self.context["title_placeholders"] = {"name": brand.capitalize()}
        # One Modbus probe per discovered wallbox. An Elli Charger 2 offers both connections;
        # the first generation (SHIP port 4712) has no Modbus server.
        self._modbus = {CONF_HOST: host, CONF_PORT: DEFAULT_PORT, CONF_UNIT_ID: DEFAULT_UNIT_ID}
        self._modbus_ok = await _validate(self._modbus) is None
        if self._modbus_ok or port != FIRST_GEN_EEBUS_PORT:
            return await self.async_step_zeroconf_menu()
        return await self.async_step_zeroconf_confirm()

    async def async_step_zeroconf_menu(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        return self.async_show_menu(
            step_id="zeroconf_menu",
            menu_options=["zeroconf_modbus", "zeroconf_confirm"],
            description_placeholders={"host": self._modbus[CONF_HOST]},
        )

    async def async_step_enable_modbus(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Guide the user to turn on the Modbus server, then check again."""
        errors: dict[str, str] = {}
        if user_input is not None:
            if await _validate(self._modbus) is None:
                self._modbus_ok = True
                return await self.async_step_zeroconf_modbus()
            errors["base"] = "modbus_off"
        return self.async_show_form(
            step_id="enable_modbus",
            description_placeholders={"host": self._modbus[CONF_HOST]},
            errors=errors,
        )

    async def async_step_zeroconf_modbus(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if not self._modbus_ok:
            return await self.async_step_enable_modbus()
        errors: dict[str, str] = {}
        if user_input is not None:
            await self.async_set_unique_id(_unique_id(self._modbus), raise_on_progress=False)
            self._abort_if_unique_id_configured()
            if (error := await _validate(self._modbus)) is None:
                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    data={CONF_CONNECTION: CONNECTION_MODBUS, **self._modbus},
                )
            errors["base"] = error
        return self.async_show_form(
            step_id="zeroconf_modbus",
            data_schema=vol.Schema({vol.Required(CONF_NAME, default=DEFAULT_NAME): str}),
            description_placeholders={"host": self._modbus[CONF_HOST]},
            errors=errors,
        )

    async def async_step_zeroconf_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            self._eebus[CONF_NAME] = user_input[CONF_NAME]
            return await self.async_step_pair()
        return self.async_show_form(
            step_id="zeroconf_confirm",
            data_schema=vol.Schema({vol.Required(CONF_NAME, default=DEFAULT_NAME): str}),
            description_placeholders={"host": self._eebus[CONF_HOST]},
        )

    async def async_step_pair(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Run our EEBUS node until the user has paired it in the wallbox."""
        errors: dict[str, str] = {}
        if self._client is None:
            self._client = await async_create_client(
                self.hass, self._eebus[CONF_SKI], self._eebus[CONF_HOST], self._eebus[CONF_PORT]
            )
            await self._client.start()
        # Kept locally: the flow may be removed (and the client stopped) while we wait.
        client = self._client
        if user_input is not None:
            try:
                await client.wait_connected(EEBUS_PAIR_TIMEOUT)
            except TimeoutError:
                errors["base"] = "not_paired"
            else:
                await self._stop_client()
                data = {CONF_CONNECTION: CONNECTION_EEBUS, **self._eebus}
                return self.async_create_entry(title=data.pop(CONF_NAME), data=data)
        return self.async_show_form(
            step_id="pair",
            errors=errors,
            description_placeholders={
                "our_ski": client.our_ski,
                "our_name": EEBUS_NAME,
                "host": self._eebus[CONF_HOST],
            },
        )

    async def _stop_client(self) -> None:
        if self._client is not None:
            client, self._client = self._client, None
            await client.stop()

    @callback
    def async_remove(self) -> None:
        if self._client is not None:
            self.hass.async_create_task(self._stop_client())

    # --- reconfigure / options --------------------------------------------------

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        entry = self._get_reconfigure_entry()
        if entry.data.get(CONF_CONNECTION) == CONNECTION_EEBUS:
            if user_input is not None:
                user_input[CONF_HOST] = user_input[CONF_HOST].strip()
                return self.async_update_reload_and_abort(entry, data_updates=user_input)
            return self.async_show_form(
                step_id="reconfigure",
                data_schema=_eebus_schema(dict(entry.data), with_ski=False),
            )
        errors: dict[str, str] = {}
        if user_input is not None:
            user_input[CONF_HOST] = user_input[CONF_HOST].strip()
            if (error := await _validate(user_input)) is None:
                # Keep the unique id stable so entities survive an IP change.
                return self.async_update_reload_and_abort(entry, data_updates=user_input)
            errors["base"] = error
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_connection_schema(user_input or dict(entry.data)),
            errors=errors,
        )

    @classmethod
    @callback
    def async_supports_options_flow(cls, config_entry: ElliConfigEntry) -> bool:
        return config_entry.data.get(CONF_CONNECTION) != CONNECTION_EEBUS

    @staticmethod
    @callback
    def async_get_options_flow(entry: ElliConfigEntry) -> ElliOptionsFlow:
        return ElliOptionsFlow()


class ElliOptionsFlow(OptionsFlow):
    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(
                data={CONF_SCAN_INTERVAL: int(user_input[CONF_SCAN_INTERVAL])}
            )
        current = self.config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        schema = vol.Schema(
            {
                vol.Required(CONF_SCAN_INTERVAL, default=current): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=MIN_SCAN_INTERVAL,
                        max=MAX_SCAN_INTERVAL,
                        step=1,
                        unit_of_measurement="s",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                )
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
