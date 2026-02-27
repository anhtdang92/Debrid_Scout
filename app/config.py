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

class Config:
    """Base configuration with shared settings."""
    JACKETT_API_KEY = os.getenv('JACKETT_API_KEY')
    JACKETT_URL = os.getenv('JACKETT_URL', 'http://localhost:9117')
    REAL_DEBRID_API_KEY = os.getenv('REAL_DEBRID_API_KEY')
    HERESPHERE_AUTH_TOKEN = os.getenv('HERESPHERE_AUTH_TOKEN')  # optional

    # Tunable parameters (override via environment variables)
    ACCOUNT_CACHE_TTL = int(os.getenv('ACCOUNT_CACHE_TTL', '300'))
    RD_RATE_LIMIT_DELAY = float(os.getenv('RD_RATE_LIMIT_DELAY', '0.2'))
    RD_API_TIMEOUT = int(os.getenv('RD_API_TIMEOUT', '15'))
    JACKETT_TIMEOUT = int(os.getenv('JACKETT_TIMEOUT', '20'))
    JACKETT_RETRY_COUNT = int(os.getenv('JACKETT_RETRY_COUNT', '5'))
    LOG_MAX_BYTES = int(os.getenv('LOG_MAX_BYTES', '10240'))
    THUMBNAIL_MAX_AGE_DAYS = int(os.getenv('THUMBNAIL_MAX_AGE_DAYS', '7'))

class DevelopmentConfig(Config):
    """Development-specific configuration."""
    DEBUG = os.getenv("DEBUG", "True") == "True"

class ProductionConfig(Config):
    """Production-specific configuration."""
    DEBUG = False
