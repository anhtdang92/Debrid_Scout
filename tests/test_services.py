import pytest
import responses
from app.services.real_debrid import RealDebridService, RealDebridError
from app.services.jackett_search import JackettSearchService, JackettSearchError
from app.services.file_helper import FileHelper


# ── FileHelper tests ──────────────────────────────────────────

class TestFileHelperFormatFileSize:
    """Tests for FileHelper.format_file_size()."""

    def test_zero_bytes(self):
        assert FileHelper.format_file_size(0) == "0.00 B"

    def test_bytes(self):
        assert FileHelper.format_file_size(512) == "512.00 B"

    def test_kilobytes(self):
        assert FileHelper.format_file_size(1024) == "1.00 KB"

    def test_megabytes(self):
        assert FileHelper.format_file_size(1048576) == "1.00 MB"

    def test_gigabytes(self):
        assert FileHelper.format_file_size(4831838208) == "4.50 GB"

    def test_terabytes(self):
        assert FileHelper.format_file_size(1099511627776) == "1.00 TB"

    def test_negative_returns_zero(self):
        assert FileHelper.format_file_size(-100) == "0.00 B"

    def test_non_numeric_returns_zero(self):
        assert FileHelper.format_file_size("abc") == "0.00 B"

    def test_none_returns_zero(self):
        assert FileHelper.format_file_size(None) == "0.00 B"


class TestFileHelperSimplifyFilename:
    """Tests for FileHelper.simplify_filename()."""

    def test_dots_replaced_with_spaces(self):
        assert FileHelper.simplify_filename("Test.Movie.2024.mkv") == "Test Movie 2024.mkv"

    def test_numeric_extension_preserved(self):
        # rsplit('.', 1) treats the last segment as an extension
        assert FileHelper.simplify_filename("Test.Movie.2024") == "Test Movie.2024"

    def test_no_dots(self):
        assert FileHelper.simplify_filename("TestMovie") == "TestMovie"

    def test_single_extension_only(self):
        assert FileHelper.simplify_filename("movie.mp4") == "movie.mp4"

    def test_preserves_last_extension(self):
        assert FileHelper.simplify_filename("My.Great.Video.File.avi") == "My Great Video File.avi"


class TestFileHelperIsVideoFile:
    """Tests for FileHelper.is_video_file() — requires app context for static file loading."""

    def test_video_file_recognized(self, app):
        with app.app_context():
            assert FileHelper.is_video_file("movie.mkv") is True

    def test_non_video_file_rejected(self, app):
        with app.app_context():
            assert FileHelper.is_video_file("readme.txt") is False

    def test_mp4_recognized(self, app):
        with app.app_context():
            assert FileHelper.is_video_file("clip.mp4") is True

    def test_case_insensitive(self, app):
        with app.app_context():
            assert FileHelper.is_video_file("MOVIE.MKV") is True


class TestFileHelperLoadVideoExtensions:
    """Tests for FileHelper.load_video_extensions()."""

    def test_returns_list(self, app):
        with app.app_context():
            extensions = FileHelper.load_video_extensions()
            assert isinstance(extensions, list)
            assert len(extensions) > 0
            assert ".mkv" in extensions or ".mp4" in extensions

    def test_load_category_mapping(self, app):
        with app.app_context():
            mapping = FileHelper.load_category_mapping()
            assert isinstance(mapping, dict)
            assert len(mapping) > 0


# ── RealDebridService tests ───────────────────────────────────

def test_real_debrid_get_account_info(app, mocked_responses):
    with app.app_context():
        service = RealDebridService(api_key="test_rd_key")

        # Test successful response
        mocked_responses.get(
            "https://api.real-debrid.com/rest/1.0/user",
            json={"id": 12345, "username": "testuser", "expiration": "2030-01-01T00:00:00.000Z"},
            status=200
        )
        info = service.get_account_info()
        assert info["username"] == "testuser"
        assert info["formatted_expiration"] == "January 01, 2030, 00:00:00 UTC"

        # Test failure response
        mocked_responses.replace(
            responses.GET,
            "https://api.real-debrid.com/rest/1.0/user",
            json={"error": "bad_token"},
            status=401
        )
        with pytest.raises(RealDebridError):
            service.get_account_info()

def test_real_debrid_add_magnet(app, mocked_responses):
    with app.app_context():
        service = RealDebridService(api_key="test_rd_key")

        mocked_responses.post(
            "https://api.real-debrid.com/rest/1.0/torrents/addMagnet",
            json={"id": "XYZ123"},
            status=201
        )

        torrent_id = service.add_magnet("magnet:?xt=urn:btih:fake")
        assert torrent_id == "XYZ123"


def test_real_debrid_delete_torrent(app, mocked_responses):
    """Test RealDebridService.delete_torrent() success and failure."""
    with app.app_context():
        service = RealDebridService(api_key="test_rd_key")

        mocked_responses.delete(
            "https://api.real-debrid.com/rest/1.0/torrents/delete/abc123",
            status=204,
        )
        assert service.delete_torrent("abc123") is True

        # Test failure
        mocked_responses.delete(
            "https://api.real-debrid.com/rest/1.0/torrents/delete/bad_id",
            status=404,
            json={"error": "not found"},
        )
        with pytest.raises(RealDebridError):
            service.delete_torrent("bad_id")


