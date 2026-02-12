# Wolf Smartset Logger

Python-Tool zum automatischen Loggen von Heizungsdaten (Wolf Wärmepumpe) in eine SQLite-Datenbank.

## Features

- ✅ **OAuth2 PKCE Login** (vollautomatisch)
- ✅ **Datenerfassung**: Temperaturen, Verbrauch, JAZ (Jahresarbeitszahl)
- ✅ **SQLite-Datenbank** für historische Daten
- ✅ **CSV-Export** für Excel/LibreOffice
- ✅ **Duplikats-Bereinigung** (ein Eintrag pro Tag)
- ✅ **Abfrage-Tools** mit Statistiken

## Installation

```bash
# Repository klonen und ins Verzeichnis wechseln
cd wolf-logger

# Virtual Environment erstellen
python3 -m venv venv
source venv/bin/activate

# Dependencies installieren
pip install -r requirements.txt

# Credentials konfigurieren
cp .env.template .env
nano .env  # Username, Password, System-ID und Gateway-ID eintragen
```

**Inhalt der `.env` Datei:**
```env
WOLF_USERNAME=dein_username
WOLF_PASSWORD=dein_password
WOLF_SYSTEM_ID=85915
WOLF_GATEWAY_ID=62897
```

> **Hinweis:** System-ID und Gateway-ID findest du im Wolf Smartset Portal oder in der Browser-Konsole.

## Verwendung

### 1. Daten loggen (`wolf_logger.py`)

**Einmal manuell ausführen:**

```bash
source venv/bin/activate
python3 wolf_logger.py
```

Das Script:
1. Führt OAuth2 PKCE Login durch
2. Holt aktuelle Heizungsdaten vom Wolf Smartset Portal
3. Speichert Daten in SQLite-Datenbank (`data/wolf.db`)
4. Hängt eine Zeile an CSV-Datei an (`data/wolf.csv`)

### 2. Daten abfragen (`query_data.py`)

**Verschiedene Abfragemöglichkeiten:**

```bash
# Letzte 10 Einträge anzeigen
python3 query_data.py

# Alle Einträge von heute
python3 query_data.py today

# Statistik der letzten 7 Tage (Durchschnittswerte)
python3 query_data.py stats

# Statistik der letzten 30 Tage
python3 query_data.py stats 30

# Letzte 50 Einträge
python3 query_data.py latest 50
```

**Ausgabe-Beispiel:**

```
[2026-02-12 10:30:15]
  Temperaturen:  Vorlauf 46.4°C | Rücklauf 39.9°C | Kessel 46.4°C | Außen 5.2°C
  Verbrauch:     Jahr 1250 kWh (Strom)
  Wärmemenge:    Heizung 4850 kWh | Warmwasser 950 kWh
  JAZ:           4.64
```

### 3. CSV-Export (`export_csv.py`)

**Vollständiger Datenbank-Export:**

```bash
# Alle Daten aus SQLite in CSV exportieren
python3 export_csv.py

# Mit benutzerdefiniertem Dateinamen
python3 export_csv.py data/meine_daten.csv
```

> **Unterschied:** `wolf_logger.py` fügt bei jedem Lauf **eine** Zeile zu `data/wolf.csv` hinzu, während `export_csv.py` die **gesamte** Datenbank in eine neue CSV-Datei exportiert.

### 4. Duplikate bereinigen (`deduplicate_data.py`)

Falls durch mehrfaches Logging am selben Tag Duplikate entstanden sind:

```bash
# Dry-Run (zeigt nur, was gelöscht würde)
python3 deduplicate_data.py

# Duplikate tatsächlich entfernen
python3 deduplicate_data.py --execute

# Nur CSV bereinigen
python3 deduplicate_data.py --csv-only --execute

# Nur Datenbank bereinigen
python3 deduplicate_data.py --db-only --execute
```

Das Tool behält pro Tag nur den **letzten** Eintrag (neueste Messung).

## Automatisches Logging mit Cron

Für kontinuierliche Datenerfassung kann ein Cronjob eingerichtet werden:

```bash
# Crontab bearbeiten
crontab -e
```

