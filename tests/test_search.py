import pytest
import json
import threading
from unittest.mock import patch


def test_index_page_loads(client, mocked_responses):
    """Test that the index page loads successfully on GET."""
    mocked_responses.get(
        "https://api.real-debrid.com/rest/1.0/user",
        json={"id": 12345, "username": "testuser", "premium": 100},
        status=200
    )

    response = client.get("/")
    assert response.status_code == 200
    assert b"Debrid Scout" in response.data


def test_search_post_validates(client, mocked_responses):
    """Test that empty queries return 400 Bad Request."""
    mocked_responses.get(
        "https://api.real-debrid.com/rest/1.0/user",
        json={"id": 12345, "username": "testuser"},
        status=200
    )

    response = client.post("/", data={"query": "", "limit": "10"})
    assert response.status_code == 400
    assert b"Search query cannot be empty" in response.data


def test_search_post_invalid_limit(client, mocked_responses):
    """Test that invalid limit returns 400 Bad Request."""
    mocked_responses.get(
        "https://api.real-debrid.com/rest/1.0/user",
        json={"id": 12345, "username": "testuser"},
        status=200
    )

    response = client.post("/", data={"query": "test", "limit": "abc"})
    assert response.status_code == 400
    assert b"Limit must be a positive integer" in response.data


def test_jackett_search_pipeline(client, mocked_responses):
    """Test the full search pipeline end-to-end with mocked service layer."""
    mocked_responses.get(
        "https://api.real-debrid.com/rest/1.0/user",
        json={"id": 12345, "username": "testuser"},
        status=200
    )

    # Mock the download link service to return a complete result
    mock_result = {
        "data": [
            {
                "Torrent Name": "Test.Movie.1080p",
                "Categories": ["Movies"],
                "Files": [
                    {
                        "File Name": "Test.Movie.1080p.mkv",
                        "File Size": "1.00 GB",
                        "Download Link": "https://download.real-debrid.com/d/abc123/Test.Movie.1080p.mkv"
                    }
                ]
            }
        ],
        "timers": [
            {"script": "Jackett Search", "time": 1.5},
            {"script": "RD Download Links", "time": 3.2}
        ]
    }

    with patch('app.routes.search.RDDownloadLinkService') as MockService:
        MockService.return_value.search_and_get_links.return_value = mock_result

        response = client.post("/", data={"query": "Test Movie", "limit": "10"})
        assert response.status_code == 200
        assert b"Test Movie 1080p" in response.data  # simplify_filename replaces dots with spaces
        assert b"1.00 GB" in response.data


def test_search_no_results(client, mocked_responses):
    """Test that 'No Results Found' is shown when pipeline returns empty."""
    mocked_responses.get(
        "https://api.real-debrid.com/rest/1.0/user",
        json={"id": 12345, "username": "testuser"},
        status=200
    )

    with patch('app.routes.search.RDDownloadLinkService') as MockService:
        MockService.return_value.search_and_get_links.return_value = {"data": [], "timers": []}

        response = client.post("/", data={"query": "nonexistent", "limit": "10"})
        assert response.status_code == 200
        assert b"No Results Found" in response.data


def test_cancel_search_not_found(client, mocked_responses):
    """Test that cancelling a non-existent search returns 404."""
    mocked_responses.get(
        "https://api.real-debrid.com/rest/1.0/user",
        json={"id": 12345, "username": "testuser"},
        status=200
    )

    response = client.post("/cancel", json={"search_id": "nonexistent_id"})
    assert response.status_code == 404
    assert response.json["status"] == "not_found"


def test_cancel_search_active(client, mocked_responses):
    """Test that cancelling an active search sets the cancel event."""
    mocked_responses.get(
        "https://api.real-debrid.com/rest/1.0/user",
        json={"id": 12345, "username": "testuser"},
        status=200
    )

    # Manually inject a cancel event into _active_searches
    from app.routes.search import _active_searches
    cancel_event = threading.Event()
    _active_searches["test_search_123"] = cancel_event

    try:
        response = client.post("/cancel", json={"search_id": "test_search_123"})
        assert response.status_code == 200
        assert response.json["status"] == "cancelled"
        assert cancel_event.is_set()
    finally:
        _active_searches.pop("test_search_123", None)


def test_cancel_search_no_json(client, mocked_responses):
    """Test that cancel without JSON body returns 400."""
    mocked_responses.get(
        "https://api.real-debrid.com/rest/1.0/user",
        json={"id": 12345, "username": "testuser"},
        status=200
    )

    response = client.post("/cancel", data="not json")
    assert response.status_code == 400


# ── SSE Streaming Endpoint Tests ─────────────────────────────

def test_stream_search_no_json(client, mocked_responses):
    """Test that stream endpoint rejects non-JSON requests."""
    mocked_responses.get(
        "https://api.real-debrid.com/rest/1.0/user",
        json={"id": 12345, "username": "testuser"},
        status=200,
    )
    response = client.post("/stream", data="not json")
    assert response.status_code == 400
    assert response.json["status"] == "error"


def test_stream_search_empty_query(client, mocked_responses):
    """Test that stream endpoint rejects empty query."""
    mocked_responses.get(
        "https://api.real-debrid.com/rest/1.0/user",
        json={"id": 12345, "username": "testuser"},
        status=200,
    )
    response = client.post("/stream", json={"query": "", "limit": 10})
    assert response.status_code == 400
    assert "Query is required" in response.json["error"]


def test_stream_search_invalid_limit(client, mocked_responses):
    """Test that stream endpoint rejects invalid limit."""
    mocked_responses.get(
        "https://api.real-debrid.com/rest/1.0/user",
        json={"id": 12345, "username": "testuser"},
        status=200,
    )
    response = client.post("/stream", json={"query": "test", "limit": "abc"})
    assert response.status_code == 400
    assert "positive integer" in response.json["error"]


def test_stream_search_negative_limit(client, mocked_responses):
    """Test that stream endpoint rejects negative limit."""
    mocked_responses.get(
        "https://api.real-debrid.com/rest/1.0/user",
        json={"id": 12345, "username": "testuser"},
        status=200,
    )
    response = client.post("/stream", json={"query": "test", "limit": -5})
    assert response.status_code == 400


def test_stream_search_returns_event_stream(client, mocked_responses):
    """Test that valid stream request returns text/event-stream."""
    mocked_responses.get(
        "https://api.real-debrid.com/rest/1.0/user",
        json={"id": 12345, "username": "testuser"},
        status=200,
    )

    with patch('app.routes.search.RDDownloadLinkService') as MockService:
        # Simulate a generator that yields a done event
        def mock_stream(query, limit, cancel_event=None):
            yield {"type": "progress", "stage": "Searching...", "detail": "", "current": 0, "total": 0}
            yield {"type": "done", "total": 0, "elapsed": "0.50"}

        MockService.return_value.search_and_get_links_stream = mock_stream

        response = client.post("/stream", json={"query": "test movie", "limit": 10})
        assert response.status_code == 200
        assert response.content_type.startswith("text/event-stream")

        # Parse the SSE events from the response
        data = response.get_data(as_text=True)
        events = [line for line in data.split("\n") if line.startswith("data: ")]

        # Should have at least: search_id, progress, done
        assert len(events) >= 2

        # First event should be the search_id
        first = json.loads(events[0].replace("data: ", ""))
        assert first["type"] == "search_id"

        # Last event should be done
        last = json.loads(events[-1].replace("data: ", ""))
        assert last["type"] == "done"
        assert last["total"] == 0
