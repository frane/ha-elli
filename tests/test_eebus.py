"""EEBUS connection against the simulated Elli Charger 2 from elli-eebus."""

from __future__ import annotations

import asyncio
from ipaddress import ip_address
from unittest.mock import patch

from ellieebus.simulator import SimulatedElli
from pyeebus.ship import Identity
import pytest

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from custom_components.elli.const import (
    CONF_CONNECTION,
    CONF_SKI,
    CONNECTION_EEBUS,
    DOMAIN,
)
from custom_components.elli.eebus import state_dir


@pytest.fixture(autouse=True)
def no_zeroconf():
    # no multicast in tests: do not announce, connect directly
    with patch("custom_components.elli.eebus.async_get_zeroconf", return_value=None):
        yield


@pytest.fixture
async def elli(socket_enabled):
    sim = SimulatedElli(Identity.create("elli"), port=0, announce=False, discover=False, host="127.0.0.1")
    await sim.start()
    yield sim
    await sim.stop()


def _state(hass, entity_id):
    st = hass.states.get(entity_id)
    assert st is not None, f"{entity_id} missing; have {hass.states.async_entity_ids()}"
    return st.state


async def _wait(condition, timeout=10.0):
    for _ in range(int(timeout / 0.05)):
        if condition():
            return
        await asyncio.sleep(0.05)
    raise AssertionError("condition not met in time")


def _trust_us(hass, sim: SimulatedElli, our_ski: str) -> None:
    """What pairing in the wallbox UI does (the simulator also needs our certificate)."""
    cert = (state_dir(hass, sim.ski) / "cert.pem").read_bytes()
    sim.service.trust(our_ski, cert)


async def _pair(hass, elli: SimulatedElli, result) -> dict:
    assert result["type"] is FlowResultType.FORM and result["step_id"] == "pair"
    _trust_us(hass, elli, result["description_placeholders"]["our_ski"])
    return await hass.config_entries.flow.async_configure(result["flow_id"], {})


async def test_eebus_setup_and_control(hass, elli):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": "eebus"})
    assert result["step_id"] == "eebus"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_NAME: "Elli Wallbox", CONF_HOST: "127.0.0.1", CONF_PORT: elli.service.node.port, CONF_SKI: "nope"},
    )
    assert result["errors"] == {CONF_SKI: "invalid_ski"}
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_NAME: "Elli Wallbox", CONF_HOST: "127.0.0.1", CONF_PORT: elli.service.node.port, CONF_SKI: elli.ski},
    )
    result = await _pair(hass, elli, result)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_CONNECTION: CONNECTION_EEBUS, CONF_HOST: "127.0.0.1",
                              CONF_PORT: elli.service.node.port, CONF_SKI: elli.ski}
    entry = result["result"]
    await hass.async_block_till_done()

    await _wait(lambda: hass.states.get("number.elli_wallbox_failsafe_power") is not None
                and _state(hass, "number.elli_wallbox_failsafe_power") == "22000")
    assert _state(hass, "binary_sensor.elli_wallbox_eebus_connected") == "on"
    assert float(_state(hass, "sensor.elli_wallbox_charging_power")) == 0
    assert _state(hass, "switch.elli_wallbox_power_limit") == "off"
    assert _state(hass, "sensor.elli_wallbox_operating_state") == "normalOperation"
    assert _state(hass, "binary_sensor.elli_wallbox_problem") == "off"
    assert float(_state(hass, "number.elli_wallbox_failsafe_duration")) == 2
    limit = hass.states.get("number.elli_wallbox_charging_power_limit")
    assert limit.attributes["min"] == 0 and limit.attributes["max"] == 11040
    # the Elli Charger 2 reports neither the car nor currents: no such entities
    assert hass.states.get("binary_sensor.elli_wallbox_vehicle_connected") is None
    assert hass.states.get("sensor.elli_wallbox_current_l1") is None

    # target first (nothing written), then switch the limit on
    await hass.services.async_call("number", "set_value",
                                   {"entity_id": "number.elli_wallbox_charging_power_limit", "value": 5000},
                                   blocking=True)
    assert elli.limit == (0, False)
    await hass.services.async_call("switch", "turn_on", {"entity_id": "switch.elli_wallbox_power_limit"},
                                   blocking=True)
    assert elli.limit == (5000, True)
    await _wait(lambda: _state(hass, "sensor.elli_wallbox_active_power_limit") == "5000")
    assert _state(hass, "switch.elli_wallbox_power_limit") == "on"

    elli.set_demand(11000)  # a car draws more than the limit
    await _wait(lambda: _state(hass, "sensor.elli_wallbox_charging_power") == "5000")

    await hass.services.async_call("number", "set_value",
                                   {"entity_id": "number.elli_wallbox_charging_power_limit", "value": 6000},
                                   blocking=True)
    assert elli.limit == (6000, True)
    await hass.services.async_call("switch", "turn_off", {"entity_id": "switch.elli_wallbox_power_limit"},
                                   blocking=True)
    assert elli.limit == (0, False)
    await _wait(lambda: _state(hass, "sensor.elli_wallbox_charging_power") == "11000")

    await hass.services.async_call("number", "set_value",
                                   {"entity_id": "number.elli_wallbox_failsafe_power", "value": 4200},
                                   blocking=True)
    await hass.services.async_call("number", "set_value",
                                   {"entity_id": "number.elli_wallbox_failsafe_duration", "value": 3},
                                   blocking=True)
    await _wait(lambda: _state(hass, "number.elli_wallbox_failsafe_power") == "4200"
                and _state(hass, "number.elli_wallbox_failsafe_duration") == "3.0")

    # no options for EEBUS, reconfigure keeps the SKI
    assert not config_entries.HANDLERS[DOMAIN].async_supports_options_flow(entry)
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_eebus_already_configured_and_zeroconf(hass, elli):
    info = ZeroconfServiceInfo(
        ip_address=ip_address("127.0.0.1"), ip_addresses=[ip_address("127.0.0.1")], hostname="wallbox.local.",
        name="Elli-Wallbox._ship._tcp.local.", port=elli.service.node.port, type="_ship._tcp.local.",
        properties={"txtvers": "1", "id": "Elli-Wallbox-00099999", "ski": elli.ski, "brand": "Elli",
                    "model": "EVSE", "type": "Wallbox", "register": "false", "path": "/ship/"},
    )
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_ZEROCONF},
                                                       data=info)
    assert result["type"] is FlowResultType.FORM and result["step_id"] == "zeroconf_confirm"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_NAME: "Garage"})
    result = await _pair(hass, elli, result)
    assert result["type"] is FlowResultType.CREATE_ENTRY and result["title"] == "Garage"
    entry = result["result"]
    await hass.async_block_till_done()

    # discovered again (e.g. new IP): no new flow, host updated
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_ZEROCONF},
                                                       data=info)
    assert result["type"] is FlowResultType.ABORT and result["reason"] == "already_configured"
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_eebus_pairing_not_done(hass, elli):
    with patch("custom_components.elli.config_flow.EEBUS_PAIR_TIMEOUT", 1):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": "eebus"})
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_NAME: "x", CONF_HOST: "127.0.0.1", CONF_PORT: elli.service.node.port, CONF_SKI: elli.ski},
        )
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {})  # not paired
        assert result["type"] is FlowResultType.FORM and result["errors"] == {"base": "not_paired"}
        hass.config_entries.flow.async_abort(result["flow_id"])
        await hass.async_block_till_done()
