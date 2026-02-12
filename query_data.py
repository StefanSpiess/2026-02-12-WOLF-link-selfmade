#!/usr/bin/env python3
"""
Query Wolf heating data from SQLite database
"""

import sqlite3
import sys
from datetime import datetime, timedelta

def query_latest(db_path='data/wolf.db', limit=10):
    """Show latest entries"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
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
    ''', (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        print("No data in database yet.")
        return
    
    print(f"\n{'='*140}")
    print("LATEST MEASUREMENTS")
    print("="*140)
    
    for row in rows:
        timestamp = datetime.fromisoformat(row[0]).strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n[{timestamp}]")
        print(f"  Temperaturen:  Vorlauf {row[1]:.1f}°C | Rücklauf {row[2]:.1f}°C | Kessel {row[3]:.1f}°C | Außen {row[4]:.1f}°C")
        print(f"  Verbrauch:     Jahr {row[5]:.0f} kWh (Strom)")
        print(f"  Wärmemenge:    Heizung {row[6]:.0f} kWh | Warmwasser {row[7]:.0f} kWh")
        print(f"  Details:       Vortag {row[8]:.0f} kWh | Monat {row[9]:.0f} kWh | Erzeugt {row[10]:.0f} kWh")
        print(f"  JAZ:           {row[11]:.2f}")

def query_today(db_path='data/wolf.db'):
    """Show today's entries"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    cursor.execute('''
        SELECT 
            timestamp,
            vorlauftemperatur,
            ruecklauftemperatur,
            aussentemperatur,
            jaz
        FROM heating_data
        WHERE date(timestamp) = ?
        ORDER BY timestamp ASC
    ''', (today,))
    
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        print(f"No data for today ({today})")
        return
    
    print(f"\nData for {today}:")
    print(f"{'Time':<15} {'Vorlauf':<10} {'Rücklauf':<10} {'Außen':<10} {'JAZ':<8}")
    print("="*60)
    
    for row in rows:
        time = datetime.fromisoformat(row[0]).strftime("%H:%M:%S")
        vorlauf = f"{row[1]:.1f}°C" if row[1] else "N/A"
        ruecklauf = f"{row[2]:.1f}°C" if row[2] else "N/A"
        aussen = f"{row[3]:.1f}°C" if row[3] else "N/A"
        jaz = f"{row[4]:.2f}" if row[4] else "N/A"
        
        print(f"{time:<15} {vorlauf:<10} {ruecklauf:<10} {aussen:<10} {jaz:<8}")

def query_stats(db_path='data/wolf.db', days=7):
    """Show statistics for last N days"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    
    cursor.execute('''
        SELECT 
            COUNT(*) as count,
            AVG(vorlauftemperatur) as avg_vorlauf,
            AVG(ruecklauftemperatur) as avg_ruecklauf,
            AVG(aussentemperatur) as avg_aussen,
            MIN(aussentemperatur) as min_aussen,
            MAX(aussentemperatur) as max_aussen,
            AVG(jaz) as avg_jaz,
            MAX(gesamtverbrauch) as total_verbrauch,
            MAX(waermemenge_heizung) as total_heizung,
            MAX(waermemenge_warmwasser) as total_warmwasser,
            MAX(erzeugte_waermemenge_jahr) as total_erzeugt
        FROM heating_data
        WHERE date(timestamp) >= ?
    ''', (since,))
    
    row = cursor.fetchone()
    conn.close()
    
    if not row or row[0] == 0:
        print(f"No data for last {days} days")
        return
    
    print(f"\n{'='*60}")
    print(f"STATISTICS for last {days} days (since {since})")
    print("="*60)
    print(f"\nMessungen:           {row[0]}")
    print(f"\nTemperaturen:")
    print(f"  Ø Vorlauf:         {row[1]:.1f}°C" if row[1] else "N/A")
    print(f"  Ø Rücklauf:        {row[2]:.1f}°C" if row[2] else "N/A")
    print(f"  Ø Außen:           {row[3]:.1f}°C" if row[3] else "N/A")
    print(f"  Min Außen:         {row[4]:.1f}°C" if row[4] else "N/A")
    print(f"  Max Außen:         {row[5]:.1f}°C" if row[5] else "N/A")
    print(f"\nEnergie (kumulativ):")
    print(f"  Verbrauch Jahr:    {row[7]:.0f} kWh (Strom)" if row[7] else "N/A")
    print(f"  Wärmemenge HZ:     {row[8]:.0f} kWh (erzeugt)" if row[8] else "N/A")
    print(f"  Wärmemenge WW:     {row[9]:.0f} kWh (erzeugt)" if row[9] else "N/A")
    print(f"  Erzeugt (Jahr):    {row[10]:.0f} kWh (gesamt)" if row[10] else "N/A")
    print(f"\nEffizienz:")
    print(f"  Ø JAZ:             {row[6]:.2f}" if row[6] else "N/A")

def main():
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == 'today':
            query_today()
        elif command == 'stats':
            days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
            query_stats(days=days)
        elif command == 'latest':
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
            query_latest(limit=limit)
        else:
            print("Unknown command. Use: today, stats [days], or latest [limit]")
    else:
        # Default: show latest 10
        query_latest()

if __name__ == "__main__":
    main()
