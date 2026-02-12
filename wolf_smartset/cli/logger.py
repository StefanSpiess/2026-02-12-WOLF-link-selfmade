#!/usr/bin/env python
"""
CLI command for logging Wolf heating data
"""

import sys
import os
import logging
import requests
from dotenv import load_dotenv

from wolf_smartset.client import WolfLogger, WolfLoginError, MaintenanceError, InvalidCredentialsError
from wolf_smartset.weather import DWDWeatherClient
from wolf_smartset import database

# Setup logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


def main():
    """Main entry point for wolf-logger CLI command"""
    try:
        logger.info("Initializing Wolf Logger...")
        
        # Check DWD weather integration
        dwd_station_id = os.getenv("DWD_STATION_ID")
        dwd_enabled = bool(dwd_station_id)
        
        # Initialize Wolf client
        wolf = WolfLogger()

        logger.info("\n" + "=" * 60)
        logger.info("Logging heating data to database...")
        logger.info("=" * 60 + "\n")

        # Ensure database exists
        database.init_database()

        # Login and fetch GUI description
        wolf.login()
        gui_data = wolf.get_gui_description()

        # Extract key metrics
        metrics = wolf.extract_key_metrics(gui_data)

        # Fetch weather data if enabled
        if dwd_enabled:
            try:
                logger.info("Fetching weather data from DWD...")
                weather_client = DWDWeatherClient(station_id=dwd_station_id)
                weather_metrics = weather_client.get_weather_metrics()
                metrics.update(weather_metrics)
                logger.info(
                    f"Weather data added: Temp={weather_metrics.get('dwd_temperature_current')}°C, "
                    f"Wind={weather_metrics.get('dwd_wind_speed')} m/s"
                )
            except Exception as e:
                logger.error(f"Failed to fetch weather data: {e}")
                logger.warning("Continuing without weather data")

        # Save to database and CSV
        row_id = database.save_metrics_to_db(metrics)
        database.save_metrics_to_csv(metrics)

        print("\n" + "=" * 60)
        print("SUCCESS! Data logged to database:")
        print("=" * 60)
        print(f"Timestamp:                    {metrics['timestamp']}")
        print(f"Vorlauftemperatur:            {metrics['vorlauftemperatur']}°C")
        print(f"Rücklauftemperatur:           {metrics['ruecklauftemperatur']}°C")
        print(f"Kesseltemperatur:             {metrics['kesseltemperatur']}°C")
        print(f"Außentemperatur:              {metrics['aussentemperatur']}°C")
        print(f"Gesamtverbrauch (Jahr):       {metrics['gesamtverbrauch']} kWh")
        print(f"Wärmemenge Heizung (gesamt):  {metrics['waermemenge_heizung']} kWh")
        print(f"Wärmemenge Warmwasser (ges.): {metrics['waermemenge_warmwasser']} kWh")
        print(f"Verbrauch Vortag:             {metrics['verbrauch_vortag']} kWh")
        print(
            f"Verbrauch aktueller Monat:    {metrics['verbrauch_aktueller_monat']} kWh"
        )
        print(
            f"Erzeugte Wärmemenge (Jahr):   {metrics['erzeugte_waermemenge_jahr']} kWh"
        )
        print(f"JAZ (aktuelles Jahr):         {metrics['jaz']}")

        # Display weather data if available
        if metrics.get("dwd_station_id"):
            print("\n" + "-" * 60)
            print("Weather Data (DWD):")
            print("-" * 60)
            print(f"Station:                      {metrics.get('dwd_station_id')}")
            print(
                f"Temperatur (aktuell):         {metrics.get('dwd_temperature_current')}°C"
            )
            print(
                f"Temperatur (Min/Max):         {metrics.get('dwd_temperature_min')}°C / {metrics.get('dwd_temperature_max')}°C"
            )
            print(f"Windgeschwindigkeit:          {metrics.get('dwd_wind_speed')} m/s")
            print(f"Windböen:                     {metrics.get('dwd_wind_gust')} m/s")
            print(
                f"Niederschlag (täglich):       {metrics.get('dwd_precipitation_daily')} mm"
            )
            print(
                f"Sonnenscheindauer:            {metrics.get('dwd_sunshine_minutes')} s"
            )
            print(f"Luftfeuchtigkeit:             {metrics.get('dwd_humidity')}%")
            print(f"Luftdruck:                    {metrics.get('dwd_pressure')} hPa")

        print(f"\nSaved as row ID: {row_id}")
        print("=" * 60)

    except MaintenanceError as e:
        print("\n" + "=" * 60)
        print("⚠️  PORTAL MAINTENANCE")
        print("=" * 60)
        print(f"\n{e}")
        print("\nDas Wolf Smartset Portal ist momentan in Wartung.")
        print("Bitte versuchen Sie es in einigen Minuten erneut.")
        print("\n💡 Tipp: Richten Sie einen Cronjob ein, der automatisch")
        print("   alle 15-30 Minuten versucht, Daten zu loggen.")
        print("=" * 60)
        sys.exit(2)  # Exit code 2 = temporary failure

    except InvalidCredentialsError as e:
        print("\n" + "=" * 60)
        print("❌ LOGIN FEHLGESCHLAGEN")
        print("=" * 60)
        print(f"\n{e}")
        print("\nBitte überprüfen Sie Ihre Zugangsdaten in der .env Datei:")
        print("  - WOLF_USERNAME")
        print("  - WOLF_PASSWORD")
        print("\nStellen Sie sicher, dass Sie sich mit diesen Daten")
        print("im Browser bei Wolf Smartset einloggen können:")
        print("  https://www.wolf-smartset.com")
        print("=" * 60)
        sys.exit(1)

    except WolfLoginError as e:
        print("\n" + "=" * 60)
        print("❌ LOGIN FEHLER")
        print("=" * 60)
        print(f"\n{e}")
        print("\nEin unbekannter Login-Fehler ist aufgetreten.")
        print("Bitte überprüfen Sie:")
        print("  1. Ihre Internetverbindung")
        print("  2. Ob das Wolf Portal erreichbar ist")
        print("  3. Ihre Zugangsdaten in der .env Datei")
        print("\nFür mehr Details führen Sie das Script mit DEBUG aus:")
        print("  wolf-logger 2>&1 | tee debug.log")
        print("=" * 60)
        sys.exit(1)

    except requests.exceptions.ConnectionError as e:
        print("\n" + "=" * 60)
        print("⚠️  VERBINDUNGSFEHLER")
        print("=" * 60)
        print("\nDas Wolf Portal ist nicht erreichbar.")
        print("\nMögliche Ursachen:")
        print("  1. Keine Internetverbindung")
        print("  2. Wolf Portal ist offline/nicht erreichbar")
        print("  3. Firewall blockiert die Verbindung")
        print("\nBitte versuchen Sie:")
        print("  - Ihre Internetverbindung zu prüfen")
        print("  - https://www.wolf-smartset.com im Browser zu öffnen")
        print("  - Es später erneut zu versuchen")
        print("=" * 60)
        sys.exit(2)  # Exit code 2 für temporären Fehler, cron kann retry

    except KeyboardInterrupt:
        print("\n\n⚠️  Abgebrochen durch Benutzer")
        sys.exit(130)

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        print("\n" + "=" * 60)
        print("❌ FEHLER")
        print("=" * 60)
        print(f"\n{type(e).__name__}: {e}")
        print("\nEin unerwarteter Fehler ist aufgetreten.")
        print("Details im Log oben. Für Hilfe:")
        print("  - Siehe README.md")
        print("  - Prüfen Sie die Log-Ausgabe")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
