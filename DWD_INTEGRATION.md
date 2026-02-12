# DWD Wetterdaten Integration

## Übersicht

Die Wolf-Logger Software wurde um eine optionale Integration der DWD (Deutscher Wetterdienst) API erweitert. Dies ermöglicht das automatische Logging von Wetterdaten zusammen mit den Heizungsdaten.

## Warum Wetterdaten?

Wetterfaktoren haben einen **massiven Einfluss** auf den Heizungsverbrauch:

- 🌡️ **Temperatur**: Direkter Einfluss auf Heizbedarf
- 💨 **Wind**: Erhöht Wärmeverluste durch Gebäudehülle
- ☀️ **Sonneneinstrahlung**: Passive solare Gewinne
- 🌧️ **Niederschlag/Schnee**: Beeinflusst Luftfeuchtigkeit und gefühlte Temperatur

Durch die Korrelation von Heizungsdaten mit Wetterdaten können Sie:
- Verbrauchsmuster besser analysieren
- Effizienz der Heizungsregelung bewerten
- Anomalien im Verbrauch erkennen
- Vorhersagemodelle für Verbrauch entwickeln

## Installation & Konfiguration

### 1. DWD Station ID finden

Besuchen Sie die offizielle DWD Stationsliste:
https://www.dwd.de/DE/leistungen/klimadatendeutschland/stationsliste.html

**Beliebte Stationen:**
- `G005` - Beispielstation (für Tests)
- `10865` - Stuttgart (Schnarrenberg)
- `10381` - München Flughafen
- `10382` - Frankfurt/Main Flughafen
- `03987` - Hamburg-Fuhlsbüttel
- `10382` - Köln/Bonn Flughafen

### 2. .env Datei konfigurieren

Fügen Sie Ihrer `.env` Datei hinzu:

```env
# DWD Weather Station (optional)
DWD_STATION_ID=G005
```

**Hinweis:** Wenn `DWD_STATION_ID` nicht gesetzt ist, werden nur Heizungsdaten geloggt (wie bisher).

### 3. Testen

```bash
source venv/bin/activate

# Wetterdaten-Modul testen
python3 dwd_weather.py

# Vollständigen Logger mit Wetterdaten testen
python3 wolf_logger.py
```

## Gespeicherte Wetterdaten

Folgende Wetterdaten werden in der Datenbank gespeichert:

| Feld | Beschreibung | Einheit |
|------|--------------|---------|
| `dwd_station_id` | ID der Wetterstation | - |
| `dwd_timestamp` | Zeitstempel der Wetterdaten | ISO 8601 |
| `dwd_temperature_current` | Aktuelle Temperatur | °C |
| `dwd_temperature_min` | Tagesminimum | °C |
| `dwd_temperature_max` | Tagesmaximum | °C |
| `dwd_wind_speed` | Windgeschwindigkeit | m/s |
| `dwd_wind_gust` | Maximale Windböen | m/s |
| `dwd_wind_direction` | Windrichtung | ° (0-360) |
| `dwd_precipitation_daily` | Niederschlag (täglich) | mm |
| `dwd_sunshine_minutes` | Sonnenscheindauer | Sekunden |
| `dwd_humidity` | Relative Luftfeuchtigkeit | % |
| `dwd_pressure` | Luftdruck | hPa |
| `dwd_cloud_cover` | Bewölkungsgrad | % |

## Beispiel-Ausgabe

```
============================================================
SUCCESS! Data logged to database:
============================================================
Timestamp:                    2026-02-12T20:43:24.301Z
Vorlauftemperatur:            43.2°C
Rücklauftemperatur:           40.3°C
Kesseltemperatur:             42.7°C
Außentemperatur:              5.5°C
Gesamtverbrauch (Jahr):       1697.0 kWh
Wärmemenge Heizung (gesamt):  4640.0 kWh
Wärmemenge Warmwasser (ges.): 116.0 kWh
Verbrauch Vortag:             40.0 kWh
Verbrauch aktueller Monat:    860.0 kWh
Erzeugte Wärmemenge (Jahr):   4757.0 kWh
JAZ (aktuelles Jahr):         2.8

------------------------------------------------------------
Weather Data (DWD):
------------------------------------------------------------
Station:                      G005
Temperatur (aktuell):         3.9°C
Temperatur (Min/Max):         3.7°C / 9.3°C
Windgeschwindigkeit:          9.3 m/s
Windböen:                     22.2 m/s
Niederschlag (täglich):       11.6 mm
Sonnenscheindauer:            0 s
Luftfeuchtigkeit:             100.0%
Luftdruck:                    97.96 hPa

Saved as row ID: 42
============================================================
```

## API Details

Die Integration nutzt den offiziellen DWD API Endpoint:
```
https://app-prod-ws.warnwetter.de/v30/stationOverviewExtended
```

**Dokumentation:** https://dwd.api.bund.dev

### Rate Limiting

Die DWD API hat keine offiziell dokumentierten Rate Limits, aber es wird empfohlen:
- Daten nicht öfter als alle 10-15 Minuten abzurufen
- Keine parallelen Requests von derselben IP
- Bei Fehlern exponentielles Backoff verwenden

## Datenanalyse

### SQL Abfragen mit Wetterdaten

