#!/usr/bin/env python
"""
CLI command for querying Wolf heating data
"""

import sys
from datetime import datetime
from wolf_smartset import database


def print_latest(rows):
    """Print latest measurements"""
    if not rows:
        print("No data in database yet.")
        return

    print(f"\n{'='*140}")
    print("LATEST MEASUREMENTS")
    print("=" * 140)

    for row in rows:
        timestamp = datetime.fromisoformat(row[0]).strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n[{timestamp}]")
        print(
            f"  Temperaturen:  Vorlauf {row[1]:.1f}°C | Rücklauf {row[2]:.1f}°C | Kessel {row[3]:.1f}°C | Außen {row[4]:.1f}°C"
        )
        print(f"  Verbrauch:     Jahr {row[5]:.0f} kWh (Strom)")
        print(
            f"  Wärmemenge:    Heizung {row[6]:.0f} kWh | Warmwasser {row[7]:.0f} kWh"
        )
        print(
            f"  Details:       Vortag {row[8]:.0f} kWh | Monat {row[9]:.0f} kWh | Erzeugt {row[10]:.0f} kWh"
        )
        print(f"  JAZ:           {row[11]:.2f}")


def print_today(rows, today):
    """Print today's data"""
    if not rows:
        print(f"No data for today ({today})")
        return

    print(f"\nData for {today}:")
    print(f"{'Time':<15} {'Vorlauf':<10} {'Rücklauf':<10} {'Außen':<10} {'JAZ':<8}")
    print("=" * 60)

    for row in rows:
        time = datetime.fromisoformat(row[0]).strftime("%H:%M:%S")
        vorlauf = f"{row[1]:.1f}°C" if row[1] else "N/A"
        ruecklauf = f"{row[2]:.1f}°C" if row[2] else "N/A"
        aussen = f"{row[3]:.1f}°C" if row[3] else "N/A"
        jaz = f"{row[4]:.2f}" if row[4] else "N/A"
        print(f"{time:<15} {vorlauf:<10} {ruecklauf:<10} {aussen:<10} {jaz:<8}")


def print_stats(stats):
    """Print statistics"""
    if not stats:
        print("No data available for statistics")
        return

    print(f"\nStatistics for the last {stats['days']} days:")
    print("=" * 60)
    print(f"Number of measurements: {stats['count']}")
    print(f"Average Vorlauf:        {stats['avg_vorlauf']:.1f}°C")
    print(f"Average Rücklauf:       {stats['avg_ruecklauf']:.1f}°C")
    print(f"Average Außentemp:      {stats['avg_aussen']:.1f}°C")
    print(f"  Min Außentemp:        {stats['min_aussen']:.1f}°C")
    print(f"  Max Außentemp:        {stats['max_aussen']:.1f}°C")
    print(f"Average JAZ:            {stats['avg_jaz']:.2f}")
    print("=" * 60)


def main():
    """Main entry point for wolf-query CLI command"""
    db_path = "data/wolf.db"
    
    # Parse command line arguments
    if len(sys.argv) < 2:
        # Default: show latest 10 entries
        rows = database.query_latest(db_path, limit=10)
        print_latest(rows)
    elif sys.argv[1] == "today":
        # Show today's entries
        today = datetime.now().strftime("%Y-%m-%d")
        rows = database.query_today(db_path)
        print_today(rows, today)
    elif sys.argv[1] == "stats":
        # Show statistics
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
        stats = database.query_stats(db_path, days=days)
        print_stats(stats)
    elif sys.argv[1] == "latest":
        # Show latest N entries
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        rows = database.query_latest(db_path, limit=limit)
        print_latest(rows)
    else:
        print("Wolf Smartset Query Tool")
        print("\nUsage:")
        print("  wolf-query              Show latest 10 entries")
        print("  wolf-query today        Show today's entries")
        print("  wolf-query stats [N]    Show statistics for last N days (default: 7)")
        print("  wolf-query latest [N]   Show latest N entries (default: 10)")
        sys.exit(1)


if __name__ == "__main__":
    main()
