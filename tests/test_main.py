# tests/test_main.py
import pytest
import platform
from unittest.mock import patch, MagicMock


# Test the index route
def test_index_route(client, mocked_responses):
    mocked_responses.get(
        "https://api.real-debrid.com/rest/1.0/user",
        json={"id": 12345, "username": "testuser"},
        status=200
    )
    response = client.get("/")
    assert response.status_code == 200
    assert b"Search" in response.data or b"Debrid Scout" in response.data


# Test the RD Manager route
def test_rd_manager_route(client, mocked_responses):
    mocked_responses.get(
        "https://api.real-debrid.com/rest/1.0/user",
        json={"id": 12345, "username": "testuser"},
        status=200
    )

    with patch('app.services.real_debrid.RealDebridService.get_all_torrents') as mock_torrents:
        mock_torrents.return_value = [
            {"id": "abc123", "filename": "Test.Movie.mkv", "status": "downloaded", "progress": 100}
        ]

        response = client.get("/torrent/rd_manager")
        assert response.status_code == 200
        assert b"RD Manager" in response.data


# Test the About route
def test_about_route(client, mocked_responses):
    mocked_responses.get(
        "https://api.real-debrid.com/rest/1.0/user",
        json={"id": 12345, "username": "testuser"},
        status=200
    )
    response = client.get("/about")
    assert response.status_code == 200
    assert b"About" in response.data


# Test the Contact route
def test_contact_route(client, mocked_responses):
    mocked_responses.get(
        "https://api.real-debrid.com/rest/1.0/user",
        json={"id": 12345, "username": "testuser"},
        status=200
    )
    response = client.get("/contact")
    assert response.status_code == 200
    assert b"Contact" in response.data


# Test the search POST request route
def test_search_post_route(client, mocked_responses):
    mocked_responses.get(
        "https://api.real-debrid.com/rest/1.0/user",
        json={"id": 12345, "username": "testuser"},
        status=200
    )
    response = client.post("/", data={"query": "alien romulus 2160p", "limit": "10"})
    assert response.status_code == 200
    assert b"No Results Found" in response.data or b"Total Torrents Found" in response.data


# Test the delete torrent route with actual mock response
def test_delete_torrent_route(client, mocked_responses):
    mocked_responses.get(
        "https://api.real-debrid.com/rest/1.0/user",
        json={"id": 12345, "username": "testuser"},
        status=200
    )
    mocked_responses.delete(
        "https://api.real-debrid.com/rest/1.0/torrents/delete/sample_torrent_id",
        status=204,
    )

    response = client.delete("/torrent/delete_torrent/sample_torrent_id")
    assert response.status_code == 200
    assert response.json['status'] == 'success'


# Test the launch VLC route (corrected from /stream_vlc to /launch_vlc)
def test_launch_vlc_route(client, mocked_responses):
    test_url = "https://example.com/video.mkv"

    mocked_responses.get(
        "https://api.real-debrid.com/rest/1.0/user",
        json={"id": 12345, "username": "testuser"},
        status=200
    )

    with patch('subprocess.Popen') as mock_popen, \
         patch('shutil.which', return_value="/usr/bin/vlc"):
        mock_popen.return_value = MagicMock()

        response = client.post("/torrent/launch_vlc", json={"video_url": test_url})

        assert response.status_code == 200
        assert response.json['status'] == 'success'
        mock_popen.assert_called_once_with(["/usr/bin/vlc", test_url])


# Test the unrestrict link route with an actual mock response
def test_unrestrict_link_route(client, mocked_responses):
    mocked_responses.get(
        "https://api.real-debrid.com/rest/1.0/user",
        json={"id": 12345, "username": "testuser"},
        status=200
    )
    mocked_responses.post(
        "https://api.real-debrid.com/rest/1.0/unrestrict/link",
        json={'download': 'https://download.real-debrid.com/d/abc123/movie.mkv'},
        status=200,
    )

    response = client.post("/torrent/unrestrict_link", json={"link": "http://example.com/restricted"})
    assert response.status_code == 200
    assert response.json['unrestricted_link'] == 'https://download.real-debrid.com/d/abc123/movie.mkv'


