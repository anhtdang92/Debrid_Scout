from flask import Flask
import logging
from logging.handlers import RotatingFileHandler
import os
import json
from dotenv import load_dotenv
from app.config import DevelopmentConfig, ProductionConfig
from .routes.search import search_bp
from .routes.account import account_bp
from .routes.torrent import torrent_bp
from .routes.info import info_bp  # Import the info blueprint
from .routes.heresphere import heresphere_bp

# Load environment variables here in case it’s not loaded in config.py
load_dotenv()

def create_app():
    app = Flask(__name__, template_folder='templates')

    # Load the configuration (choose based on your environment)
    environment = os.getenv('FLASK_ENV', 'development')
    if environment == 'production':
        app.config.from_object(ProductionConfig)
    else:
        app.config.from_object(DevelopmentConfig)

    # Validate essential configurations
    if not app.config.get('REAL_DEBRID_API_KEY'):
        app.logger.error("REAL_DEBRID_API_KEY is not set. Application cannot run without it.")
        raise RuntimeError("REAL_DEBRID_API_KEY is missing.")

    # Ensure the logs directory exists
    log_directory = os.path.join(app.root_path, '..', 'logs')
    if not os.path.exists(log_directory):
        os.makedirs(log_directory)

    # Set up logging with RotatingFileHandler
    log_file = os.path.join(log_directory, 'app.log')
    file_handler = RotatingFileHandler(log_file, maxBytes=10240, backupCount=10)
    file_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    )
    file_handler.setFormatter(formatter)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.DEBUG)

    # Log the app startup
    app.logger.info('DebridScout startup')

    # Load static resources like category icons and video extensions
    static_folder_path = os.path.join(app.root_path, 'static')
    try:
        with open(os.path.join(static_folder_path, "category_icons.json"), "r") as f:
            category_icons = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        app.logger.error(f"Error loading category_icons.json: {e}")
        category_icons = {}

    try:
        with open(os.path.join(static_folder_path, "video_extensions.json"), "r") as f:
            video_extensions = json.load(f).get("video_extensions", [])
    except (FileNotFoundError, json.JSONDecodeError) as e:
        app.logger.error(f"Error loading video_extensions.json: {e}")
        video_extensions = []

    # Inject static resources and API key into templates
    @app.context_processor
    def inject_static_resources():
        return {
            "category_icons": category_icons,
            "video_extensions": video_extensions,
            "jackett_url": app.config.get("JACKETT_URL")
        }


    # Register Blueprints
    app.register_blueprint(search_bp, url_prefix='/')
    app.register_blueprint(account_bp, url_prefix='/account')
    app.register_blueprint(torrent_bp, url_prefix='/torrent')
    app.register_blueprint(info_bp)  # No URL prefix for info
    app.register_blueprint(heresphere_bp, url_prefix='/heresphere')

    return app
