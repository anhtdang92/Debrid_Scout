import pytest
import json

def test_index_page_loads(client, mocked_responses):
    """Test that the index page loads successfully on GET."""
    # Mock the Before-Request Real-Debrid /user account API call 
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

def test_jackett_search_pipeline(client, mocked_responses):
    """Test the full torznab XML search pipeline."""
    # Mock RD User
    mocked_responses.get("https://api.real-debrid.com/rest/1.0/user", json={}, status=200)

    # Mock Jackett Search Result
    jackett_xml = b'''<?xml version="1.0" encoding="UTF-8"?>
    <rss version="1.0" xmlns:torznab="http://torznab.com/schemas/2015/feed">
    <channel>
        <item>
            <title>Test Movie 1080p</title>
            <link>magnet:?xt=urn:btih:1234567890abcdef1234567890abcdef12345678</link>
            <size>1048576000</size>
            <torznab:attr name="seeders" value="100" />
            <torznab:attr name="peers" value="20" />
        </item>
    </channel>
    </rss>
    '''
    mocked_responses.get(
        "http://localhost:9117/api/v2.0/indexers/all/results/torznab/api",
        body=jackett_xml,
        status=200,
        content_type="application/xml"
    )

    # Mock RD Instant Availability hash check
    mocked_responses.get(
        "https://api.real-debrid.com/rest/1.0/torrents/instantAvailability/1234567890abcdef1234567890abcdef12345678",
        json={"1234567890abcdef1234567890abcdef12345678": {"rd": [{"1": {"filename": "Test Movie 1080p.mkv", "filesize": 1048576000}}]}},
        status=200
    )

    response = client.post("/", data={"query": "Test Movie", "limit": "10"})
    assert response.status_code == 200
    assert b"Test Movie 1080p" in response.data
    # Ensure it's marked as cached (since availability returned success)
    assert b"Cached" in response.data
