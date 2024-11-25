import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set DEBUG_MODE based on an environment variable, defaulting to False
DEBUG_MODE = os.getenv("DEBUG_MODE", "False") == "True"

if DEBUG_MODE:
    # Debug print statements to verify environment variables
    real_debrid_api_key_set = os.getenv('REAL_DEBRID_API_KEY') is not None
    print(f"REAL_DEBRID_API_KEY is set: {real_debrid_api_key_set}")
    print(f"FLASK_ENV: {os.getenv('FLASK_ENV')}")
    print(f"DEBUG: {os.getenv('DEBUG')}")

class Config:
    """Base configuration with shared settings."""
    JACKETT_API_KEY = os.getenv('JACKETT_API_KEY')
    JACKETT_URL = os.getenv('JACKETT_URL', 'http://localhost:9117')
    REAL_DEBRID_API_KEY = os.getenv('REAL_DEBRID_API_KEY')

    if DEBUG_MODE:
        real_debrid_api_key_set = REAL_DEBRID_API_KEY is not None
        print(f"Config REAL_DEBRID_API_KEY is set: {real_debrid_api_key_set}")

class DevelopmentConfig(Config):
    """Development-specific configuration."""
    DEBUG = os.getenv("DEBUG", "True") == "True"

    if DEBUG_MODE:
        real_debrid_api_key_set = Config.REAL_DEBRID_API_KEY is not None
        print(f"REAL_DEBRID_API_KEY in DevelopmentConfig is set: {real_debrid_api_key_set}")

class ProductionConfig(Config):
    """Production-specific configuration."""
    DEBUG = False

    if DEBUG_MODE:
        real_debrid_api_key_set = Config.REAL_DEBRID_API_KEY is not None
        print(f"REAL_DEBRID_API_KEY in ProductionConfig is set: {real_debrid_api_key_set}")

# Debug print to confirm configuration being used
if DEBUG_MODE:
    flask_env = os.getenv('FLASK_ENV', 'production')
    print(f"Using {'DevelopmentConfig' if flask_env == 'development' else 'ProductionConfig'}")
