# Modbus (Elli Charger 2)

**English** | [Deutsch](modbus.de.md)

## Enable Modbus on the wallbox

You need the **card with the access data** that came with the wallbox. The web interface is available in English and German; German labels in brackets.

1. **Open the charger configuration** in a browser:
   - on your home network: `https://<IP or hostname of the wallbox>` (hostname on the card, IP in your router), or
   - through the wallbox hotspot: connect to its Wi-Fi (SSID and password on the card) and open `https://10.0.2.1`.

   The browser warns about the certificate: **Advanced** (*Erweitert*) → continue.
2. **Log in as Service User** with the service user password from the card.
3. **Software update** (*Software-Update*): firmware **R03.004.045.121** or newer.
4. **Connections → Modbus server** (*Verbindungen → Modbus-Server*): on. Port 502, unit ID 1.
5. **Fixed IP address:** DHCP reservation in your router, or a static IP under **Connections → Ethernet**. Home Assistant must reach the wallbox on the local network (not over LTE).
6. **PV surplus charging of the wallbox** (*Ladeverwaltung → Ladeeinstellungen → PV-Überschuss-Laden*): turn it off if Home Assistant should set the current. Otherwise both regulate at the same time.
7. **Instant charging** (charging without authentication) in the Elli app: without it, a session may still need RFID or app approval.

Check from any computer: `pip install elli-2-modbus && elli-2-modbus status <ip>`. More: [enable-modbus.md](https://github.com/frane/elli-2-modbus/blob/main/docs/enable-modbus.md) in elli-2-modbus.

## Add to Home Assistant

*Settings → Devices & services → Add integration →* **Elli Charger** → **Modbus TCP**: name, IP, port `502`, Modbus ID `1`.

- **Configure:** polling interval (default 5 s).
- **Reconfigure:** change the IP address without losing the entities.

## Failsafe and watchdog

**Failsafe current** is what the wallbox does when Home Assistant has not talked to it for longer than the **Watchdog timeout** (default 15 s):

- `0`: stop charging (safe for PV-only charging)
- `6`–`16` A: keep charging at that current

The wallbox counts only writes, not reads, as contact. While the watchdog is on, the integration therefore writes the charging current (or 0 when charging is off) on every poll. If the wallbox has fallen back to the failsafe current, the next poll restores the configured current. Keep the polling interval well below the watchdog timeout.

## PV surplus charging

An automation that sets *Charging current* and *Charging enabled* from your grid power. Any grid power sensor works: smart meter, inverter or the integration of your energy manager.

## Firmware limits

- Maximum 16 A, also on 22 kW models (Elli has announced 32 A).
- No phase switching.
- The wallbox's own limits (temperature, load management, §14a) take priority; *Active current limit* shows what applies.

## Troubleshooting

| Problem | Fix |
|---|---|
| "Cannot connect" during setup | Is the Modbus server on? Is the IP correct? Are Home Assistant and the wallbox on the same network? |
| "Wallbox answers, but not with the expected registers" | Firmware older than R03.004.045.121, or wrong Modbus ID |
| Charging stops by itself after a while | Home Assistant was unreachable longer than the watchdog timeout, so the failsafe current applied. Versions before 0.1.1 also tripped it during normal operation: update |
| Stays at 0 A after an energy manager paused charging over EEBUS | Versions before 0.1.10 took the pause over as their own setting after a restart and kept writing 0: update, then switch *Charging enabled* on once |
| Current is lower than set | The wallbox's own limits apply; see *Active current limit* |
