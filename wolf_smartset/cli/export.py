#!/usr/bin/env python
"""
CLI command for exporting Wolf heating data to CSV
"""

import sys
from wolf_smartset import database


def main():
    """Main entry point for wolf-export CLI command"""
    if len(sys.argv) > 1:
        output_file = sys.argv[1]
    else:
        output_file = "data/wolf_export.csv"

    db_path = "data/wolf.db"
    
    print(f"Exporting data from {db_path} to {output_file}...")
    rows = database.export_to_csv(db_path=db_path, csv_path=output_file)
    
    if rows > 0:
        print(f"✓ Exported {rows} rows to {output_file}")
    else:
        print("No data to export")
        sys.exit(1)


if __name__ == "__main__":
    main()
