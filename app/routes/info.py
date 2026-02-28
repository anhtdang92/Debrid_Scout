# app/routes/info.py

from flask import Blueprint, render_template, jsonify, current_app
import logging
import time

info_bp = Blueprint('info', __name__)
logger = logging.getLogger(__name__)


@info_bp.route('/health')
def health():
    """Lightweight health check for Docker/orchestrators.

    Returns JSON with service status and basic connectivity checks.
    """
    checks = {"api_key_set": bool(current_app.config.get('REAL_DEBRID_API_KEY'))}

    jackett_key = current_app.config.get('JACKETT_API_KEY')
    checks["jackett_key_set"] = bool(jackett_key)

    status = "healthy" if all(checks.values()) else "degraded"
    return jsonify({"status": status, "checks": checks}), 200


@info_bp.route('/about')
def about():
    """Render the About page."""
    return render_template('about.html')


@info_bp.route('/contact')
def contact():
    """Render the Contact page."""
    return render_template('contact.html')
