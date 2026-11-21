"""Finding the wallbox: network scan in the user flow, zeroconf, Modbus offered next to EEBUS."""

from __future__ import annotations

from ipaddress import ip_address
from unittest.mock import patch

from pyeebus.ship.mdns import ShipService

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from custom_components.elli.const import CONF_CONNECTION, CONF_UNIT_ID, CONNECTION_MODBUS, DOMAIN

SKI = "a" * 40


def _service(host: str = "127.0.0.1") -> ShipService:
    return ShipService(name="Elli-Wallbox._ship._tcp.local.", ski=SKI, ship_id="Elli-Wallbox-1",
                       host="wallbox.local", addresses=[host], port=4711, brand="elli", model="Charger 2")


def _zeroconf(host: str = "127.0.0.1") -> ZeroconfServiceInfo:
    return ZeroconfServiceInfo(
        ip_address=ip_address(host), ip_addresses=[ip_address(host)], hostname="wallbox.local.",
        name="Elli-Wallbox._ship._tcp.local.", port=4711, type="_ship._tcp.local.",
        properties={"txtvers": "1", "id": "Elli-Wallbox-1", "ski": SKI, "brand": "elli", "register": "false"},
    )


async def _unload(hass, entry):
    await hass.async_block_till_done()
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_user_flow_offers_found_wallboxes_and_modbus(hass, sim):
    _, port = sim
    with patch("custom_components.elli.config_flow._async_discover", return_value=[_service()]), \
            patch("custom_components.elli.config_flow.DEFAULT_PORT", port):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
        assert result["type"] is FlowResultType.MENU and result["step_id"] == "user"
        assert set(result["menu_options"]) == {"found_0", "manual"}
        assert "127.0.0.1" in result["menu_options"]["found_0"]
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": "found_0"})
        assert result["type"] is FlowResultType.MENU and result["step_id"] == "zeroconf_menu"
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": "zeroconf_modbus"})
        assert result["type"] is FlowResultType.FORM and result["step_id"] == "zeroconf_modbus"
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_NAME: "Garage"})
    assert result["type"] is FlowResultType.CREATE_ENTRY and result["title"] == "Garage"
    assert result["data"] == {CONF_CONNECTION: CONNECTION_MODBUS, CONF_HOST: "127.0.0.1", CONF_PORT: port, CONF_UNIT_ID: 1}
    entry = result["result"]

    # set up already: neither the scan nor zeroconf offer it again
    with patch("custom_components.elli.config_flow._async_discover", return_value=[_service()]):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.MENU and result["step_id"] == "manual"
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_ZEROCONF}, data=_zeroconf())
    assert result["type"] is FlowResultType.ABORT and result["reason"] == "already_configured"
    await _unload(hass, entry)


async def test_manual_setup_when_nothing_is_found(hass):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.MENU and result["step_id"] == "manual"
    assert result["menu_options"] == ["modbus", "eebus"]


async def test_zeroconf_without_modbus_goes_to_eebus(hass, socket_enabled):
    with patch("custom_components.elli.config_flow._validate", return_value="cannot_connect"):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_ZEROCONF}, data=_zeroconf())
    assert result["type"] is FlowResultType.FORM and result["step_id"] == "zeroconf_confirm"


async def test_user_flow_found_wallbox_without_modbus(hass, socket_enabled):
    with patch("custom_components.elli.config_flow._async_discover", return_value=[_service()]), \
            patch("custom_components.elli.config_flow._validate", return_value="cannot_connect"):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": "found_0"})
    assert result["type"] is FlowResultType.FORM and result["step_id"] == "zeroconf_confirm"
