from flask import Blueprint, render_template, current_app
from app.services.real_debrid import RealDebridService, RealDebridError
import logging

info_bp = Blueprint('info', __name__)

# Set up logging
logger = logging.getLogger(__name__)

@info_bp.route('/about')
def about():
    # Initialize the RealDebridService to get account info
    service = RealDebridService()

    account_info = None
    real_debrid_api_error = None
    jackett_url = current_app.config.get('JACKETT_URL')  # Get Jackett URL from config

    try:
        # Fetch account information
        account_info = service.get_account_info()
        logger.info("Successfully retrieved Real-Debrid account information.")
    except RealDebridError as e:
        logger.error("Failed to retrieve Real-Debrid account information", exc_info=True)
        real_debrid_api_error = str(e)

    # Render the about page with the gathered context
    return render_template(
        'about.html',
        account_info=account_info,
        jackett_url=jackett_url,
        real_debrid_api_error=real_debrid_api_error
    )

@info_bp.route('/contact')
def contact():
    # Initialize the RealDebridService to get account info
    service = RealDebridService()

    account_info = None
    real_debrid_api_error = None
    jackett_url = current_app.config.get('JACKETT_URL')  # Get Jackett URL from config

    try:
        # Fetch account information
        account_info = service.get_account_info()
        logger.info("Successfully retrieved Real-Debrid account information.")
    except RealDebridError as e:
        logger.error("Failed to retrieve Real-Debrid account information", exc_info=True)
        real_debrid_api_error = str(e)

    # Render the contact page with the gathered context
    return render_template(
        'contact.html',
        account_info=account_info,
        jackett_url=jackett_url,
        real_debrid_api_error=real_debrid_api_error
    )