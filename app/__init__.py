from flask import Flask, g
import logging
from logging.handlers import RotatingFileHandler
import os
import json
import time
from dotenv import load_dotenv
from app.config import DevelopmentConfig, ProductionConfig
from .routes.search import search_bp
from .routes.account import account_bp
from .routes.torrent import torrent_bp
from .routes.info import info_bp
from .routes.heresphere import heresphere_bp

# Load environment variables here in case it's not loaded in config.py
load_dotenv()

# ── Cached account info with TTL ──────────────────────────────
# Avoids hitting the RD API on every single page load.
_account_cache = {"data": None, "error": None, "expires": 0}
_CACHE_TTL = 300  # 5 minutes


def _get_cached_account_info(app):
    """Return cached RD account info, refreshing at most every _CACHE_TTL seconds."""
    now = time.time()
    if _account_cache["expires"] > now:
        return _account_cache["data"], _account_cache["error"]

    from app.services.real_debrid import RealDebridService, RealDebridError

    api_key = app.config.get('REAL_DEBRID_API_KEY')
    if not api_key:
        _account_cache["data"] = None
        _account_cache["error"] = "Real-Debrid API key is not set."
        _account_cache["expires"] = now + _CACHE_TTL
        return _account_cache["data"], _account_cache["error"]

    try:
        service = RealDebridService(api_key=api_key)
        info = service.get_account_info()
        _account_cache["data"] = info
        _account_cache["error"] = None
    except RealDebridError as e:
        _account_cache["data"] = None
        _account_cache["error"] = str(e)

    _account_cache["expires"] = now + _CACHE_TTL
    return _account_cache["data"], _account_cache["error"]


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

    # Set a secret key for CSRF (use env var or fallback to a random key)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', os.urandom(32).hex())

    # ── CSRF protection ────────────────────────────────────────
    from flask_wtf.csrf import CSRFProtect
    csrf = CSRFProtect(app)

    # Exempt JSON API endpoints from CSRF (they use Authorization headers)
    csrf.exempt(torrent_bp)
    csrf.exempt(heresphere_bp)

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

    # ── before_request: cache account info in g ────────────────
    @app.before_request
    def load_account_info():
        g.account_info, g.real_debrid_api_error = _get_cached_account_info(app)

    # Inject static resources + cached account info into ALL templates
    @app.context_processor
    def inject_globals():
        return {
            "category_icons": category_icons,
            "video_extensions": video_extensions,
            "jackett_url": app.config.get("JACKETT_URL"),
            "account_info": getattr(g, 'account_info', None),
            "real_debrid_api_error": getattr(g, 'real_debrid_api_error', None),
        }

    # Register Blueprints
    app.register_blueprint(search_bp, url_prefix='/')
    app.register_blueprint(account_bp, url_prefix='/account')
    app.register_blueprint(torrent_bp, url_prefix='/torrent')
    app.register_blueprint(info_bp)  # No URL prefix for info
    app.register_blueprint(heresphere_bp, url_prefix='/heresphere')

    return app
