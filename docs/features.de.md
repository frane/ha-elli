# Funktionen und Entitäten

[English](features.md) | **Deutsch**

M = Elli Charger 2 über Modbus · E2 = Elli Charger 2 über EEBUS · E1 = erste Generation über EEBUS

## Steuern

| Entität | Typ | Werte | M | E2 | E1 |
|---|---|---|---|---|---|
| Laden freigegeben | Schalter | aus = die Wallbox sperrt das Laden | ✅ | | |
| Ladestrom | Zahl | 6–16 A in 0,1-A-Schritten; wirkt, solange *Laden freigegeben* an ist | ✅ | | |
| Ladeleistungslimit | Zahl | W in 100-W-Schritten, 0 = Pause; wirkt, solange *Leistungslimit* an ist | | ✅ | ✅ |
| Leistungslimit | Schalter | an = die Wallbox lädt mit höchstens *Ladeleistungslimit* | | ✅ | ✅ |

## Messwerte

| Entität | Typ | Werte | M | E2 | E1 |
|---|---|---|---|---|---|
| Ladeleistung | Sensor | W | ✅ | ✅ | ✅ ¹ |
| Energie gesamt | Sensor | kWh, Zählerstand, für das Energie-Dashboard | ✅ | | |
| Energie seit Neustart | Sensor | kWh | ✅ | | |
| Energie | Sensor | kWh, nur wenn die Wallbox sie meldet | | ² | ² |
| Energie (berechnet) | Sensor | kWh, aus der *Ladeleistung* berechnet, für das Energie-Dashboard | | ✅ | ✅ |
| Strom L1–L3 | Sensor | A | ✅ | | ✅ |
| Spannung L1–L3 | Sensor | V | ✅ | | |
| Platinentemperatur | Sensor | °C, Diagnose | ✅ | | |

¹ Die erste Generation meldet keine Leistung. Sie wird aus den Strömen × 230 V berechnet.
² Entsteht nur, wenn die Wallbox Energie meldet. Die bisher getesteten Wallboxen tun das nicht.

## Zustand

| Entität | Typ | Werte | M | E2 | E1 |
|---|---|---|---|---|---|
| Ladestatus | Sensor | IEC 61851: A1 … F | ✅ | | |
| Ladezustand | Sensor | active, paused, finished, error, unplugged | | | ✅ ³ |
| Fahrzeug verbunden | Binärsensor | | ✅ | | ✅ ⁴ |
| Lädt | Binärsensor | an = Strom fließt | ✅ | | ✅ ⁴ |
| Störung | Binärsensor | | ✅ | ✅ | ✅ |
| Betriebszustand | Sensor | Normalbetrieb, Standby, Fehler …, Diagnose | | ✅ | ✅ |
| Aktive Stromgrenze | Sensor | A, die Grenze, die die Wallbox anwendet (kann unter dem Sollwert liegen: Temperatur, Lastmanagement, §14a) | ✅ | | |
| Aktives Leistungslimit | Sensor | W, das Limit, das die Wallbox anwendet; leer, wenn keins | | ✅ | ✅ |
| EEBUS verbunden | Binärsensor | Diagnose | | ✅ | ✅ |

³ *Ladezustand* steht schon auf `active`, während das Auto auf die Freigabe wartet. Ob Strom fließt, zeigt *Lädt*.
⁴ Erscheinen, sobald ein Auto bei bestehender EEBUS-Verbindung angesteckt wurde.

## Wenn Home Assistant weg ist

| Entität | Typ | Werte | M | E2 | E1 |
|---|---|---|---|---|---|
| Failsafe-Strom | Zahl | 0 = Laden stoppen, 6–16 A = weiterladen; Konfiguration | ✅ | | |
| Watchdog-Timeout | Zahl | s, Standard 15; danach gilt der Failsafe-Strom; Konfiguration | ✅ | | |
| Failsafe-Leistung | Zahl | W, Standard 22 kW = kein Limit; Konfiguration | | ✅ | |
| Failsafe-Dauer | Zahl | 2–24 h; Konfiguration | | ✅ | |

Die erste Generation hat keine Failsafe-Einstellungen.

## Sonstiges

| | M | E2 | E1 |
|---|---|---|---|
| Aktualisierung | Abfrage alle 5 s (einstellbar) | Push, sobald sich etwas ändert | Push |
| Wird automatisch gefunden | ✅ ⁵ | ✅ | ✅ |
| Einrichtung an der Wallbox | Modbus-Server einschalten | koppeln | koppeln |
| EEBUS-Energiemanager gleichzeitig | | einer | einer |
| Maximaler Strom | 16 A, auch bei 22-kW-Modellen | | |
| Phasenumschaltung | nein | nein | nein |

⁵ Über die EEBUS-Ankündigung der Wallbox; Home Assistant prüft dann, ob Modbus antwortet.