def test_real_debrid_unrestrict_link(app, mocked_responses):
    """Test RealDebridService.unrestrict_link()."""
    with app.app_context():
        service = RealDebridService(api_key="test_rd_key")

        mocked_responses.post(
            "https://api.real-debrid.com/rest/1.0/unrestrict/link",
            json={"download": "https://download.rd.com/d/xyz/movie.mkv"},
            status=200,
        )
        url = service.unrestrict_link("https://example.com/restricted")
        assert url == "https://download.rd.com/d/xyz/movie.mkv"


def test_real_debrid_get_torrent_info(app, mocked_responses):
    """Test RealDebridService.get_torrent_info()."""
    with app.app_context():
        service = RealDebridService(api_key="test_rd_key")

        mocked_responses.get(
            "https://api.real-debrid.com/rest/1.0/torrents/info/tid123",
            json={
                "id": "tid123",
                "filename": "Great.Movie.mkv",
                "status": "downloaded",
                "files": [{"id": 1, "path": "/Great.Movie.mkv", "bytes": 5000000000, "selected": 1}],
                "links": ["https://rd.link/1"],
            },
            status=200,
        )
        info = service.get_torrent_info("tid123")
        assert info["filename"] == "Great.Movie.mkv"
        assert len(info["files"]) == 1


def test_real_debrid_get_all_torrents(app, mocked_responses):
    """Test RealDebridService.get_all_torrents() with pagination."""
    with app.app_context():
        service = RealDebridService(api_key="test_rd_key")

        mocked_responses.get(
            "https://api.real-debrid.com/rest/1.0/torrents?page=1",
            json=[{"id": "t1"}, {"id": "t2"}],
            status=200,
        )
        mocked_responses.get(
            "https://api.real-debrid.com/rest/1.0/torrents?page=2",
            json=[],
            status=200,
        )
        torrents = service.get_all_torrents()
        assert len(torrents) == 2
        assert torrents[0]["id"] == "t1"


def test_real_debrid_missing_api_key(app):
    """Test that missing API key raises RealDebridError."""
    with app.app_context():
        app.config['REAL_DEBRID_API_KEY'] = None
        with pytest.raises(RealDebridError, match="missing"):
            RealDebridService(api_key=None)


def test_real_debrid_select_files(app, mocked_responses):
    """Test RealDebridService.select_files()."""
    with app.app_context():
        service = RealDebridService(api_key="test_rd_key")

        mocked_responses.post(
            "https://api.real-debrid.com/rest/1.0/torrents/selectFiles/tid123",
            status=204,
        )
        assert service.select_files("tid123") is True


# ── RDCachedLinkService tests ─────────────────────────────────

def test_rd_cached_link_check_instant_availability(app, mocked_responses):
    """Test the internal _check_instant_availability method."""
    with app.app_context():
        from app.services.rd_cached_link import RDCachedLinkService
        service = RDCachedLinkService(api_key="test_rd_key")

        infohash = "abcdef1234567890abcdef1234567890abcdef12"
        mocked_responses.get(
            f"https://api.real-debrid.com/rest/1.0/torrents/instantAvailability/{infohash}",
            json={
                infohash: {
                    "rd": [
                        {"1": {"filename": "movie.mkv", "filesize": 5000000000}}
                    ]
                }
            },
            status=200,
        )

        result = service._check_instant_availability(infohash, "5000000000")
        assert result["is_fully_cached"] is True
        assert result["infohash"] == infohash


def test_rd_cached_link_not_cached(app, mocked_responses):
    """Test _check_instant_availability when torrent is NOT cached."""
    with app.app_context():
        from app.services.rd_cached_link import RDCachedLinkService
        service = RDCachedLinkService(api_key="test_rd_key")

        infohash = "abcdef1234567890abcdef1234567890abcdef12"
        mocked_responses.get(
            f"https://api.real-debrid.com/rest/1.0/torrents/instantAvailability/{infohash}",
            json={},
            status=200,
        )

        result = service._check_instant_availability(infohash, "5000000000")
        assert result["is_fully_cached"] is False


# ── JackettSearchService tests ────────────────────────────────

def test_jackett_search(app, mocked_responses):
    with app.app_context():
        service = JackettSearchService(api_key="test_jackett", base_url="http://localhost:9117")

        jackett_xml = b'''<?xml version="1.0" encoding="UTF-8"?>
        <rss version="1.0" xmlns:torznab="http://torznab.com/schemas/2015/feed">
        <channel>
            <item>
                <title>Test Movie 1080p</title>
                <link>magnet:?xt=urn:btih:1234567890abcdef1234567890abcdef12345678</link>
                <size>1048576000</size>
                <torznab:attr name="seeders" value="100" />
                <torznab:attr name="peers" value="20" />
                <torznab:attr name="category" value="2000" />
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

        results, elapsed = service.search("test query", limit=1)
        assert len(results) == 1
        assert results[0]["title"] == "Test Movie 1080p"
        assert results[0]["infohash"] == "1234567890abcdef1234567890abcdef12345678"

        # Test empty response (no results)
        mocked_responses.replace(
            responses.GET,
            "http://localhost:9117/api/v2.0/indexers/all/results/torznab/api",
            body=b"<?xml version=\"1.0\" encoding=\"UTF-8\"?><rss version=\"1.0\"><channel></channel></rss>",
            status=200,
            content_type="application/xml"
        )
        empty_results, _ = service.search("test query", limit=1)
        assert len(empty_results) == 0