```sql
-- Verbrauch vs. Außentemperatur
SELECT 
    DATE(timestamp) as tag,
    AVG(aussentemperatur) as avg_aussen_temp,
    AVG(dwd_temperature_current) as avg_dwd_temp,
    AVG(verbrauch_vortag) as avg_verbrauch
FROM heating_data
WHERE dwd_temperature_current IS NOT NULL
GROUP BY DATE(timestamp)
ORDER BY tag DESC
LIMIT 30;

-- Korrelation Wind und Verbrauch
SELECT 
    ROUND(dwd_wind_speed, 1) as windstaerke,
    AVG(verbrauch_vortag) as avg_verbrauch,
    COUNT(*) as messungen
FROM heating_data
WHERE dwd_wind_speed IS NOT NULL
GROUP BY ROUND(dwd_wind_speed, 1)
ORDER BY windstaerke;

-- Sonnige vs. bewölkte Tage
SELECT 
    CASE 
        WHEN dwd_sunshine_minutes > 3600 THEN 'Sonnig'
        WHEN dwd_sunshine_minutes > 1800 THEN 'Teilweise sonnig'
        ELSE 'Bewölkt'
    END as wetter,
    AVG(verbrauch_vortag) as avg_verbrauch,
    AVG(dwd_temperature_current) as avg_temp
FROM heating_data
WHERE dwd_sunshine_minutes IS NOT NULL
GROUP BY 
    CASE 
        WHEN dwd_sunshine_minutes > 3600 THEN 'Sonnig'
        WHEN dwd_sunshine_minutes > 1800 THEN 'Teilweise sonnig'
        ELSE 'Bewölkt'
    END;
```

### Python Analyse

```python
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt

# Daten laden
conn = sqlite3.connect('data/wolf.db')
df = pd.read_sql_query("""
    SELECT 
        timestamp,
        verbrauch_vortag,
        dwd_temperature_current,
        dwd_wind_speed,
        dwd_sunshine_minutes
    FROM heating_data
    WHERE dwd_temperature_current IS NOT NULL
    ORDER BY timestamp
""", conn)

# Zeitstempel konvertieren
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Korrelation berechnen
correlation = df[['verbrauch_vortag', 'dwd_temperature_current', 
                   'dwd_wind_speed', 'dwd_sunshine_minutes']].corr()
print(correlation)

# Visualisierung
fig, axes = plt.subplots(2, 2, figsize=(12, 10))

# Verbrauch vs. Temperatur
axes[0, 0].scatter(df['dwd_temperature_current'], df['verbrauch_vortag'])
axes[0, 0].set_xlabel('Temperatur (°C)')
axes[0, 0].set_ylabel('Verbrauch (kWh)')
axes[0, 0].set_title('Verbrauch vs. Temperatur')

# Verbrauch vs. Windgeschwindigkeit
axes[0, 1].scatter(df['dwd_wind_speed'], df['verbrauch_vortag'])
axes[0, 1].set_xlabel('Windgeschwindigkeit (m/s)')
axes[0, 1].set_ylabel('Verbrauch (kWh)')
axes[0, 1].set_title('Verbrauch vs. Wind')

# Zeitreihe Temperatur
axes[1, 0].plot(df['timestamp'], df['dwd_temperature_current'])
axes[1, 0].set_xlabel('Datum')
axes[1, 0].set_ylabel('Temperatur (°C)')
axes[1, 0].set_title('Temperaturverlauf')

# Zeitreihe Verbrauch
axes[1, 1].plot(df['timestamp'], df['verbrauch_vortag'])
axes[1, 1].set_xlabel('Datum')
axes[1, 1].set_ylabel('Verbrauch (kWh)')
axes[1, 1].set_title('Verbrauchsverlauf')

plt.tight_layout()
plt.savefig('weather_analysis.png')
plt.show()
```

## Fehlerbehandlung

Das System ist robust gegenüber Fehlern bei der Wetterdaten-Abfrage:

- ✅ Bei API-Fehlern werden nur Heizungsdaten geloggt
- ✅ Wetterdaten-Spalten bleiben `NULL` wenn API nicht erreichbar
- ✅ Detailliertes Logging für Debugging
- ✅ Keine Unterbrechung des Hauptworkflows

## Troubleshooting

### Keine Wetterdaten in Datenbank

1. Prüfen Sie `.env` Datei:
   ```bash
   grep DWD_STATION_ID .env
   ```

2. Testen Sie die Wetterstation:
   ```bash
   source venv/bin/activate
   python3 dwd_weather.py
   ```

3. Prüfen Sie Logs:
   ```bash
   python3 wolf_logger.py 2>&1 | grep -i dwd
   ```

### Falsche Station ID

Wenn die Station ID nicht existiert, erhalten Sie einen 404 Fehler. Verwenden Sie eine gültige Station ID von der DWD-Liste.

### API Timeout

Bei langsamer Internetverbindung kann es zu Timeouts kommen. Der Standard-Timeout ist 10 Sekunden. Sie können dies im Code anpassen:

```python
# In dwd_weather.py, Zeile ~49
response = requests.get(url, params=params, timeout=30)  # 30 Sekunden
```

## Weiterführende Links

- **DWD OpenData Portal:** https://opendata.dwd.de/
- **DWD API Dokumentation:** https://dwd.api.bund.dev
- **Stationsliste:** https://www.dwd.de/DE/leistungen/klimadatendeutschland/stationsliste.html
- **CDC Readme (Historische Daten):** https://opendata.dwd.de/climate_environment/CDC/Readme_intro_CDC_ftp.pdf

## Lizenz

Diese Integration nutzt offene Daten des Deutschen Wetterdienstes (DWD), die unter einer offenen Lizenz zur Verfügung gestellt werden.

**Quellenangabe:** Deutscher Wetterdienst (DWD)
