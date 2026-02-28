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

### Optional / Tunable Variables

| Variable | Default | Description |
|---|---|---|
| `FLASK_ENV` | `development` | `development` or `production` |
| `DEBUG_MODE` | `False` | Enable debug logging |
| `SECRET_KEY` | random | Required in production; random in dev |
| `HERESPHERE_AUTH_TOKEN` | (none) | Optional bearer token for VR API auth |
| `ACCOUNT_CACHE_TTL` | `300` | Seconds to cache RD account info |
| `RD_RATE_LIMIT_DELAY` | `0.2` | Seconds between RD API calls |
| `RD_API_TIMEOUT` | `15` | Timeout for RD API requests (seconds) |
| `JACKETT_TIMEOUT` | `20` | Timeout for Jackett requests (seconds) |
| `JACKETT_RETRY_COUNT` | `5` | Max retries for Jackett queries |
| `LOG_MAX_BYTES` | `10240` | Max log file size before rotation |
| `THUMBNAIL_MAX_AGE_DAYS` | `7` | TTL for cached thumbnails/previews |

## Architecture

```
Flask Routes (app/routes/) → Service Layer (app/services/) → External APIs
                                    ↓
                        Shared caching (rd_cache — torrent info, all-torrents, batch unrestrict)
                                    ↓
                        Shared helpers (vr_helper, file_helper)
                                    ↓
                        App extensions (UserDataStore, ThumbnailService)
```

**Core search pipeline:**
1. `JackettSearchService.search()` — query Jackett Torznab API, parse XML, extract infohashes
2. `RDCachedLinkService.search_and_check_cache()` — check Real-Debrid instant availability
3. `RDDownloadLinkService._process_torrent()` — add magnet, select video files, unrestrict links

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
| POST | `/deovr/event/<id>` | deovr | `event()` | Receive playback events (play/pause/close + position) |
| POST | `/deovr/launch_heresphere` | deovr | `launch_heresphere()` | Launch HereSphere.exe from DeoVR context |
| GET | `/health` | info | `health()` | Health check endpoint for Docker/orchestrators |
| GET | `/about` | info | `about()` | About page |
| GET | `/contact` | info | `contact()` | Contact page |

## Service Layer API

### `RealDebridService` (`app/services/real_debrid.py` — 215 lines)
- `get_account_info()` → Dict — fetch RD user/account data
- `add_magnet(magnet_link)` → str (torrent_id) — add magnet to RD
- `select_files(torrent_id, files='all')` → bool — select files for download
- `get_torrent_info(torrent_id)` → Dict — detailed torrent info (files, links, status)
- `unrestrict_link(link)` → str (direct URL) — unrestrict a download link
- `get_all_torrents()` → List[Dict] — paginated fetch of all user torrents
- `delete_torrent(torrent_id)` → None — delete torrent from RD
- Uses `requests.Session()` for connection pooling; rate-limited with configurable delay

### `JackettSearchService` (`app/services/jackett_search.py` — 321 lines)
- `search(query, limit=10)` → (results, elapsed_seconds)
- Uses `cloudscraper` for Cloudflare bypass, retries up to 5 times
- Resolves infohashes from: magnet URIs → torznab XML attribute → .torrent file download
- Parses torznab XML with `xml.etree.ElementTree`
- Graceful fallback if `bencodepy` is not installed (skips .torrent parsing)

### `RDCachedLinkService` (`app/services/rd_cached_link.py` — 159 lines)
- `search_and_check_cache(query, limit=10)` → (results, self_elapsed, jackett_elapsed)
- Deduplicates by infohash, checks RD instant availability API
- Uses `requests.Session()` for connection pooling

### `RDCacheService` (`app/services/rd_cache.py` — 92 lines)
- `get_torrent_info_cached(service, torrent_id)` → dict — TTL-cached torrent info (5 min)
- `get_all_torrents_cached(service)` → list — TTL-cached all-torrents list (60s)
- `batch_unrestrict(service, links, max_workers=3)` → List[str] — concurrent link unrestriction via ThreadPoolExecutor
- `clear_caches()` → None — reset all caches (used by test fixtures)
- Thread-safe with `threading.Lock` for each cache

