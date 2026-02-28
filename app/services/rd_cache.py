# app/services/rd_cache.py

"""
Shared caching layer for Real-Debrid API responses.

Provides TTL-based caching for:
  - Individual torrent info (used by HereSphere/DeoVR detail views)
  - All-torrents list (used by library views and RD Manager)
  - Batch link unrestriction with ThreadPoolExecutor

Moved here from heresphere.py to eliminate tight coupling between blueprints.
"""

import os
import time
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def _safe_int(name: str, default: int) -> int:
    """Read an env var as int, falling back to default on parse error."""
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except (ValueError, TypeError):
        logger.warning(f"Invalid {name}={raw!r}, using default {default}")
        return default


# ── Torrent info cache (per-torrent, TTL configurable) ─────────
_torrent_cache: Dict[str, dict] = {}
_torrent_cache_lock = threading.Lock()
_TORRENT_CACHE_TTL = _safe_int('RD_TORRENT_CACHE_TTL', 300)

# ── All-torrents list cache (TTL configurable) ─────────────────
_all_torrents_cache: Dict[str, object] = {"data": None, "expires": 0}
_all_torrents_lock = threading.Lock()
_ALL_TORRENTS_TTL = _safe_int('RD_ALL_TORRENTS_CACHE_TTL', 60)


def clear_caches():
    """Reset all caches — used by test fixtures to avoid cross-test leakage."""
    with _torrent_cache_lock:
        _torrent_cache.clear()
    with _all_torrents_lock:
        _all_torrents_cache["data"] = None
        _all_torrents_cache["expires"] = 0


def get_torrent_info_cached(service, torrent_id: str) -> dict:
    """Fetch torrent info via RealDebridService with a short TTL cache."""
    now = time.time()
    with _torrent_cache_lock:
        cached = _torrent_cache.get(torrent_id)
        if cached and (now - cached['ts']) < _TORRENT_CACHE_TTL:
            return cached['data']
    data = service.get_torrent_info(torrent_id)
    with _torrent_cache_lock:
        _torrent_cache[torrent_id] = {'data': data, 'ts': now}
    return data


def get_all_torrents_cached(service) -> list:
    """Fetch all torrents with a short TTL cache to avoid repeated API calls."""
    now = time.time()
    with _all_torrents_lock:
        if _all_torrents_cache["data"] is not None and _all_torrents_cache["expires"] > now:
            return _all_torrents_cache["data"]

    data = service.get_all_torrents()
    with _all_torrents_lock:
        _all_torrents_cache["data"] = data
        _all_torrents_cache["expires"] = now + _ALL_TORRENTS_TTL
    return data


def batch_unrestrict(service, links: List[str], max_workers: int = 3) -> List[str]:
    """Unrestrict multiple links concurrently using a thread pool.

    Returns a list of unrestricted URLs in the same order as the input.
    Falls back to the restricted link on per-link failure.
    """
    if not links:
        return []

    results: List[Optional[str]] = [None] * len(links)

    def _unrestrict_one(idx: int, link: str) -> Tuple[int, str]:
        try:
            return idx, service.unrestrict_link(link)
        except Exception as e:
            logger.warning(f"Failed to unrestrict link {idx}: {e}")
            return idx, link

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(_unrestrict_one, i, link) for i, link in enumerate(links)]
        for future in as_completed(futures):
            idx, url = future.result(timeout=60)
            results[idx] = url

    return [r or links[i] for i, r in enumerate(results)]
