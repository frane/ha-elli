# EEBUS (Elli Charger 2 und erste Generation)

[English](eebus.md) | **Deutsch**

## Einrichtung

1. **Wallbox hinzufügen:** Home Assistant findet sie im Netz (mDNS) und bietet sie unter *Einstellungen → Geräte & Dienste* → **Entdeckt** an.

   Manuell: *Integration hinzufügen →* **Elli Charger** → **EEBUS**, mit IP-Adresse, Port und der SKI der Wallbox (in ihrer Weboberfläche bei den EEBUS-Einstellungen). Port: `4711` bei der Elli Charger 2, `4712` bei der ersten Generation (ID. Charger, Škoda iV Charger).
2. **Koppeln:** Home Assistant zeigt seine eigene SKI. In der Weboberfläche der Wallbox **Verbindungen → HEMS-Verbindung** (*EEBUS-Energiemanager*) öffnen, unter **Gefundene EEBUS-Geräte** „home-assistant“ auswählen und koppeln.
3. In Home Assistant auf **Absenden** klicken. Die Wallbox verbindet sich innerhalb weniger Sekunden.
4. **Failsafe** (nur Elli Charger 2): Im Gerät *Failsafe-Leistung* und *Failsafe-Dauer* setzen. Das tut die Wallbox, wenn Home Assistant weg ist (Standard 22 kW = kein Limit).

Die Wallbox arbeitet mit einem EEBUS-Energiemanager zur Zeit. Andere unter **HEMS-Verbindung** entfernen.

Home Assistant legt sein EEBUS-Zertifikat unter `.storage/elli/` ab. Behalten: Ein neues Zertifikat heißt neu koppeln.

## Was die Wallbox über EEBUS anbietet

| | Elli Charger 2 | Erste Generation |
|---|---|---|
| Use Cases | Leistungslimit (LPC), Leistungsmessung (MPC), Zustand (EVSECC); solange ein Auto angesteckt ist auch Stromlimits am Fahrzeug (OPEV), Fahrzeug-Messwerte (EVCEM), Fahrzeugzustand (EVCC) | Stromlimits am Fahrzeug (OPEV), Fahrzeug-Messwerte (EVCEM), Zustand von Fahrzeug und Wallbox (EVCC, EVSECC) |
| Messwerte | Gesamtleistung; solange ein Auto angesteckt ist auch Strom und Leistung je Phase und die geladene Energie | Strom je Phase, keine Leistung, keine Energie |
| Fahrzeug | wird gemeldet, solange angesteckt | wird gemeldet, solange angesteckt |
| Failsafe | Leistung und Dauer | keiner |

## Erste Generation

- **Leistung:** aus den Strömen × 230 V berechnet, weil die Wallbox keine meldet. Daraus berechnet Home Assistant auch *Energie (berechnet)* in kWh.
- **Limit:** wird als Strom je Phase am Fahrzeug gesetzt. Die Wallbox setzt es bei jedem Anstecken zurück und startet dann mit 6 A. Die Integration schreibt das Limit jedes Mal neu (das Maximum, solange *Leistungslimit* aus ist).
- **Ladezustand** steht schon auf `active`, während das Auto auf die Freigabe wartet. Ob Strom fließt, zeigt *Lädt*.
- **Fahrzeug:** wird nur für ein Auto gemeldet, das bei bestehender EEBUS-Verbindung angesteckt wurde.

## Firmware-Fehler, die die Integration abfängt

- Die Elli Charger 2 ignoriert Limits mit Dauer.
- Sie hebt ein Limit nur auf, wenn es als inaktiv mit 0 W geschrieben wird.
- Sie pausiert nur, wenn der Energiemanager auch die EV-Ladedienste anbietet.
- Erste Generation: Direkt nach dem Anstecken meldet sie leere erlaubte Werte; die gelten als unbekannt, nicht als 0 A.

Details: [elli-eebus](https://github.com/frane/elli-eebus/blob/main/README.de.md#firmware-fehler-der-elli-und-wie-elli-eebus-damit-umgeht).

## Fehlersuche

| Problem | Lösung |
|---|---|
| Wallbox nicht gefunden, oder „home-assistant“ taucht in der Wallbox nicht auf | Gleiches Netz, kein VLAN dazwischen? mDNS muss durchkommen |
| Limit wird nicht übernommen, im Log steht „Adding binding failed“ | Die Wallbox hält noch die Bindung eines entfernten Energiemanagers: Wallbox neu starten |
| Erste Generation: Port bleibt nach einem Neustart von Home Assistant zu | Firmware-Fehler: Wallbox am Sicherungsautomaten aus- und einschalten |
| Erste Generation: kein Fahrzeug, obwohl es lädt | Ab- und wieder anstecken |
| Alles andere | Die Diagnosedaten ans Issue hängen: *Geräte & Dienste → Elli Charger → ⋮ → Diagnosedaten herunterladen*. Sie enthalten, was die Wallbox über EEBUS meldet, ohne Seriennummern und SKIs |
