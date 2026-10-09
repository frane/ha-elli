"""Config flow."""

from __future__ import annotations

import logging
from typing import Any

from elli2modbus import ElliCharger, ModbusConnectionError, ModbusError
from ellieebus import ElliEebus
from pyeebus.ship import is_ski_valid, normalize_ski
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from .const import (
    CONF_CONNECTION,
    CONF_SKI,
    CONF_UNIT_ID,
    CONNECTION_EEBUS,
    CONNECTION_MODBUS,
    DEFAULT_EEBUS_PORT,
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
from .eebus import async_create_client

_LOGGER = logging.getLogger(__name__)


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
        self._client: ElliEebus | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        return self.async_show_menu(step_id="user", menu_options=["modbus", "eebus"])

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
        await self.async_set_unique_id(ski)
        self._abort_if_unique_id_configured(updates={CONF_HOST: discovery_info.host})
        self._eebus = {
            CONF_NAME: DEFAULT_NAME,
            CONF_HOST: discovery_info.host,
            CONF_PORT: discovery_info.port or DEFAULT_EEBUS_PORT,
            CONF_SKI: ski,
        }
        self.context["title_placeholders"] = {"name": f"{props.get('brand', 'Elli')} (EEBUS)"}
        return await self.async_step_zeroconf_confirm()

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
        if user_input is not None:
            try:
                await self._client.wait_connected(EEBUS_PAIR_TIMEOUT)
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
                "our_ski": self._client.our_ski,
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
