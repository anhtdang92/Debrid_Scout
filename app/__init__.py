from flask import Flask, g
import logging
from logging.handlers import RotatingFileHandler
import os
import json
import time
import threading
from flask_caching import Cache
from app.config import DevelopmentConfig, ProductionConfig

# Global cache instance
cache = Cache(config={'CACHE_TYPE': 'SimpleCache', 'CACHE_DEFAULT_TIMEOUT': 300})

from .routes.search import search_bp
from .routes.account import account_bp
from .routes.torrent import torrent_bp
from .routes.info import info_bp
from .routes.heresphere import heresphere_bp
from .routes.deovr import deovr_bp

# ── Cached account info with TTL ──────────────────────────────
# Avoids hitting the RD API on every single page load.
_account_cache = {"data": None, "error": None, "expires": 0}
_account_cache_lock = threading.Lock()

def _get_cached_account_info(app):
    """Return cached RD account info, refreshing at most every ACCOUNT_CACHE_TTL seconds."""
    cache_ttl = app.config.get('ACCOUNT_CACHE_TTL', 300)
    now = time.time()

    with _account_cache_lock:
        if _account_cache["expires"] > now:
            return _account_cache["data"], _account_cache["error"]

    from app.services.real_debrid import RealDebridService, RealDebridError

    api_key = app.config.get('REAL_DEBRID_API_KEY')
    if not api_key:
        with _account_cache_lock:
            _account_cache["data"] = None
            _account_cache["error"] = "Real-Debrid API key is not set."
            _account_cache["expires"] = now + cache_ttl
            return _account_cache["data"], _account_cache["error"]

    try:
        service = RealDebridService(api_key=api_key)
        info = service.get_account_info()
        with _account_cache_lock:
            _account_cache["data"] = info
            _account_cache["error"] = None
    except RealDebridError as e:
        with _account_cache_lock:
            _account_cache["data"] = None
            _account_cache["error"] = str(e)

    with _account_cache_lock:
        _account_cache["expires"] = now + cache_ttl
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

    if not app.config.get('JACKETT_API_KEY'):
        app.logger.warning(
            "JACKETT_API_KEY is not set — search functionality will not work."
        )

    # Set a secret key for CSRF and sessions.
    secret_key = os.getenv('SECRET_KEY')
    if not secret_key:
        if environment == 'production':
            raise RuntimeError(
                "SECRET_KEY is required in production. "
                "Set SECRET_KEY in your .env or environment variables."
            )
        app.logger.warning(
            "SECRET_KEY is not set — using a random key. "
            "Sessions will be invalidated on restart. "
            "Set SECRET_KEY in your .env for production use."
        )
        secret_key = os.urandom(32).hex()
    app.config['SECRET_KEY'] = secret_key

    # ── CSRF protection ────────────────────────────────────────
    from flask_wtf.csrf import CSRFProtect
    csrf = CSRFProtect(app)

    # Initialize Cache
    cache.init_app(app)

    # Exempt JSON API endpoints from CSRF (they use Authorization headers)
    csrf.exempt(torrent_bp)
    csrf.exempt(heresphere_bp)
    csrf.exempt(deovr_bp)
    csrf.exempt(search_bp)

    # Ensure the logs directory exists
    log_directory = os.path.join(app.root_path, '..', 'logs')
    if not os.path.exists(log_directory):
        os.makedirs(log_directory)

    # Set up logging with RotatingFileHandler
    log_file = os.path.join(log_directory, 'app.log')
    log_max_bytes = app.config.get('LOG_MAX_BYTES', 10240)
    file_handler = RotatingFileHandler(log_file, maxBytes=log_max_bytes, backupCount=10)
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

    # ── Security headers ──────────────────────────────────────────
    @app.after_request
    def set_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' https://fonts.googleapis.com https://cdnjs.cloudflare.com 'unsafe-inline'; "
            "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com; "
            "img-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'self'"
        )
        return response

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

    # ── Register shared services as app extensions ───────────
    from app.services.user_data import UserDataStore
    from app.services.thumbnail import ThumbnailService
    app.extensions['user_data'] = UserDataStore()
    thumb_service = ThumbnailService()
    app.extensions['thumb_service'] = thumb_service

    # Clean up expired thumbnails/previews on startup
    thumb_service.cleanup(max_age_days=app.config.get('THUMBNAIL_MAX_AGE_DAYS', 7))

    # Register Blueprints
    app.register_blueprint(search_bp, url_prefix='/')
    app.register_blueprint(account_bp, url_prefix='/account')
    app.register_blueprint(torrent_bp, url_prefix='/torrent')
    app.register_blueprint(info_bp)  # No URL prefix for info
    app.register_blueprint(heresphere_bp, url_prefix='/heresphere')
    app.register_blueprint(deovr_bp, url_prefix='/deovr')

    return app
