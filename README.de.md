# Elli Charger für Home Assistant

[English](README.md) | **Deutsch**

Steuere deine **Elli**-Wallbox aus Home Assistant, lokal und ohne Cloud. Die Elli-App funktioniert weiter.

[![In HACS öffnen](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=frane&repository=ha-elli&category=integration)

## Welche Wallbox?

| Deine Wallbox | Verbindung | Was du bekommst |
|---|---|---|
| **Elli Charger 2**, mit „2“ im Namen (auch die Volkswagen-, Škoda- und CUPRA-Varianten) | **Modbus** | Laden an/aus, Ladestrom (6–16 A), Leistung, Energie, Fahrzeugstatus |
| **Erste Generation** (Elli Charger Connect / Pro, VW ID. Charger, Škoda iV Charger, CUPRA) | **EEBUS** | Leistungslimit und Pause, Leistung, Fahrzeugstatus |

Die erste Generation hat kein Modbus. EEBUS geht auch bei der Elli Charger 2, kann dort aber weniger: Nimm da Modbus.

Du kommst von [ha-elli-2-modbus](https://github.com/frane/ha-elli-2-modbus)? Erst die alte Integration entfernen, dann diese einrichten.

## Installation

1. In Home Assistant: **HACS** → nach **Elli Charger** suchen → **Herunterladen**.
2. Home Assistant neu starten.

<details><summary>Ohne HACS</summary>

Den Ordner `custom_components/elli` in den Ordner `custom_components` deiner Home-Assistant-Konfiguration kopieren und neu starten.
</details>

## Einrichtung: Elli Charger 2 (Modbus)

**An der Wallbox** (einmalig). Du brauchst die Zugangsdatenkarte, die bei der Wallbox lag.

1. `https://<IP der Wallbox>` im Browser öffnen (Zertifikatswarnung bestätigen) und als **Service User** anmelden.
2. **Software-Update:** Firmware **R03.004.045.121** oder neuer.
3. **Verbindungen → Modbus-Server:** an.
4. **Ladeverwaltung → Ladeeinstellungen → PV-Überschuss-Laden:** aus, damit die Wallbox nicht gegen Home Assistant regelt.
5. Der Wallbox im Router eine feste IP geben.

**In Home Assistant:** *Einstellungen → Geräte & Dienste → Integration hinzufügen →* **Elli Charger** → **Modbus TCP**, IP eintragen. Fertig.

Danach im Gerät den **Failsafe-Strom** setzen: Das macht die Wallbox, wenn Home Assistant 15 s lang weg ist. `0` stoppt das Laden, `6`–`16` A lädt weiter.

Tipp: In der Elli-App *Sofortladen* einschalten, sonst braucht jeder Ladevorgang eine Freigabe per RFID oder App. Ausführlicher: [enable-modbus.de.md](https://github.com/frane/elli-2-modbus/blob/main/docs/enable-modbus.de.md).

## Einrichtung: erste Generation (EEBUS)

1. Home Assistant findet die Wallbox selbst: *Einstellungen → Geräte & Dienste*, unter **Entdeckt** → **Hinzufügen**. Falls nicht: *Integration hinzufügen →* **Elli Charger** → **EEBUS**, mit IP, Port `4712` und der SKI der Wallbox (in ihrer Weboberfläche bei EEBUS).
2. Home Assistant zeigt jetzt einen Kopplungsschritt. In der Weboberfläche der Wallbox **Verbindungen → HEMS-Verbindung** öffnen, **home-assistant** auswählen und koppeln.
3. Zurück in Home Assistant auf **Absenden** klicken.

Die Wallbox arbeitet nur mit einem Energiemanager. Andere unter **HEMS-Verbindung** entfernen.

## Entitäten

**Modbus:** Laden freigegeben (Schalter), Ladestrom (6–16 A), Ladestatus, Fahrzeug verbunden, Lädt, Störung, Ladeleistung, Energie gesamt (für das Energie-Dashboard), Strom und Spannung je Phase, Aktive Stromgrenze, Platinentemperatur.

**EEBUS:** Ladeleistungslimit (W, 0 = Pause), Leistungslimit (Schalter), Ladeleistung, Fahrzeug verbunden, Lädt, Strom je Phase, Energie des Ladevorgangs, EEBUS verbunden.

Erste Generation:

- Die Wallbox meldet keine Leistung, *Ladeleistung* wird aus den Strömen berechnet. Für kWh einen *Integral*-Helfer darauf anlegen.
- Fahrzeugwerte erscheinen, sobald einmal ein Auto angesteckt war.
- Ob Strom fließt, zeigt *Lädt*. *Ladezustand* steht schon auf `active`, während das Auto auf die Freigabe wartet.

**PV-Überschussladen:** eine Automation, die *Ladestrom* (Modbus) oder *Ladeleistungslimit* (EEBUS) anhand deiner Netzleistung setzt.

## Grenzen

- Über Modbus maximal 16 A, auch bei 22-kW-Wallboxen. Keine Phasenumschaltung.

## Fehlersuche

| Problem | Lösung |
|---|---|
| Modbus: keine Verbindung | Modbus-Server an? IP richtig? Gleiches Netz wie Home Assistant? |
| Modbus: falsche Register | Firmware der Wallbox aktualisieren |
| Modbus: Laden stoppt von selbst | Home Assistant war nicht erreichbar, deshalb galt der Failsafe-Strom |
| Modbus: Strom niedriger als eingestellt | Die Wallbox begrenzt selbst (Temperatur, Lastmanagement); siehe *Aktive Stromgrenze* |
| EEBUS: Wallbox nicht gefunden | Gleiches Netz, kein VLAN dazwischen |
| EEBUS: Limit wird ignoriert | Wallbox neu starten (sie hält noch einen entfernten Energiemanager) |
| EEBUS: kein Fahrzeug angezeigt | Ab- und wieder anstecken |
| EEBUS: keine Verbindung nach Neustart von Home Assistant | Wallbox am Sicherungsautomaten aus- und einschalten |
| Alles andere | Issue öffnen und die Diagnosedaten anhängen: *Geräte & Dienste → Elli Charger → ⋮ → Diagnosedaten herunterladen* |

## Entwicklung

Der Protokoll-Code steckt in [elli-2-modbus](https://github.com/frane/elli-2-modbus) und [elli-eebus](https://github.com/frane/elli-eebus).

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements_test.txt
pytest
```

*Kein offizielles Projekt von Elli oder der Volkswagen Group Charging GmbH.*
