# tests/test_vr_routes.py

"""Tests for HereSphere and DeoVR VR route endpoints."""

import os
import pytest
import tempfile
from unittest.mock import patch, MagicMock


# ── Shared mock data ─────────────────────────────────────────

MOCK_USER = {"id": 12345, "username": "testuser"}

MOCK_TORRENTS = [
    {
        "id": "torrent1",
        "filename": "Great.VR.Video_180_SBS.mp4",
        "status": "downloaded",
        "hash": "abc123",
        "bytes": 5368709120,
        "added": "2026-02-20T10:00:00.000Z",
        "links": ["https://real-debrid.com/d/link1"],
    },
    {
        "id": "torrent2",
        "filename": "Flat.Movie.2024.mkv",
        "status": "downloading",  # should be excluded
        "hash": "def456",
        "bytes": 1073741824,
        "added": "2026-01-01T10:00:00.000Z",
        "links": [],
    },
]

MOCK_TORRENT_INFO = {
    "id": "torrent1",
    "filename": "Great.VR.Video_180_SBS.mp4",
    "status": "downloaded",
    "added": "2026-02-20",
    "files": [
        {"id": 1, "path": "/Great.VR.Video_180_SBS.mp4", "bytes": 5368709120, "selected": 1},
        {"id": 2, "path": "/sample.txt", "bytes": 1024, "selected": 0},
    ],
    "links": ["https://real-debrid.com/d/link1"],
}


# ── HereSphere tests ─────────────────────────────────────────

def test_heresphere_library_json(client, mocked_responses):
    """POST /heresphere returns JSON library for API clients."""
    mocked_responses.get(
        "https://api.real-debrid.com/rest/1.0/user",
        json=MOCK_USER, status=200,
    )
    with patch('app.services.real_debrid.RealDebridService.get_all_torrents') as mock:
        mock.return_value = MOCK_TORRENTS
        response = client.post("/heresphere")

    assert response.status_code == 200
    data = response.json
    assert data["access"] == 1
    assert "library" in data
    # Only 'downloaded' torrents should appear
    total_urls = sum(len(section["list"]) for section in data["library"])
    assert total_urls == 1


def test_heresphere_library_html(client, mocked_responses):
    """GET /heresphere with Accept: text/html returns the browser view."""
    mocked_responses.get(
        "https://api.real-debrid.com/rest/1.0/user",
        json=MOCK_USER, status=200,
    )
    with patch('app.services.real_debrid.RealDebridService.get_all_torrents') as mock:
        mock.return_value = MOCK_TORRENTS
        response = client.get("/heresphere", headers={"Accept": "text/html"})

    assert response.status_code == 200
    assert b"HereSphere" in response.data or b"heresphere" in response.data.lower()


def test_heresphere_video_detail_metadata(client, mocked_responses):
    """POST /heresphere/<id> with needsMediaSource=false returns full metadata."""
    mocked_responses.get(
        "https://api.real-debrid.com/rest/1.0/user",
        json=MOCK_USER, status=200,
    )
    mocked_responses.get(
        "https://api.real-debrid.com/rest/1.0/torrents/info/torrent1",
        json=MOCK_TORRENT_INFO, status=200,
    )
    response = client.post(
        "/heresphere/torrent1",
        json={"needsMediaSource": False},
    )
    assert response.status_code == 200
    data = response.json
    assert data["access"] == 1
    assert "title" in data
    assert data["media"] == []
    assert data["projection"] == "equirectangular"
    assert data["stereo"] == "sbs"

    # ── New enriched fields ──────────────────────────────
    assert "thumbnailImage" in data
    assert "/heresphere/thumb/torrent1" in data["thumbnailImage"]
    assert data["isFavorite"] is False
    assert data["rating"] == 0
    assert data["writeFavorite"] is False
    assert data["writeRating"] is False
    assert data["writeTags"] is False
    assert data["writeHSP"] is False
    assert data["subtitles"] == []
    assert data["scripts"] == []
    assert "thumbnailVideo" in data


def test_heresphere_video_detail_with_media(client, mocked_responses):
    """POST /heresphere/<id> with needsMediaSource=true returns playable sources."""
    mocked_responses.get(
        "https://api.real-debrid.com/rest/1.0/user",
        json=MOCK_USER, status=200,
    )
    mocked_responses.get(
        "https://api.real-debrid.com/rest/1.0/torrents/info/torrent1",
        json=MOCK_TORRENT_INFO, status=200,
    )
    with patch('app.services.real_debrid.RealDebridService.unrestrict_link') as mock_unrestrict:
        mock_unrestrict.return_value = "https://unrestricted.real-debrid.com/video.mp4"
        response = client.post(
            "/heresphere/torrent1",
            json={"needsMediaSource": True},
        )

    assert response.status_code == 200
    data = response.json
    assert len(data["media"]) == 1
    assert "url" in data["media"][0]["sources"][0]
    # Enriched fields should still be present on full response
    assert "thumbnailImage" in data
    assert "isFavorite" in data


