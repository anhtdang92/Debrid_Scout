import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set DEBUG_MODE based on an environment variable, defaulting to False
DEBUG_MODE = os.getenv("DEBUG_MODE", "False") == "True"

if DEBUG_MODE:
    # Debug print statements to verify environment variables
    print("REAL_DEBRID_API_KEY:", os.getenv('REAL_DEBRID_API_KEY'))
    print("FLASK_ENV:", os.getenv("FLASK_ENV"))
    print("DEBUG:", os.getenv("DEBUG"))

class Config:
    """Base configuration with shared settings."""
    JACKETT_API_KEY = os.getenv('JACKETT_API_KEY')
    JACKETT_URL = os.getenv('JACKETT_URL', 'http://localhost:9117')
    REAL_DEBRID_API_KEY = os.getenv('REAL_DEBRID_API_KEY')

    if DEBUG_MODE:
        print("Config REAL_DEBRID_API_KEY:", REAL_DEBRID_API_KEY)

class DevelopmentConfig(Config):
    """Development-specific configuration."""
    DEBUG = os.getenv("DEBUG", "True") == "True"

    if DEBUG_MODE:
        print("REAL_DEBRID_API_KEY in DevelopmentConfig:", Config.REAL_DEBRID_API_KEY)

class ProductionConfig(Config):
    """Production-specific configuration."""
    DEBUG = False

    if DEBUG_MODE:
        print("REAL_DEBRID_API_KEY in ProductionConfig:", Config.REAL_DEBRID_API_KEY)

# Debug print to confirm configuration being used
if DEBUG_MODE:
    if os.getenv('FLASK_ENV') == 'development':
        print("Using DevelopmentConfig")
    else:
        print("Using ProductionConfig")