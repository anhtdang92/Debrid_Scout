# app/services/thumbnail.py

"""
Thumbnail generation service using ffmpeg.

Extracts a single frame from a remote video URL and caches it to disk.
HereSphere and DeoVR use the cached thumbnails for library grid display.
"""

import os
import subprocess
import shutil
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Default cache directory (project root / thumbnails)
_DEFAULT_CACHE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'thumbnails',
)


_DEFAULT_PREVIEW_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'previews',
)


class ThumbnailService:
    """Generate and cache video thumbnails and preview clips via ffmpeg."""

    def __init__(self, cache_dir: Optional[str] = None,
                 preview_dir: Optional[str] = None):
        self.cache_dir = cache_dir or _DEFAULT_CACHE_DIR
        self.preview_dir = preview_dir or _DEFAULT_PREVIEW_DIR
        os.makedirs(self.cache_dir, exist_ok=True)
        os.makedirs(self.preview_dir, exist_ok=True)
        self._ffmpeg = shutil.which('ffmpeg')

    @property
    def available(self) -> bool:
        """True if ffmpeg is installed on this system."""
        return self._ffmpeg is not None

    def get_cached_path(self, torrent_id: str) -> Optional[str]:
        """Return the cached thumbnail path if it exists, else None."""
        path = os.path.join(self.cache_dir, f"{torrent_id}.jpg")
        return path if os.path.isfile(path) else None

    def generate(self, torrent_id: str, video_url: str,
                 seek_seconds: int = 10) -> Optional[str]:
        """
        Extract a single frame from a remote video URL using ffmpeg.

        Uses HTTP range requests so only a few MB are downloaded, not the
        entire file.  The result is cached to disk as a 640px-wide JPEG.

        Returns the path to the cached file, or None on failure.
        """
        if not self._ffmpeg:
            logger.warning("ffmpeg not found — cannot generate thumbnail")
            return None

        # Return from cache if already generated
        cached = self.get_cached_path(torrent_id)
        if cached:
            return cached

        output_path = os.path.join(self.cache_dir, f"{torrent_id}.jpg")

        try:
            result = subprocess.run(
                [
                    self._ffmpeg,
                    '-ss', str(seek_seconds),   # seek before opening (fast)
                    '-i', video_url,
                    '-frames:v', '1',            # grab exactly one frame
                    '-vf', 'scale=640:-1',       # 640px wide, keep aspect ratio
                    '-q:v', '3',                 # JPEG quality (2-5 is good)
                    '-y',                        # overwrite if exists
                    output_path,
                ],
                capture_output=True,
                timeout=30,
            )

            if result.returncode == 0 and os.path.isfile(output_path):
                size = os.path.getsize(output_path)
                logger.info(f"Thumbnail generated for {torrent_id}: {size} bytes")
                return output_path

            stderr = result.stderr.decode(errors='replace')[:300]
            logger.warning(f"ffmpeg failed for {torrent_id} (rc={result.returncode}): {stderr}")

            # If seek position was too far into the file, retry at 0
            if seek_seconds > 0:
                return self.generate(torrent_id, video_url, seek_seconds=0)

            return None

        except subprocess.TimeoutExpired:
            logger.warning(f"ffmpeg timed out for {torrent_id}")
            if os.path.isfile(output_path):
                os.remove(output_path)
            return None
        except Exception as e:
            logger.error(f"Thumbnail generation error for {torrent_id}: {e}")
            return None

    # ── Preview clip generation ───────────────────────────────

    def get_cached_preview_path(self, torrent_id: str) -> Optional[str]:
        """Return the cached preview clip path if it exists, else None."""
        path = os.path.join(self.preview_dir, f"{torrent_id}.mp4")
        return path if os.path.isfile(path) else None

    def generate_preview(self, torrent_id: str, video_url: str,
                         seek_seconds: int = 10,
                         duration: int = 5) -> Optional[str]:
        """
        Extract a short preview clip from a remote video URL using ffmpeg.

        Generates a small, muted MP4 clip (320px wide, 5s, ~200-500 KB)
        that HereSphere displays as an animated thumbnail on hover.

        Returns the path to the cached file, or None on failure.
        """
        if not self._ffmpeg:
            logger.warning("ffmpeg not found — cannot generate preview")
            return None

        cached = self.get_cached_preview_path(torrent_id)
        if cached:
            return cached

        output_path = os.path.join(self.preview_dir, f"{torrent_id}.mp4")

        try:
            result = subprocess.run(
                [
                    self._ffmpeg,
                    '-ss', str(seek_seconds),      # seek before open (fast)
                    '-i', video_url,
                    '-t', str(duration),            # clip length
                    '-vf', 'scale=320:-2',          # 320px wide, even height
                    '-an',                          # strip audio
                    '-c:v', 'libx264',
                    '-preset', 'ultrafast',
                    '-crf', '30',                   # small file, decent quality
                    '-movflags', '+faststart',      # web-friendly: moov atom first
                    '-y',
                    output_path,
                ],
                capture_output=True,
                timeout=60,
            )

            if result.returncode == 0 and os.path.isfile(output_path):
                size = os.path.getsize(output_path)
                logger.info(
                    f"Preview generated for {torrent_id}: {size} bytes"
                )
                return output_path

            stderr = result.stderr.decode(errors='replace')[:300]
            logger.warning(
                f"ffmpeg preview failed for {torrent_id} "
                f"(rc={result.returncode}): {stderr}"
            )

            if seek_seconds > 0:
                return self.generate_preview(
                    torrent_id, video_url,
                    seek_seconds=0, duration=duration,
                )

            return None

        except subprocess.TimeoutExpired:
            logger.warning(f"ffmpeg preview timed out for {torrent_id}")
            if os.path.isfile(output_path):
                os.remove(output_path)
            return None
        except Exception as e:
            logger.error(
                f"Preview generation error for {torrent_id}: {e}"
            )
            return None
