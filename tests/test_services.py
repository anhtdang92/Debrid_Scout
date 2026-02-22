import pytest
import responses
from app.services.real_debrid import RealDebridService, RealDebridError
from app.services.jackett_search import JackettSearchService, JackettSearchError

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
