# app/routes/info.py

from flask import Blueprint, render_template
import logging

info_bp = Blueprint('info', __name__)
logger = logging.getLogger(__name__)


@info_bp.route('/about')
def about():
    # account_info and real_debrid_api_error are injected automatically
    # via the context processor in __init__.py
    return render_template('about.html')


@info_bp.route('/contact')
def contact():
    return render_template('contact.html')
