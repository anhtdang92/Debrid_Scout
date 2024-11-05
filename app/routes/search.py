from flask import Blueprint, request, render_template, current_app
import logging
import subprocess
import json
import sys
import time
from app.services.file_helper import FileHelper
from app.services.real_debrid import RealDebridService, RealDebridError

search_bp = Blueprint('search', __name__)
logger = logging.getLogger(__name__)

@search_bp.route('/', methods=['GET', 'POST'])
def index():
    output = ""
    data = None
    error = None
    stderr = None  # Capture stderr for debugging
    status_messages = ""
    overall_elapsed_time = None
    script_elapsed_time = None
    account_info = None
    real_debrid_api_error = None

    # Access the REAL_DEBRID_API_KEY from the app configuration
    REAL_DEBRID_API_KEY = current_app.config.get('REAL_DEBRID_API_KEY')

    # Initialize RealDebridService if API key is available
    if REAL_DEBRID_API_KEY:
        try:
            # Instantiate the service to fetch account information
            real_debrid_service = RealDebridService(api_key=REAL_DEBRID_API_KEY)
            account_info = real_debrid_service.get_account_info()
            logger.info("Successfully retrieved account information in DS Search.")
        except RealDebridError as e:
            real_debrid_api_error = str(e)
            logger.error(f"Failed to fetch account info in DS Search: {e}")
    else:
        real_debrid_api_error = "Real-Debrid API key is not set. Please configure the API key correctly."
        logger.warning(real_debrid_api_error)

    # Handle POST request for search functionality
    if request.method == "POST":
        query = request.form.get("query", "").strip()
        limit = request.form.get("limit", "10").strip()

        if not query:
            error = "Search query cannot be empty."
            logger.warning("Empty search query received.")
            return render_template('index.html', error=error), 400

        if not limit.isdigit() or int(limit) < 1:
            error = "Limit must be a positive integer."
            logger.warning(f"Invalid limit value received: {limit}")
            return render_template('index.html', error=error), 400

        try:
            # Start time measurement for the script execution
            overall_start_time = time.perf_counter()

            # Execute the search script with only query and limit arguments
            result = subprocess.run(
                [sys.executable, "scripts/Get_RD_Download_Link.py", query, "--limit", limit],
                capture_output=True, text=True, timeout=300
            )

            # Capture stdout and stderr for debugging
            stderr = result.stderr.strip()
            script_elapsed_time = time.perf_counter() - overall_start_time
            overall_elapsed_time = time.perf_counter() - overall_start_time

            # Parse JSON output if available, or handle empty response
            if result.returncode == 0:
                if result.stdout.strip():
                    try:
                        data = json.loads(result.stdout)
                        if not data:  # Handle empty result set
                            error = "No Results Found."
                            logger.info("No results returned from search script.")
                    except json.JSONDecodeError as e:
                        error = "Error parsing JSON data from search script."
                        logger.error(f"JSON decode error: {e}")
                else:
                    error = "No Results Found."
                    logger.info("Search script returned an empty response.")
            else:
                error = "Command failed."
                logger.error(f"Error during search subprocess: {stderr}")

        except subprocess.TimeoutExpired:
            error = "The search operation timed out."
            logger.error("Search operation timed out.")
        except Exception as e:
            error = f"An error occurred: {e}"
            logger.exception("Unexpected error during search operation.")

    # Render the index template with the results, account info, and any errors
    return render_template(
        'index.html',
        output=output,
        data=data,
        error=error,
        stderr=stderr,  # Include stderr in template for debug visibility
        status_messages=status_messages,
        overall_time=f"{overall_elapsed_time:.2f}" if overall_elapsed_time else None,
        script_time=f"{script_elapsed_time:.2f}" if script_elapsed_time else None,
        account_info=account_info,
        real_debrid_api_error=real_debrid_api_error,
        simplify_filename=FileHelper.simplify_filename
    )