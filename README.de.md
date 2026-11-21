# Elli Charger für Home Assistant

[English](README.md) | **Deutsch**

Steuere deine **Elli**-Wallbox aus Home Assistant, lokal und ohne Cloud. Die Elli-App funktioniert weiter. Unterstützt beide Wallbox-Generationen, über **Modbus** oder **EEBUS**.

[![In HACS öffnen](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=frane&repository=ha-elli&category=integration)

## Welche Wallbox hast du?

| | Modelle | Verbindung |
|---|---|---|
| **Elli Charger 2** | Elli Charger Connect 2 / Pro 2, dazu die VW-, Škoda- und CUPRA-Modelle mit „2“ im Namen | Modbus oder EEBUS |
| **Erste Generation** | Elli Charger Connect / Pro, VW ID. Charger, Škoda iV Charger | nur EEBUS |

## Was geht wo

| | Charger 2  · Modbus | Charger 2 · EEBUS | 1. Gen. · EEBUS |
|---|---|---|---|
| Laden starten / stoppen | ✅ Schalter | ✅ Limit 0 W | ✅ Limit 0 W |
| Ladegeschwindigkeit | ✅ Strom, 6–16 A | ✅ Leistungslimit, W | ✅ Leistungslimit, W |
| Ladeleistung | ✅ gemessen | ✅ gemessen | ✅ aus den Strömen berechnet |
| Energie (kWh) | ✅ gesamt und seit Neustart | – | – (*Integral*-Helfer) |
| Strom je Phase | ✅ | – | ✅ |
| Spannung je Phase | ✅ | – | – |
| Fahrzeug verbunden, lädt | ✅ | – | ✅ |
| Ladestatus | ✅ A1 … F | – | ✅ aktiv, pausiert, fertig … |
| Störung | ✅ | ✅ | ✅ |
| Grenze, die die Wallbox anwendet | ✅ Strom | ✅ Leistung | ✅ Leistung |
| Platinentemperatur | ✅ | – | – |
| Wenn Home Assistant weg ist | Failsafe-Strom | Failsafe-Leistung und -Dauer | – |
| Aktualisierung | alle 5 s (einstellbar) | sobald sich etwas ändert | sobald sich etwas ändert |
| An der Wallbox | Modbus-Server einschalten | koppeln | koppeln |

Alle Entitäten: [docs/features.de.md](https://github.com/frane/ha-elli/blob/main/docs/features.de.md).

## Installation

1. In Home Assistant: **HACS** → nach **Elli Charger** suchen → **Herunterladen**.
2. Home Assistant neu starten.

<details><summary>Ohne HACS</summary>

Den Ordner `custom_components/elli` in den Ordner `custom_components` deiner Home-Assistant-Konfiguration kopieren und neu starten.
</details>

## Einrichtung mit Modbus (Elli Charger 2)

**An der Wallbox** (einmalig). Du brauchst die Zugangsdatenkarte, die bei der Wallbox lag.

1. `https://<IP der Wallbox>` im Browser öffnen (Zertifikatswarnung bestätigen) und als **Service User** anmelden.
2. **Software-Update:** Firmware **R03.004.045.121** oder neuer.
3. **Verbindungen → Modbus-Server:** an.
4. **Ladeverwaltung → Ladeeinstellungen → PV-Überschuss-Laden:** aus, wenn Home Assistant den Strom vorgeben soll.
5. Der Wallbox im Router eine feste IP geben.

**In Home Assistant:** *Einstellungen → Geräte & Dienste → Integration hinzufügen →* **Elli Charger**. Deine Wallbox aus der Liste wählen, dann **Modbus TCP**. Nicht in der Liste: **Manuell einrichten** → **Modbus TCP**, IP eintragen.

Danach im Gerät den **Failsafe-Strom** setzen: `0` stoppt das Laden, wenn Home Assistant weg ist, `6`–`16` A lädt weiter.

Mehr: [docs/modbus.de.md](https://github.com/frane/ha-elli/blob/main/docs/modbus.de.md).

## Einrichtung mit EEBUS (beide Generationen)

1. *Einstellungen → Geräte & Dienste → Integration hinzufügen →* **Elli Charger**. Deine Wallbox aus der Liste wählen (bei der Elli Charger 2 dann **EEBUS**). Nicht in der Liste: **Manuell einrichten** → **EEBUS**.
2. Home Assistant zeigt einen Kopplungsschritt. In der Weboberfläche der Wallbox **Verbindungen → HEMS-Verbindung** öffnen, **home-assistant** auswählen und koppeln.
3. Zurück in Home Assistant auf **Absenden** klicken.

Die Wallbox arbeitet mit einem EEBUS-Energiemanager zur Zeit. Andere unter **HEMS-Verbindung** entfernen.

Mehr: [docs/eebus.de.md](https://github.com/frane/ha-elli/blob/main/docs/eebus.de.md).

## Hilfe

Fehlersuche für [Modbus](https://github.com/frane/ha-elli/blob/main/docs/modbus.de.md#fehlersuche) und [EEBUS](https://github.com/frane/ha-elli/blob/main/docs/eebus.de.md#fehlersuche). Für ein Issue die Diagnosedaten anhängen: *Geräte & Dienste → Elli Charger → ⋮ → Diagnosedaten herunterladen* (ohne Seriennummern).

## Entwicklung

Der Protokoll-Code steckt in [elli-2-modbus](https://github.com/frane/elli-2-modbus) und [elli-eebus](https://github.com/frane/elli-eebus).

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements_test.txt
pytest
```

*Kein offizielles Projekt von Elli oder der Volkswagen Group Charging GmbH.*