# Test torrent details route with actual data structure
def test_get_torrent_details_route(client, mocked_responses):
    mocked_responses.get(
        "https://api.real-debrid.com/rest/1.0/user",
        json={"id": 12345, "username": "testuser"},
        status=200
    )
    mocked_responses.get(
        "https://api.real-debrid.com/rest/1.0/torrents/info/sample_torrent_id",
        json={
            "filename": "Test.Movie.2024.mkv",
            "status": "downloaded",
            "progress": 100,
            "files": [
                {
                    "id": 1,
                    "path": "/Test.Movie.2024.mkv",
                    "bytes": 22523456789,
                    "selected": 1
                }
            ],
            "links": [
                "https://download.real-debrid.com/d/abc123/Test.Movie.2024.mkv"
            ]
        },
        status=200,
    )

    response = client.get("/torrent/torrents/sample_torrent_id")
    assert response.status_code == 200
    assert response.json['filename'] == "Test.Movie.2024.mkv"
    assert response.json['files'][0]['link'] == "https://download.real-debrid.com/d/abc123/Test.Movie.2024.mkv"


# ── HereSphere scan endpoint tests ───────────────────────────

def test_heresphere_library_includes_scan_url(client, mocked_responses):
    """The library index JSON should include a 'scan' URL."""
    mocked_responses.get(
        "https://api.real-debrid.com/rest/1.0/user",
        json={"id": 12345, "username": "testuser"},
        status=200,
    )
    with patch('app.services.real_debrid.RealDebridService.get_all_torrents') as mock_torrents:
        mock_torrents.return_value = []
        response = client.post("/heresphere/")
        assert response.status_code == 200
        data = response.get_json()
        assert "scan" in data
        assert "/heresphere/scan" in data["scan"]


def test_heresphere_scan_returns_bulk_metadata(client, mocked_responses):
    """POST /heresphere/scan returns metadata for all downloaded torrents."""
    mocked_responses.get(
        "https://api.real-debrid.com/rest/1.0/user",
        json={"id": 12345, "username": "testuser"},
        status=200,
    )
    torrents = [
        {
            "id": "abc123",
            "filename": "Great.VR.Video_180_SBS.mp4",
            "status": "downloaded",
            "bytes": 5000000000,
            "added": "2025-12-01T10:00:00.000Z",
            "links": ["https://rd.link/1"],
        },
        {
            "id": "def456",
            "filename": "Another.Movie.mkv",
            "status": "downloaded",
            "bytes": 2000000000,
            "added": "2025-11-15T08:00:00.000Z",
            "links": ["https://rd.link/2", "https://rd.link/3"],
        },
        {
            "id": "ghi789",
            "filename": "Still.Downloading.mkv",
            "status": "downloading",
            "bytes": 1000000000,
            "added": "2025-12-20T12:00:00.000Z",
            "links": [],
        },
    ]
    with patch('app.services.real_debrid.RealDebridService.get_all_torrents') as mock_torrents:
        mock_torrents.return_value = torrents
        response = client.post("/heresphere/scan")
        assert response.status_code == 200
        body = response.get_json()
        assert "scanData" in body
        data = body["scanData"]
        # Only 2 downloaded torrents should be in the response
        assert len(data) == 2
        # Each entry has required HereSphere scan fields
        for entry in data:
            assert "link" in entry
            assert "title" in entry
            assert "tags" in entry
            assert "dateAdded" in entry
            assert "duration" in entry
            assert "isFavorite" in entry
        # Check specific entries
        assert data[0]["title"] == "Great VR Video_180_SBS.mp4"
        assert "/heresphere/abc123" in data[0]["link"]
        # Tags should include VR projection info
        tag_names = [t["name"] for t in data[0]["tags"]]
        assert any("180" in name for name in tag_names)


def test_heresphere_scan_empty_library(client, mocked_responses):
    """POST /heresphere/scan returns empty array when no torrents exist."""
    mocked_responses.get(
        "https://api.real-debrid.com/rest/1.0/user",
        json={"id": 12345, "username": "testuser"},
        status=200,
    )
    with patch('app.services.real_debrid.RealDebridService.get_all_torrents') as mock_torrents:
        mock_torrents.return_value = []
        response = client.post("/heresphere/scan")
        assert response.status_code == 200
        body = response.get_json()
        assert body == {"scanData": []}


def test_heresphere_scan_has_correct_header(client, mocked_responses):
    """POST /heresphere/scan response includes HereSphere-JSON-Version header."""
    mocked_responses.get(
        "https://api.real-debrid.com/rest/1.0/user",
        json={"id": 12345, "username": "testuser"},
        status=200,
    )
    with patch('app.services.real_debrid.RealDebridService.get_all_torrents') as mock_torrents:
        mock_torrents.return_value = []
        response = client.post("/heresphere/scan")
        assert response.headers.get('HereSphere-JSON-Version') == '1'
