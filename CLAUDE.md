# CLAUDE.md — Debrid Scout Project Index

## Overview

Debrid Scout (v1.1.2) is a Python/Flask web application that integrates Jackett (torrent search aggregator) with Real-Debrid (cached torrent service). It provides a unified interface for searching torrents, checking cache availability, and generating direct download/streaming links. Includes VR playback support for HereSphere and DeoVR headsets.

**Entry point:** `app/main.py` — runs Flask on `0.0.0.0:5000`

## Quick Start

```bash
pip install -r requirements.txt
cp .env.template .env   # then fill in API keys
python app/main.py
```

## Required Environment Variables

| Variable | Description |
|---|---|
| `REAL_DEBRID_API_KEY` | Real-Debrid OAuth bearer token |
| `JACKETT_API_KEY` | Jackett API key |
| `JACKETT_URL` | Jackett base URL (default: `http://localhost:9117`) |

Optional: `FLASK_ENV` (development/production), `DEBUG_MODE` (True/False), `SECRET_KEY`.

## Architecture

```
Flask Routes (app/routes/) → Service Layer (app/services/) → External APIs
```

**Core search pipeline:**
1. `JackettSearchService.search()` — query Jackett Torznab API, parse XML, extract infohashes
2. `RDCachedLinkService.search_and_check_cache()` — check Real-Debrid instant availability
3. `RDDownloadLinkService.search_and_get_links()` — add magnets, select video files, unrestrict links

Streaming variant uses SSE (Server-Sent Events) via `search_and_get_links_stream()`.

## Complete Route Map

| Method | Path | Blueprint | Handler | Description |
|---|---|---|---|---|
| GET/POST | `/` | search | `index()` | Search page (GET) or execute search (POST) |
| POST | `/stream` | search | `stream_search()` | SSE streaming search (JSON body: query, limit) |
| POST | `/cancel` | search | `cancel_search()` | Cancel active streaming search by ID |
| GET | `/account/account` | account | `account_info()` | Account info page (data injected via context processor) |
| GET | `/torrent/rd_manager` | torrent | `rd_manager()` | RD Manager page with paginated torrent list |
| DELETE | `/torrent/delete_torrent/<id>` | torrent | `delete_torrent()` | Delete single torrent from RD |
| POST | `/torrent/delete_torrents` | torrent | `delete_torrents()` | Bulk-delete multiple torrents |
| POST | `/torrent/unrestrict_link` | torrent | `unrestrict_link()` | Unrestrict an RD link to get direct download URL |
| GET | `/torrent/torrents/<id>` | torrent | `get_torrent_details()` | Fetch file details for a specific torrent |
| POST | `/torrent/launch_vlc` | torrent | `launch_vlc()` | Launch VLC.exe locally with video URL |
| GET/POST | `/heresphere` | heresphere | `library_index()` | HereSphere library (HTML for browsers, JSON for API) |
| POST | `/heresphere/scan` | heresphere | `scan()` | Bulk metadata for all videos (avoids N individual requests) |
| GET/POST | `/heresphere/<id>` | heresphere | `video_detail()` | HereSphere video detail with playable sources |
| GET | `/heresphere/thumb/<id>` | heresphere | `thumbnail()` | Serve cached video thumbnail (JPEG) |
| GET | `/heresphere/preview/<id>` | heresphere | `preview()` | Serve cached animated preview clip (MP4) |
| POST | `/heresphere/event/<id>` | heresphere | `event()` | Receive playback events (play/pause/close + position) |
| POST | `/heresphere/launch_heresphere` | heresphere | `launch_heresphere()` | Launch HereSphere.exe locally |
| GET/POST | `/deovr` | deovr | `library_index()` | DeoVR library listing (JSON) |
| GET/POST | `/deovr/<id>` | deovr | `video_detail()` | DeoVR video detail with playable sources |
| POST | `/deovr/launch_heresphere` | deovr | `launch_heresphere()` | Launch HereSphere.exe from DeoVR context |
| GET | `/about` | info | `about()` | About page |
| GET | `/contact` | info | `contact()` | Contact page |

## Service Layer API

