# app/services/user_data.py

"""
Local persistence for user data (favorites, ratings) that HereSphere
can write back to the server.

Modelled after XBVR's write-back pattern: HereSphere POSTs isFavorite
and rating in the JSON body, and we store them in a local JSON file.

Thread-safe via a threading lock (HereSphere can fire rapid POSTs).
"""

import json
import os
import threading
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_DEFAULT_DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'data',
)


class UserDataStore:
    """Thread-safe JSON-backed store for per-torrent user data."""

    def __init__(self, data_dir: Optional[str] = None):
        self._dir = data_dir or _DEFAULT_DATA_DIR
        os.makedirs(self._dir, exist_ok=True)
        self._path = os.path.join(self._dir, 'user_data.json')
        self._lock = threading.Lock()
        self._cache = self._load()

    # ── Read ──────────────────────────────────────────────────

    def get(self, torrent_id: str) -> dict:
        """Return stored data for a torrent, or defaults."""
        with self._lock:
            return self._cache.get(torrent_id, {}).copy()

    def is_favorite(self, torrent_id: str) -> bool:
        return self.get(torrent_id).get('isFavorite', False)

    def get_rating(self, torrent_id: str) -> float:
        return self.get(torrent_id).get('rating', 0.0)

    # ── Write ─────────────────────────────────────────────────

    def set_favorite(self, torrent_id: str, value: bool):
        """Set or clear the favorite flag for a torrent."""
        with self._lock:
            entry = self._cache.setdefault(torrent_id, {})
            if entry.get('isFavorite') != value:
                entry['isFavorite'] = value
                self._save()
                logger.info(f"Favorite updated for {torrent_id}: {value}")

    def set_rating(self, torrent_id: str, value: float):
        """Set the star rating (0-5) for a torrent."""
        value = max(0.0, min(5.0, float(value)))
        with self._lock:
            entry = self._cache.setdefault(torrent_id, {})
            if entry.get('rating') != value:
                entry['rating'] = value
                self._save()
                logger.info(f"Rating updated for {torrent_id}: {value}")

    def process_heresphere_update(self, torrent_id: str, body: dict):
        """
        Process a HereSphere POST body and persist any write-back data.

        XBVR pattern: HereSphere sends isFavorite and/or rating alongside
        needsMediaSource in the same POST body.
        """
        if 'isFavorite' in body:
            self.set_favorite(torrent_id, bool(body['isFavorite']))
        if 'rating' in body:
            self.set_rating(torrent_id, body['rating'])

    # ── Persistence ───────────────────────────────────────────

    def _load(self) -> dict:
        """Load from disk, returning empty dict on any error."""
        if not os.path.isfile(self._path):
            return {}
        try:
            with open(self._path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Could not load user data: {e}")
            return {}

    def _save(self):
        """Write cache to disk. Caller must hold self._lock."""
        try:
            with open(self._path, 'w') as f:
                json.dump(self._cache, f, indent=2)
        except OSError as e:
            logger.error(f"Could not save user data: {e}")
