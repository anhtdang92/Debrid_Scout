import pytest
import json
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
