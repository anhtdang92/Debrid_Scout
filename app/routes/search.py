# app/routes/search.py

from flask import Blueprint, request, render_template, current_app
import logging
import time
from app import cache
from app.services.file_helper import FileHelper
from app.services.real_debrid import RealDebridError
from app.services.rd_download_link import RDDownloadLinkService, RDDownloadLinkError

search_bp = Blueprint('search', __name__)
logger = logging.getLogger(__name__)


@search_bp.route('/', methods=['GET', 'POST'])
@cache.cached(timeout=300, query_string=True, key_prefix=lambda: request.url + str(request.form))
def index():
    # account_info is injected automatically via context processor.
    output = ""
    data = None
    error = None
    status_messages = ""
    overall_elapsed_time = None
    script_times_data = []

    REAL_DEBRID_API_KEY = current_app.config.get('REAL_DEBRID_API_KEY')

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
            overall_start_time = time.perf_counter()

            download_service = RDDownloadLinkService(api_key=REAL_DEBRID_API_KEY)
            result = download_service.search_and_get_links(query, int(limit))

            data = result.get("data")
            script_times_data = result.get("timers", [])
            overall_elapsed_time = time.perf_counter() - overall_start_time

            if not data:
                error = "No Results Found."
                logger.info("No results returned from search pipeline.")

        except (RDDownloadLinkError, RealDebridError) as e:
            error = f"Service error: {e}"
            logger.error(f"Service error during search: {e}")
        except Exception as e:
            error = f"An error occurred: {e}"
            logger.exception("Unexpected error during search operation.")

    return render_template(
        'index.html',
        output=output,
        data=data,
        error=error,
        status_messages=status_messages,
        overall_time=overall_elapsed_time if overall_elapsed_time else None,
        script_times=script_times_data,
        simplify_filename=FileHelper.simplify_filename
    )
