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
        "https://api.real-debrid.com/rest/1.0/torrents/delete/sampleTorrentId",
        status=204,
    )

    response = client.delete("/torrent/delete_torrent/sampleTorrentId")
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
        "https://api.real-debrid.com/rest/1.0/torrents/info/sampleTorrentId",
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

    response = client.get("/torrent/torrents/sampleTorrentId")
    assert response.status_code == 200
    assert response.json['filename'] == "Test.Movie.2024.mkv"
    assert response.json['files'][0]['link'] == "https://download.real-debrid.com/d/abc123/Test.Movie.2024.mkv"


# ── Account route smoke test ──────────────────────────────────

def test_account_route(client, mocked_responses):
    """Test that /account/account renders without error."""
    mocked_responses.get(
        "https://api.real-debrid.com/rest/1.0/user",
        json={"id": 12345, "username": "testuser", "expiration": "2030-01-01T00:00:00.000Z", "premium": 100},
        status=200,
    )
    response = client.get("/account/account")
    assert response.status_code == 200
    assert b"testuser" in response.data


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


# ── /health endpoint tests ─────────────────────────────────────
def test_health_endpoint_returns_healthy(client, mocked_responses):
    """GET /health returns 200 with healthy status when keys are set."""
    mocked_responses.get(
        "https://api.real-debrid.com/rest/1.0/user",
        json={"id": 12345, "username": "testuser"},
        status=200,
    )
    response = client.get("/health")
    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "healthy"
    assert body["checks"]["api_key_set"] is True
    assert body["checks"]["jackett_key_set"] is True


def test_health_endpoint_degraded_without_jackett(client, mocked_responses):
    """GET /health returns degraded when JACKETT_API_KEY is missing."""
    mocked_responses.get(
        "https://api.real-debrid.com/rest/1.0/user",
        json={"id": 12345, "username": "testuser"},
        status=200,
    )
    client.application.config['JACKETT_API_KEY'] = ''
    response = client.get("/health")
    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "degraded"
    assert body["checks"]["jackett_key_set"] is False


# ── Bulk delete validation tests ────────────────────────────────
def test_bulk_delete_rejects_non_list(client, mocked_responses):
    """POST /torrent/delete_torrents rejects non-list torrentIds."""
    mocked_responses.get(
        "https://api.real-debrid.com/rest/1.0/user",
        json={"id": 12345, "username": "testuser"},
        status=200,
    )
    response = client.post(
        "/torrent/delete_torrents",
        json={"torrentIds": "not-a-list"},
        content_type="application/json",
    )
    assert response.status_code == 400


def test_bulk_delete_rejects_invalid_ids(client, mocked_responses):
    """POST /torrent/delete_torrents rejects IDs with special characters."""
    mocked_responses.get(
        "https://api.real-debrid.com/rest/1.0/user",
        json={"id": 12345, "username": "testuser"},
        status=200,
    )
    response = client.post(
        "/torrent/delete_torrents",
        json={"torrentIds": ["valid123", "../etc/passwd"]},
        content_type="application/json",
    )
    assert response.status_code == 400
    body = response.get_json()
    assert "Invalid torrent ID" in body["error"]


def test_bulk_delete_rejects_oversized_array(client, mocked_responses):
    """POST /torrent/delete_torrents rejects arrays larger than 500."""
    mocked_responses.get(
        "https://api.real-debrid.com/rest/1.0/user",
        json={"id": 12345, "username": "testuser"},
        status=200,
    )
    response = client.post(
        "/torrent/delete_torrents",
        json={"torrentIds": ["id" + str(i) for i in range(501)]},
        content_type="application/json",
    )
    assert response.status_code == 400


