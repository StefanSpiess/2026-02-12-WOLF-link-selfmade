#!/usr/bin/env python
"""
DWD Weather API Integration - Legacy wrapper script

This script is maintained for backward compatibility.
For new projects, import directly from the package:

    from wolf_smartset import DWDWeatherClient
    
    client = DWDWeatherClient(station_id="G005")
    metrics = client.get_weather_metrics()
"""

from wolf_smartset.weather import DWDWeatherClient
import sys
import os
import logging

# For testing
def main():
    """Test the DWD Weather Client"""
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    station_id = os.getenv("DWD_STATION_ID", "G005")

    print(f"\nTesting DWD Weather API with station: {station_id}")
    print("=" * 60)

    try:
        client = DWDWeatherClient(station_id=station_id)
        metrics = client.get_weather_metrics()

        print("\nWeather Data:")
        print("=" * 60)
        print(f"Station: {metrics['dwd_station_name']} ({metrics['dwd_station_id']})")
        print(f"Timestamp: {metrics['dwd_timestamp']}")
        print(f"Temperature (current): {metrics['dwd_temperature_current']}°C")
        print(
            f"Temperature (min/max): {metrics['dwd_temperature_min']}°C / {metrics['dwd_temperature_max']}°C"
        )
        print(f"Wind Speed: {metrics['dwd_wind_speed']} m/s")
        print(f"Wind Gust: {metrics['dwd_wind_gust']} m/s")
        print(f"Wind Direction: {metrics['dwd_wind_direction']}°")
        print(f"Precipitation (daily): {metrics['dwd_precipitation_daily']} mm")
        print(f"Sunshine duration: {metrics['dwd_sunshine_minutes']} seconds")
        print(f"Humidity: {metrics['dwd_humidity']}%")
        print(f"Pressure: {metrics['dwd_pressure']} hPa")
        print(f"Cloud Cover: {metrics['dwd_cloud_cover']}%")
        print("=" * 60)

    except Exception as e:
        logging.error(f"Test failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
