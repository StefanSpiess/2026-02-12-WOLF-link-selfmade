#!/usr/bin/env python
"""
Database operations for Wolf heating data
Handles SQLite database and CSV exports.
"""

import sqlite3
import csv
import logging
from pathlib import Path
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def init_database(db_path="data/wolf.db"):
    """
    Initialize SQLite database with heating data table
    
    Args:
        db_path: Path to SQLite database file
    """
    # Ensure directory exists
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS heating_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            vorlauftemperatur REAL,
            ruecklauftemperatur REAL,
            kesseltemperatur REAL,
            aussentemperatur REAL,
            gesamtverbrauch REAL,
            waermemenge_heizung REAL,
            waermemenge_warmwasser REAL,
            verbrauch_vortag REAL,
            verbrauch_aktueller_monat REAL,
            erzeugte_waermemenge_jahr REAL,
            jaz REAL,
            dwd_timestamp TEXT,
            dwd_station_id TEXT,
            dwd_temperature_min REAL,
            dwd_temperature_max REAL,
            dwd_temperature_current REAL,
            dwd_wind_speed REAL,
            dwd_wind_direction INTEGER,
            dwd_wind_gust REAL,
            dwd_precipitation_daily REAL,
            dwd_sunshine_minutes INTEGER,
            dwd_humidity REAL,
            dwd_pressure REAL,
            dwd_cloud_cover INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create index on timestamp for faster queries
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_timestamp 
        ON heating_data(timestamp)
    """)

    conn.commit()
    conn.close()
    logger.info(f"Database initialized: {db_path}")


def save_metrics_to_db(metrics, db_path="data/wolf.db"):
    """
    Save metrics to SQLite database
    
    Args:
        metrics: Dictionary with heating/weather metrics
        db_path: Path to SQLite database file
        
    Returns:
        int: Row ID of inserted record
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO heating_data (
            timestamp, vorlauftemperatur, ruecklauftemperatur, kesseltemperatur,
            aussentemperatur, gesamtverbrauch, waermemenge_heizung, waermemenge_warmwasser,
            verbrauch_vortag, verbrauch_aktueller_monat, erzeugte_waermemenge_jahr, jaz,
            dwd_timestamp, dwd_station_id, dwd_temperature_min, dwd_temperature_max,
            dwd_temperature_current, dwd_wind_speed, dwd_wind_direction, dwd_wind_gust,
            dwd_precipitation_daily, dwd_sunshine_minutes, dwd_humidity, dwd_pressure,
            dwd_cloud_cover
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            metrics["timestamp"],
            metrics["vorlauftemperatur"],
            metrics["ruecklauftemperatur"],
            metrics["kesseltemperatur"],
            metrics["aussentemperatur"],
            metrics["gesamtverbrauch"],
            metrics["waermemenge_heizung"],
            metrics["waermemenge_warmwasser"],
            metrics["verbrauch_vortag"],
            metrics["verbrauch_aktueller_monat"],
            metrics["erzeugte_waermemenge_jahr"],
            metrics["jaz"],
            metrics.get("dwd_timestamp"),
            metrics.get("dwd_station_id"),
            metrics.get("dwd_temperature_min"),
            metrics.get("dwd_temperature_max"),
            metrics.get("dwd_temperature_current"),
            metrics.get("dwd_wind_speed"),
            metrics.get("dwd_wind_direction"),
            metrics.get("dwd_wind_gust"),
            metrics.get("dwd_precipitation_daily"),
            metrics.get("dwd_sunshine_minutes"),
            metrics.get("dwd_humidity"),
            metrics.get("dwd_pressure"),
            metrics.get("dwd_cloud_cover"),
        ),
    )

    conn.commit()
    row_id = cursor.lastrowid
    conn.close()

    logger.info(f"Metrics saved to database (row {row_id})")
    return row_id


