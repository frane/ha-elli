# Elli Charger für Home Assistant (Modbus, EEBUS)

[English](README.md) | **Deutsch**

> Nachfolger von [ha-elli-2-modbus](https://github.com/frane/ha-elli-2-modbus) (nur Modbus). Zum Wechseln die alte Integration entfernen, dann diese installieren und neu einrichten. Nicht beide gleichzeitig mit derselben Wallbox betreiben.

Lokale Home-Assistant-Integration für **Elli**-Wallboxen beider Generationen, über **Modbus TCP** oder **EEBUS**. Ohne Cloud, und die Elli-App funktioniert weiter.

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz/)
[![In HACS öffnen](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=frane&repository=ha-elli&category=integration)

Der Protokoll-Code steckt in den Bibliotheken [elli-2-modbus](https://github.com/frane/elli-2-modbus) und [elli-eebus](https://github.com/frane/elli-eebus) (auf [pyeebus](https://github.com/frane/pyeebus)). Home Assistant installiert sie automatisch.

## Welche Verbindung?

| Wallbox | Verbindung | Warum |
|---|---|---|
| **Elli Charger 2** (Connect 2, Pro 2, Pro 2 Eichrecht; Volkswagen ID. Charger Connect 2 / Pro 2; Škoda Charger Connect 2 / Pro 2; CUPRA Charger 2 / Pro 2), Firmware R03.004.045.121 oder neuer | **Modbus TCP** | mehr Werte (Status, Fahrzeug, Ströme, Spannungen, Energie) und direkte Steuerung (Strom 6–16 A, an/aus) |
| **Erste Generation** (Elli Charger Connect / Pro und ihre Volkswagen-, Škoda-, CUPRA-Varianten) | **EEBUS** | sie haben keinen Modbus-Server |
| Elli Charger 2, wenn Modbus nicht in Frage kommt | EEBUS | geht, aber nur Leistungslimit, Gesamtleistung und Failsafe |

**Faustregel: Hat deine Wallbox Modbus, nimm Modbus.** EEBUS bietet bei der Elli Charger 2 deutlich weniger, und die Wallbox verträgt sinnvoll nur einen EEBUS-Energiemanager.

**Energiemanager auch per EEBUS?** Steuert schon ein Energiemanager wie Solar Manager die Wallbox per EEBUS, nimm für Home Assistant Modbus, oder schalte [elli-eebus-proxy](https://github.com/frane/elli-eebus-proxy) dazwischen und verbinde Home Assistant mit dem Proxy.

## Installation (HACS)

1. In Home Assistant **HACS** öffnen → **⋮ (oben rechts) → Benutzerdefinierte Repositories**. Alternativ den Button „In HACS öffnen“ oben nutzen.
2. Repository: `https://github.com/frane/ha-elli`, Typ: **Integration** → **Hinzufügen**.
3. In HACS nach **Elli Charger** suchen → **Herunterladen**.
4. **Home Assistant neu starten** (*Einstellungen → System → Neu starten*).

<details><summary>Ohne HACS</summary>

Den Ordner `custom_components/elli` in den Ordner `custom_components` deiner Home-Assistant-Konfiguration kopieren und neu starten.
</details>

## Einrichtung mit Modbus TCP (Elli Charger 2)

### 1. Modbus an der Wallbox aktivieren

Du brauchst die **Zugangsdatenkarte**, die bei der Wallbox lag. Die Weboberfläche der Wallbox gibt es auf Deutsch und Englisch; die englischen Bezeichnungen stehen in Klammern.

1. **Wallbox-Konfiguration öffnen** im Browser:
   - im Heimnetz: `https://<IP oder Hostname der Wallbox>` (Hostname steht auf der Karte, die IP im Router), oder
   - über den Hotspot der Wallbox: mit dem WLAN der Wallbox verbinden (SSID und Passwort von der Karte) und `https://10.0.2.1` öffnen.

   Der Browser warnt wegen des Zertifikats. Auf **Erweitert** (*Advanced*) klicken und fortfahren.
2. **Als Service User anmelden**, mit dem Service-User-Passwort von der Karte.
3. **Firmware prüfen** unter **Software-Update** (*Software update*). Sie muss **R03.004.045.121 oder neuer** sein; sonst zuerst aktualisieren.
4. **Modbus-Server einschalten:** **Verbindungen → Modbus-Server** (*Connections → Modbus server*) → **an**. Port 502, Modbus-ID 1.
5. **Feste IP-Adresse vergeben:** DHCP-Reservierung im Router oder statische IP unter **Verbindungen → Ethernet**. Home Assistant muss im selben lokalen Netz sein (nicht über LTE).
6. **Eigenes PV-Überschussladen der Wallbox ausschalten**, damit sie nicht gegen Home Assistant regelt: **Ladeverwaltung → Ladeeinstellungen → PV-Überschuss-Laden → PV-Laden aus** (*Charging management → Charging settings → PV surplus charging → off*).
7. Für vollautomatisches Laden in der Elli-App *Sofortladen* (Laden ohne Authentifizierung) aktivieren. Sonst kann ein Ladevorgang weiterhin eine Freigabe per RFID oder App brauchen.

Optionaler Test von einem beliebigen Rechner: `pip install elli-2-modbus && elli-2-modbus status <ip>`. Ausführlich: [enable-modbus.de.md](https://github.com/frane/elli-2-modbus/blob/main/docs/enable-modbus.de.md).

### 2. Wallbox hinzufügen

1. *Einstellungen → Geräte & Dienste → Integration hinzufügen →* **Elli Charger** → **Modbus TCP**.
2. Name, **IP-Adresse** der Wallbox, Port `502` und Modbus-ID `1` eintragen.
3. Fertig. Die Wallbox erscheint als Gerät mit den Entitäten unten.

Spätere Änderungen: Über *Konfigurieren* stellst du das Abfrageintervall ein (Standard 5 s). Über *Neu konfigurieren* änderst du die IP, ohne die Entitäten zu verlieren.

### 3. Failsafe festlegen

Im Gerät den **Failsafe-Strom** setzen. Diesen Strom nutzt die Wallbox, wenn Home Assistant länger als der **Watchdog-Timeout** (Standard 15 s) nicht mit ihr spricht:

- `0` = Laden stoppen (sicher für reines PV-Laden)
- `6`–`16` A = mit diesem Strom weiterladen

Das Abfrageintervall deutlich kürzer als den Watchdog-Timeout halten.

## Einrichtung mit EEBUS (erste Generation, oder Elli Charger 2 ohne Modbus)

1. **Wallbox hinzufügen:** Home Assistant findet sie im Netz und bietet sie unter *Einstellungen → Geräte & Dienste* (*Entdeckt*) an. Sonst: *Integration hinzufügen →* **Elli Charger** → **EEBUS**, und IP-Adresse, Port `4711` und die SKI der Wallbox eintragen (steht in der Weboberfläche bei den EEBUS-Einstellungen).
2. **Koppeln:** Home Assistant zeigt seine eigene SKI. In der Weboberfläche der Wallbox **Verbindungen → HEMS-Verbindung** (*EEBUS-Energiemanager*) öffnen, unter **Gefundene EEBUS-Geräte** „home-assistant“ auswählen und koppeln. Einen Energiemanager, den du nicht mehr nutzt, dort entfernen.
3. In Home Assistant auf **Absenden** klicken. Die Wallbox verbindet sich innerhalb weniger Sekunden.
4. **Failsafe:** Im Gerät *Failsafe-Leistung* und *Failsafe-Dauer* setzen. Das tut die Wallbox, wenn Home Assistant weg ist (Standard 22 kW = kein Limit).

Home Assistant legt sein EEBUS-Zertifikat unter `.storage/elli/` ab. Behalten: Ein neues Zertifikat heißt neu koppeln.

## Entitäten

### Modbus

| Entität | Typ |
|---|---|
| Laden freigegeben | Schalter (aus = Wallbox sperrt das Laden) |
| Ladestrom | Zahl, 6–16 A in 0,1-A-Schritten, wirkt solange das Laden freigegeben ist |
| Ladestatus | Sensor (A1 … F) |
| Fahrzeug verbunden, Lädt, Störung | Binärsensoren |
| Ladeleistung, Energie gesamt (Energie-Dashboard), Energie seit Neustart | Sensoren |
| Aktive Stromgrenze | Sensor (kann wegen interner Grenzen unter dem Sollwert liegen) |
| Strom und Spannung L1–L3, Platinentemperatur | Sensoren |
| Failsafe-Strom, Watchdog-Timeout | Konfiguration |

Für PV-Überschussladen eine Automation schreiben, die *Ladestrom* und *Laden freigegeben* anhand der Netzleistung setzt. Dafür eignet sich jeder Netzleistungs-Sensor: Smart Meter, Wechselrichter oder die Integration deines Energiemanagers.

### EEBUS

| Entität | Typ |
|---|---|
| Ladeleistungslimit | Zahl, W (0 = Pause) |
| Leistungslimit | Schalter (an = Limit gilt) |
| Ladeleistung, Aktives Leistungslimit, Betriebszustand | Sensoren |
| Problem, EEBUS verbunden | Binärsensoren |
| Failsafe-Leistung, Failsafe-Dauer | Konfiguration |
| Fahrzeug verbunden, Ströme L1–L3, Energie des Ladevorgangs | nur wenn die Wallbox das Fahrzeug meldet (erste Generation) |

## Grenzen der Firmware

- Modbus: maximal 16 A, auch bei 22-kW-Varianten (Elli hat 32 A angekündigt); keine Phasenumschaltung
- EEBUS: Die Elli-Firmware ignoriert Limits mit Dauer, hebt Limits nur mit 0 W auf und pausiert nur, wenn der Energiemanager die EV-Ladedienste anbietet. [elli-eebus](https://github.com/frane/elli-eebus/blob/main/README.de.md#firmware-fehler-der-elli-und-wie-elli-eebus-damit-umgeht) fängt all das ab.

## Fehlersuche

| Problem | Lösung |
|---|---|
| Modbus: „Keine Verbindung“ bei der Einrichtung | Ist der Modbus-Server an? Stimmt die IP? Sind Home Assistant und Wallbox im selben Netz? |
| Modbus: „Die Wallbox antwortet, aber nicht mit den erwarteten Registern“ | Firmware älter als R03.004.045.121 oder falsche Modbus-ID |
| Modbus: Laden stoppt nach einer Weile von selbst | Watchdog: Home Assistant war länger als der Watchdog-Timeout nicht erreichbar, deshalb greift der Failsafe-Strom |
| Modbus: Strom niedriger als eingestellt | Die internen Grenzen der Wallbox (Temperatur, Lastmanagement, §14a) haben Vorrang; siehe *Aktive Stromgrenze* |
| EEBUS: Wallbox nicht gefunden / „home-assistant“ taucht in der Wallbox nicht auf | Gleiches Netz (kein VLAN dazwischen)? mDNS muss durchkommen |
| EEBUS: Limit wird nicht übernommen, im Log steht „Adding binding failed“ | Die Wallbox hält noch die Bindung eines entfernten Energiemanagers: Wallbox neu starten |

## Entwicklung

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements_test.txt   # oder: pip install -e ../elli-2-modbus -e ../pyeebus -e ../elli-eebus
pytest
```

Die Tests starten eine echte Home-Assistant-Testinstanz gegen den Wallbox-Simulator aus `elli-2-modbus`.

*Kein offizielles Projekt von Elli oder der Volkswagen Group Charging GmbH.*
