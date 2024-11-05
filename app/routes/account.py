from flask import Blueprint, render_template, current_app
from app.services.real_debrid import RealDebridService, RealDebridError
import logging

# Initialize the Blueprint
account_bp = Blueprint('account', __name__)

# Set up logger
logger = logging.getLogger(__name__)

@account_bp.route("/account")
def account_info():
    """
    Render the account information page with details from Real-Debrid and Jackett.

    Utilizes the RealDebridService to fetch account information.
    Handles errors gracefully and provides meaningful feedback to the user.
    """
    # Initialize the RealDebridService with the API key from config
    service = RealDebridService()

    # Retrieve the Jackett URL from the app configuration
    jackett_url = current_app.config.get('JACKETT_URL')
    account_info = None
    real_debrid_api_error = None

    try:
        # Fetch account information using the service
        account_info = service.get_account_info()
        logger.info("Successfully retrieved Real-Debrid account information.")
    except RealDebridError as e:
        # Log the error with more context
        logger.error("Failed to retrieve Real-Debrid account information", exc_info=True)

        # Provide a user-friendly error message
        real_debrid_api_error = "Could not retrieve account information from Real-Debrid. Please try again later."

    # Render the 'account_info.html' template with the fetched data and any errors
    return render_template(
        'account_info.html',
        account_info=account_info,
        jackett_url=jackett_url,
        real_debrid_api_error=real_debrid_api_error
    )
