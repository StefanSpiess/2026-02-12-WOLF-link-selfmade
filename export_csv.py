#!/usr/bin/env python3
"""
Export complete SQLite database to CSV file
"""

import sqlite3
import csv
import sys
from pathlib import Path


def export_to_csv(db_path="data/wolf.db", csv_path="data/wolf_export.csv"):
    """Export all data from SQLite database to CSV"""

    if not Path(db_path).exists():
        print(f"Error: Database not found: {db_path}")
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get all data
    cursor.execute("""
        SELECT 
            timestamp, vorlauftemperatur, ruecklauftemperatur, kesseltemperatur,
            aussentemperatur, gesamtverbrauch, waermemenge_heizung, waermemenge_warmwasser,
            verbrauch_vortag, verbrauch_aktueller_monat, erzeugte_waermemenge_jahr, jaz
        FROM heating_data
        ORDER BY timestamp ASC
    """)

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print("No data in database to export.")
        return

    # Write to CSV
    fieldnames = [
        "timestamp",
        "vorlauftemperatur",
        "ruecklauftemperatur",
        "kesseltemperatur",
        "aussentemperatur",
        "gesamtverbrauch",
        "waermemenge_heizung",
        "waermemenge_warmwasser",
        "verbrauch_vortag",
        "verbrauch_aktueller_monat",
        "erzeugte_waermemenge_jahr",
        "jaz",
    ]

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(fieldnames)
        writer.writerows(rows)

    print(f"✓ Exported {len(rows)} rows to {csv_path}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        output_file = sys.argv[1]
    else:
        output_file = "data/wolf_export.csv"

    export_to_csv(csv_path=output_file)
