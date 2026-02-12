#!/usr/bin/env python3
"""
Deduplicate Wolf heating data - keep only latest entry per day
Processes both CSV and SQLite database files
"""

import sqlite3
import sys
import csv
from pathlib import Path
from datetime import datetime
import argparse
from collections import defaultdict


def deduplicate_csv(csv_path='data/wolf.csv', dry_run=False):
    """
    Remove duplicate entries from CSV file, keeping only latest entry per day
    
    Args:
        csv_path: Path to CSV file
        dry_run: If True, don't modify file, just show statistics
        
    Returns:
        dict: Statistics (before_count, after_count, removed_count, days_with_duplicates)
    """
    if not Path(csv_path).exists():
        print(f"❌ CSV file not found: {csv_path}")
        return None
    
    # Read CSV
    print(f"\n📄 Processing CSV: {csv_path}")
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames
    
    before_count = len(rows)
    
    if before_count == 0:
        print("   No data in CSV file")
        return {'before_count': 0, 'after_count': 0, 'removed_count': 0, 'days_with_duplicates': {}}
    
    # Group rows by date, keeping only latest per day
    rows_by_date = defaultdict(list)
    
    for row in rows:
        # Parse timestamp and extract date
        try:
            # Handle ISO format timestamps like "2026-02-12T01:55:46.920165+00:00"
            timestamp_str = row['timestamp']
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            date = timestamp.date()
            
            # Store row with its parsed timestamp for sorting
            rows_by_date[date].append((timestamp, row))
        except Exception as e:
            print(f"   ⚠️  Warning: Could not parse timestamp '{row.get('timestamp')}': {e}")
            continue
    
    # Find duplicates per day and keep only latest
    days_with_duplicates = {}
    deduplicated_rows = []
    
    for date in sorted(rows_by_date.keys()):
        entries = rows_by_date[date]
        count = len(entries)
        
        if count > 1:
            days_with_duplicates[str(date)] = count
        
        # Sort by timestamp and keep latest (last one)
        entries.sort(key=lambda x: x[0])
        latest_entry = entries[-1][1]  # Get the row dict from the tuple
        deduplicated_rows.append(latest_entry)
    
    after_count = len(deduplicated_rows)
    removed_count = before_count - after_count
    
    # Write back to CSV if not dry run
    if not dry_run:
        with open(csv_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(deduplicated_rows)
        print(f"   ✓ CSV deduplicated: {before_count} → {after_count} entries ({removed_count} removed)")
    else:
        print(f"   [DRY RUN] Would remove {removed_count} duplicates: {before_count} → {after_count} entries")
    
    return {
        'before_count': before_count,
        'after_count': after_count,
        'removed_count': removed_count,
        'days_with_duplicates': days_with_duplicates
    }


def deduplicate_database(db_path='data/wolf.db', dry_run=False):
    """
    Remove duplicate entries from SQLite database, keeping only latest entry per day
    
    Args:
        db_path: Path to SQLite database
        dry_run: If True, don't modify database, just show statistics
        
    Returns:
        dict: Statistics (before_count, after_count, removed_count, days_with_duplicates)
    """
    if not Path(db_path).exists():
        print(f"❌ Database not found: {db_path}")
        return None
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print(f"\n💾 Processing Database: {db_path}")
    
    # Get current count
    cursor.execute('SELECT COUNT(*) FROM heating_data')
    before_count = cursor.fetchone()[0]
    
    if before_count == 0:
        print("   No data in database")
        conn.close()
        return {'before_count': 0, 'after_count': 0, 'removed_count': 0, 'days_with_duplicates': {}}
    
    # Find duplicates per day
    cursor.execute('''
        SELECT 
            date(timestamp) as day,
            COUNT(*) as count
        FROM heating_data
        GROUP BY date(timestamp)
        HAVING COUNT(*) > 1
        ORDER BY day
    ''')
    
    days_with_duplicates = {}
    for row in cursor.fetchall():
        days_with_duplicates[row[0]] = row[1]
    
    if not dry_run:
        # Delete all entries except the latest per day
        # Strategy: Keep only rows where id matches the max id for that day
        cursor.execute('''
            DELETE FROM heating_data
            WHERE id NOT IN (
                SELECT MAX(id)
                FROM heating_data
                GROUP BY date(timestamp)
            )
        ''')
        
        deleted_count = cursor.rowcount
        conn.commit()
        
        # Get new count
        cursor.execute('SELECT COUNT(*) FROM heating_data')
        after_count = cursor.fetchone()[0]
        
        print(f"   ✓ Database deduplicated: {before_count} → {after_count} entries ({deleted_count} removed)")
    else:
        # Calculate what would be removed
        cursor.execute('''
            SELECT COUNT(*)
            FROM heating_data
            WHERE id NOT IN (
                SELECT MAX(id)
                FROM heating_data
                GROUP BY date(timestamp)
            )
        ''')
        would_delete = cursor.fetchone()[0]
        after_count = before_count - would_delete
        
        print(f"   [DRY RUN] Would remove {would_delete} duplicates: {before_count} → {after_count} entries")
        deleted_count = would_delete
    
    conn.close()
    
    return {
        'before_count': before_count,
        'after_count': after_count,
        'removed_count': deleted_count,
        'days_with_duplicates': days_with_duplicates
    }


def show_statistics(csv_stats, db_stats):
    """Display detailed statistics about deduplication"""
    
    print("\n" + "="*80)
    print("📊 DEDUPLICATION STATISTICS")
    print("="*80)
    
    # CSV Statistics
    if csv_stats:
        print("\n📄 CSV File:")
        print(f"   Before:  {csv_stats['before_count']} entries")
        print(f"   After:   {csv_stats['after_count']} entries")
        print(f"   Removed: {csv_stats['removed_count']} duplicates")
        
        if csv_stats['days_with_duplicates']:
            print(f"\n   Days with duplicates: {len(csv_stats['days_with_duplicates'])}")
            for date, count in sorted(csv_stats['days_with_duplicates'].items(), 
                                      key=lambda x: x[1], reverse=True)[:10]:
                print(f"     • {date}: {count} entries (removed {count-1})")
    
    # Database Statistics
    if db_stats:
        print("\n💾 SQLite Database:")
        print(f"   Before:  {db_stats['before_count']} entries")
        print(f"   After:   {db_stats['after_count']} entries")
        print(f"   Removed: {db_stats['removed_count']} duplicates")
        
        if db_stats['days_with_duplicates']:
            print(f"\n   Days with duplicates: {len(db_stats['days_with_duplicates'])}")
            for date, count in sorted(db_stats['days_with_duplicates'].items(), 
                                      key=lambda x: x[1], reverse=True)[:10]:
                print(f"     • {date}: {count} entries (removed {count-1})")
    
    # Summary
    total_removed = (csv_stats['removed_count'] if csv_stats else 0) + \
                    (db_stats['removed_count'] if db_stats else 0)
    
    print("\n" + "="*80)
    print(f"✓ COMPLETED: {total_removed} duplicate entries removed in total")
    print("="*80 + "\n")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Deduplicate Wolf heating data - keep only latest entry per day',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    # Deduplicate both CSV and database
  %(prog)s --csv-only         # Only deduplicate CSV file
  %(prog)s --db-only          # Only deduplicate database
  %(prog)s --dry-run          # Show what would be changed without modifying files
  
Note: This will OVERWRITE the original files. There is no backup!
        """
    )
    
    parser.add_argument('--csv-only', action='store_true',
                        help='Only process CSV file')
    parser.add_argument('--db-only', action='store_true',
                        help='Only process SQLite database')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show statistics without modifying files')
    parser.add_argument('--csv-path', default='data/wolf.csv',
                        help='Path to CSV file (default: data/wolf.csv)')
    parser.add_argument('--db-path', default='data/wolf.db',
                        help='Path to SQLite database (default: data/wolf.db)')
    
    args = parser.parse_args()
    
    # Determine what to process
    process_csv = not args.db_only
    process_db = not args.csv_only
    
    # Show warning if not dry run
    if not args.dry_run:
        print("\n⚠️  WARNING: This will OVERWRITE the original files!")
        print("   No backup will be created.")
        print("   Press Ctrl+C within 3 seconds to cancel...\n")
        try:
            import time
            time.sleep(3)
        except KeyboardInterrupt:
            print("\n❌ Cancelled by user")
            sys.exit(1)
    
    # Process files
    csv_stats = None
    db_stats = None
    
    if process_csv:
        csv_stats = deduplicate_csv(args.csv_path, dry_run=args.dry_run)
    
    if process_db:
        db_stats = deduplicate_database(args.db_path, dry_run=args.dry_run)
    
    # Show statistics
    if csv_stats is not None or db_stats is not None:
        show_statistics(csv_stats, db_stats)
    else:
        print("\n❌ No files were processed")
        sys.exit(1)
    
    if args.dry_run:
        print("🔍 This was a DRY RUN - no files were modified")
        print("   Run without --dry-run to actually deduplicate the data\n")


if __name__ == "__main__":
    main()
