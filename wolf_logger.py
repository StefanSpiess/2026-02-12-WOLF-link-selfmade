#!/usr/bin/env python3
"""
Wolf Smartset Logger
Logs into Wolf Smartset portal using OAuth2 PKCE flow and retrieves heating system data.
"""

import requests
import os
import sys
import logging
import hashlib
import base64
import secrets
import time
import re
from urllib.parse import urlencode, urlparse, parse_qs
from dotenv import load_dotenv
from datetime import datetime, timezone
import json
import sqlite3
import csv
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


class WolfLogger:
    """Handles OAuth2 PKCE authentication and API communication with Wolf Smartset portal"""
    
    def __init__(self):
        self.base_url = "https://www.wolf-smartset.com"
        self.username = os.getenv("WOLF_USERNAME")
        self.password = os.getenv("WOLF_PASSWORD")
        self.system_id = int(os.getenv("WOLF_SYSTEM_ID", 0))
        self.gateway_id = int(os.getenv("WOLF_GATEWAY_ID", 0))
        
        # OAuth2 PKCE parameters
        self.client_id = "smartset.web"
        self.redirect_uri = f"{self.base_url}/signin-callback.html"
        self.scope = "openid profile api role"
        
        # Session and token storage
        self.session = requests.Session()
        self.token = None
        self.token_expires_at = 0
        self.csrf_token = None
        self.code_verifier = None
        self.code_challenge = None
        self.state = None
        self.portal_session_id = None
        
        # Validate credentials
        if not self.username or not self.password:
            raise ValueError("WOLF_USERNAME and WOLF_PASSWORD must be set in .env file")
        if not self.system_id or not self.gateway_id:
            raise ValueError("WOLF_SYSTEM_ID and WOLF_GATEWAY_ID must be set in .env file")
        
        logger.info(f"WolfLogger initialized for system {self.system_id}, gateway {self.gateway_id}")
    
    def _generate_pkce(self):
        """Generate PKCE code_verifier and code_challenge for OAuth2 flow"""
        # Generate code_verifier: 43-128 characters, base64url encoded
        self.code_verifier = secrets.token_urlsafe(64)  # Creates ~86 char string
        logger.debug(f"Generated code_verifier: {self.code_verifier[:20]}...")
        
        # Generate code_challenge: SHA256 hash of verifier, base64url encoded
        challenge_bytes = hashlib.sha256(self.code_verifier.encode('utf-8')).digest()
        self.code_challenge = base64.urlsafe_b64encode(challenge_bytes).decode('utf-8').rstrip('=')
        logger.debug(f"Generated code_challenge: {self.code_challenge[:20]}...")
        
        return self.code_verifier, self.code_challenge
    
    def _generate_state(self):
        """Generate random state parameter for OAuth2 flow"""
        self.state = secrets.token_hex(16)
        logger.debug(f"Generated state: {self.state}")
        return self.state
    
    def _get_csrf_token(self, return_url):
        """
        Fetch CSRF token from login page
        
        Args:
            return_url: OAuth return URL with parameters
            
        Returns:
            str: CSRF token value
        """
        login_url = f"{self.base_url}/idsrv/Account/Login"
        params = {"ReturnUrl": return_url}
        
        logger.info("Fetching CSRF token from login page...")
        response = self.session.get(login_url, params=params)
        response.raise_for_status()
        
        # Extract CSRF token from HTML
        # Looking for: <input name="__RequestVerificationToken" ... value="...">
        match = re.search(
            r'<input[^>]+name=["\']__RequestVerificationToken["\'][^>]+value=["\']([^"\']+)["\']',
            response.text
        )
        
        if not match:
            # Try alternate pattern
            match = re.search(
                r'<input[^>]+value=["\']([^"\']+)["\'][^>]+name=["\']__RequestVerificationToken["\']',
                response.text
            )
        
        if not match:
            logger.error("Failed to extract CSRF token from login page")
            raise ValueError("Could not find __RequestVerificationToken in login page")
        
        self.csrf_token = match.group(1)
        logger.debug(f"Extracted CSRF token: {self.csrf_token[:20]}...")
        return self.csrf_token
    
    def _perform_login(self, return_url):
        """
        Perform login POST request
        
        Args:
            return_url: OAuth return URL with parameters
            
        Returns:
            str: Location header from redirect response
        """
        login_url = f"{self.base_url}/idsrv/Account/Login"
        params = {"ReturnUrl": return_url}
        
        # Prepare form data
        data = {
            "Input.Username": self.username,
            "Input.Password": self.password,
            "__RequestVerificationToken": self.csrf_token,
            "ReturnUrl": return_url
        }
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": self.base_url,
            "Referer": f"{login_url}?ReturnUrl={return_url}"
        }
        
        logger.info("Performing login POST...")
        response = self.session.post(
            login_url,
            params=params,
            data=data,
            headers=headers,
            allow_redirects=False
        )
        
        # Check for successful login (302 redirect)
        if response.status_code == 302:
            location = response.headers.get('Location')
            logger.info(f"Login successful, redirecting to: {location[:50]}...")
            return location
        elif response.status_code == 200:
            # Login failed, check for error message in HTML
            error_match = re.search(r'<div[^>]+class=["\'][^"\']*validation-summary[^"\']*["\'][^>]*>([^<]+)', response.text)
            error_msg = error_match.group(1).strip() if error_match else "Unknown error"
            logger.error(f"Login failed: {error_msg}")
            raise ValueError(f"Login failed: {error_msg}")
        else:
            logger.error(f"Unexpected status code: {response.status_code}")
            raise ValueError(f"Login failed with status code: {response.status_code}")
    
    def _follow_redirects(self, location):
        """
        Manually follow OAuth redirects to extract authorization code
        
        Args:
            location: Initial redirect location
            
        Returns:
            str: Authorization code
        """
        logger.info("Following OAuth redirects...")
        
        # Follow first redirect (authorize/callback)
        if not location.startswith('http'):
            location = f"{self.base_url}{location}"
        
        response = self.session.get(location, allow_redirects=False)
        
        if response.status_code != 302:
            logger.error(f"Expected 302 redirect, got {response.status_code}")
            raise ValueError(f"OAuth flow error: expected redirect, got {response.status_code}")
        
        # Get final redirect location (signin-callback.html with code)
        final_location = response.headers.get('Location')
        logger.debug(f"Final redirect: {final_location[:100]}...")
        
        # Parse authorization code from URL
        parsed = urlparse(final_location)
        params = parse_qs(parsed.query)
        
        if 'code' not in params:
            logger.error("No authorization code in redirect URL")
            raise ValueError("Failed to get authorization code from OAuth flow")
        
        code = params['code'][0]
        
        # Verify state matches
        if 'state' in params:
            returned_state = params['state'][0]
            if returned_state != self.state:
                logger.error(f"State mismatch: expected {self.state}, got {returned_state}")
                raise ValueError("OAuth state mismatch - possible CSRF attack")
        
        logger.info(f"Successfully extracted authorization code: {code[:20]}...")
        return code
    
    def _exchange_code_for_token(self, code):
        """
        Exchange authorization code for access token
        
        Args:
            code: Authorization code from OAuth flow
            
        Returns:
            dict: Token response with access_token, expires_in, etc.
        """
        token_url = f"{self.base_url}/idsrv/connect/token"
        
        data = {
            "client_id": self.client_id,
            "code": code,
            "redirect_uri": self.redirect_uri,
            "code_verifier": self.code_verifier,
            "grant_type": "authorization_code"
        }
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        logger.info("Exchanging authorization code for access token...")
        response = self.session.post(token_url, data=data, headers=headers)
        response.raise_for_status()
        
        token_data = response.json()
        
        if 'access_token' not in token_data:
            logger.error("No access_token in response")
            raise ValueError("Failed to get access token from token endpoint")
        
        self.token = token_data['access_token']
        expires_in = token_data.get('expires_in', 3600)
        self.token_expires_at = time.time() + expires_in
        
        logger.info(f"Successfully obtained access token (expires in {expires_in}s)")
        logger.debug(f"Token: {self.token[:50]}...")
        
        return token_data
    
    def login(self):
        """
        Perform complete OAuth2 PKCE login flow
        
        Returns:
            bool: True if login successful
        """
        try:
            logger.info("=== Starting OAuth2 PKCE login flow ===")
            
            # Step 1: Generate PKCE parameters
            logger.info("Step 1: Generating PKCE parameters...")
            self._generate_pkce()
            self._generate_state()
            
            # Step 2: Build return URL with OAuth parameters
            oauth_params = {
                "client_id": self.client_id,
                "redirect_uri": self.redirect_uri,
                "response_type": "code",
                "scope": self.scope,
                "state": self.state,
                "code_challenge": self.code_challenge,
                "code_challenge_method": "S256",
                "response_mode": "query",
                "lang": "de-DE"
            }
            return_url = f"/idsrv/connect/authorize/callback?{urlencode(oauth_params)}"
            logger.debug(f"Return URL: {return_url[:100]}...")
            
            # Step 3: Get CSRF token from login page
            logger.info("Step 2: Fetching CSRF token...")
            self._get_csrf_token(return_url)
            
            # Step 4: Perform login
            logger.info("Step 3: Performing login...")
            location = self._perform_login(return_url)
            
            # Step 5: Follow redirects and extract authorization code
            logger.info("Step 4: Following OAuth redirects...")
            code = self._follow_redirects(location)
            
            # Step 6: Exchange code for token
            logger.info("Step 5: Exchanging code for access token...")
            self._exchange_code_for_token(code)
            
            logger.info("=== Login flow completed successfully ===")
            return True
            
        except Exception as e:
            logger.error(f"Login failed: {e}", exc_info=True)
            raise
    
    def _ensure_authenticated(self):
        """Check if token is valid, re-login if expired"""
        if not self.token or time.time() >= self.token_expires_at - 300:
            logger.info("Token expired or missing, re-authenticating...")
            self.login()
    
    def init_portal(self):
        """Initialize portal session - fetches config data"""
        self._ensure_authenticated()
        
        url = f"{self.base_url}/portal/api/portal/Init"
        params = {"_": int(time.time() * 1000)}  # Timestamp in milliseconds
        
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "*/*"
        }
        
        logger.info("Initializing portal...")
        response = self.session.get(url, params=params, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        logger.info(f"Portal initialized (FullYear: {data.get('FullYear', 'N/A')})")
        return data
    
    def create_session(self):
        """Create portal session and get session ID"""
        self._ensure_authenticated()
        
        url = f"{self.base_url}/portal/api/portal/CreateSession2"
        
        # Timestamp in format: "YYYY-MM-DD HH:MM:SS"
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        
        payload = {
            "Timestamp": timestamp
        }
        
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "*/*",
            "Origin": self.base_url,
            "Referer": f"{self.base_url}/index.html"
        }
        
        logger.info(f"Creating portal session with timestamp: {timestamp}")
        response = self.session.post(url, json=payload, headers=headers)
        response.raise_for_status()
        
        # Response should contain BrowserSessionId
        try:
            data = response.json()
            if isinstance(data, dict) and 'BrowserSessionId' in data:
                self.portal_session_id = data['BrowserSessionId']
            elif isinstance(data, dict) and 'SessionId' in data:
                self.portal_session_id = data['SessionId']
            elif isinstance(data, (int, str)):
                self.portal_session_id = int(data)
            else:
                logger.error(f"Unexpected session response format: {data}")
                raise ValueError(f"Could not extract SessionId from response: {data}")
        except ValueError as e:
            # Response might be plain text/number
            try:
                self.portal_session_id = int(response.text.strip())
            except ValueError:
                logger.error(f"Failed to parse session response: {response.text}")
                raise
        
        logger.info(f"Portal session created: {self.portal_session_id}")
        return self.portal_session_id
    
    def get_system_list(self):
        """Get list of available systems"""
        self._ensure_authenticated()
        
        url = f"{self.base_url}/portal/api/portal/GetSystemList"
        params = {"_": int(time.time() * 1000)}
        
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "*/*"
        }
        
        logger.info("Fetching system list...")
        response = self.session.get(url, params=params, headers=headers)
        response.raise_for_status()
        
        systems = response.json()
        logger.info(f"Found {len(systems)} system(s)")
        return systems
    
    def get_system_state_list(self):
        """Get state of systems"""
        self._ensure_authenticated()
        
        if not self.portal_session_id:
            raise ValueError("Portal session not initialized. Call create_session() first.")
        
        url = f"{self.base_url}/portal/api/portal/GetSystemStateList"
        
        payload = {
            "SessionId": self.portal_session_id,
            "SystemList": [
                {
                    "SystemId": self.system_id,
                    "GatewayId": self.gateway_id
                }
            ]
        }
        
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "*/*"
        }
        
        logger.info("Fetching system state...")
        response = self.session.post(url, json=payload, headers=headers)
        response.raise_for_status()
        
        states = response.json()
        if states and len(states) > 0:
            state = states[0]
            is_online = state.get('GatewayState', {}).get('IsOnline', False)
            logger.info(f"System {self.system_id} is {'online' if is_online else 'offline'}")
        return states
    
    def get_parameter_values(self, value_ids=None, bundle_id=1000):
        """
        Get parameter values from Wolf Smartset API
        
        Args:
            value_ids: List of parameter IDs to fetch (defaults to common heating parameters)
            bundle_id: Bundle ID (default: 1000)
            
        Returns:
            dict: API response with parameter values
        """
        self._ensure_authenticated()
        
        # Create portal session if not exists
        if not self.portal_session_id:
            self.init_portal()
            self.create_session()
            self.get_system_list()
            self.get_system_state_list()
        
        # Default parameter IDs (from DevTools capture)
        if value_ids is None:
            value_ids = [
                27000600001, 27000900001, 27002900001, 27000700001, 27002800001,
                27003000001, 27001200001, 27001100001, 27001300001, 27001400001,
                27004800001, 27001600001
            ]
        
        url = f"{self.base_url}/portal/api/portal/GetParameterValues"
        
        payload = {
            "BundleId": bundle_id,
            "IsSubBundle": False,
            "ValueIdList": value_ids,
            "GatewayId": self.gateway_id,
            "SystemId": self.system_id,
            "LastAccess": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "GuiIdChanged": False,
            "SessionId": self.portal_session_id
        }
        
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json; charset=UTF-8",
            "Accept": "*/*",
            "Origin": self.base_url,
            "Referer": f"{self.base_url}/index.html",
            "X-Requested-With": "XMLHttpRequest"
        }
        
        logger.info(f"Fetching parameter values for system {self.system_id}...")
        logger.debug(f"Request payload: {json.dumps(payload, indent=2)}")
        response = self.session.post(url, json=payload, headers=headers)
        
        if response.status_code == 401:
            logger.warning("Got 401, token expired. Re-authenticating...")
            self.login()
            # Retry with new token
            headers["Authorization"] = f"Bearer {self.token}"
            response = self.session.post(url, json=payload, headers=headers)
        
        # Log response details before raising error
        if response.status_code != 200:
            logger.error(f"API call failed with status {response.status_code}")
            logger.error(f"Response headers: {dict(response.headers)}")
            logger.error(f"Response body: {response.text}")
        
        response.raise_for_status()
        data = response.json()
        
        logger.info(f"Successfully fetched {len(data.get('Values', []))} parameter values")
        return data
    
    def get_gui_description(self):
        """
        Get GUI description with current values
        
        This returns the complete GUI structure including all current parameter values.
        This is more comprehensive than get_parameter_values().
        
        Returns:
            dict: GUI structure with menu items, tabs, and parameter values
        """
        self._ensure_authenticated()
        
        # Create portal session if not exists
        if not self.portal_session_id:
            self.init_portal()
            self.create_session()
            self.get_system_list()
            self.get_system_state_list()
        
        url = f"{self.base_url}/portal/api/portal/GetGuiDescriptionForGateway"
        
        params = {
            "GatewayId": self.gateway_id,
            "SystemId": self.system_id,
            "_": int(time.time() * 1000)
        }
        
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "*/*",
            "Referer": f"{self.base_url}/index.html"
        }
        
        logger.info(f"Fetching GUI description for system {self.system_id}...")
        response = self.session.get(url, params=params, headers=headers)
        
        if response.status_code == 401:
            logger.warning("Got 401, token expired. Re-authenticating...")
            self.login()
            # Retry with new token
            headers["Authorization"] = f"Bearer {self.token}"
            response = self.session.get(url, params=params, headers=headers)
        
        response.raise_for_status()
        data = response.json()
        
        # Count total parameters
        total_params = 0
        if 'MenuItems' in data:
            for menu in data['MenuItems']:
                if 'TabViews' in menu:
                    for tab in menu['TabViews']:
                        if 'ParameterDescriptors' in tab:
                            total_params += len(tab['ParameterDescriptors'])
        
        logger.info(f"Successfully fetched GUI description with {total_params} parameters")
        return data
    
    def extract_key_metrics(self, gui_data):
        """
        Extract key metrics from GUI description
        
        Returns:
            dict: Dictionary with key heating metrics
        """
        metrics = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'vorlauftemperatur': None,
            'ruecklauftemperatur': None,
            'kesseltemperatur': None,
            'aussentemperatur': None,
            'gesamtverbrauch': None,
            'waermemenge_heizung': None,
            'waermemenge_warmwasser': None,
            'verbrauch_vortag': None,
            'verbrauch_aktueller_monat': None,
            'erzeugte_waermemenge_jahr': None,
            'jaz': None
        }
        
        # Parameter name mappings (case-insensitive search)
        mappings = {
            'vorlauftemperatur': ['vorlauftemperatur', 'kf kesseltemperatur'],
            'ruecklauftemperatur': ['rücklauftemperatur', 'rl rücklauffühler'],
            'kesseltemperatur': ['kesseltemperatur'],
            'aussentemperatur': ['außentemperatur'],
            'gesamtverbrauch': ['verbrauch aktuelles jahr'],
            'waermemenge_heizung': ['energiemenge hz'],
            'waermemenge_warmwasser': ['energiemenge ww'],
            'verbrauch_vortag': ['verbrauch vortag'],
            'verbrauch_aktueller_monat': ['verbrauch aktueller monat'],
            'erzeugte_waermemenge_jahr': ['erzeugte wärmemenge aktuelles jahr'],
            'jaz': ['jaz aktuelles jahr']
        }
        
        # Search through all parameters
        for menu in gui_data.get('MenuItems', []):
            for tab in menu.get('TabViews', []):
                for param in tab.get('ParameterDescriptors', []):
                    param_name = param.get('Name', '').lower()
                    param_value = param.get('Value')
                    
                    if param_value is None:
                        continue
                    
                    # Try to match parameter name to our metrics
                    for metric_key, search_terms in mappings.items():
                        if any(term in param_name for term in search_terms):
                            # Convert to float if possible
                            try:
                                metrics[metric_key] = float(param_value)
                            except (ValueError, TypeError):
                                metrics[metric_key] = param_value
                            break
        
        return metrics
    
    def init_database(self, db_path='data/wolf.db'):
        """Initialize SQLite database with heating data table"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS heating_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                vorlauftemperatur REAL,
                ruecklauftemperatur REAL,
                kesseltemperatur REAL,
                aussentemperatur REAL,
                gesamtverbrauch REAL,
                waermemenge_heizung REAL,
                waermemenge_warmwasser REAL,
                verbrauch_vortag REAL,
                verbrauch_aktueller_monat REAL,
                erzeugte_waermemenge_jahr REAL,
                jaz REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create index on timestamp for faster queries
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_timestamp 
            ON heating_data(timestamp)
        ''')
        
        conn.commit()
        conn.close()
        logger.info(f"Database initialized: {db_path}")
    
    def save_metrics_to_db(self, metrics, db_path='data/wolf.db'):
        """Save metrics to SQLite database"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO heating_data (
                timestamp, vorlauftemperatur, ruecklauftemperatur, kesseltemperatur,
                aussentemperatur, gesamtverbrauch, waermemenge_heizung, waermemenge_warmwasser,
                verbrauch_vortag, verbrauch_aktueller_monat, erzeugte_waermemenge_jahr, jaz
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            metrics['timestamp'],
            metrics['vorlauftemperatur'],
            metrics['ruecklauftemperatur'],
            metrics['kesseltemperatur'],
            metrics['aussentemperatur'],
            metrics['gesamtverbrauch'],
            metrics['waermemenge_heizung'],
            metrics['waermemenge_warmwasser'],
            metrics['verbrauch_vortag'],
            metrics['verbrauch_aktueller_monat'],
            metrics['erzeugte_waermemenge_jahr'],
            metrics['jaz']
        ))
        
        conn.commit()
        row_id = cursor.lastrowid
        conn.close()
        
        logger.info(f"Metrics saved to database (row {row_id})")
        return row_id
    
    def save_metrics_to_csv(self, metrics, csv_path='data/wolf.csv'):
        """Save metrics to CSV file (append mode)"""
        file_exists = Path(csv_path).exists()
        
        # Ensure directory exists
        Path(csv_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(csv_path, 'a', newline='', encoding='utf-8') as f:
            fieldnames = [
                'timestamp', 'vorlauftemperatur', 'ruecklauftemperatur', 'kesseltemperatur',
                'aussentemperatur', 'gesamtverbrauch', 'waermemenge_heizung', 'waermemenge_warmwasser',
                'verbrauch_vortag', 'verbrauch_aktueller_monat', 'erzeugte_waermemenge_jahr', 'jaz'
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            # Write header only if file is new
            if not file_exists:
                writer.writeheader()
            
            writer.writerow(metrics)
        
        logger.info(f"Metrics saved to CSV: {csv_path}")
    
    def log_data(self, db_path='data/wolf.db', csv_path='data/wolf.csv'):
        """
        Complete workflow: Login, fetch data, extract metrics, save to DB
        
        This is the main method to call for regular data logging.
        """
        logger.info("Starting data logging workflow...")
        
        # Ensure database exists
        self.init_database(db_path)
        
        # Fetch GUI description with all current values
        gui_data = self.get_gui_description()
        
        # Extract key metrics
        metrics = self.extract_key_metrics(gui_data)
        
        # Save to database
        row_id = self.save_metrics_to_db(metrics, db_path)
        
        # Save to CSV
        self.save_metrics_to_csv(metrics, csv_path)
        
        logger.info("Data logging completed successfully")
        return metrics, row_id


def main():
    """Main entry point for testing"""
    try:
        logger.info("Initializing Wolf Logger...")
        wolf = WolfLogger()
        
        logger.info("\n" + "="*60)
        logger.info("Testing login flow...")
        logger.info("="*60 + "\n")
        
        wolf.login()
        
        logger.info("\n" + "="*60)
        logger.info("Logging heating data to database...")
        logger.info("="*60 + "\n")
        
        # Main workflow: fetch data and save to DB
        metrics, row_id = wolf.log_data()
        
        print("\n" + "="*60)
        print("SUCCESS! Data logged to database:")
        print("="*60)
        print(f"Timestamp:                    {metrics['timestamp']}")
        print(f"Vorlauftemperatur:            {metrics['vorlauftemperatur']}°C")
        print(f"Rücklauftemperatur:           {metrics['ruecklauftemperatur']}°C")
        print(f"Kesseltemperatur:             {metrics['kesseltemperatur']}°C")
        print(f"Außentemperatur:              {metrics['aussentemperatur']}°C")
        print(f"Gesamtverbrauch (Jahr):       {metrics['gesamtverbrauch']} kWh")
        print(f"Wärmemenge Heizung (gesamt):  {metrics['waermemenge_heizung']} kWh")
        print(f"Wärmemenge Warmwasser (ges.): {metrics['waermemenge_warmwasser']} kWh")
        print(f"Verbrauch Vortag:             {metrics['verbrauch_vortag']} kWh")
        print(f"Verbrauch aktueller Monat:    {metrics['verbrauch_aktueller_monat']} kWh")
        print(f"Erzeugte Wärmemenge (Jahr):   {metrics['erzeugte_waermemenge_jahr']} kWh")
        print(f"JAZ (aktuelles Jahr):         {metrics['jaz']}")
        print(f"\nSaved as row ID: {row_id}")
        print("="*60)
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
