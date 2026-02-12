#!/usr/bin/env python
"""
Wolf Smartset Logger - Legacy wrapper script

This script is maintained for backward compatibility.
For new projects, use the wolf_smartset package directly:

    from wolf_smartset import WolfLogger, database
    
    wolf = WolfLogger()
    wolf.login()
    gui_data = wolf.get_gui_description()
    metrics = wolf.extract_key_metrics(gui_data)
    database.init_database()
    database.save_metrics_to_db(metrics)

Or use the CLI commands after installation:
    wolf-logger    # Log data
    wolf-query     # Query data
    wolf-export    # Export to CSV
"""

from wolf_smartset.cli.logger import main

if __name__ == "__main__":
    main()
