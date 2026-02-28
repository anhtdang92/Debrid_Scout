import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

# Set DEBUG_MODE based on an environment variable, defaulting to False
DEBUG_MODE = os.getenv("DEBUG_MODE", "False") == "True"

if DEBUG_MODE:
    logging.basicConfig(level=logging.DEBUG)
    logger.debug("REAL_DEBRID_API_KEY is set: %s", os.getenv('REAL_DEBRID_API_KEY') is not None)
    logger.debug("FLASK_ENV: %s", os.getenv('FLASK_ENV'))

def _safe_int(var_name: str, default: int) -> int:
    """Parse an integer env var, falling back to default on invalid input."""
    raw = os.getenv(var_name)
    if raw is None:
        return default
    try:
        return int(raw)
    except (ValueError, TypeError):
        logger.warning(f"Invalid integer for {var_name}={raw!r}, using default {default}")
        return default


def _safe_float(var_name: str, default: float) -> float:
    """Parse a float env var, falling back to default on invalid input."""
    raw = os.getenv(var_name)
    if raw is None:
        return default
    try:
        return float(raw)
    except (ValueError, TypeError):
        logger.warning(f"Invalid float for {var_name}={raw!r}, using default {default}")
        return default


class Config:
    """Base configuration with shared settings."""
    JACKETT_API_KEY = os.getenv('JACKETT_API_KEY')
    JACKETT_URL = os.getenv('JACKETT_URL', 'http://localhost:9117')
    REAL_DEBRID_API_KEY = os.getenv('REAL_DEBRID_API_KEY')
    HERESPHERE_AUTH_TOKEN = os.getenv('HERESPHERE_AUTH_TOKEN')  # optional

    # Tunable parameters (override via environment variables)
    ACCOUNT_CACHE_TTL = _safe_int('ACCOUNT_CACHE_TTL', 300)
    RD_RATE_LIMIT_DELAY = _safe_float('RD_RATE_LIMIT_DELAY', 0.2)
    RD_API_TIMEOUT = _safe_int('RD_API_TIMEOUT', 15)
    RD_CONNECT_TIMEOUT = _safe_int('RD_CONNECT_TIMEOUT', 5)
    JACKETT_TIMEOUT = _safe_int('JACKETT_TIMEOUT', 20)
    JACKETT_RETRY_COUNT = _safe_int('JACKETT_RETRY_COUNT', 5)
    JACKETT_RETRY_DELAY = _safe_int('JACKETT_RETRY_DELAY', 2)
    RD_STATUS_RETRIES = _safe_int('RD_STATUS_RETRIES', 3)
    RD_STATUS_RETRY_DELAY = _safe_float('RD_STATUS_RETRY_DELAY', 1.0)
    FFPROBE_TIMEOUT = _safe_int('FFPROBE_TIMEOUT', 15)
    FFMPEG_THUMB_TIMEOUT = _safe_int('FFMPEG_THUMB_TIMEOUT', 30)
    FFMPEG_PREVIEW_TIMEOUT = _safe_int('FFMPEG_PREVIEW_TIMEOUT', 60)
    RD_MAX_WORKERS = _safe_int('RD_MAX_WORKERS', 4)
    LOG_MAX_BYTES = _safe_int('LOG_MAX_BYTES', 10240)
    THUMBNAIL_MAX_AGE_DAYS = _safe_int('THUMBNAIL_MAX_AGE_DAYS', 7)

class DevelopmentConfig(Config):
    """Development-specific configuration."""
    DEBUG = os.getenv("DEBUG", "True") == "True"

class ProductionConfig(Config):
    """Production-specific configuration."""
    DEBUG = False
