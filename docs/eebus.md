# EEBUS (Elli Charger 2 and first generation)

**English** | [Deutsch](eebus.de.md)

## Setup

1. **Add the wallbox:** Home Assistant finds it on the network (mDNS) and offers it under *Settings → Devices & services* → **Discovered**.

   Manually: *Add integration →* **Elli Charger** → **EEBUS**, with the IP address, the port and the SKI of the wallbox (in its web interface under the EEBUS settings). Port: `4711` on the Elli Charger 2, `4712` on the first generation (ID. Charger, Škoda iV Charger).
2. **Pair:** Home Assistant shows its own SKI. In the wallbox web interface open **Connections → HEMS connection** (*EEBUS-Energiemanager*), select **home-assistant** under **Found EEBUS devices** and pair.
3. Click **Submit** in Home Assistant. The wallbox connects within a few seconds.
4. **Failsafe** (Elli Charger 2 only): set *Failsafe power* and *Failsafe duration* on the device. That is what the wallbox does when Home Assistant is gone (default 22 kW = no limit).

The wallbox works with one EEBUS energy manager at a time. Remove other ones under **HEMS connection**.

Home Assistant keeps its EEBUS certificate in `.storage/elli/`. Keep it: a new certificate means pairing again.

## What the wallbox offers over EEBUS

| | Elli Charger 2 | First generation |
|---|---|---|
| Use cases | power limit (LPC), power measurement (MPC), state (EVSECC); while a car is plugged in also vehicle current limits (OPEV), vehicle measurements (EVCEM), vehicle state (EVCC) | vehicle current limits (OPEV), vehicle measurements (EVCEM), vehicle and wallbox state (EVCC, EVSECC) |
| Measurements | total power; while a car is plugged in also current and power per phase and the charged energy | current per phase, no power, no energy |
| Vehicle | reported while plugged in | reported while plugged in |
| Failsafe | power and duration | none |

## First generation

- **Power:** calculated from the currents × 230 V, because the wallbox reports none. Home Assistant also calculates *Energy (calculated)* in kWh from it.
- **Limit:** set as current per phase on the vehicle. The wallbox resets it on every plug-in and then starts at 6 A. The integration writes the limit again each time (the maximum while *Power limit* is off).
- **Charge state** is already `active` while the car waits for authorization. *Charging* shows whether current flows.
- **Vehicle:** only reported for a car that was plugged in while EEBUS was connected.

## Firmware bugs the integration handles

- The Elli Charger 2 ignores limits with a duration.
- It lifts a limit only when it is written as inactive with 0 W.
- It pauses only if the energy manager also offers the EV charging services.
- First generation: right after plug-in it reports empty permitted values; they are treated as unknown, not as 0 A.

Details: [elli-eebus](https://github.com/frane/elli-eebus#elli-firmware-bugs-and-how-elli-eebus-handles-them).

## Troubleshooting

| Problem | Fix |
|---|---|
| Wallbox not found, or home-assistant not listed in the wallbox | Same network, no VLAN in between? mDNS must pass |
| Limit not applied, log says "Adding binding failed" | The wallbox still holds the binding of a removed energy manager: restart the wallbox |
| First generation: port stays closed after a Home Assistant restart | Firmware bug: switch the wallbox off and on at the breaker |
| First generation: no vehicle although one is charging | Unplug and plug in again |
| Anything else | Attach the diagnostics to the issue: *Devices & services → Elli Charger → ⋮ → Download diagnostics*. They contain what the wallbox reports over EEBUS, without serial numbers and SKIs |
