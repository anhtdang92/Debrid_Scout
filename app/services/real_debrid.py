# app/services/real_debrid.py

import requests
import logging
from datetime import datetime
from flask import current_app
from typing import Optional, Dict, Any, List

# Initialize logger for RealDebridService
logger = logging.getLogger(__name__)

class RealDebridError(Exception):
    """Custom exception for Real-Debrid service errors."""
    pass

class RealDebridService:
    """Service for interacting with the Real-Debrid API."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the RealDebridService with an API key."""
        self.api_key = api_key or current_app.config.get('REAL_DEBRID_API_KEY')
        if not self.api_key:
            logger.error("REAL_DEBRID_API_KEY is not set.")
            raise RealDebridError("Real-Debrid API key is missing.")
        
        # Headers for authentication in Real-Debrid API requests
        self.headers = {
            'Authorization': f'Bearer {self.api_key}'
        }
        logger.debug(f"RealDebridService initialized with API key: {self.api_key[:6]}...")

    def get_account_info(self) -> Dict[str, Any]:
        """Fetch account information from Real-Debrid."""
        try:
            logger.debug("Requesting Real-Debrid account information.")
            response = requests.get('https://api.real-debrid.com/rest/1.0/user', headers=self.headers)
            response.raise_for_status()  # Will raise HTTPError for bad responses
            account_data = response.json()
            logger.debug("Successfully fetched account information.")

            # Format expiration date if it exists
            expiration = account_data.get('expiration')
            if expiration:
                try:
                    expiration_date = datetime.strptime(expiration, '%Y-%m-%dT%H:%M:%S.%fZ')
                    account_data['formatted_expiration'] = expiration_date.strftime('%B %d, %Y, %H:%M:%S UTC')
                    logger.debug(f"Formatted expiration date: {account_data['formatted_expiration']}")
                except ValueError as e:
                    logger.error(f"Error parsing expiration date '{expiration}': {e}")
                    account_data['formatted_expiration'] = expiration  # Fallback to raw value
            else:
                account_data['formatted_expiration'] = 'N/A'
                logger.debug("Expiration date not available in account data.")

            return account_data

        except requests.RequestException as e:
            logger.error(f"Error fetching account info from Real-Debrid: {e}")
            raise RealDebridError("Failed to fetch account information. Please check your network and API key.")
        except ValueError as e:
            logger.error(f"JSON processing error for account info: {e}")
            raise RealDebridError("Invalid account data received from Real-Debrid.")

    def add_magnet(self, magnet_link: str) -> Optional[str]:
        """Add a magnet link to Real-Debrid."""
        try:
            logger.debug(f"Adding magnet link to Real-Debrid: {magnet_link}")
            response = requests.post(
                'https://api.real-debrid.com/rest/1.0/torrents/addMagnet',
                headers=self.headers,
                data={'magnet': magnet_link}
            )
            response.raise_for_status()
            torrent_id = response.json().get('id')
            logger.debug(f"Magnet link added successfully with torrent ID: {torrent_id}")
            return torrent_id
        except requests.RequestException as e:
            logger.error(f"Error adding magnet link '{magnet_link}': {e}")
            raise RealDebridError("Failed to add magnet link.")

    def select_files(self, torrent_id: str) -> bool:
        """Select all files for a torrent in Real-Debrid."""
        try:
            logger.debug(f"Selecting all files for torrent ID: {torrent_id}")
            response = requests.post(
                f'https://api.real-debrid.com/rest/1.0/torrents/selectFiles/{torrent_id}',
                headers=self.headers,
                data={'files': 'all'}
            )
            if response.status_code == 204:
                logger.debug(f"Files selected successfully for torrent ID: {torrent_id}")
                return True
            else:
                logger.warning(f"Unexpected status code {response.status_code} when selecting files.")
                return False
        except requests.RequestException as e:
            logger.error(f"Error selecting files for torrent ID {torrent_id}: {e}")
            raise RealDebridError(f"Failed to select files for torrent {torrent_id}.")

    def get_torrent_info(self, torrent_id: str) -> Dict[str, Any]:
        """Retrieve detailed information about a specific torrent."""
        try:
            logger.debug(f"Fetching torrent info for ID: {torrent_id}")
            response = requests.get(
                f'https://api.real-debrid.com/rest/1.0/torrents/info/{torrent_id}',
                headers=self.headers
            )
            response.raise_for_status()
            torrent_info = response.json()
            logger.debug(f"Torrent info fetched successfully for ID: {torrent_id}")
            return torrent_info
        except requests.RequestException as e:
            logger.error(f"Error fetching torrent info for ID {torrent_id}: {e}")
            raise RealDebridError(f"Failed to fetch info for torrent {torrent_id}.")

    def unrestrict_link(self, link: str) -> Optional[str]:
        """Unrestrict a Real-Debrid link to obtain a direct download link."""
        try:
            logger.debug(f"Unrestricting link: {link}")
            response = requests.post(
                'https://api.real-debrid.com/rest/1.0/unrestrict/link',
                headers=self.headers,
                data={'link': link}
            )
            response.raise_for_status()
            unrestricted_link = response.json().get('download')
            logger.debug(f"Link unrestricted successfully: {unrestricted_link}")
            return unrestricted_link
        except requests.RequestException as e:
            logger.error(f"Error unrestricting link '{link}': {e}")
            raise RealDebridError("Failed to unrestrict link.")

    def get_all_torrents(self) -> List[Dict[str, Any]]:
        """Fetch all torrents from Real-Debrid with pagination."""
        all_torrents = []
        page = 1  # Start with the first page

        try:
            logger.debug("Fetching all torrents from Real-Debrid.")
            while True:
                logger.debug(f"Fetching torrents from page {page}.")
                response = requests.get(
                    f'https://api.real-debrid.com/rest/1.0/torrents?page={page}',
                    headers=self.headers
                )
                
                if response.status_code == 204:
                    logger.info("No more torrents available.")
                    break
                
                response.raise_for_status()
                torrents = response.json()
                
                if not torrents:
                    logger.debug("No torrents on current page, stopping pagination.")
                    break

                all_torrents.extend(torrents)
                logger.debug(f"Fetched {len(torrents)} torrents from page {page}. Total: {len(all_torrents)}")
                page += 1

            logger.info(f"Total torrents fetched: {len(all_torrents)}")
            return all_torrents

        except requests.RequestException as e:
            logger.error(f"Error fetching torrents: {e}")
            raise RealDebridError("Failed to fetch torrents.")