### `RealDebridService` (`app/services/real_debrid.py`)
- `get_account_info()` → Dict — fetch RD user/account data
- `add_magnet(magnet_link)` → str (torrent_id) — add magnet to RD
- `select_files(torrent_id, files='all')` → bool — select files for download
- `get_torrent_info(torrent_id)` → Dict — detailed torrent info (files, links, status)
- `unrestrict_link(link)` → str (direct URL) — unrestrict a download link
- `get_all_torrents()` → List[Dict] — paginated fetch of all user torrents
- Rate-limited: 0.2s delay between API calls

### `JackettSearchService` (`app/services/jackett_search.py`)
- `search(query, limit=10)` → (results, elapsed_seconds)
- Uses `cloudscraper` for Cloudflare bypass, retries up to 5 times
- Resolves infohashes from: magnet URIs → torznab XML attribute → .torrent file download
- Parses torznab XML with `xml.etree.ElementTree`

### `RDCachedLinkService` (`app/services/rd_cached_link.py`)
- `search_and_check_cache(query, limit=10)` → (results, self_elapsed, jackett_elapsed)
- Deduplicates by infohash, checks RD instant availability API

### `RDDownloadLinkService` (`app/services/rd_download_link.py`)
- `search_and_get_links(query, limit=10)` → Dict with `data` and `timers`
- `search_and_get_links_stream(query, limit=10, cancel_event=None)` → generator of SSE events
- Full pipeline: search → cache check → deduplicate against existing RD torrents → add magnet → select video files → unrestrict links
- Auto-cleanup: deletes stale/failed torrents that don't reach "downloaded" status

### `FileHelper` (`app/services/file_helper.py`)
- `is_video_file(filename)` → bool — checks against `video_extensions.json`
- `format_file_size(bytes)` → str — human-readable size (e.g., "4.50 GB")
- `simplify_filename(name)` → str — replaces dots with spaces, preserves extension
- `load_video_extensions()` / `load_category_mapping()` — JSON loaders

## Project Structure

```
app/
├── __init__.py              # App factory, blueprint registration, CSRF, caching
├── main.py                  # Entry point (creates app, runs on 0.0.0.0:5000)
├── config.py                # Config/DevelopmentConfig/ProductionConfig classes
├── routes/
│   ├── __init__.py          # Empty
│   ├── search.py            # GET/POST /, POST /stream, POST /cancel
│   ├── torrent.py           # /torrent/* — RD manager, delete, unrestrict, VLC launch
│   ├── account.py           # GET /account/account
│   ├── info.py              # GET /about, GET /contact
│   ├── heresphere.py        # /heresphere/* — HereSphere native VR API + HTML browser view
│   └── deovr.py             # /deovr/* — DeoVR-compatible VR API
├── services/
│   ├── __init__.py          # Empty
│   ├── real_debrid.py       # RealDebridService — RD API wrapper
│   ├── jackett_search.py    # JackettSearchService — Torznab search + XML parsing
│   ├── rd_cached_link.py    # RDCachedLinkService — cache availability checking
│   ├── rd_download_link.py  # RDDownloadLinkService — full download orchestration pipeline
│   └── file_helper.py       # FileHelper — video extensions, file sizes, category mapping
├── static/
│   ├── css/styles.css       # Main stylesheet (dark theme)
│   ├── js/scripts.js        # Frontend JS (SSE handling, VLC/HereSphere launch, RD Manager UI)
│   ├── category_mapping.json # Torznab category ID → name mapping
│   ├── category_icons.json  # Category → icon mapping for UI
│   ├── video_extensions.json # List of recognized video file extensions
│   ├── logo.png, logo-1.png, logo-bg.png  # Branding assets
│   ├── favicon-32x32.png, apple-touch-icon.png  # Favicons
│   └── sample_search_result.png  # Screenshot for README
└── templates/
    ├── base.html            # Base layout with navbar, CSS/JS includes
    ├── index.html           # Search page with results display
    ├── rd_manager.html      # RD torrent manager with file browser
    ├── account_info.html    # Account info display
    ├── heresphere.html      # HereSphere browser view for VR library
    ├── navbar.html          # Navigation bar partial
    ├── about.html           # About page
    ├── contact.html         # Contact page
    └── partials/
        └── search_results.html  # Search results partial (reused by SSE)

tests/
├── conftest.py              # Fixtures: app, client, runner, mocked_responses
├── test_main.py             # Route tests (index, RD manager, about, contact, search, delete, VLC, unrestrict, torrent details)
├── test_search.py           # Search functionality tests (currently empty or minimal)
└── test_services.py         # Service unit tests (RealDebridService, JackettSearchService)

Root files:
├── .env.template            # Environment variable template
├── .gitignore               # Standard Python/Node ignores
├── .gitattributes           # Git LFS / line ending config
├── .dockerignore            # Docker build exclusions
├── Dockerfile               # Container build (gunicorn on port 5000)
├── requirements.txt         # Python dependencies (13 packages)
├── package.json             # Node config (ESLint, Prettier, Commitizen, lint-staged)
├── eslint.config.mjs        # ESLint flat config for JS files
├── CLAUDE.md                # This file — project index for AI assistants
├── README.md                # User-facing documentation
├── CHANGELOG.md             # Version history (Conventional Commits)
├── ROADMAP.md               # Feature roadmap with completion status
├── LICENSE                  # MIT License
├── project_index.md         # Legacy project index (superseded by CLAUDE.md)
└── project_files.txt        # Legacy file listing
```

