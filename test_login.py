#!/usr/bin/env python3
import os
import sys
import logging
from dotenv import load_dotenv

# Enable DEBUG logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Load environment
load_dotenv()

# Check credentials
username = os.getenv("WOLF_USERNAME")
password = os.getenv("WOLF_PASSWORD")

if not username or not password:
    print("❌ FEHLER: WOLF_USERNAME oder WOLF_PASSWORD nicht in .env gefunden")
    sys.exit(1)

print(f"✓ Username gefunden: {username}")
print(f"✓ Password gefunden: {'*' * len(password)} ({len(password)} Zeichen)")

# Try login
from wolf_logger import WolfLogger

try:
    wolf = WolfLogger()
    print("\n=== Login-Test startet ===")
    wolf.login()
    print("\n✓ Login erfolgreich!")
except Exception as e:
    print(f"\n❌ Login fehlgeschlagen: {e}")
    sys.exit(1)
