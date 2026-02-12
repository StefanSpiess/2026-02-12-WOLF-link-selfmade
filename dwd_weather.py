#!/usr/bin/env python3
"""
DWD Weather API Integration
Fetches weather data from Deutscher Wetterdienst (German Weather Service) API.
"""

import requests
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class DWDWeatherClient:
    """Client for fetching weather data from DWD API"""

    def __init__(self, station_id=None):
        """
        Initialize DWD Weather Client

        Args:
            station_id: DWD station ID (e.g., 'G005' for a specific station)
                       If None, you need to set it via environment variable or config
        """
        self.base_url = "https://app-prod-ws.warnwetter.de/v30"
        self.station_id = station_id

        logger.info(
            f"DWD Weather Client initialized (station: {station_id or 'not set'})"
        )

    def get_station_data(self, station_id=None):
        """
        Fetch weather data for a specific station

        Args:
            station_id: DWD station ID (overrides instance station_id)

        Returns:
            dict: Weather data from the station
        """
        sid = station_id or self.station_id

        if not sid:
            raise ValueError(
                "station_id must be provided either in __init__ or get_station_data"
            )

        url = f"{self.base_url}/stationOverviewExtended"
        params = {"stationIds": sid}

        logger.info(f"Fetching weather data for station {sid}...")

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            logger.debug(f"Received weather data: {data}")
            return data

        except requests.RequestException as e:
            logger.error(f"Failed to fetch weather data: {e}")
            raise

    def extract_weather_metrics(self, station_data):
        """
        Extract relevant weather metrics from station data

        Args:
            station_data: Raw data from DWD API

        Returns:
            dict: Extracted weather metrics with standardized keys
        """
        try:
            # The API returns data keyed by station_id
            if not isinstance(station_data, dict):
                logger.warning(f"Unexpected station data format: {station_data}")
                return self._empty_metrics()

            # Get the first station's data (e.g., 'G005')
            station_key = list(station_data.keys())[0] if station_data else None
            if not station_key:
                logger.warning("No station data found in response")
                return self._empty_metrics()

            station = station_data[station_key]

            # Extract current day data (first day in the 'days' array)
            days = station.get("days", [])
            today = days[0] if days else {}

            # Extract hourly forecast data (current values)
            forecast1 = station.get("forecast1", {})

            # Temperature values are in 1/10 degrees Celsius (need to divide by 10)
            # Wind speed in m/s * 10, precipitation in mm * 10, etc.

            metrics = {
                "dwd_timestamp": datetime.now().isoformat(),
                "dwd_station_id": station_key,
                "dwd_station_name": station_key,  # API doesn't provide station name here
                # Daily values from 'days' array (today)
                "dwd_temperature_min": (
                    self._safe_float(today.get("temperatureMin")) / 10.0
                    if today.get("temperatureMin") is not None
                    else None
                ),
                "dwd_temperature_max": (
                    self._safe_float(today.get("temperatureMax")) / 10.0
                    if today.get("temperatureMax") is not None
                    else None
                ),
                "dwd_wind_speed": (
                    self._safe_float(today.get("windSpeed")) / 10.0
                    if today.get("windSpeed") is not None
                    else None
                ),
                "dwd_wind_gust": (
                    self._safe_float(today.get("windGust")) / 10.0
                    if today.get("windGust") is not None
                    else None
                ),
                "dwd_wind_direction": self._safe_int(today.get("windDirection")),
                "dwd_precipitation_daily": (
                    self._safe_float(today.get("precipitation")) / 10.0
                    if today.get("precipitation") is not None
                    else None
                ),
                "dwd_sunshine_minutes": self._safe_int(
                    today.get("sunshine")
                ),  # sunshine duration in seconds
                # Current hour temperature (first value in forecast)
                "dwd_temperature_current": (
                    self._safe_float(forecast1.get("temperature", [None])[0]) / 10.0
                    if forecast1.get("temperature")
                    and len(forecast1.get("temperature", [])) > 0
                    and forecast1.get("temperature")[0] is not None
                    else None
                ),
                # Current hour humidity (first value)
                "dwd_humidity": (
                    self._safe_float(forecast1.get("humidity", [None])[0]) / 10.0
                    if forecast1.get("humidity")
                    and len(forecast1.get("humidity", [])) > 0
                    and forecast1.get("humidity")[0] is not None
                    else None
                ),
                # Current hour pressure (first value in Pa, convert to hPa)
                "dwd_pressure": (
                    self._safe_float(forecast1.get("surfacePressure", [None])[0])
                    / 100.0
                    if forecast1.get("surfacePressure")
                    and len(forecast1.get("surfacePressure", [])) > 0
                    and forecast1.get("surfacePressure")[0] is not None
                    else None
                ),
                # Cloud cover from daily data
                "dwd_cloud_cover": None,  # Not directly available in this endpoint
            }

            logger.info(
                f"Extracted weather metrics for station {metrics['dwd_station_id']}"
            )
            logger.debug(
                f"Temperature: {metrics['dwd_temperature_current']}°C (min: {metrics['dwd_temperature_min']}, max: {metrics['dwd_temperature_max']}), "
                f"Wind: {metrics['dwd_wind_speed']} m/s, "
                f"Precipitation: {metrics['dwd_precipitation_daily']} mm"
            )

            return metrics

        except Exception as e:
            logger.error(f"Failed to extract weather metrics: {e}", exc_info=True)
            return self._empty_metrics()

    def get_weather_metrics(self, station_id=None):
        """
        Convenience method: Fetch and extract weather metrics in one call

        Args:
            station_id: DWD station ID (optional)

        Returns:
            dict: Extracted weather metrics
        """
        station_data = self.get_station_data(station_id)
        return self.extract_weather_metrics(station_data)

    @staticmethod
    def _safe_float(value):
        """Safely convert value to float, return None if not possible"""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _safe_int(value):
        """Safely convert value to int, return None if not possible"""
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _empty_metrics():
        """Return empty metrics dict with None values"""
        return {
            "dwd_timestamp": datetime.now().isoformat(),
            "dwd_station_id": None,
            "dwd_station_name": None,
            "dwd_temperature_min": None,
            "dwd_temperature_max": None,
            "dwd_temperature_current": None,
            "dwd_wind_speed": None,
            "dwd_wind_direction": None,
            "dwd_wind_gust": None,
            "dwd_precipitation_daily": None,
            "dwd_sunshine_minutes": None,
            "dwd_humidity": None,
            "dwd_pressure": None,
            "dwd_cloud_cover": None,
        }


def main():
    """Test the DWD Weather Client"""
    import sys
    import os

    # Setup logging for testing
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Example station ID - you can find station IDs at:
    # https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/daily/kl/recent/KL_Tageswerte_Beschreibung_Stationen.txt
    # Common stations:
    # - G005: Example station
    # - 10381: München Flughafen
    # - 10382: Frankfurt/Main Flughafen
    # - 10384: Stuttgart (Schnarrenberg)

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
        logger.error(f"Test failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
