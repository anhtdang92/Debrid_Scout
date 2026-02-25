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

## Architecture

```
Flask Routes (app/routes/) → Service Layer (app/services/) → External APIs
```

**Core search pipeline:**
1. `JackettSearchService.search()` — query Jackett Torznab API, parse XML, extract infohashes
2. `RDCachedLinkService.search_and_check_cache()` — check Real-Debrid instant availability
3. `RDDownloadLinkService.search_and_get_links()` — add magnets, select video files, unrestrict links

Streaming variant uses SSE (Server-Sent Events) via `search_and_get_links_stream()`.

## Project Structure

```
app/
├── __init__.py              # App factory, blueprint registration, CSRF, caching
├── main.py                  # Entry point
├── config.py                # Dev/Production config classes
├── routes/
│   ├── search.py            # GET/POST /, POST /stream, POST /cancel
│   ├── torrent.py           # /torrent/* — RD manager, delete, unrestrict, VLC launch
│   ├── account.py           # GET /account
│   ├── info.py              # GET /about, GET /contact
│   ├── heresphere.py        # /heresphere/* — HereSphere native VR API
│   └── deovr.py             # /deovr/* — DeoVR-compatible VR API
├── services/
│   ├── real_debrid.py       # RealDebridService — RD API wrapper (add magnet, unrestrict, etc.)
│   ├── jackett_search.py    # JackettSearchService — Torznab search + XML parsing
│   ├── rd_cached_link.py    # RDCachedLinkService — cache availability checking
│   ├── rd_download_link.py  # RDDownloadLinkService — full download orchestration pipeline
│   └── file_helper.py       # FileHelper — video extensions, file sizes, category mapping
├── static/
│   ├── css/styles.css
│   ├── js/scripts.js
│   ├── category_mapping.json
│   ├── category_icons.json
│   └── video_extensions.json
└── templates/
    ├── base.html, index.html, rd_manager.html, account_info.html
    ├── heresphere.html, navbar.html, about.html, contact.html
    └── partials/search_results.html
tests/
├── conftest.py              # Fixtures, test app config
├── test_main.py             # Route tests
├── test_search.py           # Search functionality tests
└── test_services.py         # Service layer unit tests
scripts/                     # Legacy/deprecated subprocess scripts (unused)
```

## Key Technical Details

- **Flask factory pattern** in `app/__init__.py` with blueprint registration
- **CSRF protection** via Flask-WTF; JSON API endpoints are exempt
- **Account info caching** — 5-minute TTL via Flask-Caching, injected via context processor
- **Cloudflare bypass** — `cloudscraper` used in Jackett search for protected indexers
- **Rate limiting** — 0.2s delay between Real-Debrid API calls to prevent throttling
- **Torrent file parsing** — `bencodepy` decodes .torrent files to extract infohashes
- **VR detection** — filename-based detection of projection (180/360/fisheye) and stereo mode (SBS/TB)
- **Rotating logs** — `logs/app.log`, 10KB max, 10 backup files

## Running Tests

```bash
pytest tests/
```

Tests use `pytest-mock` and `responses` to mock external HTTP calls. CSRF is disabled in test config.

## Development Conventions

- **Commits:** Conventional Commits via Commitizen (feat, fix, refactor, docs, etc.)
- **Linting:** ESLint + Prettier for JS; Husky + lint-staged for pre-commit hooks
- **Versioning:** standard-version for semantic versioning
- **Branching:** `main` is the primary branch

## Dependencies

Key Python packages (see `requirements.txt`):
- Flask 3.1.0, Flask-Caching, Flask-WTF
- requests, cloudscraper, bencodepy, lxml
- python-dotenv, gunicorn

Dev/test packages:
- pytest, pytest-mock, responses
