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
    with patch('requests.delete') as mock_delete:
        mock_delete.return_value.status_code = 200
        mock_delete.return_value.json.return_value = {'status': 'success', 'message': 'Torrent deleted successfully'}
        mock_delete.return_value.raise_for_status = MagicMock()

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
    with patch('requests.post') as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            'download': 'https://download.real-debrid.com/d/abc123/movie.mkv'
        }
        mock_post.return_value.raise_for_status = MagicMock()

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
    with patch('requests.get') as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.raise_for_status = MagicMock()
        mock_get.return_value.json.return_value = {
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
        }

        response = client.get("/torrent/torrents/sample_torrent_id")
        assert response.status_code == 200
        assert response.json['filename'] == "Test.Movie.2024.mkv"
        assert response.json['files'][0]['link'] == "https://download.real-debrid.com/d/abc123/Test.Movie.2024.mkv"
