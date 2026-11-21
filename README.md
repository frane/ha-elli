# Elli Charger for Home Assistant

**English** | [Deutsch](README.de.md)

Control your **Elli** wallbox from Home Assistant, locally, without the cloud. The Elli app keeps working. Supports both wallbox generations, over **Modbus** or **EEBUS**.

[![Open your Home Assistant instance and open this repository in HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=frane&repository=ha-elli&category=integration)

## What is available where

The **Elli Charger 2** (with "2" in the name, also the Volkswagen, Škoda and CUPRA versions) speaks Modbus and EEBUS. The **first generation** (Elli Charger Connect / Pro, VW ID. Charger, Škoda iV Charger, CUPRA) speaks only EEBUS.

| | Charger 2 · Modbus | Charger 2 · EEBUS | 1st gen · EEBUS |
|---|---|---|---|
| Start / stop charging | ✅ switch | ✅ limit 0 W | ✅ limit 0 W |
| Set charging speed | ✅ current, 6–16 A | ✅ power limit, W | ✅ power limit, W |
| Charging power | ✅ measured | ✅ measured | ✅ calculated from the currents |
| Energy (kWh) | ✅ total and since power on | – | – (*Integral* helper) |
| Current per phase | ✅ | – | ✅ |
| Voltage per phase | ✅ | – | – |
| Vehicle connected, charging | ✅ | – | ✅ |
| Charging state | ✅ A1 … F | – | ✅ active, paused, finished … |
| Problem | ✅ | ✅ | ✅ |
| Limit the wallbox applies | ✅ current | ✅ power | ✅ power |
| PCB temperature | ✅ | – | – |
| If Home Assistant is gone | failsafe current | failsafe power and duration | – |
| Updates | every 5 s (adjustable) | as soon as something changes | as soon as something changes |
| On the wallbox | turn on the Modbus server | pair | pair |

Every entity and value: [docs/features.md](https://github.com/frane/ha-elli/blob/main/docs/features.md).

## Installation

1. In Home Assistant: **HACS** → search **Elli Charger** → **Download**.
2. Restart Home Assistant.

Coming from [ha-elli-2-modbus](https://github.com/frane/ha-elli-2-modbus)? Remove it first, then set up this one.

<details><summary>Without HACS</summary>

Copy `custom_components/elli` into the `custom_components` folder of your Home Assistant configuration and restart.
</details>

## Setup with Modbus (Elli Charger 2)

**On the wallbox** (once). You need the access data card that came with it.

1. Open `https://<IP of the wallbox>` in a browser (accept the certificate warning) and log in as **Service User**.
2. **Software update:** firmware **R03.004.045.121** or newer.
3. **Connections → Modbus server:** on.
4. **Charging management → Charging settings → PV surplus charging:** off, if Home Assistant should control the current.
5. Give the wallbox a fixed IP address in your router.

**In Home Assistant:** *Settings → Devices & services → Add integration →* **Elli Charger** → **Modbus TCP**, enter the IP.

Then set **Failsafe current** on the device: `0` stops charging when Home Assistant is gone, `6`–`16` A keeps charging.

Details: [docs/modbus.md](https://github.com/frane/ha-elli/blob/main/docs/modbus.md).

## Setup with EEBUS (both generations)

1. Home Assistant finds the wallbox by itself: *Settings → Devices & services*, under **Discovered** → **Add**.
2. Home Assistant shows a pairing step. In the wallbox web interface open **Connections → HEMS connection**, select **home-assistant** and pair.
3. Back in Home Assistant, click **Submit**.

The wallbox works with one EEBUS energy manager at a time. Remove other ones under **HEMS connection**.

Details, manual setup and first-generation notes: [docs/eebus.md](https://github.com/frane/ha-elli/blob/main/docs/eebus.md).

## Help

Troubleshooting for [Modbus](https://github.com/frane/ha-elli/blob/main/docs/modbus.md#troubleshooting) and [EEBUS](https://github.com/frane/ha-elli/blob/main/docs/eebus.md#troubleshooting). For an issue, attach the diagnostics: *Devices & services → Elli Charger → ⋮ → Download diagnostics* (without serial numbers).

## Development

The protocol code lives in [elli-2-modbus](https://github.com/frane/elli-2-modbus) and [elli-eebus](https://github.com/frane/elli-eebus).

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements_test.txt
pytest
```

*Not affiliated with Elli or Volkswagen Group Charging GmbH.*
