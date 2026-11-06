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


async def test_eebus_first_generation(hass, socket_enabled):
    """ha-elli #3: a first-generation wallbox, set up while no car is plugged in."""
    from pyeebus.simulator import SimulatedEVSE
    from pyeebus.spine import Role

    from custom_components.elli.diagnostics import async_get_config_entry_diagnostics

    evse = SimulatedEVSE(Identity.create("gen1"), port=0, announce=False, discover=False, host="127.0.0.1")
    await evse.start()
    try:
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": "eebus"})
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_NAME: "Elli Wallbox", CONF_HOST: "127.0.0.1", CONF_PORT: evse.service.node.port,
             CONF_SKI: evse.service.ski},
        )
        assert result["step_id"] == "pair"
        cert = (state_dir(hass, evse.service.ski) / "cert.pem").read_bytes()
        evse.service.trust(result["description_placeholders"]["our_ski"], cert)
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
        entry = result["result"]
        await hass.async_block_till_done()
        await _wait(lambda: hass.states.get("binary_sensor.elli_wallbox_vehicle_connected") is not None)
        assert _state(hass, "binary_sensor.elli_wallbox_vehicle_connected") == "off"
        assert _state(hass, "sensor.elli_wallbox_charge_state") == "unplugged"
        # no failsafe limit on the first generation
        assert hass.states.get("number.elli_wallbox_failsafe_power") is None

        # The car comes later. Like the real wallbox, it starts at 6 A and reports no power.
        evse.plug_in()
        meas = evse.ev.feature("Measurement", Role.SERVER)
        descs = meas.data["measurementDescriptionListData"]["measurementDescriptionData"]
        meas.data["measurementDescriptionListData"]["measurementDescriptionData"] = [
            d for d in descs if d["scopeType"] != "acPower"]
        plain = evse._measurements
        evse._measurements = lambda c, e: [m for m in plain(c, e) if not 4 <= m["measurementId"] <= 6]
        meas.data["measurementListData"] = {"measurementData": evse._measurements(0.0, 0.0)}
        for item in evse.ev.feature("LoadControl", Role.SERVER).data["loadControlLimitListData"][
                "loadControlLimitData"]:
            if item["limitId"] <= 3:
                item.update(isLimitActive=True, value={"number": 6, "scale": 0})
        evse.limits["obligation"] = [6, 6, 6]

        await _wait(lambda: evse.limits["obligation"] == [16, 16, 16])  # unrestricted
        await _wait(lambda: hass.states.get("binary_sensor.elli_wallbox_charging") is not None)
        assert _state(hass, "binary_sensor.elli_wallbox_charging") == "off", "plugged in, no current yet"
        evse.set_charging(10, 1200)
        await _wait(lambda: hass.states.get("sensor.elli_wallbox_energy") is not None
                    and _state(hass, "sensor.elli_wallbox_charging_power") == "6900.0")
        assert _state(hass, "binary_sensor.elli_wallbox_vehicle_connected") == "on"
        assert float(_state(hass, "sensor.elli_wallbox_current_l1")) == 10
        assert _state(hass, "binary_sensor.elli_wallbox_charging") == "on"

        # the limit switch stays on while a limit is written
        await hass.services.async_call("number", "set_value",
                                       {"entity_id": "number.elli_wallbox_charging_power_limit", "value": 11000},
                                       blocking=True)
        await hass.services.async_call("switch", "turn_on", {"entity_id": "switch.elli_wallbox_power_limit"},
                                       blocking=True)
        assert evse.limits["obligation"] == [pytest.approx(15.9, abs=0.1)] * 3
        await _wait(lambda: _state(hass, "switch.elli_wallbox_power_limit") == "on")
        await asyncio.sleep(0.3)
        assert _state(hass, "switch.elli_wallbox_power_limit") == "on"

        diagnostics = await async_get_config_entry_diagnostics(hass, entry)
        assert diagnostics["status"]["profile"] == "opev"
        assert {e["type"] for e in diagnostics["eebus"]["entities"]} >= {"EVSE", "EV"}
        assert diagnostics["entry"][CONF_SKI] == "**REDACTED**"

        # failsafe entities left over from 0.1.1 are removed
        from homeassistant.helpers import entity_registry as er
        registry = er.async_get(hass)
        stale = registry.async_get_or_create("number", DOMAIN, f"{entry.unique_id}_failsafe_power",
                                             config_entry=entry)
        assert await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()
        assert registry.async_get(stale.entity_id) is None

        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()
    finally:
        await evse.stop()