### `RDDownloadLinkService` (`app/services/rd_download_link.py` — 407 lines)
- `search_and_get_links(query, limit=10)` → Dict with `data` and `timers`
- `search_and_get_links_stream(query, limit=10, cancel_event=None)` → generator of SSE events
- `_process_torrent(cached_link, existing_hashes, processed_infohashes)` → Optional[Dict] — shared per-torrent pipeline
- `_fetch_existing_hashes()` → Dict[str, str] — hash→ID lookup for deduplication
- Auto-cleanup: deletes stale/failed torrents that don't reach "downloaded" status

### `ThumbnailService` (`app/services/thumbnail.py` — 315 lines)
- `get_thumbnail(torrent_id)` → bytes — generate/cache video thumbnail via ffmpeg
- `get_preview(torrent_id)` → bytes — generate/cache animated preview clip
- `get_duration(torrent_id)` → int — video duration in milliseconds
- `cleanup(max_age_days=7)` → int — remove expired cache files
- Singleton via `app.extensions['thumb_service']`

### `UserDataStore` (`app/services/user_data.py` — 187 lines)
- `is_favorite(torrent_id)` → bool
- `get_rating(torrent_id)` → float
- `get_playback_time(torrent_id)` → float (seconds)
- `increment_play_count(torrent_id)` → None
- `process_heresphere_update(torrent_id, body)` → None — write-back favorites/ratings
- Persists to `data/user_data.json` with thread-safe locking and atomic writes (`tempfile` + `os.replace`)

### `VR Helper` (`app/services/vr_helper.py` — 188 lines)
- `guess_projection(filename)` → (projection, stereo, fov, lens) — VR format detection
- `guess_projection_deovr(filename)` → (screenType, stereoMode) — DeoVR format
- `build_restricted_map(selected_files, links)` → Dict — shared file-ID→link mapping
- `get_video_files(selected_files)` → List — filter to video files only
- `is_video(filename)` / `is_subtitle(filename)` — extension checks
- `launch_heresphere_exe(video_url)` → (bool, error_msg)

### `FileHelper` (`app/services/file_helper.py` — 72 lines)
- `is_video_file(filename)` → bool — checks against `video_extensions.json`
- `format_file_size(bytes)` → str — human-readable size (e.g., "4.50 GB")
- `simplify_filename(name)` → str — replaces dots with spaces, preserves extension
- `load_video_extensions()` / `load_category_mapping()` — class-level cached JSON loaders

## Project Structure