def save_metrics_to_csv(metrics, csv_path="data/wolf.csv"):
    """
    Save metrics to CSV file (append mode)
    
    Args:
        metrics: Dictionary with heating/weather metrics
        csv_path: Path to CSV file
    """
    file_exists = Path(csv_path).exists()

    # Ensure directory exists
    Path(csv_path).parent.mkdir(parents=True, exist_ok=True)

    with open(csv_path, "a", newline="", encoding="utf-8") as f:
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
            "dwd_timestamp",
            "dwd_station_id",
            "dwd_temperature_min",
            "dwd_temperature_max",
            "dwd_temperature_current",
            "dwd_wind_speed",
            "dwd_wind_direction",
            "dwd_wind_gust",
            "dwd_precipitation_daily",
            "dwd_sunshine_minutes",
            "dwd_humidity",
            "dwd_pressure",
            "dwd_cloud_cover",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")

        # Write header only if file is new
        if not file_exists:
            writer.writeheader()

        writer.writerow(metrics)

    logger.info(f"Metrics saved to CSV: {csv_path}")


def query_latest(db_path="data/wolf.db", limit=10):
    """
    Query latest entries from database
    
    Args:
        db_path: Path to SQLite database file
        limit: Maximum number of entries to return
        
    Returns:
        list: List of tuples with heating data
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT 
            timestamp,
            vorlauftemperatur,
            ruecklauftemperatur,
            kesseltemperatur,
            aussentemperatur,
            gesamtverbrauch,
            waermemenge_heizung,
            waermemenge_warmwasser,
            verbrauch_vortag,
            verbrauch_aktueller_monat,
            erzeugte_waermemenge_jahr,
            jaz
        FROM heating_data
        ORDER BY timestamp DESC
        LIMIT ?
    """,
        (limit,),
    )

    rows = cursor.fetchall()
    conn.close()

    return rows


def query_today(db_path="data/wolf.db"):
    """
    Query today's entries from database
    
    Args:
        db_path: Path to SQLite database file
        
    Returns:
        list: List of tuples with today's heating data
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    today = datetime.now().strftime("%Y-%m-%d")

    cursor.execute(
        """
        SELECT 
            timestamp,
            vorlauftemperatur,
            ruecklauftemperatur,
            aussentemperatur,
            jaz
        FROM heating_data
        WHERE date(timestamp) = ?
        ORDER BY timestamp ASC
    """,
        (today,),
    )

    rows = cursor.fetchall()
    conn.close()

    return rows


def query_stats(db_path="data/wolf.db", days=7):
    """
    Query statistics for the last N days
    
    Args:
        db_path: Path to SQLite database file
        days: Number of days to include in statistics
        
    Returns:
        dict: Statistics dictionary
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    cursor.execute(
        """
        SELECT 
            COUNT(*) as count,
            AVG(vorlauftemperatur) as avg_vorlauf,
            AVG(ruecklauftemperatur) as avg_ruecklauf,
            AVG(aussentemperatur) as avg_aussen,
            AVG(jaz) as avg_jaz,
            MIN(aussentemperatur) as min_aussen,
            MAX(aussentemperatur) as max_aussen
        FROM heating_data
        WHERE date(timestamp) >= ?
    """,
        (start_date,),
    )

    row = cursor.fetchone()
    conn.close()

    if row and row[0] > 0:
        return {
            "count": row[0],
            "avg_vorlauf": row[1],
            "avg_ruecklauf": row[2],
            "avg_aussen": row[3],
            "avg_jaz": row[4],
            "min_aussen": row[5],
            "max_aussen": row[6],
            "days": days,
        }
    return None


def export_to_csv(db_path="data/wolf.db", csv_path="data/wolf_export.csv"):
    """
    Export all data from SQLite database to CSV
    
    Args:
        db_path: Path to SQLite database file
        csv_path: Path to CSV output file
        
    Returns:
        int: Number of rows exported
    """
    if not Path(db_path).exists():
        logger.error(f"Database not found: {db_path}")
        return 0

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
        logger.warning("No data in database to export.")
        return 0

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

    logger.info(f"Exported {len(rows)} rows to {csv_path}")
    return len(rows)
