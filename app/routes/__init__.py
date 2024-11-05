# app/routes/__init__.py
from .search import search_bp
from .torrent import torrent_bp
from .info import info_bp  # Import the info blueprint

def register_blueprints(app):
    app.register_blueprint(search_bp)
    app.register_blueprint(torrent_bp)
    app.register_blueprint(info_bp)  # Register the info blueprint