```
app/
├── __init__.py              # App factory, blueprint registration, CSRF, caching, extensions
├── main.py                  # Entry point (creates app, runs on 0.0.0.0:5000)
├── config.py                # Config/DevelopmentConfig/ProductionConfig + safe env var parsing (72 lines)
├── routes/
│   ├── __init__.py          # Empty
│   ├── search.py            # GET/POST /, POST /stream, POST /cancel (163 lines)
│   ├── torrent.py           # /torrent/* — RD manager, delete, unrestrict, VLC launch (208 lines)
│   ├── account.py           # GET /account/account
│   ├── info.py              # GET /health, GET /about, GET /contact (35 lines)
│   ├── heresphere.py        # /heresphere/* — HereSphere native VR API + HTML browser (683 lines)
│   └── deovr.py             # /deovr/* — DeoVR-compatible VR API (288 lines)
├── services/
│   ├── __init__.py          # Empty
│   ├── real_debrid.py       # RealDebridService — RD API wrapper with Session pooling (215 lines)
│   ├── jackett_search.py    # JackettSearchService — Torznab search + XML parsing (321 lines)
│   ├── rd_cached_link.py    # RDCachedLinkService — cache availability + Session pooling (159 lines)
│   ├── rd_cache.py          # Shared caching — torrent info, all-torrents, batch unrestrict (92 lines)
│   ├── rd_download_link.py  # RDDownloadLinkService — full download pipeline (407 lines)
│   ├── file_helper.py       # FileHelper — video extensions, file sizes, category mapping (72 lines)
│   ├── vr_helper.py         # Shared VR utilities — projection, restricted maps, launch (188 lines)
│   ├── thumbnail.py         # ThumbnailService — ffmpeg thumbnails + preview clips (315 lines)
│   └── user_data.py         # UserDataStore — favorites, ratings, playback tracking (187 lines)
├── static/
│   ├── css/styles.css       # Main stylesheet — dark theme, skeletons, responsive (1506 lines)
│   ├── js/scripts.js        # Frontend JS — SSE, modals, event delegation, VR launch (1254 lines)
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
    ├── heresphere.html      # HereSphere browser view with skeleton loading
    ├── navbar.html          # Navigation bar partial
    ├── about.html           # About page
    ├── contact.html         # Contact page
    └── partials/
        └── search_results.html  # Search results partial (reused by SSE)

tests/                       # 117 tests total
├── conftest.py              # Fixtures: app, client, runner, mocked_responses + cache reset (53 lines)
├── test_main.py             # Route + integration tests: 31 tests (449 lines)
├── test_search.py           # Search + SSE streaming tests: 13 tests (230 lines)
├── test_services.py         # Service unit tests: 25 tests (318 lines)
└── test_vr_routes.py        # VR route + service tests: 48 tests (1021 lines)

docs/
├── codebase-improvements.md # 37-item improvement plan (all complete ✅)
└── heresphere-improvements.md # HereSphere-specific improvement plan

Root files:
├── .env.template            # Environment variable template
├── .gitignore               # Standard Python/Node ignores
├── .gitattributes           # Git LFS / line ending config
├── .dockerignore            # Docker build exclusions
├── .github/dependabot.yml   # Dependabot config for pip, npm, GitHub Actions, Docker
├── .github/workflows/ci.yml # GitHub Actions CI (pytest + coverage + mypy + ESLint, Python 3.11/3.12)
├── docker-compose.yml       # Docker Compose with named volumes
├── Dockerfile               # Container build (gunicorn, non-root user, port 5000)
├── requirements.txt         # Python dependencies (13 packages, pinned upper bounds)
├── package.json             # Node config (ESLint, Prettier, Commitizen, lint-staged)
├── eslint.config.mjs        # ESLint flat config with @eslint/js recommended rules
├── mypy.ini                 # Python type checking config (gradual adoption)
├── CLAUDE.md                # This file — project index for AI assistants
├── README.md                # User-facing documentation
├── CHANGELOG.md             # Version history (Conventional Commits)
├── ROADMAP.md               # Feature roadmap with completion status
└── LICENSE                  # MIT License
```

## Key Technical Details