## Key Technical Details

- **Flask factory pattern** in `app/__init__.py` with blueprint registration
- **CSRF protection** via Flask-WTF (`CSRFProtect`); all API blueprints (torrent, heresphere, deovr, search) are exempt
- **Account info caching** — 5-minute TTL via module-level `_account_cache` dict, loaded in `before_request` hook into Flask `g`, injected into all templates via `context_processor`
- **Cloudflare bypass** — `cloudscraper` used in Jackett search for protected indexers (5 retries with 2s delay)
- **Rate limiting** — 0.2s delay between Real-Debrid API calls (`_rate_limit()`) to prevent throttling
- **Torrent file parsing** — `bencodepy` decodes .torrent files, SHA1-hashes the `info` dict to extract infohashes
- **Infohash resolution** — three-tier: magnet URI regex → torznab XML attribute → .torrent download+parse
- **Duplicate prevention** — fetches existing RD torrents, builds hash→ID lookup to reuse instead of re-adding magnets
- **Stale cache cleanup** — auto-deletes newly-added torrents that fail to reach "downloaded" status (dead statuses: error, magnet_error, virus, dead)
- **VR projection detection** — filename-based pattern matching for projection type (equirectangular, fisheye, perspective) and stereo mode (SBS, TB, mono), with FOV and lens detection (MKX200, MKX220, RF52)
- **HereSphere native API** — structured tags, time-based library sections (Recent/This Month/Older), `HereSphere-JSON-Version: 1` header
- **DeoVR API** — simplified format with `screenType`/`stereoMode` fields, `encodings` array
- **SSE streaming** — search results streamed via `text/event-stream` with cancellation support (threading.Event)
- **Rotating logs** — `logs/app.log`, 10KB max, 10 backup files
- **Docker support** — `Dockerfile` with gunicorn, `.dockerignore` for clean builds

## Running Tests

```bash
pytest tests/
```

Tests use `pytest-mock` and `responses` to mock external HTTP calls. CSRF is disabled in test config.
Test fixtures in `conftest.py` reset the account cache between tests and provide `app`, `client`, `runner`, and `mocked_responses`.

## Development Conventions

- **Commits:** Conventional Commits via Commitizen (feat, fix, refactor, docs, etc.)
- **Linting:** ESLint + Prettier for JS; Husky + lint-staged for pre-commit hooks
- **Versioning:** standard-version for semantic versioning
- **Branching:** `main` is the primary branch

## Dependencies

Key Python packages (see `requirements.txt`):
- Flask 3.1.0, Flask-Caching, Flask-WTF
- requests, cloudscraper, bencodepy
- python-dotenv, gunicorn

Dev/test packages:
- pytest, pytest-mock, responses
