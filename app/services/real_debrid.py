# app/services/real_debrid.py

import requests
import logging
from datetime import datetime
import time
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

        # Reusable session for connection pooling
        self._session = requests.Session()
        self._session.headers['Authorization'] = f'Bearer {self.api_key}'

        # Legacy attribute kept for compatibility
        self.headers = dict(self._session.headers)

        # Read timeouts from config (with fallbacks for non-Flask contexts)
        try:
            self.request_delay = current_app.config.get('RD_RATE_LIMIT_DELAY', 0.2)
            connect = current_app.config.get('RD_CONNECT_TIMEOUT', 5)
            read = current_app.config.get('RD_API_TIMEOUT', 15)
        except RuntimeError:
            self.request_delay = 0.2
            connect = 5
            read = 15
        self.timeout = (connect, read)

    def _rate_limit(self):
        """Enforce a simple delay to avoid hitting rate limits."""
        time.sleep(self.request_delay)

    def _check_response(self, response):
        """Check response for rate limiting; back off on 429."""
        if response.status_code == 429:
            retry_after = int(response.headers.get('Retry-After', 2))
            logger.warning(f"RD rate limit hit (429). Retrying after {retry_after}s.")
            time.sleep(retry_after)
            raise requests.HTTPError("429 Too Many Requests", response=response)
        return response

    def get_account_info(self) -> Dict[str, Any]:
        """Fetch account information from Real-Debrid."""
        try:
            self._rate_limit()
            logger.debug("Requesting Real-Debrid account information.")
            response = self._session.get('https://api.real-debrid.com/rest/1.0/user', timeout=self.timeout)
            self._check_response(response)
            response.raise_for_status()
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
            raise RealDebridError("Failed to fetch Real-Debrid account information. Please check your network and API key.")
        except ValueError as e:
            logger.error(f"JSON processing error for account info: {e}")
            raise RealDebridError("Invalid account data received from Real-Debrid.")

    def add_magnet(self, magnet_link: str) -> Optional[str]:
        """Add a magnet link to Real-Debrid."""
        try:
            self._rate_limit()
            logger.debug(f"Adding magnet link to Real-Debrid: {magnet_link}")
            response = self._session.post(
                'https://api.real-debrid.com/rest/1.0/torrents/addMagnet',
                data={'magnet': magnet_link},
                timeout=self.timeout,
            )
            self._check_response(response)
            response.raise_for_status()
            torrent_id = response.json().get('id')
            logger.debug(f"Magnet link added successfully with torrent ID: {torrent_id}")
            return torrent_id
        except requests.RequestException as e:
            logger.error(f"Error adding magnet link '{magnet_link}': {e}")
            raise RealDebridError("Failed to add magnet link.")

    def select_files(self, torrent_id: str, files: str = 'all') -> bool:
        """Select specific files for a torrent in Real-Debrid."""
        try:
            self._rate_limit()
            logger.debug(f"Selecting files '{files}' for torrent ID: {torrent_id}")
            response = self._session.post(
                f'https://api.real-debrid.com/rest/1.0/torrents/selectFiles/{torrent_id}',
                data={'files': files},
                timeout=self.timeout,
            )
            self._check_response(response)
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
            self._rate_limit()
            logger.debug(f"Fetching torrent info for ID: {torrent_id}")
            response = self._session.get(
                f'https://api.real-debrid.com/rest/1.0/torrents/info/{torrent_id}',
                timeout=self.timeout,
            )
            self._check_response(response)
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
            self._rate_limit()
            logger.debug(f"Unrestricting link: {link}")
            response = self._session.post(
                'https://api.real-debrid.com/rest/1.0/unrestrict/link',
                data={'link': link},
                timeout=self.timeout,
            )
            self._check_response(response)
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
                self._rate_limit()
                logger.debug(f"Fetching torrents from page {page}.")
                response = self._session.get(
                    f'https://api.real-debrid.com/rest/1.0/torrents?page={page}',
                    timeout=self.timeout,
                )

                if response.status_code == 204:
                    logger.info("No more torrents available.")
                    break

                self._check_response(response)
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

    def delete_torrent(self, torrent_id: str) -> bool:
        """Delete a torrent from Real-Debrid by ID."""
        try:
            self._rate_limit()
            response = self._session.delete(
                f'https://api.real-debrid.com/rest/1.0/torrents/delete/{torrent_id}',
                timeout=self.timeout,
            )
            self._check_response(response)
            response.raise_for_status()
            logger.info(f"Torrent {torrent_id} deleted successfully.")
            return True
        except requests.RequestException as e:
            logger.error(f"Error deleting torrent {torrent_id}: {e}")
            raise RealDebridError(f"Failed to delete torrent {torrent_id}.")
