# tests/test_main.py
import os
import sys
import pytest
import platform
from unittest.mock import patch, MagicMock

# Add project root directory to Python path to locate app/main.py
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from app.main import app  # Import the Flask app from app/main.py

# Fixture to create a test client for the Flask app
@pytest.fixture
def client():
    with app.test_client() as client:
        yield client

# Test the index route
def test_index_route(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Welcome" in response.data or b"Real-Debrid" in response.data  # Check for expected content

# Test the RD Manager route
def test_rd_manager_route(client):
    response = client.get("/torrent/rd_manager")
    assert response.status_code == 200
    assert b"Torrents" in response.data or b"Account Information" in response.data

# Test the About route
def test_about_route(client):
    response = client.get("/about")
    assert response.status_code == 200
    assert b"About" in response.data

# Test the Contact route
def test_contact_route(client):
    response = client.get("/contact")
    assert response.status_code == 200
    assert b"Contact" in response.data

# Test the search POST request route
def test_search_post_route(client):
    response = client.post("/", data={"query": "alien romulus 2160p", "limit": "10"})
    assert response.status_code == 200
    assert b"No Results Found" in response.data or b"Total Torrents Found" in response.data

# Test the delete torrent route with actual mock response
def test_delete_torrent_route(client):
    with patch('requests.delete') as mock_delete:
        mock_delete.return_value.status_code = 200
        mock_delete.return_value.json.return_value = {'status': 'success', 'message': 'Torrent deleted successfully'}

        response = client.delete("/torrent/delete_torrent/sample_torrent_id")
        assert response.status_code == 200
        assert response.json['status'] == 'success'

# Test the stream VLC route with actual unrestricted link without launching VLC
def test_stream_vlc_route(client):
    test_link = "https://mia1-4.download.real-debrid.com/d/XZI7EGZURKBNC84/Alien.Romulus.2024.2160p.WEB-DL.DDP5.1.Atmos.DV.HDR.H.265-FLUX.mkv"

    # Determine VLC path based on the operating system
    if platform.system() == 'Darwin':
        vlc_path = "/Applications/VLC.app/Contents/MacOS/VLC"
    elif platform.system() == 'Windows':
        vlc_path = "C:\\Program Files\\VideoLAN\\VLC\\vlc.exe"
    else:
        vlc_path = "/usr/bin/vlc"

    # Patch subprocess.Popen to prevent VLC from launching
    with patch('subprocess.Popen') as mock_popen:
        mock_popen.return_value = MagicMock()  # Mock the Popen object

        # Perform the request to the stream_vlc endpoint
        response = client.post("/torrent/stream_vlc", json={"link": test_link})

        # Assert the response status and that subprocess.Popen was called correctly
        assert response.status_code == 200
        assert response.json['status'] == 'success'
        mock_popen.assert_called_once_with([vlc_path, test_link])

# Test the unrestrict link route with an actual mock response
def test_unrestrict_link_route(client):
    with patch('requests.post') as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            'download': 'https://mia4-4.download.real-debrid.com/d/DC3FQQOWJU2G623/Alien.Romulus.2024.2160p.4K.WEB.x265.10bit.AAC5.1-%5BYTS.MX%5D.mkv'
        }

        response = client.post("/torrent/unrestrict_link", json={"link": "http://example.com/restricted_link"})
        assert response.status_code == 200
        assert response.json['unrestricted_link'] == 'https://mia4-4.download.real-debrid.com/d/DC3FQQOWJU2G623/Alien.Romulus.2024.2160p.4K.WEB.x265.10bit.AAC5.1-%5BYTS.MX%5D.mkv'

# Test torrent details route with actual data structure
def test_get_torrent_details_route(client):
    torrent_id = "sample_torrent_id"
    with patch('requests.get') as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "filename": "Alien.Romulus.2024.2160p.WEB-DL.DDP5.1.Atmos.DV.HDR.H.265-FLUX.mkv",
            "files": [
                {
                    "id": 1,
                    "path": "/Alien.Romulus.2024.2160p.WEB-DL.DDP5.1.Atmos.DV.HDR.H.265-FLUX.mkv",
                    "bytes": 22523456789,
                    "selected": 1
                }
            ],
            "links": [
                "https://mia1-4.download.real-debrid.com/d/XZI7EGZURKBNC84/Alien.Romulus.2024.2160p.WEB-DL.DDP5.1.Atmos.DV.HDR.H.265-FLUX.mkv"
            ]
        }

        response = client.get(f"/torrent/torrents/{torrent_id}")
        assert response.status_code == 200
        assert response.json['filename'] == "Alien.Romulus.2024.2160p.WEB-DL.DDP5.1.Atmos.DV.HDR.H.265-FLUX.mkv"
        assert response.json['files'][0]['link'] == "https://mia1-4.download.real-debrid.com/d/XZI7EGZURKBNC84/Alien.Romulus.2024.2160p.WEB-DL.DDP5.1.Atmos.DV.HDR.H.265-FLUX.mkv"