# ── VR auth token tests ────────────────────────────────────────
def test_heresphere_auth_rejects_bad_token(client, mocked_responses):
    """HereSphere API rejects requests with wrong auth token."""
    mocked_responses.get(
        "https://api.real-debrid.com/rest/1.0/user",
        json={"id": 12345, "username": "testuser"},
        status=200,
    )
    client.application.config['HERESPHERE_AUTH_TOKEN'] = 'secret-token'
    response = client.post(
        "/heresphere",
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert response.status_code == 401


def test_heresphere_auth_allows_correct_token(client, mocked_responses):
    """HereSphere API allows requests with correct auth token."""
    mocked_responses.get(
        "https://api.real-debrid.com/rest/1.0/user",
        json={"id": 12345, "username": "testuser"},
        status=200,
    )
    client.application.config['HERESPHERE_AUTH_TOKEN'] = 'secret-token'
    with patch('app.services.real_debrid.RealDebridService.get_all_torrents') as mock_torrents:
        mock_torrents.return_value = []
        response = client.post(
            "/heresphere",
            headers={"Authorization": "Bearer secret-token"},
        )
        assert response.status_code == 200


def test_deovr_auth_rejects_bad_token(client, mocked_responses):
    """DeoVR API rejects requests with wrong auth token."""
    mocked_responses.get(
        "https://api.real-debrid.com/rest/1.0/user",
        json={"id": 12345, "username": "testuser"},
        status=200,
    )
    client.application.config['HERESPHERE_AUTH_TOKEN'] = 'secret-token'
    response = client.post(
        "/deovr",
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert response.status_code == 401


# ── Security headers test ──────────────────────────────────────
def test_responses_include_security_headers(client, mocked_responses):
    """All responses include CSP and X-Content-Type-Options headers."""
    mocked_responses.get(
        "https://api.real-debrid.com/rest/1.0/user",
        json={"id": 12345, "username": "testuser"},
        status=200,
    )
    response = client.get("/health")
    assert response.headers.get('X-Content-Type-Options') == 'nosniff'
    assert response.headers.get('X-Frame-Options') == 'SAMEORIGIN'
    assert 'Content-Security-Policy' in response.headers


# ── Error path tests ───────────────────────────────────────────
def test_unrestrict_link_rejects_missing_link(client, mocked_responses):
    """POST /torrent/unrestrict_link returns 400 when link is missing."""
    mocked_responses.get(
        "https://api.real-debrid.com/rest/1.0/user",
        json={"id": 12345, "username": "testuser"},
        status=200,
    )
    response = client.post(
        "/torrent/unrestrict_link",
        json={"not_link": "value"},
        content_type="application/json",
    )
    assert response.status_code == 400


def test_delete_torrent_handles_api_error(client, mocked_responses):
    """DELETE /torrent/delete_torrent returns 500 on RD API error."""
    mocked_responses.get(
        "https://api.real-debrid.com/rest/1.0/user",
        json={"id": 12345, "username": "testuser"},
        status=200,
    )
    with patch('app.services.real_debrid.RealDebridService.delete_torrent') as mock_del:
        from app.services.real_debrid import RealDebridError
        mock_del.side_effect = RealDebridError("API error")
        response = client.delete("/torrent/delete_torrent/abc123")
        assert response.status_code == 500


# ── Torrent ID validation tests ──────────────────────────────

def test_delete_torrent_rejects_invalid_id(client, mocked_responses):
    """DELETE /torrent/delete_torrent/<id> rejects IDs with special chars."""
    mocked_responses.get(
        "https://api.real-debrid.com/rest/1.0/user",
        json={"id": 12345, "username": "testuser"},
        status=200,
    )
    response = client.delete("/torrent/delete_torrent/bad_id_here")
    assert response.status_code == 400
    assert "Invalid torrent ID" in response.get_json()["error"]


def test_get_torrent_details_rejects_invalid_id(client, mocked_responses):
    """GET /torrent/torrents/<id> rejects IDs with special chars."""
    mocked_responses.get(
        "https://api.real-debrid.com/rest/1.0/user",
        json={"id": 12345, "username": "testuser"},
        status=200,
    )
    response = client.get("/torrent/torrents/bad_id_here")
    assert response.status_code == 400


# ── Partial bulk delete (207) test ────────────────────────────

def test_bulk_delete_partial_success(client, mocked_responses):
    """POST /torrent/delete_torrents returns 207 on partial failure."""
    mocked_responses.get(
        "https://api.real-debrid.com/rest/1.0/user",
        json={"id": 12345, "username": "testuser"},
        status=200,
    )
    from app.services.real_debrid import RealDebridError

    call_count = {"n": 0}

    def side_effect(tid):
        call_count["n"] += 1
        if call_count["n"] == 2:
            raise RealDebridError("API error")
        return True

    with patch('app.services.real_debrid.RealDebridService.delete_torrent') as mock_del:
        mock_del.side_effect = side_effect
        response = client.post(
            "/torrent/delete_torrents",
            json={"torrentIds": ["abc123", "def456"]},
            content_type="application/json",
        )
        assert response.status_code == 207
        body = response.get_json()
        assert body["status"] == "partial_success"
        assert len(body["results"]["deleted"]) == 1
        assert len(body["results"]["failed"]) == 1


# ── Pagination edge case tests ────────────────────────────────

def test_rd_manager_clamps_high_page(client, mocked_responses):
    """GET /torrent/rd_manager?page=999 clamps to last page."""
    mocked_responses.get(
        "https://api.real-debrid.com/rest/1.0/user",
        json={"id": 12345, "username": "testuser"},
        status=200,
    )
    with patch('app.services.real_debrid.RealDebridService.get_all_torrents') as mock_torrents:
        mock_torrents.return_value = [
            {"id": f"t{i}", "filename": f"file{i}.mkv", "status": "downloaded", "progress": 100}
            for i in range(3)
        ]
        response = client.get("/torrent/rd_manager?page=999")
        assert response.status_code == 200


def test_rd_manager_negative_page_defaults_to_one(client, mocked_responses):
    """GET /torrent/rd_manager?page=-5 defaults to page 1."""
    mocked_responses.get(
        "https://api.real-debrid.com/rest/1.0/user",
        json={"id": 12345, "username": "testuser"},
        status=200,
    )
    with patch('app.services.real_debrid.RealDebridService.get_all_torrents') as mock_torrents:
        mock_torrents.return_value = []
        response = client.get("/torrent/rd_manager?page=-5")
        assert response.status_code == 200


# ── Network failure / timeout tests ──────────────────────────

def test_real_debrid_connection_error(app, mocked_responses):
    """RealDebridService raises RealDebridError on connection failure."""
    import requests as req
    with app.app_context():
        from app.services.real_debrid import RealDebridService, RealDebridError
        service = RealDebridService(api_key="test_rd_key")
        mocked_responses.get(
            "https://api.real-debrid.com/rest/1.0/user",
            body=req.ConnectionError("Connection refused"),
        )
        with pytest.raises(RealDebridError):
            service.get_account_info()


def test_real_debrid_timeout_error(app, mocked_responses):
    """RealDebridService raises RealDebridError on timeout."""
    import requests as req
    with app.app_context():
        from app.services.real_debrid import RealDebridService, RealDebridError
        service = RealDebridService(api_key="test_rd_key")
        mocked_responses.get(
            "https://api.real-debrid.com/rest/1.0/user",
            body=req.Timeout("Timed out"),
        )
        with pytest.raises(RealDebridError):
            service.get_account_info()
