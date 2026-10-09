# Elli Charger for Home Assistant (Modbus, EEBUS)

**English** | [Deutsch](README.de.md)

> Successor of [ha-elli-2-modbus](https://github.com/frane/ha-elli-2-modbus) (Modbus only). To switch: remove the old integration, then install this one and set it up again. Don't run both against the same wallbox.

Local Home Assistant integration for **Elli** wallboxes of both generations, over **Modbus TCP** or **EEBUS**. No cloud, and the Elli app keeps working.

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz/)
[![Open your Home Assistant instance and open this repository in HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=frane&repository=ha-elli&category=integration)

The protocol code lives in the libraries [elli-2-modbus](https://github.com/frane/elli-2-modbus) and [elli-eebus](https://github.com/frane/elli-eebus) (on [pyeebus](https://github.com/frane/pyeebus)). Home Assistant installs them automatically.

## Which connection?

| Wallbox | Use | Why |
|---|---|---|
| **Elli Charger 2** (Connect 2, Pro 2, Pro 2 Eichrecht; Volkswagen ID. Charger Connect 2 / Pro 2; Škoda Charger Connect 2 / Pro 2; CUPRA Charger 2 / Pro 2), firmware R03.004.045.121 or newer | **Modbus TCP** | more values (state, vehicle, currents, voltages, energy) and direct control (current 6–16 A, on/off) |
| **First generation** (Elli Charger Connect / Pro and their Volkswagen, Škoda, CUPRA versions) | **EEBUS** | they have no Modbus server |
| Elli Charger 2 where Modbus is not an option | EEBUS | works, but only power limit, total power and failsafe |

**Rule of thumb: if your wallbox has Modbus, use Modbus.** EEBUS on the Elli Charger 2 offers much less, and the wallbox accepts only one EEBUS energy manager in a sensible way.

**Energy manager on EEBUS too?** If an energy manager such as Solar Manager already controls the wallbox over EEBUS, use Modbus for Home Assistant, or put [elli-eebus-proxy](https://github.com/frane/elli-eebus-proxy) in between and connect Home Assistant to the proxy.

## Installation (HACS)

1. In Home Assistant, open **HACS** and click **⋮ (top right) → Custom repositories**. You can also use the "Open in HACS" button above.
2. Repository: `https://github.com/frane/ha-elli`, Type: **Integration** → **Add**.
3. Search for **Elli Charger** in HACS → **Download**.
4. **Restart Home Assistant** (*Settings → System → Restart*).

<details><summary>Without HACS</summary>

Copy `custom_components/elli` into the `custom_components` folder of your Home Assistant configuration and restart.
</details>

## Setup with Modbus TCP (Elli Charger 2)

### 1. Enable Modbus on the wallbox

You need the **card with the access data** that came with the wallbox. The wallbox web interface is available in English and German; the German labels are given in brackets.

1. **Open the charger configuration** in a browser:
   - on your home network: `https://<IP or hostname of the wallbox>` (the hostname is on the card, the IP is in your router), or
   - through the wallbox hotspot: connect to the wallbox Wi-Fi (SSID and password from the card) and open `https://10.0.2.1`.

   The browser warns about the certificate. Click **Advanced** (*Erweitert*) and continue.
2. **Log in as Service User** with the service user password from the card.
3. **Check the firmware** under **Software update** (*Software-Update*). It must be **R03.004.045.121 or newer**; update first if it is older.
4. **Turn on the Modbus server:** **Connections → Modbus server** (*Verbindungen → Modbus-Server*) → **on**. Port 502, unit ID 1.
5. **Give the wallbox a fixed IP address:** a DHCP reservation in your router, or a static IP under **Connections → Ethernet**. Home Assistant must be on the same local network (not via LTE).
6. **Turn off the wallbox's own PV surplus charging**, so it does not regulate against Home Assistant: **Charging management → Charging settings → PV surplus charging → off** (*Ladeverwaltung → Ladeeinstellungen → PV-Laden aus*).
7. For fully automatic charging, enable instant charging (charging without authentication) in the Elli app. Otherwise a session may still need RFID or app authorization.

Optional check from any computer: `pip install elli-2-modbus && elli-2-modbus status <ip>`. More details: [enable-modbus.md](https://github.com/frane/elli-2-modbus/blob/main/docs/enable-modbus.md).

### 2. Add the wallbox

1. *Settings → Devices & services → Add integration →* **Elli Charger** → **Modbus TCP**.
2. Enter a name, the **IP address** of the wallbox, port `502` and Modbus ID `1`.
3. Done. The wallbox shows up as a device with the entities below.

Later changes: *Configure* sets the polling interval (default 5 s). *Reconfigure* changes the IP address without losing the entities.

### 3. Set the failsafe behaviour

Open the device and set **Failsafe current**. This is what the wallbox does when Home Assistant stops talking to it for longer than the **Watchdog timeout** (default 15 s):

- `0` = stop charging (safe for PV-only charging)
- `6`–`16` A = keep charging at that current

Keep the polling interval well below the watchdog timeout.

## Setup with EEBUS (first generation, or Elli Charger 2 without Modbus)

1. **Add the wallbox:** Home Assistant finds it on the network and offers it under *Settings → Devices & services* (*Discovered*). Otherwise: *Add integration →* **Elli Charger** → **EEBUS**, and enter the IP address, port `4711` and the wallbox's SKI (shown in its web interface under the EEBUS settings).
2. **Pair:** Home Assistant shows its own SKI. In the wallbox web interface, open **Connections → HEMS connection** (*EEBUS-Energiemanager*), select **home-assistant** under **Found EEBUS devices** and pair. Remove an energy manager you no longer use there.
3. Click **Submit** in Home Assistant. The wallbox connects within a few seconds.
4. **Failsafe:** set *Failsafe power* and *Failsafe duration* on the device. That is what the wallbox does when Home Assistant is gone (default 22 kW = no limit).

Home Assistant keeps its EEBUS certificate in `.storage/elli/`. Keep it: a new certificate means pairing again.

## Entities

### Modbus

| Entity | Type |
|---|---|
| Charging enabled | switch (off = wallbox blocks charging) |
| Charging current | number, 6–16 A in 0.1 A steps, applied while charging is enabled |
| Charging state | sensor (A1 … F) |
| Vehicle connected, Charging, Problem | binary sensors |
| Charging power, Total energy (Energy dashboard), Energy since power on | sensors |
| Active current limit | sensor (can be below the target because of internal limits) |
| Current and voltage L1–L3, PCB temperature | sensors |
| Failsafe current, Watchdog timeout | configuration |

For PV surplus charging, write an automation that sets *Charging current* and *Charging enabled* from your grid power. Any grid power sensor works: a smart meter, your inverter or your energy manager's integration.

### EEBUS

| Entity | Type |
|---|---|
| Charging power limit | number, W (0 = pause) |
| Power limit | switch (on = limit applies) |
| Charging power, Active power limit, Operating state | sensors |
| Problem, EEBUS connected | binary sensors |
| Failsafe power, Failsafe duration | configuration |
| Vehicle connected, currents L1–L3, energy of the session | only if the wallbox reports the vehicle (first generation) |

## Firmware limits

- Modbus: maximum 16 A, also on 22 kW variants (32 A announced by Elli); no phase switching
- EEBUS: the Elli firmware ignores limits with a duration, lifts limits only with 0 W, and pauses only if the energy manager offers the EV charging services. [elli-eebus](https://github.com/frane/elli-eebus#elli-firmware-bugs-and-how-elli-eebus-handles-them) handles all of this.

## Troubleshooting

| Problem | Fix |
|---|---|
| Modbus: "Cannot connect" during setup | Is the Modbus server on? Is the IP correct? Are Home Assistant and the wallbox on the same network? |
| Modbus: "Wallbox answers, but not with the expected registers" | Firmware older than R03.004.045.121, or wrong Modbus ID |
| Modbus: charging stops by itself after a while | Watchdog: Home Assistant was unreachable longer than the watchdog timeout, so the failsafe current applies |
| Modbus: current is lower than set | The wallbox's internal limits (temperature, load management, §14a) have priority; see *Active current limit* |
| EEBUS: wallbox not found / home-assistant not listed in the wallbox | Same network (no VLAN in between)? mDNS must pass |
| EEBUS: limit is not applied, log says "Adding binding failed" | The wallbox still holds the binding of a removed energy manager: restart the wallbox |

## Development

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements_test.txt   # or: pip install -e ../elli-2-modbus -e ../pyeebus -e ../elli-eebus
pytest
```

The tests run a real Home Assistant test instance against the wallbox simulator from `elli-2-modbus`.

*Not affiliated with Elli or Volkswagen Group Charging GmbH.*
