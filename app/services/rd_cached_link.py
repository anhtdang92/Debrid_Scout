# app/services/rd_cached_link.py

"""
Real-Debrid cache-checking service — replaces scripts/Get_RD_Cached_Link.py subprocess calls.

Searches Jackett via JackettSearchService, then checks each result's instant
availability on Real-Debrid.
"""

import time
import logging
from typing import Optional, List, Dict, Tuple

import requests
from flask import current_app

from app.services.jackett_search import JackettSearchService

logger = logging.getLogger(__name__)


class RDCachedLinkError(Exception):
    """Custom exception for RD cached link service errors."""
    pass


class RDCachedLinkService:
    """Service for checking Real-Debrid cache status of Jackett search results."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize with a Real-Debrid API key from config or explicit arg."""
        self.api_key = api_key or current_app.config.get('REAL_DEBRID_API_KEY')
        if not self.api_key:
            raise RDCachedLinkError("REAL_DEBRID_API_KEY is not set.")

        self.headers = {'Authorization': f'Bearer {self.api_key}'}
        self._session = requests.Session()
        self._session.headers.update(self.headers)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def search_and_check_cache(
        self, query: str, limit: int = 10
    ) -> Tuple[List[Dict], float, float]:
        """
        Search Jackett and check RD instant availability for each result.

        Returns:
            (results, self_elapsed, jackett_elapsed)
            Each result dict has keys:
                infohash, is_fully_cached, magnet_link, title, categories,
                seeders, leechers, size, torznab_attributes (optional)
        """
        start = time.perf_counter()

        # 1. Search Jackett
        jackett_service = JackettSearchService()
        search_results, jackett_elapsed = jackett_service.search(query, limit)
        logger.info(f"Jackett returned {len(search_results)} results in {jackett_elapsed:.2f}s.")

        # 2. Check cache for each result
        output = []
        processed_infohashes = set()
        skipped_no_hash = 0
        skipped_dup = 0
        skipped_no_size = 0

        for result in search_results:
            infohash = result.get("infohash")
            if not infohash:
                skipped_no_hash += 1
                continue
            if infohash in processed_infohashes:
                skipped_dup += 1
                continue

            byte_size = result.get("byte_size")
            if not byte_size:
                skipped_no_size += 1
                continue

            processed_infohashes.add(infohash)

            cached_result = self._check_instant_availability(infohash, byte_size)
            cached_result["title"] = result.get("title", "No Title")
            cached_result["categories"] = result.get("categories", [])
            cached_result["seeders"] = result.get("seeders", "0")
            cached_result["leechers"] = result.get("leechers", "0")
            cached_result["size"] = result.get("size", "Unknown")

            torznab_attrs = result.get("torznab_attributes")
            if torznab_attrs:
                cached_result["torznab_attributes"] = torznab_attrs

            output.append(cached_result)

        logger.info(
            f"Cache check: {len(output)} results returned "
            f"(skipped: {skipped_no_hash} no-hash, {skipped_dup} dup, {skipped_no_size} no-size)"
        )

        elapsed = time.perf_counter() - start
        return output, elapsed, jackett_elapsed

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _check_instant_availability(self, infohash: str, expected_size: str) -> Dict:
        """
        Check if a torrent identified by infohash is fully cached on Real-Debrid.

        Returns dict with keys: infohash, is_fully_cached, magnet_link
        """
        result = {
            "infohash": infohash,
            "is_fully_cached": False,
            "magnet_link": f"magnet:?xt=urn:btih:{infohash}",
        }

        try:
            connect = current_app.config.get('RD_CONNECT_TIMEOUT', 5)
            read = current_app.config.get('RD_API_TIMEOUT', 15)
        except RuntimeError:
            connect = 5
            read = 15

        try:
            expected_bytes = int(expected_size)
            url = f"https://api.real-debrid.com/rest/1.0/torrents/instantAvailability/{infohash}"
            response = self._session.get(url, timeout=(connect, read))
            response.raise_for_status()
            data = response.json()

            # RD returns: { "<hash>": { "rd": [ { "<file_id>": { "filename": ..., "filesize": N } }, ... ] } }
            # Each "rd" entry is a variant (different file selection).
            # Sum all file sizes across variants; if total >= expected, it's fully cached.
            if data and infohash in data and "rd" in data[infohash]:
                total_cached = 0
                for instance in data[infohash]["rd"]:
                    for file_key, file_info in instance.items():
                        try:
                            total_cached += int(file_info.get("filesize", "0"))
                        except ValueError:
                            pass

                if total_cached >= expected_bytes:
                    result["is_fully_cached"] = True

        except requests.RequestException as e:
            logger.error(f"Request error checking cache for {infohash}: {e}")
        except ValueError as e:
            logger.error(f"Value error checking cache: {e}")
        except Exception as e:
            logger.error(f"Unexpected error checking cache for {infohash}: {e}")

        return result
