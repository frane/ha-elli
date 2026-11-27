# Modbus (Elli Charger 2)

[English](modbus.md) | **Deutsch**

## Modbus an der Wallbox aktivieren

Du brauchst die **Zugangsdatenkarte**, die bei der Wallbox lag. Die Weboberfläche gibt es auf Deutsch und Englisch; englische Bezeichnungen in Klammern.

1. **Wallbox-Konfiguration öffnen** im Browser:
   - im Heimnetz: `https://<IP oder Hostname der Wallbox>` (Hostname auf der Karte, IP im Router), oder
   - über den Hotspot der Wallbox: mit ihrem WLAN verbinden (SSID und Passwort auf der Karte) und `https://10.0.2.1` öffnen.

   Der Browser warnt wegen des Zertifikats: **Erweitert** (*Advanced*) → fortfahren.
2. **Als Service User anmelden**, mit dem Service-User-Passwort von der Karte.
3. **Software-Update** (*Software update*): Firmware **R03.004.045.121** oder neuer.
4. **Verbindungen → Modbus-Server** (*Connections → Modbus server*): an. Port 502, Modbus-ID 1.
5. **Feste IP-Adresse:** DHCP-Reservierung im Router oder statische IP unter **Verbindungen → Ethernet**. Home Assistant muss die Wallbox im lokalen Netz erreichen (nicht über LTE).
6. **PV-Überschussladen der Wallbox** (*Charging management → Charging settings → PV surplus charging*): ausschalten, wenn Home Assistant den Strom vorgeben soll. Sonst regeln beide gleichzeitig.
7. **Sofortladen** (Laden ohne Authentifizierung) in der Elli-App: Ohne braucht ein Ladevorgang eventuell weiter eine Freigabe per RFID oder App.

Test von einem beliebigen Rechner: `pip install elli-2-modbus && elli-2-modbus status <ip>`. Mehr: [enable-modbus.de.md](https://github.com/frane/elli-2-modbus/blob/main/docs/enable-modbus.de.md) in elli-2-modbus.

## In Home Assistant hinzufügen

*Einstellungen → Geräte & Dienste → Integration hinzufügen →* **Elli Charger** → **Modbus TCP**: Name, IP, Port `502`, Modbus-ID `1`.

- **Konfigurieren:** Abfrageintervall (Standard 5 s).
- **Neu konfigurieren:** IP ändern, ohne die Entitäten zu verlieren.

## Failsafe und Watchdog

Den **Failsafe-Strom** nutzt die Wallbox, wenn Home Assistant länger als der **Watchdog-Timeout** (Standard 15 s) nicht mit ihr spricht:

- `0`: Laden stoppen (sicher für reines PV-Laden)
- `6`–`16` A: mit diesem Strom weiterladen

Die Wallbox zählt nur Schreibzugriffe als Kontakt, keine Lesezugriffe. Solange der Watchdog an ist, schreibt die Integration deshalb bei jeder Abfrage den Ladestrom (oder 0, wenn Laden aus ist). Ist die Wallbox auf den Failsafe-Strom gefallen, stellt die nächste Abfrage den eingestellten Strom wieder her. Das Abfrageintervall deutlich kürzer als den Watchdog-Timeout halten.

## PV-Überschussladen

Eine Automation, die *Ladestrom* und *Laden freigegeben* anhand der Netzleistung setzt. Jeder Netzleistungs-Sensor geht: Smart Meter, Wechselrichter oder die Integration deines Energiemanagers.

## Grenzen der Firmware

- Maximal 16 A, auch bei 22-kW-Modellen (Elli hat 32 A angekündigt).
- Keine Phasenumschaltung.
- Die eigenen Grenzen der Wallbox (Temperatur, Lastmanagement, §14a) haben Vorrang; *Aktive Stromgrenze* zeigt, was gilt.

## Fehlersuche

| Problem | Lösung |
|---|---|
| „Keine Verbindung“ bei der Einrichtung | Ist der Modbus-Server an? Stimmt die IP? Sind Home Assistant und Wallbox im selben Netz? |
| „Die Wallbox antwortet, aber nicht mit den erwarteten Registern“ | Firmware älter als R03.004.045.121 oder falsche Modbus-ID |
| Laden stoppt nach einer Weile von selbst | Home Assistant war länger als der Watchdog-Timeout nicht erreichbar, deshalb galt der Failsafe-Strom. Versionen vor 0.1.1 lösten ihn auch im Normalbetrieb aus: aktualisieren |
| Bleibt auf 0 A, nachdem ein Energiemanager das Laden über EEBUS pausiert hat | Versionen vor 0.1.10 übernahmen die Pause nach einem Neustart als eigene Einstellung und schrieben weiter 0: aktualisieren, dann *Laden freigegeben* einmal einschalten |
| Strom niedriger als eingestellt | Die eigenen Grenzen der Wallbox gelten; siehe *Aktive Stromgrenze* |
