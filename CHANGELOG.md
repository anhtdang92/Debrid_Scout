# Changelog

All notable changes to this project will be documented in this file. See [standard-version](https://github.com/conventional-changelog/standard-version) for commit guidelines.

### [1.1.2](https://github.com/yourusername/debrid-scout/compare/v1.1.1...v1.1.2) (2024-11-06)

### Features

* SSE streaming search with real-time progress events and cancellation support
* HereSphere native VR API with library browsing, structured tags, and time-based sections
* DeoVR-compatible API with projection detection and stereo mode mapping
* `/heresphere/scan` bulk metadata endpoint for fast library population
* XBVR-style write-back for favorites, ratings, and playback tracking
* Video thumbnails and animated preview clips via ffmpeg
* Resume playback support with persistent position tracking
* HereSphere browser HTML view with card grid, sort controls, and favorites
* VLC and HereSphere PC launcher endpoints
* Search result caching with sessionStorage across page navigation
* Dark theme frontend UI overhaul
* Docker support with gunicorn and health check
* GitHub Actions CI/CD with pytest and ESLint

### Bug Fixes

* Fix innerHTML XSS vulnerability with torrent file names
* Fix auth bypass in HereSphere `before_request` for POST endpoints
* Stop logging authorization tokens in request headers
* Add request timeouts to all HTTP calls (configurable via env vars)
* Validate JACKETT_API_KEY at startup with warning log
* Enforce SECRET_KEY in production mode
* Docker: run as non-root user, stop copying .env into image layer
* Verify torrent status after file selection, auto-cleanup stale/dead torrents
* Distinguish error/dead/virus torrent statuses in RD Manager
* Standardize error response format across all routes

### Improvements

* Extract duplicate VR utilities into shared `vr_helper.py` module
* Extract `build_restricted_map()` and `get_video_files()` shared helpers
* Refactor search pipeline — extract `_process_torrent()` to eliminate duplication
* Use `requests.Session()` for HTTP connection pooling in RealDebridService
* Add rate-limit backoff for HTTP 429 responses with Retry-After header
* Close cloudscraper sessions properly after use
* Add thread safety with locks for shared mutable state
* Make hardcoded values configurable via environment variables
* Add ARIA accessibility attributes to modals and dynamic content
* Add Cache-Control headers for thumbnail responses
* Add TTL-based cleanup for cached thumbnails and previews
* Improve error logging with stack traces via `logger.exception()`
* Pin dependency upper bounds in requirements.txt
* ESLint configuration with recommended rules and Prettier integration
* Improve color contrast for WCAG AA compliance

### [1.1.1](https://github.com/yourusername/debrid-scout/compare/v1.1.0...v1.1.1) (2024-11-06)

### Bug Fixes

* Remove 111 unused dependencies from requirements.txt
* Fix download button sizing in RD Manager
* Fix long-running timer display issues

## [1.1.0](https://github.com/yourusername/debrid-scout/compare/v1.0.3...v1.1.0) (2024-11-06)

### Features

* Add HereSphere video player launcher
* Add search timer component
* Add partials for template reuse
* Move from OS env to config-based environment handling

### Bug Fixes

* Fix scripts and component interactions
* Fix index timer and page formatting

### 1.0.3 (2024-11-05)

Initial public release with core search and Real-Debrid integration.

### 1.0.2 (2024-11-05)

### 1.0.1 (2024-11-05)
