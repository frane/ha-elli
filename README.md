# Elli Charger for Home Assistant

**English** | [Deutsch](README.de.md)

Control your **Elli** wallbox from Home Assistant, locally, without the cloud. The Elli app keeps working.

[![Open your Home Assistant instance and open this repository in HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=frane&repository=ha-elli&category=integration)

## Which wallbox?

| Your wallbox | Connection | What you get |
|---|---|---|
| **Elli Charger 2**, with "2" in the name (also the Volkswagen, Škoda and CUPRA versions) | **Modbus** | Switch charging on/off, set the current (6–16 A), power, energy, vehicle status |
| **First generation** (Elli Charger Connect / Pro, VW ID. Charger, Škoda iV Charger, CUPRA) | **EEBUS** | Power limit and pause, power, vehicle status |

The first generation has no Modbus. EEBUS also works on the Elli Charger 2, but offers less: use Modbus there.

Coming from [ha-elli-2-modbus](https://github.com/frane/ha-elli-2-modbus)? Remove it first, then set up this one.

## Installation

1. In Home Assistant: **HACS** → search **Elli Charger** → **Download**.
2. Restart Home Assistant.

<details><summary>Without HACS</summary>

Copy `custom_components/elli` into the `custom_components` folder of your Home Assistant configuration and restart.
</details>

## Setup: Elli Charger 2 (Modbus)

**On the wallbox** (once). You need the access data card that came with it.

1. Open `https://<IP of the wallbox>` in a browser (accept the certificate warning) and log in as **Service User**.
2. **Software update:** firmware **R03.004.045.121** or newer.
3. **Connections → Modbus server:** on.
4. **Charging management → Charging settings → PV surplus charging:** off, so the wallbox does not work against Home Assistant.
5. Give the wallbox a fixed IP address in your router.

**In Home Assistant:** *Settings → Devices & services → Add integration →* **Elli Charger** → **Modbus TCP**, enter the IP. Done.

Then set **Failsafe current** on the device: what the wallbox does if Home Assistant is gone for 15 s. `0` stops charging, `6`–`16` A keeps charging.

Tip: turn on *instant charging* in the Elli app, otherwise every charge needs RFID or app approval. More detail: [enable-modbus.md](https://github.com/frane/elli-2-modbus/blob/main/docs/enable-modbus.md).

## Setup: first generation (EEBUS)

1. Home Assistant finds the wallbox by itself: *Settings → Devices & services*, under **Discovered** → **Add**. If not: *Add integration →* **Elli Charger** → **EEBUS**, with the IP, port `4712` and the SKI of the wallbox (in its web interface under EEBUS).
2. Home Assistant now shows a pairing step. In the wallbox web interface open **Connections → HEMS connection**, select **home-assistant** and pair.
3. Back in Home Assistant, click **Submit**.

The wallbox works with one energy manager only. Remove any other one in **HEMS connection**.

## Entities

**Modbus:** Charging enabled (switch), Charging current (6–16 A), Charging state, Vehicle connected, Charging, Problem, Charging power, Total energy (for the Energy dashboard), current and voltage per phase, Active current limit, PCB temperature.

**EEBUS:** Charging power limit (W, 0 = pause), Power limit (switch), Charging power, Vehicle connected, Charging, current per phase, Energy of the session, EEBUS connected.

First generation:

- The wallbox reports no power, so *Charging power* is calculated from the currents. For kWh, add an *Integral* helper on it.
- Vehicle values appear after a car has been plugged in once.
- Use *Charging* to see if current flows. *Charge state* already says `active` while the car waits for approval.

**PV surplus charging:** an automation that sets *Charging current* (Modbus) or *Charging power limit* (EEBUS) from your grid power.

## Limits

- Maximum 16 A over Modbus, also on 22 kW wallboxes. No phase switching.

## Troubleshooting

| Problem | Fix |
|---|---|
| Modbus: cannot connect | Modbus server on? IP correct? Same network as Home Assistant? |
| Modbus: wrong registers | Update the wallbox firmware |
| Modbus: charging stops by itself | Home Assistant was unreachable, so the failsafe current applied |
| Modbus: current lower than set | The wallbox limits itself (temperature, load management); see *Active current limit* |
| EEBUS: wallbox not found | Same network, no VLAN in between |
| EEBUS: limit is ignored | Restart the wallbox (it still remembers a removed energy manager) |
| EEBUS: no vehicle shown | Unplug and plug in again |
| EEBUS: no connection after a Home Assistant restart | Switch the wallbox off and on at the breaker |
| Anything else | Open an issue and attach the diagnostics: *Devices & services → Elli Charger → ⋮ → Download diagnostics* |

## Development

The protocol code lives in [elli-2-modbus](https://github.com/frane/elli-2-modbus) and [elli-eebus](https://github.com/frane/elli-eebus).

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements_test.txt
pytest
```

*Not affiliated with Elli or Volkswagen Group Charging GmbH.*
