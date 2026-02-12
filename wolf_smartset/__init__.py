"""
Wolf Smartset Logger - Python Library for Wolf heating systems

This library provides tools to interact with Wolf Smartset Portal,
fetch heating system data, and optionally integrate weather data from DWD.

Example usage:
    >>> from wolf_smartset import WolfLogger, DWDWeatherClient
    >>> from wolf_smartset import database
    >>> 
    >>> # Initialize Wolf client
    >>> wolf = WolfLogger()
    >>> wolf.login()
    >>> 
    >>> # Fetch heating data
    >>> gui_data = wolf.get_gui_description()
    >>> metrics = wolf.extract_key_metrics(gui_data)
    >>> 
    >>> # Optional: Add weather data
    >>> weather = DWDWeatherClient(station_id="G005")
    >>> weather_metrics = weather.get_weather_metrics()
    >>> metrics.update(weather_metrics)
    >>> 
    >>> # Save to database
    >>> database.init_database()
    >>> database.save_metrics_to_db(metrics)
"""

__version__ = "0.1.0"

# Import public API
from wolf_smartset.client import (
    WolfLogger,
    WolfLoginError,
    MaintenanceError,
    InvalidCredentialsError,
)
from wolf_smartset.weather import DWDWeatherClient
from wolf_smartset import database

__all__ = [
    # Main classes
    "WolfLogger",
    "DWDWeatherClient",
    # Exceptions
    "WolfLoginError",
    "MaintenanceError",
    "InvalidCredentialsError",
    # Database module
    "database",
    # Version
    "__version__",
]
