# app/services/rd_download_link.py

"""
Real-Debrid download-link orchestrator — replaces scripts/Get_RD_Download_Link.py subprocess calls.

Searches for cached torrents (via RDCachedLinkService), adds magnets to RD,
selects files, unrestricts download links, and returns structured results
with only video files included.
"""

import time
import logging
from typing import Optional, List, Dict, Any, Tuple

import requests
from flask import current_app

from app.services.rd_cached_link import RDCachedLinkService
from app.services.real_debrid import RealDebridService, RealDebridError
from app.services.file_helper import FileHelper

logger = logging.getLogger(__name__)


class RDDownloadLinkError(Exception):
    """Custom exception for RD download link service errors."""
    pass


class RDDownloadLinkService:
    """
    Orchestrates the full search-to-download pipeline:
    Jackett search → RD cache check → add magnet → select files → unrestrict links.
    """

    def __init__(self, api_key: Optional[str] = None):
        """Initialize with a Real-Debrid API key from config or explicit arg."""
        self.api_key = api_key or current_app.config.get('REAL_DEBRID_API_KEY')
        if not self.api_key:
            raise RDDownloadLinkError("REAL_DEBRID_API_KEY is not set.")

        self.rd_service = RealDebridService(api_key=self.api_key)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def search_and_get_links(
        self, query: str, limit: int = 10
    ) -> Dict[str, Any]:
        """
        Run the full search pipeline and return structured results.

        Returns dict with keys:
            data: list of torrent result dicts (each with Torrent Name, Categories, Files)
            timers: list of {script, time} dicts for each pipeline stage
        """
        overall_start = time.perf_counter()

        # 1. Search and check cache
        cached_link_service = RDCachedLinkService(api_key=self.api_key)
        cached_links, cached_links_time, jackett_time = (
            cached_link_service.search_and_check_cache(query, limit)
        )
        logger.info(f"Pipeline: {len(cached_links)} cached links from RDCachedLinkService.")

        # 2. Build existing-hash lookup and process each cached result
        existing_hashes = self._fetch_existing_hashes()
        processed_infohashes = set()
        final_output = []

        for cached_link in cached_links:
            result = self._process_torrent(cached_link, existing_hashes, processed_infohashes)
            if result:
                final_output.append(result)

        overall_elapsed = time.perf_counter() - overall_start

        timers = [
            {"script": "Jackett Search", "time": jackett_time},
            {"script": "RD Cache Check", "time": cached_links_time},
            {"script": "RD Download Links", "time": overall_elapsed},
        ]

        return {
            "data": final_output,
            "timers": timers,
        }

    # ------------------------------------------------------------------
    # Streaming API (generator)
    # ------------------------------------------------------------------

    def search_and_get_links_stream(
        self, query: str, limit: int = 10, cancel_event=None
    ):
        """
        Generator that yields dict events as each torrent is processed.

        Event types:
            {"type": "progress", "stage": "...", "detail": "..."}
            {"type": "result",   "torrent": { ... }}
            {"type": "done",     "total": N, "elapsed": T}
            {"type": "cancelled"}
            {"type": "error",    "message": "..."}
        """
        overall_start = time.perf_counter()

        # 1. Jackett search + RD cache check
        yield {"type": "progress", "stage": "Searching", "detail": f"Querying Jackett for '{query}'..."}

        try:
            cached_link_service = RDCachedLinkService(api_key=self.api_key)
            cached_links, cached_links_time, jackett_time = (
                cached_link_service.search_and_check_cache(query, limit)
            )
        except Exception as e:
            logger.error(f"Streaming search failed: {e}")
            yield {"type": "error", "message": "Search failed. Please try again."}
            return

        total_cached = len(cached_links)

        yield {
            "type": "progress",
            "stage": "Checking Duplicates",
            "detail": "Fetching your existing Real-Debrid torrents to prevent duplicates...",
            "total": total_cached,
            "current": 0,
        }

        existing_hashes = self._fetch_existing_hashes()

        yield {
            "type": "progress",
            "stage": "Processing",
            "detail": f"Found {total_cached} cached torrents. Processing...",
            "total": total_cached,
            "current": 0,
        }

        # 2. Process each cached torrent
        processed_infohashes = set()
        result_count = 0

        for idx, cached_link in enumerate(cached_links):
            # Check cancellation
            if cancel_event and cancel_event.is_set():
                yield {"type": "cancelled"}
                return

            torrent_name = cached_link.get('title', 'Unknown Title')

            yield {
                "type": "progress",
                "stage": "Processing",
                "detail": f"Processing: {torrent_name[:60]}...",
                "total": total_cached,
                "current": idx + 1,
            }

            result = self._process_torrent(cached_link, existing_hashes, processed_infohashes)
            if result:
                result_count += 1
                yield {"type": "result", "torrent": result}

        overall_elapsed = time.perf_counter() - overall_start
        yield {
            "type": "done",
            "total": result_count,
            "elapsed": round(overall_elapsed, 2),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    # Statuses that indicate the torrent will never complete.
    _DEAD_STATUSES = frozenset(('error', 'magnet_error', 'virus', 'dead'))

    # Max retries when waiting for a cached torrent to reach "downloaded".
    _STATUS_RETRIES = 3
    _STATUS_RETRY_DELAY = 1  # seconds

    def _fetch_existing_hashes(self) -> Dict[str, str]:
        """Build a hash→ID lookup of the user's existing RD torrents.

        Used to reuse existing torrents instead of adding duplicate magnets.
        """
        try:
            existing_torrents = self.rd_service.get_all_torrents()
            return {
                t.get('hash', '').lower(): t.get('id')
                for t in existing_torrents if t.get('hash') and t.get('id')
            }
        except Exception as e:
            logger.warning(f"Failed to fetch existing torrents for duplicate check: {e}")
            return {}

    def _process_torrent(
        self,
        cached_link: Dict[str, Any],
        existing_hashes: Dict[str, str],
        processed_infohashes: set,
    ) -> Optional[Dict[str, Any]]:
        """Process a single cached torrent through the full pipeline.

        Adds/reuses magnet, selects video files, unrestricts links.
        Returns a result dict or None if the torrent was skipped or failed.
        """
        torrent_name = cached_link.get('title', 'Unknown Title')
        categories = cached_link.get('categories', [])
        magnet_link = cached_link.get('magnet_link')
        infohash = cached_link.get('infohash')

        if not magnet_link or infohash in processed_infohashes:
            return None

        processed_infohashes.add(infohash)
        infohash_lower = infohash.lower() if infohash else None

        try:
            # Reuse existing torrent if the hash is already in RD
            is_new_torrent = False
            if infohash_lower and infohash_lower in existing_hashes:
                torrent_id = existing_hashes[infohash_lower]
                logger.debug(f"Reusing existing torrent ID {torrent_id} for '{torrent_name}'")
            else:
                logger.debug(f"Adding magnet for '{torrent_name}' (hash: {infohash[:8]}...)")
                torrent_id = self.rd_service.add_magnet(magnet_link)
                is_new_torrent = True
                if not torrent_id:
                    logger.warning(f"Failed to add magnet for '{torrent_name}'")
                    return None
                if infohash_lower:
                    existing_hashes[infohash_lower] = torrent_id

            torrent_info = self.rd_service.get_torrent_info(torrent_id)
            status = torrent_info.get('status')

            # Select files if needed
            if is_new_torrent or status == 'waiting_files_selection':
                all_files = torrent_info.get('files') or []
                video_ids = [
                    str(f['id']) for f in all_files
                    if f.get('id') is not None and FileHelper.is_video_file(f.get('path', '').lstrip('/'))
                ]
                files_to_select = ','.join(video_ids) if video_ids else 'all'

                if not self.rd_service.select_files(torrent_id, files=files_to_select):
                    logger.warning(f"Failed to select files for torrent '{torrent_name}'")
                    if is_new_torrent:
                        self._try_delete_torrent(torrent_id)
                    return None

            # Verify the torrent actually reached "downloaded" status.
            if status != 'downloaded':
                torrent_info, ok = self._wait_for_downloaded(
                    torrent_id, torrent_name, is_new_torrent
                )
                if not ok:
                    return None

            files = torrent_info.get('files') or []
            links = torrent_info.get('links') or []
            selected_files = [f for f in files if f.get('selected') == 1]

            # Unrestrict links for selected files
            unrestricted_links = []
            for link in links:
                try:
                    unrestricted = self.rd_service.unrestrict_link(link)
                    unrestricted_links.append(unrestricted)
                except RealDebridError as e:
                    logger.error(f"Error unrestricting link: {e}")
                    unrestricted_links.append(link)

            # Build file list (video files only)
            torrent_files = []
            for file_info, unrestricted_link in zip(selected_files, unrestricted_links):
                file_name = file_info.get('path', '').lstrip('/')
                file_size = FileHelper.format_file_size(file_info.get('bytes', 0))
                if FileHelper.is_video_file(file_name):
                    torrent_files.append({
                        'File Name': file_name,
                        'File Size': file_size,
                        'Download Link': unrestricted_link,
                    })

            logger.debug(f"Torrent '{torrent_name}': {len(torrent_files)} video files found.")
            if torrent_files:
                return {
                    'Torrent Name': torrent_name,
                    'Categories': categories,
                    'Files': torrent_files,
                }

        except RealDebridError as e:
            logger.error(f"RD error processing torrent '{torrent_name}': {e}")
        except Exception as e:
            logger.exception(f"Unexpected error processing torrent '{torrent_name}': {e}")

        return None

    def _wait_for_downloaded(
        self, torrent_id: str, torrent_name: str, is_new_torrent: bool
    ) -> Tuple[Optional[dict], bool]:
        """
        After select_files(), poll torrent status to confirm it reached
        "downloaded".  Returns (torrent_info, ok).  If the torrent is
        stuck or dead, it is cleaned up automatically.
        """
        for attempt in range(self._STATUS_RETRIES):
            torrent_info = self.rd_service.get_torrent_info(torrent_id)
            status = torrent_info.get('status', '')

            if status == 'downloaded':
                return torrent_info, True

            if status in self._DEAD_STATUSES:
                logger.warning(
                    f"Torrent '{torrent_name}' reached dead status '{status}' — cleaning up."
                )
                if is_new_torrent:
                    self._try_delete_torrent(torrent_id)
                return None, False

            # Still processing — wait briefly before retrying
            if attempt < self._STATUS_RETRIES - 1:
                time.sleep(self._STATUS_RETRY_DELAY)

        # Exhausted retries — stale cache, clean up
        logger.warning(
            f"Torrent '{torrent_name}' stuck at '{status}' after "
            f"{self._STATUS_RETRIES} checks — cleaning up."
        )
        if is_new_torrent:
            self._try_delete_torrent(torrent_id)
        return None, False

    def _try_delete_torrent(self, torrent_id: str):
        """Best-effort cleanup of a torrent entry that failed to process."""
        try:
            requests.delete(
                f'https://api.real-debrid.com/rest/1.0/torrents/delete/{torrent_id}',
                headers={'Authorization': f'Bearer {self.api_key}'},
                timeout=(5, 15),
            )
            logger.debug(f"Cleaned up failed torrent entry {torrent_id}")
        except Exception as e:
            logger.warning(f"Failed to clean up torrent {torrent_id}: {e}")