**Alle 15 Minuten:**
```cron
*/15 * * * * cd /pfad/zum/wolf-logger && ./venv/bin/python3 wolf_logger.py >> logs/cron.log 2>&1
```

**Täglich um 6:00 Uhr:**
```cron
0 6 * * * cd /pfad/zum/wolf-logger && ./venv/bin/python3 wolf_logger.py >> logs/cron.log 2>&1
```

**Logs-Ordner erstellen:**
```bash
mkdir -p logs
```

> **Tipp:** Nach dem Einrichten des Cronjobs empfiehlt es sich, regelmäßig `deduplicate_data.py` auszuführen, falls versehentlich mehrfach pro Tag geloggt wurde.

## Gespeicherte Daten

Die folgenden Metriken werden pro Messung in der Datenbank gespeichert:

| Feld | Beschreibung | Einheit | Spalte in DB |
|------|--------------|---------|--------------|
| Zeitstempel | Zeitpunkt der Messung | ISO 8601 | `timestamp` |
| Vorlauftemperatur | Kesseltemperatur Vorlauf | °C | `vorlauftemperatur` |
| Rücklauftemperatur | Rücklauftemperatur | °C | `ruecklauftemperatur` |
| Kesseltemperatur | Kesseltemperatur | °C | `kesseltemperatur` |
| Außentemperatur | Außentemperatur | °C | `aussentemperatur` |
| Gesamtverbrauch Jahr | Stromverbrauch aktuelles Jahr | kWh | `gesamtverbrauch` |
| Wärmemenge Heizung | Erzeugte Wärmemenge für Heizung | kWh | `waermemenge_heizung` |
| Wärmemenge Warmwasser | Erzeugte Wärmemenge für Warmwasser | kWh | `waermemenge_warmwasser` |
| Verbrauch Vortag | Verbrauch des Vortages | kWh | `verbrauch_vortag` |
| Verbrauch aktueller Monat | Verbrauch im aktuellen Monat | kWh | `verbrauch_aktueller_monat` |
| Erzeugte Wärmemenge Jahr | Gesamte erzeugte Wärmemenge | kWh | `erzeugte_waermemenge_jahr` |
| JAZ | Jahresarbeitszahl | - | `jaz` |

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

## Projektstruktur

```
wolf-logger/
├── wolf_logger.py          # Hauptscript (Login, Datenerfassung, DB-Speicherung)
├── query_data.py           # Datenabfrage und Statistiken
├── export_csv.py           # Vollständiger CSV-Export der Datenbank
├── deduplicate_data.py     # Duplikate bereinigen (CSV und SQLite)
├── requirements.txt        # Python-Dependencies
├── .env.template           # Vorlage für Konfiguration
├── .env                    # Credentials (nicht im Git!)
├── .gitignore             # Git-Ignore-Regeln
├── README.md              # Diese Dokumentation
├── wolf_data.json         # Beispiel API-Daten (optional)
├── data/
│   ├── wolf.db            # SQLite-Datenbank (wird automatisch erstellt)
│   └── wolf.csv           # CSV-Ausgabe (wird automatisch befüllt)
└── logs/
    └── cron.log           # Cronjob-Logs (optional)
```

## Troubleshooting

**"WOLF_USERNAME and WOLF_PASSWORD must be set"**
→ `.env` Datei erstellen und Credentials eintragen

**"Token expired or missing"**
→ Normal. Script loggt sich automatisch neu ein.

**"Session ungültig"**
→ Prüfe, ob System-ID und Gateway-ID in `.env` korrekt sind.

**Mehrere Einträge pro Tag**
→ Nutze `deduplicate_data.py` um Duplikate zu bereinigen.

**CSV-Datei zu groß**
→ Exportiere nur relevante Zeiträume mit `query_data.py` und weiterleiteter Ausgabe:
```bash
python3 query_data.py latest 1000 > export.txt
```

## Sicherheit

- `.env` Datei wird **nicht** ins Git committed (siehe `.gitignore`)
- Credentials nur lokal gespeichert
- OAuth2 PKCE Flow für sichere Authentifizierung
- Access Token läuft nach 1 Stunde ab (automatisches Re-Login)

## Credits

Entwickelt für Wolf Smartset Portal: https://www.wolf-smartset.com

## Lizenz

MIT