def test_heresphere_launch(client, mocked_responses):
    """POST /heresphere/launch_heresphere launches the executable."""
    mocked_responses.get(
        "https://api.real-debrid.com/rest/1.0/user",
        json=MOCK_USER, status=200,
    )
    with patch('app.services.vr_helper.find_heresphere_exe', return_value="/usr/bin/heresphere"), \
         patch('subprocess.Popen') as mock_popen:
        mock_popen.return_value = MagicMock()
        response = client.post(
            "/heresphere/launch_heresphere",
            json={"video_url": "https://example.com/video.mp4"},
        )

    assert response.status_code == 200
    assert response.json["status"] == "success"


def test_heresphere_launch_no_url(client, mocked_responses):
    """POST /heresphere/launch_heresphere without URL returns 400."""
    mocked_responses.get(
        "https://api.real-debrid.com/rest/1.0/user",
        json=MOCK_USER, status=200,
    )
    response = client.post(
        "/heresphere/launch_heresphere",
        json={},
    )
    assert response.status_code == 400


# ── Thumbnail endpoint tests ─────────────────────────────────

def test_heresphere_thumb_cached(client, mocked_responses):
    """GET /heresphere/thumb/<id> serves a cached thumbnail."""
    mocked_responses.get(
        "https://api.real-debrid.com/rest/1.0/user",
        json=MOCK_USER, status=200,
    )
    # Create a fake cached thumbnail
    with patch('app.routes.heresphere._get_thumb_service') as mock_svc:
        svc = MagicMock()
        mock_svc.return_value = svc

        # Simulate a cached JPEG file
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            f.write(b'\xff\xd8\xff\xe0' + b'\x00' * 100)  # Fake JPEG header
            tmp_path = f.name

        try:
            svc.get_cached_path.return_value = tmp_path
            response = client.get("/heresphere/thumb/torrent1")
            assert response.status_code == 200
            assert response.content_type == 'image/jpeg'
        finally:
            os.unlink(tmp_path)


def test_heresphere_thumb_no_ffmpeg(client, mocked_responses):
    """GET /heresphere/thumb/<id> returns 404 when ffmpeg is unavailable."""
    mocked_responses.get(
        "https://api.real-debrid.com/rest/1.0/user",
        json=MOCK_USER, status=200,
    )
    with patch('app.routes.heresphere._get_thumb_service') as mock_svc:
        svc = MagicMock()
        mock_svc.return_value = svc
        svc.get_cached_path.return_value = None
        svc.available = False

        response = client.get("/heresphere/thumb/torrent1")
        assert response.status_code == 404


# ── DeoVR tests ───────────────────────────────────────────────

def test_deovr_library(client, mocked_responses):
    """GET /deovr returns DeoVR JSON library with thumbnail URLs."""
    mocked_responses.get(
        "https://api.real-debrid.com/rest/1.0/user",
        json=MOCK_USER, status=200,
    )
    with patch('app.services.real_debrid.RealDebridService.get_all_torrents') as mock:
        mock.return_value = MOCK_TORRENTS
        response = client.get("/deovr")

    assert response.status_code == 200
    data = response.json
    assert data["authorized"] == "1"
    assert len(data["scenes"]) == 1
    # Only 'downloaded' torrents should appear
    assert len(data["scenes"][0]["list"]) == 1
    # Thumbnail URL should be present
    video = data["scenes"][0]["list"][0]
    assert "thumbnailUrl" in video
    assert "/heresphere/thumb/torrent1" in video["thumbnailUrl"]


def test_deovr_video_detail_metadata(client, mocked_responses):
    """POST /deovr/<id> with needsMediaSource=false returns metadata with thumbnail."""
    mocked_responses.get(
        "https://api.real-debrid.com/rest/1.0/user",
        json=MOCK_USER, status=200,
    )
    mocked_responses.get(
        "https://api.real-debrid.com/rest/1.0/torrents/info/torrent1",
        json=MOCK_TORRENT_INFO, status=200,
    )
    response = client.post(
        "/deovr/torrent1",
        json={"needsMediaSource": False},
    )
    assert response.status_code == 200
    data = response.json
    assert "screenType" in data
    assert "stereoMode" in data
    assert data["screenType"] == "dome"
    assert data["stereoMode"] == "sbs"
    # Thumbnail URL should be present
    assert "thumbnailUrl" in data
    assert "/heresphere/thumb/torrent1" in data["thumbnailUrl"]


