# app/routes/info.py

from flask import Blueprint, render_template
import logging

info_bp = Blueprint('info', __name__)
logger = logging.getLogger(__name__)


@info_bp.route('/about')
def about():
    """Render the About page."""
    return render_template('about.html')


@info_bp.route('/contact')
def contact():
    """Render the Contact page."""
    return render_template('contact.html')
