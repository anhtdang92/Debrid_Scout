# app/services/jackett_search.py

"""
Jackett search service — replaces scripts/Jackett_Search_v2.py subprocess calls.

Searches Jackett for torrents, parses torznab XML results, resolves infohashes
from magnet links and .torrent files, and maps category IDs to names.
"""

import os
import re
import hashlib
import math
import json
import time
import logging
import xml.etree.ElementTree as ET
from typing import Optional, List, Dict, Tuple

import cloudscraper
import bencodepy
from flask import current_app

logger = logging.getLogger(__name__)

# Namespace for torznab XML parsing
TORZNAB_NS = {'torznab': 'http://torznab.com/schemas/2015/feed'}


class JackettSearchError(Exception):
    """Custom exception for Jackett search errors."""
    pass


class JackettSearchService:
    """Service for searching torrents via a Jackett instance."""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """Initialize with Jackett credentials from config or explicit args."""
        self.api_key = api_key or current_app.config.get('JACKETT_API_KEY')
        self.base_url = base_url or current_app.config.get('JACKETT_URL', 'http://localhost:9117')

        if not self.api_key:
            raise JackettSearchError("JACKETT_API_KEY is not set.")
        if not self.base_url:
            raise JackettSearchError("JACKETT_URL is not set.")
        if not self.base_url.startswith(("http://", "https://")):
            raise JackettSearchError("JACKETT_URL must start with http:// or https://")

        self._category_mapping = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def search(self, query: str, limit: int = 10) -> Tuple[List[Dict], float]:
        """
        Search Jackett and return parsed results with category names resolved.

        Returns:
            (results_list, elapsed_seconds)
            Each result dict has keys:
                title, seeders, leechers, categories (list of names),
                infohash, size (human-readable), byte_size (str), torznab_attributes
        """
        start = time.perf_counter()

        xml_data = self._query_jackett(query, limit)
        if not xml_data:
            elapsed = time.perf_counter() - start
            return [], elapsed

        raw_results = self._parse_xml(xml_data)
        if not raw_results:
            elapsed = time.perf_counter() - start
            return [], elapsed

        category_mapping = self._get_category_mapping()

        output = []
        for result in raw_results:
            category_names = []
            for cat in result.get('categories', []):
                try:
                    name = category_mapping.get(int(cat))
                    if name:
                        category_names.append(name)
                except ValueError:
                    logger.warning(f"Unable to convert category '{cat}' to integer.")

            output.append({
                "title": result.get('title', 'Unknown Title'),
                "seeders": result.get('seeders', '0'),
                "leechers": result.get('leechers', '0'),
                "categories": category_names,
                "infohash": result.get('infohash'),
                "size": self.bytes_to_human_readable(int(result.get('size', '0'))),
                "byte_size": result.get('size', '0'),
                "torznab_attributes": result.get('torznab_attrs', {}),
            })

        elapsed = time.perf_counter() - start
        return output, elapsed

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _create_session(self):
        """Create a cloudscraper session with browser-like headers."""
        session = cloudscraper.create_scraper()
        session.headers.update({
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/85.0.4183.102 Safari/537.36'
            ),
            'Accept-Language': 'en-US,en;q=0.9',
        })
        return session

    def _query_jackett(self, query: str, limit: int) -> Optional[bytes]:
        """Send a torznab search request to Jackett and return raw XML bytes."""
        url = f"{self.base_url}/api/v2.0/indexers/all/results/torznab/api"
        params = {
            'apikey': self.api_key,
            't': 'search',
            'q': query,
            'limit': limit,
        }

        max_retries = 5
        delay = 2
        session = self._create_session()

        for attempt in range(1, max_retries + 1):
            try:
                response = session.get(url, params=params)
                response.raise_for_status()
                return response.content
            except cloudscraper.exceptions.CloudflareChallengeError:
                if attempt < max_retries:
                    time.sleep(delay)
                else:
                    logger.error("Cloudflare challenge could not be bypassed after multiple attempts.")
                    return None
            except Exception as e:
                if attempt < max_retries:
                    time.sleep(delay)
                else:
                    logger.error(f"Failed to perform Jackett search after {max_retries} attempts: {e}")
                    return None

        return None

    def _parse_xml(self, xml_data: bytes) -> List[Dict]:
        """Parse torznab XML and extract results with infohashes."""
        results = []
        try:
            root = ET.fromstring(xml_data)
            items = root.findall('./channel/item')

            for item in items:
                title_elem = item.find('title')
                title = title_elem.text if title_elem is not None else "Unknown Title"

                seeders_elem = item.find('./torznab:attr[@name="seeders"]', TORZNAB_NS)
                seeders = seeders_elem.attrib['value'] if seeders_elem is not None else "0"

                leechers_elem = item.find('./torznab:attr[@name="peers"]', TORZNAB_NS)
                leechers = leechers_elem.attrib['value'] if leechers_elem is not None else "0"

                categories_elems = item.findall('./torznab:attr[@name="category"]', TORZNAB_NS)
                categories = [cat.attrib['value'] for cat in categories_elems]

                link_elem = item.find('link')
                link = link_elem.text if link_elem is not None else "Unknown Link"

                size_elem = item.find('size')
                size = str(size_elem.text) if size_elem is not None else "0"

                # Skip 1337x links (known to be problematic)
                if "1337x" in link:
                    continue

                # Resolve infohash
                infohash_elem = item.find('./torznab:attr[@name="infohash"]', TORZNAB_NS)
                infohash = None

                if link.startswith("magnet:"):
                    infohash = self._extract_infohash_from_magnet(link)
                elif infohash_elem is not None:
                    infohash = infohash_elem.attrib['value']
                else:
                    for _ in range(2):
                        infohash = self._get_infohash_from_torrent_url(link)
                        if infohash:
                            break
                        time.sleep(2)

                if not infohash:
                    continue

                torznab_attrs = {
                    attr.attrib.get('name'): attr.attrib.get('value')
                    for attr in item.findall('./torznab:attr', TORZNAB_NS)
                }

                results.append({
                    'title': title,
                    'seeders': seeders,
                    'leechers': leechers,
                    'categories': categories,
                    'infohash': infohash,
                    'size': size,
                    'torznab_attrs': torznab_attrs,
                })

        except ET.ParseError as e:
            logger.error(f"Failed to parse XML data: {e}")
        except Exception as e:
            logger.error(f"Unexpected error while parsing results: {e}")

        return results

    def _get_infohash_from_torrent_url(self, torrent_url: str) -> Optional[str]:
        """Download a .torrent file and compute its infohash."""
        max_retries = 5
        delay = 5
        session = self._create_session()

        for attempt in range(1, max_retries + 1):
            try:
                response = session.get(torrent_url, allow_redirects=False, timeout=20)
                if response.status_code == 404:
                    return None
                if response.status_code in (301, 302):
                    redirect_url = response.headers.get('Location', '')
                    if redirect_url.startswith('magnet:?'):
                        return self._extract_infohash_from_magnet(redirect_url)
                elif response.status_code == 200:
                    torrent_data = bencodepy.decode(response.content)
                    info_dict = torrent_data.get(b'info')
                    if info_dict:
                        encoded_info = bencodepy.encode(info_dict)
                        return hashlib.sha1(encoded_info).hexdigest()
            except Exception:
                time.sleep(delay)

        return None

    @staticmethod
    def _extract_infohash_from_magnet(magnet_link: str) -> Optional[str]:
        """Extract the infohash from a magnet URI."""
        match = re.search(r'urn:btih:([A-Fa-f0-9]{32,40})', magnet_link)
        return match.group(1).lower() if match else None

    def _get_category_mapping(self) -> Dict[int, str]:
        """Load and cache the category mapping from the static JSON file."""
        if self._category_mapping is not None:
            return self._category_mapping

        try:
            static_folder = os.path.join(current_app.root_path, 'static')
            path = os.path.join(static_folder, 'category_mapping.json')
            with open(path, 'r') as f:
                self._category_mapping = {int(k): v for k, v in json.load(f).items()}
        except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
            logger.error(f"Error loading category mapping: {e}")
            self._category_mapping = {}

        return self._category_mapping

    @staticmethod
    def bytes_to_human_readable(size_bytes: int) -> str:
        """Convert bytes to a human-readable string."""
        if size_bytes == 0:
            return "0B"
        size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_name[i]}"
