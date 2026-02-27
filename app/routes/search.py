# app/routes/search.py

from flask import Blueprint, request, render_template, current_app, Response, jsonify
import json
import logging
import time
import threading
from app.services.file_helper import FileHelper
from app.services.real_debrid import RealDebridError
from app.services.rd_download_link import RDDownloadLinkService, RDDownloadLinkError

search_bp = Blueprint('search', __name__)
logger = logging.getLogger(__name__)

# Active search sessions (keyed by a simple ID) for cancellation
_active_searches = {}
_active_searches_lock = threading.Lock()


@search_bp.route('/', methods=['GET', 'POST'])
def index():
    """Render the search page (GET) or execute a search query (POST)."""
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
            error = "Search service encountered an error. Please try again."
            logger.error(f"Service error during search: {e}")
        except Exception as e:
            error = "An unexpected error occurred. Please try again."
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


# ── SSE Streaming Search ──────────────────────────────────────

@search_bp.route('/stream', methods=['POST'])
def stream_search():
    """
    Server-Sent Events endpoint for streaming search results.

    Accepts JSON body: { "query": "...", "limit": 10 }
    Returns text/event-stream with JSON events.
    """
    if not request.is_json:
        return jsonify({"status": "error", "error": "Content-Type must be application/json"}), 400

    data = request.json
    query = (data.get("query") or "").strip()
    limit = data.get("limit", 10)

    if not query:
        return jsonify({"status": "error", "error": "Query is required"}), 400

    try:
        limit = min(int(limit), 500)
        if limit < 1:
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({"status": "error", "error": "Limit must be a positive integer"}), 400

    api_key = current_app.config.get('REAL_DEBRID_API_KEY')
    if not api_key:
        return jsonify({"status": "error", "error": "API key not configured"}), 500

    # Create a cancel event for this search
    import uuid
    search_id = str(uuid.uuid4())[:8]
    cancel_event = threading.Event()
    with _active_searches_lock:
        _active_searches[search_id] = cancel_event

    # Capture the app instance to use inside the generator thread
    app = current_app._get_current_object()

    def generate():
        with app.app_context():
            try:
                # Send search_id so the client can cancel later
                yield f"data: {json.dumps({'type': 'search_id', 'id': search_id})}\n\n"

                download_service = RDDownloadLinkService(api_key=api_key)
                for event in download_service.search_and_get_links_stream(
                    query, limit, cancel_event=cancel_event
                ):
                    yield f"data: {json.dumps(event)}\n\n"
            except Exception as e:
                logger.exception(f"Streaming search error: {e}")
                yield f"data: {json.dumps({'type': 'error', 'message': 'An error occurred during search'})}\n\n"
            finally:
                with _active_searches_lock:
                    _active_searches.pop(search_id, None)

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
        }
    )


@search_bp.route('/cancel', methods=['POST'])
def cancel_search():
    """Cancel an active streaming search by its ID."""
    if not request.is_json:
        return jsonify({"status": "error", "error": "Content-Type must be application/json"}), 400

    search_id = request.json.get("search_id")
    with _active_searches_lock:
        cancel_event = _active_searches.get(search_id)

    if cancel_event:
        cancel_event.set()
        return jsonify({"status": "cancelled"})
    else:
        return jsonify({"status": "not_found"}), 404