- **Flask factory pattern** in `app/__init__.py` with blueprint registration
- **CSRF protection** via Flask-WTF (`CSRFProtect`); all API blueprints (torrent, heresphere, deovr, search) are exempt (JSON APIs use Authorization headers)
- **Account info caching** — configurable TTL via `ACCOUNT_CACHE_TTL`, thread-safe with `threading.Lock`, loaded in `before_request` hook into Flask `g`, injected into all templates via `context_processor`
- **Safe config parsing** — `_safe_int()` / `_safe_float()` helpers catch malformed env vars with logged warnings and fallback defaults
- **Security headers** — `Content-Security-Policy`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: SAMEORIGIN` set on all responses via `after_request`
- **Connection pooling** — `requests.Session()` in both `RealDebridService` and `RDCachedLinkService` for HTTP connection reuse
- **Shared caching layer** — `rd_cache.py` provides TTL-cached torrent info (5 min) and all-torrents list (60s), shared across HereSphere, DeoVR, and torrent routes
- **Batch link unrestriction** — `batch_unrestrict()` uses `ThreadPoolExecutor` (3 workers) for concurrent RD link unrestriction in VR routes
- **Cloudflare bypass** — `cloudscraper` used in Jackett search for protected indexers (configurable retries with 2s delay); sessions closed in `finally` blocks
- **Rate limiting** — configurable delay between Real-Debrid API calls (`_rate_limit()`) with Retry-After header support for 429 responses
- **Torrent file parsing** — `bencodepy` (optional) decodes .torrent files, SHA1-hashes the `info` dict to extract infohashes; graceful fallback if not installed
- **Infohash resolution** — three-tier: magnet URI regex → torznab XML attribute → .torrent download+parse
- **Duplicate prevention** — `_fetch_existing_hashes()` builds hash→ID lookup to reuse existing RD torrents
- **Stale cache cleanup** — auto-deletes newly-added torrents that fail to reach "downloaded" status (dead statuses: error, magnet_error, virus, dead)
- **VR projection detection** — filename-based pattern matching for projection type (equirectangular, fisheye, perspective) and stereo mode (SBS, TB, mono), with FOV and lens detection (MKX200, MKX220, RF52)
- **HereSphere native API** — structured tags, time-based library sections (Recent/This Month/Older), `HereSphere-JSON-Version: 1` header, write-back for favorites/ratings
- **DeoVR API** — simplified format with `screenType`/`stereoMode` fields, `encodings` array
- **Playback tracking** — `UserDataStore` persists favorites, ratings, playback position, play count to `data/user_data.json` with thread-safe `threading.Lock()` and atomic file writes (`tempfile.mkstemp` + `os.replace`)
- **Input validation** — bulk delete endpoint validates array length (max 500) and torrent ID format (alphanumeric only)
- **Video thumbnails** — `ThumbnailService` generates JPEG thumbnails and MP4 preview clips via ffmpeg, with TTL-based cleanup
- **SSE streaming** — search results streamed via `text/event-stream` with cancellation support (`threading.Event`), thread-safe active search tracking, `requestAnimationFrame`-based backpressure on the client side
- **Shared VR helpers** — `build_restricted_map()` and `get_video_files()` eliminate duplication across heresphere, deovr, and torrent routes
- **Skeleton loading** — CSS shimmer animation placeholders for HereSphere library while content loads
- **Responsive design** — three breakpoints (768px, 600px, 480px) for mobile/tablet support
- **WCAG AA contrast** — `--text-muted` color meets 4.5:1 contrast ratio
- **Rotating logs** — `logs/app.log`, configurable max size via `LOG_MAX_BYTES`, 10 backup files
- **DOM batching** — `DocumentFragment` used for pagination and sort re-ordering to minimize reflows
- **Concurrent torrent processing** — `ThreadPoolExecutor` in `RDDownloadLinkService` with per-future timeouts (120s) and app context propagation
- **Docker support** — non-root user, gunicorn, `.dockerignore` for clean builds, `docker-compose.yml` with named volumes
- **Health check** — `/health` endpoint returns JSON with service status and key-set checks for Docker `HEALTHCHECK`

## Running Tests

```bash
pytest tests/                # 117 tests
pytest tests/ -v             # verbose output
pytest tests/ --cov=app --cov-report=term-missing --cov-fail-under=70  # with coverage
mypy app/ --config-file mypy.ini  # type checking (gradual)
npx eslint app/static/js/    # JS linting
```

Tests use `pytest-mock` and `responses` to mock external HTTP calls. CSRF is disabled in test config.
Test fixtures in `conftest.py` reset both the account cache and `rd_cache` caches between tests, and provide `app`, `client`, `runner`, and `mocked_responses`.

## Development Conventions

- **Commits:** Conventional Commits via Commitizen (feat, fix, refactor, docs, etc.)
- **Linting:** ESLint (recommended rules + no-var, prefer-const, eqeqeq) + Prettier for JS; Husky + lint-staged for pre-commit hooks
- **Type checking:** mypy configured for gradual adoption (`mypy.ini`)
- **Versioning:** standard-version for semantic versioning
- **Branching:** `main` is the primary branch
- **CI:** GitHub Actions runs pytest with coverage (70% threshold), mypy, and ESLint on push/PR (Python 3.11/3.12 matrix)

## Dependencies

Key Python packages (see `requirements.txt`):
- Flask 3.1.0, Flask-Caching, Flask-WTF
- requests, cloudscraper, bencodepy (optional)
- python-dotenv, gunicorn

Dev/test packages:
- pytest, pytest-mock, responses, mypy
