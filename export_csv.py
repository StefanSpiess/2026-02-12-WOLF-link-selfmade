#!/usr/bin/env python
"""
Export Wolf heating data to CSV - Legacy wrapper script

This script is maintained for backward compatibility.
For new projects, use the CLI command or import directly:

    # CLI command:
    wolf-export
    wolf-export output.csv

    # Or import:
    from wolf_smartset import database
    database.export_to_csv(csv_path="output.csv")
"""

from wolf_smartset.cli.export import main

if __name__ == "__main__":
    main()
