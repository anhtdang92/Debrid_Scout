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

class DevelopmentConfig(Config):
    """Development-specific configuration."""
    DEBUG = os.getenv("DEBUG", "True") == "True"

class ProductionConfig(Config):
    """Production-specific configuration."""
    DEBUG = False
