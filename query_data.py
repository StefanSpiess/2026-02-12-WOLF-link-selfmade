#!/usr/bin/env python
"""
Query Wolf heating data - Legacy wrapper script

This script is maintained for backward compatibility.
For new projects, use the CLI command or import directly:

    # CLI command:
    wolf-query
    wolf-query today
    wolf-query stats 7
    wolf-query latest 20

    # Or import:
    from wolf_smartset import database
    rows = database.query_latest(limit=10)
"""

from wolf_smartset.cli.query import main

if __name__ == "__main__":
    main()