def test_deovr_video_detail_with_media(client, mocked_responses):
    """POST /deovr/<id> with needsMediaSource=true returns playable sources."""
    mocked_responses.get(
        "https://api.real-debrid.com/rest/1.0/user",
        json=MOCK_USER, status=200,
    )
    mocked_responses.get(
        "https://api.real-debrid.com/rest/1.0/torrents/info/torrent1",
        json=MOCK_TORRENT_INFO, status=200,
    )
    with patch('app.services.real_debrid.RealDebridService.unrestrict_link') as mock_unrestrict:
        mock_unrestrict.return_value = "https://unrestricted.real-debrid.com/video.mp4"
        response = client.post(
            "/deovr/torrent1",
            json={"needsMediaSource": True},
        )

    assert response.status_code == 200
    data = response.json
    assert "encodings" in data
    assert len(data["encodings"][0]["videoSources"]) == 1


def test_deovr_launch(client, mocked_responses):
    """POST /deovr/launch_heresphere launches the executable."""
    mocked_responses.get(
        "https://api.real-debrid.com/rest/1.0/user",
        json=MOCK_USER, status=200,
    )
    with patch('app.services.vr_helper.find_heresphere_exe', return_value="/usr/bin/heresphere"), \
         patch('subprocess.Popen') as mock_popen:
        mock_popen.return_value = MagicMock()
        response = client.post(
            "/deovr/launch_heresphere",
            json={"video_url": "https://example.com/video.mp4"},
        )

    assert response.status_code == 200
    assert response.json["status"] == "success"


# ── Projection guessing tests ────────────────────────────────

def test_guess_projection_sbs():
    """Default 180 SBS projection."""
    from app.services.vr_helper import guess_projection
    proj, stereo, fov, lens = guess_projection("Video_180_SBS.mp4")
    assert proj == "equirectangular"
    assert stereo == "sbs"
    assert fov == 180.0


def test_guess_projection_fisheye():
    """Fisheye 190 detection."""
    from app.services.vr_helper import guess_projection
    proj, stereo, fov, lens = guess_projection("Video_FISHEYE190_SBS.mp4")
    assert proj == "fisheye"
    assert fov == 190.0


def test_guess_projection_mkx200():
    """MKX200 lens detection."""
    from app.services.vr_helper import guess_projection
    proj, stereo, fov, lens = guess_projection("Video_MKX200_SBS.mp4")
    assert proj == "fisheye"
    assert fov == 200.0
    assert lens == "MKX200"


def test_guess_projection_360():
    """360 sphere detection."""
    from app.services.vr_helper import guess_projection
    proj, stereo, fov, lens = guess_projection("Video_360_TB.mp4")
    assert proj == "equirectangular360"
    assert stereo == "tb"
    assert fov == 360.0


def test_guess_projection_flat():
    """Flat/2D detection."""
    from app.services.vr_helper import guess_projection
    proj, stereo, fov, lens = guess_projection("Movie_FLAT.mp4")
    assert proj == "perspective"
    assert stereo == "mono"
    assert fov == 90.0


def test_guess_projection_deovr_mapping():
    """DeoVR uses different screen type names."""
    from app.services.vr_helper import guess_projection_deovr
    screen, stereo = guess_projection_deovr("Video_180_SBS.mp4")
    assert screen == "dome"
    assert stereo == "sbs"

    screen, stereo = guess_projection_deovr("Video_360_TB.mp4")
    assert screen == "sphere"
    assert stereo == "tb"

    screen, stereo = guess_projection_deovr("Video_MKX200_SBS.mp4")
    assert screen == "mkx200"

    screen, stereo = guess_projection_deovr("Video_FLAT.mp4")
    assert screen == "flat"


# ── ThumbnailService unit tests ──────────────────────────────

def test_thumbnail_service_no_ffmpeg():
    """ThumbnailService.available is False when ffmpeg is missing."""
    from app.services.thumbnail import ThumbnailService
    with patch('shutil.which', return_value=None):
        svc = ThumbnailService(cache_dir=tempfile.mkdtemp())
    assert svc.available is False
    assert svc.generate("test", "http://example.com/video.mp4") is None


def test_thumbnail_service_cache_hit():
    """ThumbnailService returns cached path without running ffmpeg."""
    from app.services.thumbnail import ThumbnailService
    cache_dir = tempfile.mkdtemp()
    # Pre-populate cache
    cached_file = os.path.join(cache_dir, "cached_id.jpg")
    with open(cached_file, 'wb') as f:
        f.write(b'\xff\xd8\xff\xe0JFIF')

    svc = ThumbnailService(cache_dir=cache_dir)
    result = svc.get_cached_path("cached_id")
    assert result == cached_file

    # generate() should also return from cache without running ffmpeg
    with patch('shutil.which', return_value="/usr/bin/ffmpeg"):
        svc2 = ThumbnailService(cache_dir=cache_dir)
    result = svc2.generate("cached_id", "http://example.com/video.mp4")
    assert result == cached_file
