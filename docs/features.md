# Features and entities

**English** | [Deutsch](features.de.md)

M = Elli Charger 2 over Modbus · E2 = Elli Charger 2 over EEBUS · E1 = first generation over EEBUS

## Control

| Entity | Type | Values | M | E2 | E1 |
|---|---|---|---|---|---|
| Charging enabled | switch | off = the wallbox blocks charging | ✅ | | |
| Charging current | number | 6–16 A, 0.1 A steps; applies while *Charging enabled* is on | ✅ | | |
| Charging power limit | number | W, 100 W steps, 0 = pause; applies while *Power limit* is on | | ✅ | ✅ |
| Power limit | switch | on = the wallbox charges with at most *Charging power limit* | | ✅ | ✅ |

## Measurements

| Entity | Type | Values | M | E2 | E1 |
|---|---|---|---|---|---|
| Charging power | sensor | W | ✅ | ✅ | ✅ ¹ |
| Total energy | sensor | kWh, meter reading, for the Energy dashboard | ✅ | | |
| Energy since power on | sensor | kWh | ✅ | | |
| Energy | sensor | kWh, only if the wallbox reports it | | ² | ² |
| Current L1–L3 | sensor | A | ✅ | | ✅ |
| Voltage L1–L3 | sensor | V | ✅ | | |
| PCB temperature | sensor | °C, diagnostic | ✅ | | |

¹ The first generation reports no power. It is calculated from the currents × 230 V. For kWh, add an *Integral* helper on it.
² Created only when the wallbox reports energy. The wallboxes tested so far do not.

## State

| Entity | Type | Values | M | E2 | E1 |
|---|---|---|---|---|---|
| Charging state | sensor | IEC 61851: A1 … F | ✅ | | |
| Charge state | sensor | active, paused, finished, error, unplugged | | | ✅ ³ |
| Vehicle connected | binary sensor | | ✅ | | ✅ ⁴ |
| Charging | binary sensor | on = current flows | ✅ | | ✅ ⁴ |
| Problem | binary sensor | | ✅ | ✅ | ✅ |
| Operating state | sensor | normal operation, standby, failure …, diagnostic | | ✅ | ✅ |
| Active current limit | sensor | A, the limit the wallbox applies (can be below the target: temperature, load management, §14a) | ✅ | | |
| Active power limit | sensor | W, the limit the wallbox applies; empty if none | | ✅ | ✅ |
| EEBUS connected | binary sensor | diagnostic | | ✅ | ✅ |

³ *Charge state* is already `active` while the car waits for authorization. *Charging* shows whether current flows.
⁴ Appear once a car has been plugged in while EEBUS was connected.

## When Home Assistant is gone

| Entity | Type | Values | M | E2 | E1 |
|---|---|---|---|---|---|
| Failsafe current | number | 0 = stop charging, 6–16 A = keep charging; configuration | ✅ | | |
| Watchdog timeout | number | s, default 15; after this the failsafe current applies; configuration | ✅ | | |
| Failsafe power | number | W, default 22 kW = no limit; configuration | | ✅ | |
| Failsafe duration | number | 2–24 h; configuration | | ✅ | |

The first generation has no failsafe settings.

## Other

| | M | E2 | E1 |
|---|---|---|---|
| Updates | polling, every 5 s (adjustable) | push, as soon as something changes | push |
| Found automatically | ✅ ⁵ | ✅ | ✅ |
| Setup on the wallbox | turn on the Modbus server | pair | pair |
| EEBUS energy managers at the same time | | one | one |
| Maximum current | 16 A, also on 22 kW models | | |
| Phase switching | no | no | no |

⁵ Found through the wallbox's EEBUS announcement; Home Assistant then checks whether Modbus answers.
