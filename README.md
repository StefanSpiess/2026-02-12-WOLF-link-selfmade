# Wolf Smartset Logger

Python-Tool zum automatischen Loggen von Heizungsdaten (Wolf Wärmepumpe) in eine SQLite-Datenbank.

## Features

- ✅ OAuth2 PKCE Login (vollautomatisch)
- ✅ Loggt wichtige Metriken: Temperaturen, Verbrauch, JAZ
- ✅ SQLite-Datenbank für historische Daten
- ✅ CSV-Export für Excel/LibreOffice
- ✅ Einfache Abfrage-Tools

## Installation

```bash
cd wolf-logger

# Virtual Environment erstellen
python3 -m venv venv
source venv/bin/activate

# Dependencies installieren
pip install -r requirements.txt

# Credentials konfigurieren
cp .env.template .env
nano .env  # Username und Password eintragen
```

## Verwendung

### Einmal manuell ausführen

```bash
source venv/bin/activate
python3 wolf_logger.py
```

Dies:
1. Loggt sich bei Wolf Smartset ein (OAuth2 PKCE)
2. Holt aktuelle Heizungsdaten
3. Speichert Metriken in `data/wolf.db` (SQLite)
4. Schreibt Daten auch in `data/wolf.csv` (für Excel)

### CSV-Export für Excel

Die Daten werden automatisch in `data/wolf.csv` geschrieben (jeder Run fügt eine Zeile hinzu).

**Kompletten DB-Dump in CSV:**

```bash
# Exportiert alle Daten aus SQLite in eine neue CSV
python3 export_csv.py

# Oder mit eigenem Dateinamen:
python3 export_csv.py data/meine_daten.csv
```

Die CSV kann direkt in Excel oder LibreOffice geöffnet werden.

### Daten abfragen

```bash
# Letzte 10 Einträge
python3 query_data.py

# Heutige Daten
python3 query_data.py today

# Statistik der letzten 7 Tage
python3 query_data.py stats

# Statistik der letzten 30 Tage
python3 query_data.py stats 30

# Letzte 50 Einträge
python3 query_data.py latest 50
```

## Automatisches Logging mit Cron

**Alle 15 Minuten:**

```bash
crontab -e
```

Füge hinzu:

```cron
*/15 * * * * cd /home/stefanspiess/repositories/2026-02-12-WOLF-link-selfmade/wolf-logger && ./venv/bin/python3 wolf_logger.py >> logs/cron.log 2>&1
```

**Täglich um 6:00 Uhr:**

```cron
0 6 * * * cd /home/stefanspiess/repositories/2026-02-12-WOLF-link-selfmade/wolf-logger && ./venv/bin/python3 wolf_logger.py >> logs/cron.log 2>&1
```

**Logs-Ordner erstellen:**

```bash
mkdir -p logs
```

## Gespeicherte Daten

Die folgenden Metriken werden pro Messung gespeichert:

| Feld | Beschreibung | Einheit |
|------|--------------|---------|
| `timestamp` | Zeitpunkt der Messung | ISO 8601 |
| `vorlauftemperatur` | Kesseltemperatur Vorlauf | °C |
| `ruecklauftemperatur` | Rücklauftemperatur | °C |
| `kesseltemperatur` | Kesseltemperatur | °C |
| `aussentemperatur` | Außentemperatur | °C |
| `gesamtverbrauch` | Gesamtverbrauch aktuelles Jahr | kWh |
| `verbrauch_heizung` | Verbrauch Heizung | kWh |
| `verbrauch_warmwasser` | Verbrauch Warmwasser | kWh |
| `jaz` | Jahresarbeitszahl aktuelles Jahr | - |

## Datenbank direkt abfragen

Falls `sqlite3` installiert ist:

```bash
# Alle Daten anzeigen
sqlite3 data/wolf.db "SELECT * FROM heating_data;"

# Letzte 5 Messungen
sqlite3 data/wolf.db "SELECT timestamp, vorlauftemperatur, aussentemperatur, jaz FROM heating_data ORDER BY timestamp DESC LIMIT 5;"

# Durchschnitt der letzten 24h
sqlite3 data/wolf.db "SELECT AVG(vorlauftemperatur), AVG(aussentemperatur), AVG(jaz) FROM heating_data WHERE timestamp >= datetime('now', '-1 day');"
```

## Als Python-Library nutzen

```python
from wolf_logger import WolfLogger

# Logger erstellen
wolf = WolfLogger()

# Einloggen
wolf.login()

# Daten holen und in DB speichern
metrics, row_id = wolf.log_data()

print(f"Außentemperatur: {metrics['aussentemperatur']}°C")
print(f"JAZ: {metrics['jaz']}")

# Oder nur GUI-Daten holen (ohne DB)
gui_data = wolf.get_gui_description()
```

## Troubleshooting

**"WOLF_USERNAME and WOLF_PASSWORD must be set"**
→ `.env` Datei erstellen und Credentials eintragen

**"Token expired or missing"**
→ Normal. Script loggt sich automatisch neu ein.

**"Session ungültig"**
→ Prüfe, ob System-ID und Gateway-ID in `.env` korrekt sind.

## Struktur

```
wolf-logger/
├── wolf_logger.py      # Hauptscript
├── query_data.py       # Daten abfragen
├── requirements.txt    # Dependencies
├── .env                # Credentials (nicht committen!)
├── .gitignore          # Git-Ignore-Regeln
├── data/
│   └── wolf.db         # SQLite-Datenbank
└── logs/               # Cronjob-Logs (optional)
```

## Sicherheit

- `.env` Datei wird **nicht** ins Git committed
- Credentials nur lokal gespeichert
- Token läuft nach 1 Stunde ab (automatisches Re-Login)

## Credits

Entwickelt für Wolf Smartset Portal (https://www.wolf-smartset.com)

## Lizenz

MIT
